"""Check real examples, deliberate graph faults, coverage and optional full-run evidence."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from rdflib import Graph, Literal, RDF, URIRef, XSD

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/validation'))
from validate import EDU, SH, SHAPE, PROV, DCT, evaluate, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample-only', action='store_true', help='CI mode: no ignored raw data or full report required.')
    args = parser.parse_args()
    fixtures = ROOT / 'evaluation/fixtures/shacl'
    schema_path = ROOT / 'ontology/education.rdfs.ttl'
    shapes_path = ROOT / 'shapes/oulad-shapes.ttl'
    shapes = Graph().parse(shapes_path)
    schema = Graph().parse(schema_path)
    sample = Graph().parse(fixtures / 'valid.ttl')
    baseline = sample + schema
    tests = []

    def check(name, condition, detail=''):
        if not condition:
            raise AssertionError(name + ': ' + str(detail))
        tests.append({'check': name, 'passed': True, 'detail': detail})
        print('PASS:', name, flush=True)

    def run(graph, shape_graph=shapes):
        return evaluate(graph, shape_graph, check_shapes=False)[0]

    def has(result, severity, focus=None, component=None):
        return any(r['severity'] == severity and (focus is None or r['focus_node'] == str(focus))
                   and (component is None or r['constraint'] == component) for r in result['results'])

    base = evaluate(baseline, shapes)[0]  # includes SHACL meta-validation once
    check('Real sample: 0 violations, 3 visible warnings, gate passes',
          base['gate_passed'] and not base['conforms_shacl'] and base['severity_counts'] == {'Violation': 0, 'Warning': 3, 'Info': 0})
    check('All 12 assessment subtypes are targeted without RDFS materialization',
          next(r['focus_nodes'] for r in base['focus_counts'] if r['shape'] == str(SHAPE.AssessmentShape)) == 12)
    check('Only the optional activity target is empty in the real sample',
          [r['shape'] for r in base['focus_counts'] if not r['focus_nodes']] == [str(SHAPE.InteractionShape)])
    enrollment = URIRef('https://example.org/oulad/id/enrollment/AAA/2013J/100893')
    record = sorted(sample.subjects(EDU.recordForEnrollment, enrollment), key=str)[0]
    assessment = sample.value(record, EDU.forAssessment)
    student = sample.value(enrollment, EDU.hasStudent)
    offering = sample.value(enrollment, EDU.inOffering)

    broken_facts = Graph().parse(fixtures / 'broken.ttl')
    broken = run(broken_facts + schema)
    check('Broken fixture changes exactly one Student link',
          len(sample - broken_facts) == 1 and len(broken_facts - sample) == 1)
    check('Broken Student reference blocks the gate at the expected focus node',
          not broken['gate_passed'] and broken['severity_counts']['Violation'] == 1 and
          has(broken, 'Violation', enrollment, 'ClassConstraintComponent'))

    graph = Graph() + baseline
    graph.remove((enrollment, EDU.hasStudent, None))
    result = run(graph)
    check('Missing Student link is a SHACL minCount violation (OWL open-world contrast)',
          not result['gate_passed'] and has(result, 'Violation', enrollment, 'MinCountConstraintComponent'))
    graph = Graph() + baseline
    other = next(s for s in sample.subjects(RDF.type, EDU.Student) if s != student)
    graph.add((enrollment, EDU.hasStudent, other))
    check('Two distinct Student IRIs violate maxCount without OWL identity merging',
          has(run(graph), 'Violation', enrollment, 'MaxCountConstraintComponent'))

    for score, valid in [(-1, False), (0, True), (100, True), (101, False)]:
        graph = Graph() + baseline
        graph.set((record, EDU.score, Literal(str(score), datatype=XSD.decimal)))
        result = run(graph)
        check(f'Score boundary {score}: gate {"passes" if valid else "fails"}', result['gate_passed'] == valid)
    graph = Graph() + baseline
    graph.set((offering, EDU.lengthDays, Literal(0)))
    result = run(graph)
    check('Zero offering length fails and its zero value is retained in the report',
          has(result, 'Violation', offering, 'MinExclusiveConstraintComponent') and
          any(r['focus_node'] == str(offering) and r['value'] == '0' for r in result['results']))
    graph = Graph() + baseline
    graph.set((record, EDU.score, Literal('75', datatype=XSD.string)))
    check('Numeric-looking string is not an xsd:decimal score', has(run(graph), 'Violation', record, 'DatatypeConstraintComponent'))
    graph = Graph() + baseline
    graph.remove((record, EDU.score, None))
    result = run(graph)
    check('Removing a known score adds a warning, preserves the record and passes the gate',
          result['gate_passed'] and result['severity_counts']['Warning'] == 4 and has(result, 'Warning', record))
    graph = Graph() + baseline
    graph.set((record, EDU.isBanked, Literal('1', datatype=XSD.integer)))
    check('Integer banked flag is rejected after the mapping to Boolean', has(run(graph), 'Violation', record, 'DatatypeConstraintComponent'))
    graph = Graph() + baseline
    other_assessment = next(a for a in sample.subjects(EDU.assessmentInOffering, None)
                            if sample.value(a, EDU.assessmentInOffering) != offering and (a, RDF.type, EDU.Exam) in sample)
    graph.set((record, EDU.forAssessment, other_assessment))
    check('A valid Assessment from the wrong offering is caught by SHACL-SPARQL',
          has(run(graph), 'Violation', record, 'SPARQLConstraintComponent'))
    graph = Graph() + baseline
    duplicate = URIRef('https://example.org/oulad/teaching#duplicate-enrollment')
    for _, predicate, obj in sample.triples((enrollment, None, None)):
        graph.add((duplicate, predicate, obj))
    check('Duplicate contextual enrollment key is caught across distinct nodes',
          has(run(graph), 'Violation', enrollment, 'SPARQLConstraintComponent'))
    graph = Graph() + baseline
    duplicate = URIRef('https://example.org/oulad/teaching#duplicate-record')
    for _, predicate, obj in sample.triples((record, None, None)):
        graph.add((duplicate, predicate, obj))
    check('Duplicate assessment-record key is caught across distinct nodes',
          has(run(graph), 'Violation', record, 'SPARQLConstraintComponent'))
    graph = Graph() + baseline
    graph.set((enrollment, EDU.finalResult, Literal('Completed')))
    check('Unexpected outcome is a vocabulary violation', has(run(graph), 'Violation', enrollment, 'InConstraintComponent'))
    graph = Graph() + baseline
    graph.set((enrollment, EDU.previousAttempts, Literal(-1)))
    check('Negative previous-attempt count is rejected', has(run(graph), 'Violation', enrollment, 'MinInclusiveConstraintComponent'))
    graph = Graph() + baseline
    graph.set((enrollment, EDU.registrationDay, Literal(-1000)))
    graph.set((record, EDU.submissionDay, Literal(-5)))
    check('Negative day offsets remain permitted', run(graph)['gate_passed'])
    graph = Graph() + baseline
    graph.set((enrollment, EDU.unregistrationDay, Literal(10)))
    result = run(graph)
    check('Pass with a withdrawal date is a review warning, not a silent repair',
          result['gate_passed'] and has(result, 'Warning', enrollment, 'SPARQLConstraintComponent'))
    graph = Graph() + baseline
    graph.set((enrollment, EDU.registrationDay, Literal(20)))
    graph.set((enrollment, EDU.unregistrationDay, Literal(10)))
    check('Reversed dates produce a core property-pair warning',
          has(run(graph), 'Warning', enrollment, 'LessThanOrEqualsConstraintComponent'))
    graph = Graph() + baseline
    graph.add((student, EDU.finalResult, Literal('Pass')))
    check('Outcome on Student is forbidden by maxCount zero', has(run(graph), 'Violation', student, 'MaxCountConstraintComponent'))
    graph = Graph() + baseline
    graph.remove((assessment, RDF.type, None))
    graph.add((assessment, RDF.type, EDU.Assessment))
    check('Assessment without a supported subtype is rejected', has(run(graph), 'Violation', assessment, 'XoneConstraintComponent'))
    graph = Graph() + baseline
    graph.remove((record, RDF.type, EDU.AssessmentRecord))
    check('A record missing its type is still selected through its properties', has(run(graph), 'Violation', record, 'ClassConstraintComponent'))

    activity = URIRef('https://example.org/oulad/teaching#activity-test')
    resource = next(sample.subjects(EDU.resourceInOffering, offering))
    graph = Graph() + baseline
    for predicate, value in [(RDF.type, EDU.DailyInteraction), (EDU.interactionForEnrollment, enrollment),
                             (EDU.withResource, resource), (EDU.interactionDay, Literal(-5)), (EDU.clickCount, Literal(0))]:
        graph.add((activity, predicate, value))
    check('Optional activity validates when present, including zero clicks', run(graph)['gate_passed'])
    graph.set((activity, EDU.clickCount, Literal(-1)))
    check('Negative click count is rejected', has(run(graph), 'Violation', activity, 'MinInclusiveConstraintComponent'))
    graph.set((activity, EDU.clickCount, Literal(0)))
    other_resource = next(r for r in sample.subjects(EDU.resourceInOffering, None) if sample.value(r, EDU.resourceInOffering) != offering)
    graph.set((activity, EDU.withResource, other_resource))
    check('Activity cannot link to a resource in another offering', has(run(graph), 'Violation', activity, 'SPARQLConstraintComponent'))

    trap = Graph()
    trap.add((SHAPE.Typo, RDF.type, SH.NodeShape))
    trap.add((SHAPE.Typo, SH.targetClass, EDU.NonexistentClass))
    trap.add((SHAPE.Typo, SH.nodeKind, SH.IRI))
    result = run(baseline, trap)
    check('Zero-focus trap: SHACL conforms True, project gate fails',
          result['conforms_shacl'] and not result['gate_passed'] and result['empty_required_targets'] == [str(SHAPE.Typo)])
    check('An empty data graph cannot pass the coverage gate', not run(schema)['gate_passed'])

    if not args.sample_only:
        full_path = ROOT / 'outputs/shacl/full/summary.json'
        full = json.loads(full_path.read_text(encoding='utf-8'))
        check('Saved full run matches current data, schema, shapes and validator',
              all(sha256(item['path']) == item['sha256'] for item in full['inputs']) and
              sha256(ROOT / 'src/validation/validate.py') == full['validator_sha256'])
        source = Graph().parse(ROOT / 'data/processed/oulad.ttl')
        check('Every real sample triple is an unchanged source triple', all(t in source for t in sample))
        def csv_rows(name):
            with (ROOT / 'data/interim' / (name + '.csv')).open(newline='', encoding='utf-8-sig') as stream:
                return list(csv.DictReader(stream))
        records = csv_rows('studentAssessment')
        assessments = csv_rows('assessments')
        students = csv_rows('studentInfo')
        courses = csv_rows('courses')
        resources = csv_rows('vle')
        expected_focus = {'StudentShape': len({r['id_student'] for r in students}),
                          'EnrollmentShape': len(students), 'OfferingShape': len(courses),
                          'ModuleShape': len({r['code_module'] for r in courses}),
                          'AssessmentShape': len(assessments), 'RecordShape': len(records),
                          'ResourceShape': len(resources)}
        observed_focus = {r['shape'].split('#')[-1]: r['focus_nodes'] for r in full['focus_counts']}
        check('Full structural focus counts match all seven CSV-derived entity counts',
              all(observed_focus[name] == count for name, count in expected_focus.items()), expected_focus)
        expected = {('https://example.org/oulad/id/assessment-record/' + r['id_student'] + '/' + r['id_assessment'], str(EDU.score))
                    for r in records if r['score'] in ('', '?')}
        expected |= {('https://example.org/oulad/id/assessment/' + r['id_assessment'], str(EDU.deadlineDay))
                     for r in assessments if r['date'] in ('', '?')}
        actual = {(r['focus_node'], r['path']) for r in full['results'] if r['severity'] == 'Warning'}
        check('Full warning identities match the missing score/deadline CSV rows', actual == expected,
              {'expected_warning_identities': len(expected), 'observed_warning_identities': len(actual)})
        check('Full graph gate passes with no violations and visible warnings',
              full['gate_passed'] and full['severity_counts']['Violation'] == 0 and not full['conforms_shacl'])
        provenance = Graph().parse(ROOT / 'outputs/shacl/full/provenance.ttl')
        run_iri = URIRef('https://example.org/oulad/run/shacl/' + full['run_id'])
        used = set(provenance.objects(run_iri, PROV.used))
        expected_inputs = {URIRef('urn:sha256:' + i['sha256']) for i in full['inputs']}
        generated = set(provenance.subjects(PROV.wasGeneratedBy, run_iri))
        expected_outputs = {URIRef('urn:sha256:' + sha256(ROOT / 'outputs/shacl/full' / name))
                            for name in ('report.ttl', 'report.txt', 'results.csv', 'summary.json', 'report.html')}
        check('PROV-O input and output fingerprints match the actual validation run',
              used == expected_inputs and generated == expected_outputs)
    out = ROOT / 'outputs/shacl'
    out.mkdir(parents=True, exist_ok=True)
    result = {'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'sample_only': args.sample_only,
              'passed': True, 'checks': tests,
              'source_sha256': {str(p.relative_to(ROOT).as_posix()): sha256(p) for p in
                  [shapes_path, schema_path, fixtures / 'valid.ttl', fixtures / 'broken.ttl',
                   ROOT / 'src/validation/validate.py', Path(__file__)]}}
    if not args.sample_only:
        result['source_sha256']['outputs/shacl/full/summary.json'] = sha256(full_path)
    name = 'verification-sample.json' if args.sample_only else 'verification.json'
    (out / name).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'{len(tests)}/{len(tests)} checks passed. Evidence: {out / name}')


if __name__ == '__main__':
    main()
