"""Independent source reconciliation and adversarial leakage checks."""
import numpy as np,pandas as pd
from rdflib import Graph,URIRef,RDF,Literal,XSD
from common import ROOT,write_json
from build_graph import EDU,LEARN,FEATURES,extract
def verify(g,rows,assessments,records,early,out,protocol):
    checks=[]
    def check(name,ok):
        checks.append({'check':name,'passed':bool(ok)})
        if not ok:raise AssertionError(name)
    base=ROOT/'data/interim';info=pd.read_csv(base/'studentInfo.csv');reg=pd.read_csv(base/'studentRegistration.csv');ass=pd.read_csv(base/'assessments.csv');sa=pd.read_csv(base/'studentAssessment.csv')
    original=info.merge(reg,on=['code_module','code_presentation','id_student'],validate='one_to_one')
    original['enrollment']='https://example.org/oulad/id/enrollment/'+original.code_module+'/'+original.code_presentation+'/'+original.id_student.astype(str)
    original=original.set_index('enrollment').loc[rows.enrollment]
    check('All 748 RDF enrollment labels match independent CSV outcomes',len(rows)==748 and list(original.final_result)==list(rows.outcome))
    check('Original successful and unsuccessful counts are 531 and 217',sum(rows.label==0)==531 and sum(rows.label)==217)
    eligible=(original.date_registration<=protocol['cutoff_day'])&(original.date_unregistration.isna()|(original.date_unregistration>protocol['cutoff_day']))
    check('Day-60 eligibility matches registration CSVs',np.array_equal(eligible.to_numpy(),rows.eligible.to_numpy()))
    check('Previous-attempt and registration features match CSVs',np.array_equal(original.num_of_prev_attempts.to_numpy(),rows.previous_attempts.to_numpy()) and np.allclose(original.date_registration,rows.registration_day,equal_nan=True))
    joined=sa.merge(ass,on='id_assessment',validate='many_to_one')
    joined['enrollment']='https://example.org/oulad/id/enrollment/'+joined.code_module+'/'+joined.code_presentation+'/'+joined.id_student.astype(str)
    before=joined[(joined.is_banked==0)&joined.date_submitted.notna()&(joined.date_submitted<=protocol['cutoff_day'])]
    counts=before.groupby('enrollment').size().reindex(rows.enrollment,fill_value=0)
    late=before[before.date.notna()&(before.date_submitted>before.date)].groupby('enrollment').size().reindex(rows.enrollment,fill_value=0)
    last=before.groupby('enrollment').date_submitted.max().reindex(rows.enrollment)
    check('Early submission counts match independent CSV joins',np.array_equal(counts.to_numpy(),rows.early_submission_count.to_numpy()))
    check('Early late counts and last days match independent CSV joins',np.array_equal(late.to_numpy(),rows.early_late_count.to_numpy()) and np.allclose(last,rows.last_submission_day,equal_nan=True))
    check('Link target contains exactly 3107 unique nonbanked pairs',len(records[records.banked==False])==3107 and not records[records.banked==False].duplicated(['enrollment','assessment']).any())
    check('Every classifier edge is nonbanked and on or before cutoff',bool((early.banked==False).all() and (early.day<=protocol['cutoff_day']).all()))
    lg=Graph().parse(out/'learning-input.ttl')
    forbidden={EDU.finalResult,EDU.unregistrationDay,EDU.score}
    bad_types={EDU.SuccessfulEnrollment,EDU.WithdrawnEnrollment,EDU.LowScoreAssessmentRecord,EDU.EnrollmentWithLowScore}
    check('Learning RDF excludes labels, scores, withdrawal dates and inferred outcome types',not any(p in forbidden or (p==RDF.type and o in bad_types) for s,p,o in lg))
    check('Every graph feature and edge uses the explicit allowlist',all(p in {RDF.type,EDU.deadlineDay,EDU.weightPercent,LEARN.submittedByCutoff}|{LEARN[n] for n in FEATURES} for s,p,o in lg))
    # Change labels and all scores; model inputs must stay identical.
    changed=Graph()+g
    for e in g.subjects(RDF.type,EDU.Enrollment):changed.set((e,EDU.finalResult,Literal('Fail')))
    for r in g.subjects(RDF.type,EDU.AssessmentRecord):changed.set((r,EDU.score,Literal(100,datatype=XSD.decimal)))
    changed_rows,_,_,changed_edges=extract(changed,protocol['cutoff_day'])
    check('Changing final labels and grades cannot change classifier features',rows[FEATURES].equals(changed_rows[FEATURES]) and early.equals(changed_edges))
    # Remove every post-cutoff record from a copy; classifier input must be unchanged.
    future=Graph()+g
    for rec in records[records.day>protocol['cutoff_day']].itertuples():future.remove((URIRef(rec.record),None,None))
    future_rows,_,_,future_edges=extract(future,protocol['cutoff_day'])
    check('Removing later assessment records cannot change classifier inputs',rows[FEATURES].equals(future_rows[FEATURES]) and early.reset_index(drop=True).equals(future_edges.reset_index(drop=True)))
    first=rows[rows.eligible].iloc[0];a=assessments[assessments.offering==first.offering].iloc[0].iri
    test_record=URIRef('https://example.org/oulad/teaching/cutoff-boundary')
    synthetic=Graph()+g
    for p,o in [(RDF.type,EDU.AssessmentRecord),(EDU.recordForEnrollment,URIRef(first.enrollment)),(EDU.forAssessment,URIRef(a)),(EDU.isBanked,Literal(False)),(EDU.submissionDay,Literal(60,datatype=XSD.integer))]:synthetic.add((test_record,p,o))
    at,_,_,_=extract(synthetic,60)
    check('Day 60 is included at the cutoff boundary',at.loc[at.enrollment==first.enrollment,'early_submission_count'].iloc[0]==first.early_submission_count+1)
    synthetic.set((test_record,EDU.submissionDay,Literal(61,datatype=XSD.integer)));after,_,_,_=extract(synthetic,60)
    check('Day 61 is excluded at the cutoff boundary',rows[FEATURES].equals(after[FEATURES]))
    synthetic.set((test_record,EDU.submissionDay,Literal(60,datatype=XSD.integer)));synthetic.set((test_record,EDU.isBanked,Literal(True)));banked,_,_,_=extract(synthetic,60)
    check('Banked records cannot masquerade as new early submissions',rows[FEATURES].equals(banked[FEATURES]))
    write_json(out/'input-checks.json',checks);return checks
