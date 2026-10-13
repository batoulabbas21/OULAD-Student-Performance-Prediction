"""Check OWL behavior and reconcile full-data inferences with the selected CSV tables."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys

import pandas as pd
from rdflib import BNode, Graph, Literal, Namespace, OWL, RDF, RDFS, URIRef, XSD

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/graph'))
from owl_reasoner import WORK, merged_graph, reason

EDU = Namespace('https://example.org/oulad/schema#')
DEMO = Namespace('https://example.org/oulad/teaching#')
DATA = 'https://example.org/oulad/id/'
checks = []


def check(name, passed, detail):
    checks.append({'check': name, 'passed': bool(passed), 'detail': detail})
    print(('PASS: ' if passed else 'FAIL: ') + name, flush=True)


def members(result, cls):
    return {iri for iri, types in (result.get('types') or {}).items() if str(cls) in types}


def extra(base, triples):
    graph = Graph()
    graph += base
    for triple in triples:
        graph.add(triple)
    return graph


def main():
    full = json.loads((ROOT / 'outputs/ontology/reasoned-full.json').read_text(encoding='utf-8'))
    for relative, digest in full['source_sha256'].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit('Reasoner report is stale. Prepare the workspace and rerun owl_reasoner.py --full-data.')
    check('Full ontology and data are consistent and coherent', full['consistent'] and not full['unsatisfiable_classes'],
          'No unsatisfiable named class in the clean ontology plus all loaded OULAD facts.')
    base = merged_graph(WORK / 'education.owl.ttl')
    info = pd.read_csv(ROOT / 'data/interim/studentInfo.csv')
    records = pd.read_csv(ROOT / 'data/interim/studentAssessment.csv')
    assessments = pd.read_csv(ROOT / 'data/interim/assessments.csv')

    def enrollment(row):
        return f'{DATA}enrollment/{row.code_module}/{row.code_presentation}/{int(row.id_student)}'

    def record(row):
        return f'{DATA}assessment-record/{int(row.id_student)}/{int(row.id_assessment)}'

    def iris(frame, function):
        return {function(row) for row in frame.itertuples()}

    low = records[records.score < 40]
    low_context = low.merge(assessments[['id_assessment', 'code_module', 'code_presentation']], on='id_assessment', validate='many_to_one')
    expected = {
        'SuccessfulEnrollment': iris(info[info.final_result.isin(['Pass', 'Distinction'])], enrollment),
        'WithdrawnEnrollment': iris(info[info.final_result == 'Withdrawn'], enrollment),
        'LowScoreAssessmentRecord': iris(low, record),
        'BankedAssessmentRecord': iris(records[records.is_banked == 1], record),
        'NonBankedAssessmentRecord': iris(records[records.is_banked == 0], record),
        'EnrollmentWithLowScore': iris(low_context, enrollment),
    }
    counts = []
    for name, wanted in expected.items():
        actual = members(full, EDU[name])
        check(name + ' matches CSV-derived identities', actual == wanted,
              {'expected': len(wanted), 'inferred': len(actual),
               'missing': sorted(wanted - actual)[:5], 'unexpected': sorted(actual - wanted)[:5]})
        counts.append({'class': name, 'csv_expected': len(wanted), 'owl_inferred': len(actual)})
    foaf_students = {DATA + 'student/' + str(int(i)) for i in info.id_student.unique()}
    check('Published Person class is inferred for the observed students',
          members(full, URIRef('http://xmlns.com/foaf/0.1/Person')) == foaf_students,
          {'expected_people': len(foaf_students)})

    sample_graph = Graph().parse(WORK / 'sample-enrollments.ttl')
    source_graph = Graph().parse(ROOT / 'data/processed/oulad.ttl')
    retained = {t for t in sample_graph if str(t[0]).startswith(DATA) and t[1] != RDFS.label and t[2] != OWL.NamedIndividual}
    outcomes = {str(value) for value in sample_graph.objects(None, EDU.finalResult)}
    check('Teaching sample preserves real facts and all four outcomes',
          retained.issubset(set(source_graph)) and outcomes == {'Pass', 'Distinction', 'Fail', 'Withdrawn'},
          {'source_triples': len(retained), 'outcomes': sorted(outcomes)})

    broken = reason(merged_graph(WORK / 'domain-error.ttl'))
    impossible = {str(DEMO.StudentUsingEnrollmentProperty), str(DEMO.StudentWithExactlyOneStudent)}
    check('Wrong property domain makes two empty classes unsatisfiable',
          broken['consistent'] and set(broken['unsatisfiable_classes']) == impossible,
          broken['unsatisfiable_classes'])
    inconsistent = reason(merged_graph(WORK / 'domain-inconsistent.ttl'))
    check('Instantiating an impossible class makes the ontology inconsistent', not inconsistent['consistent'],
          'Synthetic individuals only; the real source graph is unchanged.')

    missing_graph = extra(base, [(DEMO.missingLinks, RDF.type, EDU.Enrollment)])
    missing = reason(missing_graph)
    check('Exactly one allows an unstated filler under the open world assumption', missing['consistent'],
          'No hasStudent or inOffering triple is asserted for the synthetic enrollment.')

    two_links = extra(base, [(DEMO.twoLinks, RDF.type, EDU.Enrollment),
                            (DEMO.twoLinks, EDU.hasStudent, DEMO.studentA),
                            (DEMO.twoLinks, EDU.hasStudent, DEMO.studentB)])
    alias = reason(two_links)
    check('Two student names need not denote different people', alias['consistent'],
          'The maximum cardinality permits equality; OWL has no unique-name assumption.')
    two_links.add((DEMO.studentA, OWL.differentFrom, DEMO.studentB))
    distinct = reason(two_links)
    check('Two explicitly different students violate exactly one', not distinct['consistent'],
          'The same example becomes inconsistent after differentFrom is asserted.')

    boundary = extra(base, [(DEMO.unknownScore, RDF.type, EDU.AssessmentRecord)])
    for name, value in [('score39', '39'), ('score40', '40'), ('score41', '41')]:
        boundary.add((DEMO[name], RDF.type, EDU.AssessmentRecord))
        boundary.add((DEMO[name], EDU.score, Literal(value, datatype=XSD.decimal)))
    boundary_result = reason(boundary)
    check('Low-score boundary is strictly below 40; unknown remains unclassified',
          boundary_result['consistent'] and members(boundary_result, EDU.LowScoreAssessmentRecord) == {str(DEMO.score39)},
          'Known 39 is inferred low; 40, 41 and an unknown score are not inferred low.')

    primitive = merged_graph(WORK / 'sample-enrollments.ttl')
    for expression in list(primitive.objects(EDU.SuccessfulEnrollment, OWL.equivalentClass)):
        primitive.remove((EDU.SuccessfulEnrollment, OWL.equivalentClass, expression))
        primitive.add((EDU.SuccessfulEnrollment, RDFS.subClassOf, expression))
    primitive_result = reason(primitive)
    check('SubClassOf alone does not classify successful enrollments from their outcomes',
          primitive_result['consistent'] and not members(primitive_result, EDU.SuccessfulEnrollment),
          'Only the SuccessfulEnrollment equivalence is changed, in memory.')

    only = BNode()
    some = BNode()
    some_only = extra(base, [
        (DEMO.OnlyLow, RDF.type, OWL.Class), (DEMO.OnlyLow, RDFS.subClassOf, EDU.Enrollment),
        (DEMO.OnlyLow, RDFS.subClassOf, only), (only, RDF.type, OWL.Restriction),
        (only, OWL.onProperty, EDU.hasAssessmentRecord), (only, OWL.allValuesFrom, EDU.LowScoreAssessmentRecord),
        (DEMO.SomeAndOnlyLow, RDF.type, OWL.Class), (DEMO.SomeAndOnlyLow, RDFS.subClassOf, DEMO.OnlyLow),
        (DEMO.SomeAndOnlyLow, RDFS.subClassOf, some), (some, RDF.type, OWL.Restriction),
        (some, OWL.onProperty, EDU.hasAssessmentRecord), (some, OWL.someValuesFrom, EDU.LowScoreAssessmentRecord),
        (DEMO.onlyCase, RDF.type, DEMO.OnlyLow), (DEMO.someOnlyCase, RDF.type, DEMO.SomeAndOnlyLow)])
    some_result = reason(some_only)
    check('Only does not assert existence; some does', some_result['consistent'] and
          members(some_result, EDU.EnrollmentWithLowScore) == {str(DEMO.someOnlyCase)},
          'Only-low records alone does not entail any record. Some-and-only entails a low-score record exists.')

    out = ROOT / 'outputs/ontology'
    summary = {'verified_at_utc': datetime.now(timezone.utc).isoformat(),
               'passed': all(c['passed'] for c in checks), 'checks': checks, 'inferred_counts': counts,
               'source_sha256': full['source_sha256']}
    (out / 'verification.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    pd.DataFrame(counts).to_csv(out / 'inferred-class-counts.csv', index=False)
    print(f'{sum(c["passed"] for c in checks)}/{len(checks)} ontology checks passed.')
    if not summary['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
