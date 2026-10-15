"""Build an unchanged real-data sample, a one-link fault, and the naive draft shapes."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from validate import sha256, SH, SHAPE

ROOT = Path(__file__).resolve().parents[2]
EDU = Namespace('https://example.org/oulad/schema#')
BASE = 'https://example.org/oulad/id/'
CASES = [('2013J', '100893'), ('2013J', '134143'), ('2013J', '1401935'),
         ('2013J', '106247'), ('2013J', '106577'), ('2014J', '129955'), ('2013J', '260355')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data/processed/oulad.ttl')
    parser.add_argument('--shapes', type=Path, default=ROOT / 'shapes/oulad-shapes.ttl')
    parser.add_argument('--fixtures', type=Path, default=ROOT / 'evaluation/fixtures/shacl')
    parser.add_argument('--examples', type=Path, default=ROOT / 'outputs/shacl/examples')
    args = parser.parse_args()
    source = Graph().parse(args.data)
    enrollments = {URIRef(BASE + f'enrollment/AAA/{presentation}/{student}') for presentation, student in CASES}
    for enrollment in enrollments:
        if (enrollment, RDF.type, EDU.Enrollment) not in source:
            raise ValueError('The example selection requires the documented AAA extract: ' + str(enrollment))
    selected = set(enrollments)
    selected.update(r for e in enrollments for r in source.subjects(EDU.recordForEnrollment, e))
    selected.update(source.subjects(EDU.assessmentInOffering, None))
    for offering in source.subjects(RDF.type, EDU.CourseOffering):
        resources = sorted(source.subjects(EDU.resourceInOffering, offering), key=str)
        if resources:
            selected.add(resources[0])
    sample = Graph()
    for prefix, ns in source.namespaces():
        sample.bind(prefix, ns)
    todo = list(selected)
    seen = set()
    while todo:
        subject = todo.pop()
        if subject in seen:
            continue
        seen.add(subject)
        for triple in source.triples((subject, None, None)):
            sample.add(triple)
            if isinstance(triple[2], URIRef) and str(triple[2]).startswith(BASE):
                todo.append(triple[2])
    assert all(t in source for t in sample), 'Sample must retain only real asserted facts.'
    args.fixtures.mkdir(parents=True, exist_ok=True)
    args.examples.mkdir(parents=True, exist_ok=True)
    sample.serialize(args.fixtures / 'valid.ttl', format='turtle')
    broken = Graph() + sample
    focus = URIRef(BASE + 'enrollment/AAA/2013J/100893')
    old = sample.value(focus, EDU.hasStudent)
    wrong = URIRef('https://example.org/oulad/teaching#untyped-student-typo')
    broken.remove((focus, EDU.hasStudent, old))
    broken.add((focus, EDU.hasStudent, wrong))
    broken.serialize(args.fixtures / 'broken.ttl', format='turtle')
    shapes = Graph().parse(args.shapes)
    # This generated draft changes only the two debated missingness policies.
    for prop in (SHAPE.ScorePresence, SHAPE.DeadlinePresence):
        shapes.set((prop, SH.severity, SH.Violation))
    shapes.serialize(args.examples / 'oulad-shapes-v0.ttl', format='turtle')
    manifest = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_data_sha256': sha256(args.data), 'source_shapes_sha256': sha256(args.shapes),
                'selected_enrollments': sorted(map(str, enrollments)), 'sample_triples': len(sample),
                'sample_individuals': len(set(sample.subjects())),
                'sample_note': 'All triples copied unchanged from asserted RDF; seven enrollments, their records, all assessments, one resource per offering, and linked entities.',
                'broken_change': {'focus': str(focus), 'path': str(EDU.hasStudent),
                                  'removed': str(old), 'added': str(wrong)},
                'files': {name: sha256(args.fixtures / name) for name in ('valid.ttl', 'broken.ttl')}}
    (args.fixtures / 'selection.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Real sample: {len(sample)} triples; broken example changes exactly one Student link.')
    print('Draft shapes:', args.examples / 'oulad-shapes-v0.ttl')


if __name__ == '__main__':
    main()
