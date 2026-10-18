"""Whitelist RDF inputs; keep historical labels outside the learning graph."""
import numpy as np,pandas as pd
from rdflib import Graph,Namespace,RDF,URIRef,Literal,XSD
from common import ROOT,write_json
EDU=Namespace('https://example.org/oulad/schema#')
LEARN=Namespace('https://example.org/oulad/learning#')
FEATURES=['previous_attempts','registration_day','early_submission_count','early_late_count','last_submission_day']
TYPES=[EDU.TutorMarkedAssessment,EDU.ComputerMarkedAssessment,EDU.Exam]
def value(g,s,p,default=None):
    vs=list(g.objects(s,p))
    if len(vs)>1:raise ValueError('Multiple values for '+str(p))
    return vs[0].toPython() if vs else default
def extract(g,cutoff=60):
    assessments={}
    for typ in TYPES:
        for a in sorted(g.subjects(RDF.type,typ),key=str):
            assessments[str(a)]={'iri':str(a),'offering':str(g.value(a,EDU.assessmentInOffering)),
                'type':str(typ).split('#')[-1],'deadline':value(g,a,EDU.deadlineDay,np.nan),'weight':value(g,a,EDU.weightPercent,0)}
    records=[]
    for r in sorted(g.subjects(RDF.type,EDU.AssessmentRecord),key=str):
        records.append({'record':str(r),'enrollment':str(g.value(r,EDU.recordForEnrollment)),
            'assessment':str(g.value(r,EDU.forAssessment)),'day':value(g,r,EDU.submissionDay,np.nan),
            'banked':value(g,r,EDU.isBanked)})
    rec=pd.DataFrame(records);enroll=[]
    for e in sorted(g.subjects(RDF.type,EDU.Enrollment),key=str):
        student=g.value(e,EDU.hasStudent);off=g.value(e,EDU.inOffering)
        reg=value(g,e,EDU.registrationDay,np.nan);unreg=value(g,e,EDU.unregistrationDay,np.nan)
        outcome=value(g,e,EDU.finalResult)
        if outcome not in {'Pass','Distinction','Fail','Withdrawn'}:raise ValueError('Unknown label')
        er=rec[(rec.enrollment==str(e)) & (rec.banked==False) & rec.day.notna() & (rec.day<=cutoff)]
        late=sum(row.day>assessments[row.assessment]['deadline'] for row in er.itertuples() if not pd.isna(assessments[row.assessment]['deadline']))
        enroll.append({'enrollment':str(e),'student':str(student),'presentation':value(g,off,EDU.presentationCode),
            'offering':str(off),'outcome':outcome,'label':int(outcome in {'Fail','Withdrawn'}),
            'eligible':bool(not pd.isna(reg) and reg<=cutoff and (pd.isna(unreg) or unreg>cutoff)),
            'previous_attempts':int(value(g,e,EDU.previousAttempts,0)),'registration_day':reg,
            'early_submission_count':len(er),'early_late_count':late,
            'last_submission_day':float(er.day.max()) if len(er) else np.nan})
    rows=pd.DataFrame(enroll)
    early=rec[(rec.banked==False)&rec.day.notna()&(rec.day<=cutoff)&rec.enrollment.isin(rows.loc[rows.eligible,'enrollment'])].copy()
    return rows,pd.DataFrame(assessments.values()),rec,early
def build(g,out,protocol):
    rows,a,rec,early=extract(g,protocol['cutoff_day'])
    # Graph intentionally has no labels, scores, withdrawal dates, outcomes or future records.
    lg=Graph();lg.bind('learn',LEARN);lg.bind('edu',EDU)
    eligible=rows[rows.eligible]
    for r in eligible.itertuples():
        e=URIRef(r.enrollment);lg.add((e,RDF.type,EDU.Enrollment))
        for name in FEATURES:
            x=getattr(r,name)
            if not pd.isna(x):lg.add((e,LEARN[name],Literal(float(x),datatype=XSD.double)))
    for r in early.itertuples():lg.add((URIRef(r.enrollment),LEARN.submittedByCutoff,URIRef(r.assessment)))
    for r in a[a.iri.isin(early.assessment)].itertuples():
        node=URIRef(r.iri);lg.add((node,RDF.type,EDU[r.type]))
        if not pd.isna(r.deadline):lg.add((node,EDU.deadlineDay,Literal(int(r.deadline),datatype=XSD.integer)))
        lg.add((node,EDU.weightPercent,Literal(float(r.weight),datatype=XSD.double)))
    out.mkdir(parents=True,exist_ok=True);lg.serialize(out/'learning-input.ttl',format='turtle')
    rows.drop(columns=['outcome','label']).to_csv(out/'features-and-cohort.csv',index=False)
    rows[['enrollment','student','presentation','outcome','label','eligible']].to_csv(out/'labels.csv',index=False)
    early.to_csv(out/'early-edges.csv',index=False)
    a.to_csv(out/'assessment-metadata.csv',index=False)
    counts={'all_enrollments':len(rows),'all_students':rows.student.nunique(),'outcomes':rows.outcome.value_counts().to_dict(),
        'successful':int((rows.label==0).sum()),'unsuccessful':int(rows.label.sum()),
        'eligible_day60':int(rows.eligible.sum()),'excluded_day60':int((~rows.eligible).sum()),
        'nonbanked_historical_links':int((rec.banked==False).sum()),'banked_records_excluded':int((rec.banked==True).sum()),
        'eligible_early_edges':len(early),'learning_triples':len(lg),'feature_names':FEATURES,
        'label_policy':'1 = final Fail or Withdrawn; 0 = final Pass or Distinction',
        'availability_assumption':'Registration and submission dates approximate recorded availability; no ingestion/revision log exists. Grades excluded because publication dates are absent.'}
    write_json(out/'cohort.json',counts)
    return rows,a,rec,early,counts
