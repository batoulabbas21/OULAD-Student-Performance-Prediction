"""Session 4 SHACL validation: visible warnings, blocking violations, checked targets.

Run from the project root with the existing M2ENV environment:
    python src/validation/validate.py
    python src/validation/validate.py --data evaluation/fixtures/shacl/valid.ttl --out outputs/shacl/sample

Exit codes: 0 = gate passes; 1 = violations or empty required targets; 2 = execution error.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import html
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time
import uuid

from pyshacl import validate as pyshacl_validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD

ROOT = Path(__file__).resolve().parents[2]
EDU = Namespace('https://example.org/oulad/schema#')
SH = Namespace('http://www.w3.org/ns/shacl#')
SHAPE = Namespace('https://example.org/oulad/shapes#')
PROV = Namespace('http://www.w3.org/ns/prov#')
DCT = Namespace('http://purl.org/dc/terms/')
TARGETS = (SH.targetClass, SH.targetNode, SH.targetSubjectsOf, SH.targetObjectsOf)


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def short(value):
    text = str(value or '')
    for base in ('https://example.org/oulad/id/', str(EDU), str(SHAPE), str(SH)):
        if text.startswith(base):
            return text[len(base):]
    return text


def focus_counts(data, shapes):
    """Count the union of standard explicit targets, with SHACL subclass semantics."""
    active = {s for predicate in TARGETS for s in shapes.subjects(predicate, None)
              if shapes.value(s, SH.deactivated) != Literal(True)}
    result = []
    for shape in sorted(active, key=str):
        nodes = set(shapes.objects(shape, SH.targetNode))
        for cls in shapes.objects(shape, SH.targetClass):
            subclasses = set(data.transitive_subjects(RDFS.subClassOf, cls)) | {cls}
            nodes.update(s for c in subclasses for s in data.subjects(RDF.type, c))
        for predicate in shapes.objects(shape, SH.targetSubjectsOf):
            nodes.update(data.subjects(predicate, None))
        for predicate in shapes.objects(shape, SH.targetObjectsOf):
            nodes.update(data.objects(None, predicate))
        optional = shapes.value(shape, SHAPE.optionalTarget) == Literal(True)
        result.append({'shape': str(shape), 'label': str(shapes.value(shape, RDFS.label) or short(shape)),
                       'focus_nodes': len(nodes), 'optional_target': optional})
    return result


def evaluate(data, shapes, *, check_shapes=True):
    """Pure validation of an in-memory graph; inputs are not repaired or materialized."""
    coverage = focus_counts(data, shapes)
    if not coverage:
        raise ValueError('No active explicit SHACL targets: refusing an empty or deactivated gate.')
    conforms, report, report_text = pyshacl_validate(
        data, shacl_graph=shapes, inference='none', meta_shacl=check_shapes,
        advanced=False, abort_on_first=False, allow_infos=False, allow_warnings=False,
        do_owl_imports=False, inplace=False)
    if not isinstance(report, Graph):
        raise RuntimeError(f'Validator failure: {report}')
    rows = []
    def term(node, predicate):
        value = report.value(node, predicate)
        return '' if value is None else str(value)
    for node in report.subjects(RDF.type, SH.ValidationResult):
        rows.append({
            'severity': short(report.value(node, SH.resultSeverity)),
            'focus_node': term(node, SH.focusNode),
            'path': term(node, SH.resultPath),
            'value': term(node, SH.value),
            'source_shape': term(node, SH.sourceShape),
            'constraint': short(report.value(node, SH.sourceConstraintComponent)),
            'message': ' | '.join(sorted(str(m) for m in report.objects(node, SH.resultMessage))),
        })
    rows.sort(key=lambda r: (r['severity'], r['focus_node'], r['path'], r['constraint']))
    counts = Counter(row['severity'] for row in rows)
    empty = [r['shape'] for r in coverage if r['focus_nodes'] == 0 and not r['optional_target']]
    unexpected = sorted(set(counts) - {'Violation', 'Warning', 'Info'})
    passed = not (counts['Violation'] or empty or unexpected)
    return {'conforms_shacl': bool(conforms), 'gate_passed': passed,
            'severity_counts': {k: counts[k] for k in ('Violation', 'Warning', 'Info')},
            'empty_required_targets': empty, 'unknown_severities': unexpected,
            'focus_counts': coverage, 'results': rows}, report, report_text


def write_provenance(out, summary):
    """Actual validation activity only; no invented timestamps for older CSV conversion."""
    graph = Graph()
    for prefix, ns in [('prov', PROV), ('dcterms', DCT), ('rdfs', RDFS), ('xsd', XSD)]:
        graph.bind(prefix, ns)
    run = URIRef('https://example.org/oulad/run/shacl/' + summary['run_id'])
    program = URIRef('urn:oulad:validator:sha256:' + summary['validator_sha256'])
    # The activity includes report assembly, after the validation timer stops.
    assembled_at = datetime.now(timezone.utc).isoformat()
    graph.add((run, RDF.type, PROV.Activity))
    graph.add((run, RDFS.label, Literal('SHACL validation of the specified OULAD graph')))
    graph.add((run, PROV.startedAtTime, Literal(summary['started_at_utc'], datatype=XSD.dateTime)))
    graph.add((run, PROV.endedAtTime, Literal(assembled_at, datatype=XSD.dateTime)))
    graph.add((program, RDF.type, PROV.SoftwareAgent))
    graph.add((program, RDFS.label, Literal('OULAD validate.py with pySHACL ' + summary['versions']['pyshacl'])))
    graph.add((program, DCT.identifier, Literal('sha256:' + summary['validator_sha256'])))
    graph.add((run, PROV.wasAssociatedWith, program))
    for item in summary['inputs']:
        entity = URIRef('urn:sha256:' + item['sha256'])
        graph.add((entity, RDF.type, PROV.Entity))
        graph.add((entity, RDFS.label, Literal(item['role'] + ': ' + Path(item['path']).name)))
        graph.add((entity, DCT.identifier, Literal('sha256:' + item['sha256'])))
        graph.add((entity, PROV.atLocation, URIRef(Path(item['path']).as_uri())))
        graph.add((run, PROV.used, entity))
    for name in ['report.ttl', 'report.txt', 'results.csv', 'summary.json', 'report.html']:
        entity = URIRef('urn:sha256:' + sha256(out / name))
        graph.add((entity, RDF.type, PROV.Entity))
        graph.add((entity, RDFS.label, Literal(name)))
        graph.add((entity, PROV.wasGeneratedBy, run))
        graph.add((entity, PROV.generatedAtTime, Literal(assembled_at, datatype=XSD.dateTime)))
        graph.add((entity, DCT.identifier, Literal('sha256:' + sha256(out / name))))
    graph.serialize(out / 'provenance.ttl', format='turtle')


def write_reports(out, summary, report, report_text):
    out.mkdir(parents=True, exist_ok=True)
    report.serialize(out / 'report.ttl', format='turtle')
    (out / 'report.txt').write_text(report_text, encoding='utf-8')
    with (out / 'results.csv').open('w', newline='', encoding='utf-8') as stream:
        fields = ['severity', 'focus_node', 'path', 'value', 'source_shape', 'constraint', 'message']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary['results'])
    esc = lambda value: html.escape(str(value))
    counts = summary['severity_counts']
    coverage = ''.join(f"<tr><td>{esc(r['label'])}</td><td>{r['focus_nodes']}</td><td>{'Optional' if r['optional_target'] else 'Required'}</td></tr>" for r in summary['focus_counts'])
    results = ''.join('<tr>' + ''.join('<td>' + esc(short(r[k]) if k in ('focus_node', 'path') else r[k]) + '</td>'
                       for k in ('severity', 'focus_node', 'path', 'constraint', 'message')) + '</tr>' for r in summary['results'])
    failures = ''.join('<li>' + esc(short(s)) + '</li>' for s in summary['empty_required_targets'])
    files = ''.join(f"<tr><td>{esc(i['role'])}</td><td>{esc(i['path'])}</td><td><code>{esc(i['sha256'])}</code></td></tr>" for i in summary['inputs'])
    document = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OULAD SHACL validation report</title><style>
body{{font:16px/1.65 "Segoe UI",Arial,sans-serif;color:#18343a;background:#f3f7f5;margin:0;padding:30px}}
main{{max-width:1150px;margin:auto;background:white;padding:35px;border:1px solid #dce6e3;border-radius:9px}}
h1{{font-size:30px;margin:0 0 8px}}h2{{font-size:21px;margin-top:32px}}a{{color:#066e62}}
.status{{background:#edf5f1;padding:18px;border-left:4px solid #087064}}.scroll{{overflow:auto}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{border-bottom:1px solid #dce6e3;text-align:left;padding:10px;vertical-align:top;overflow-wrap:anywhere}}th{{background:#eef5f2}}
code{{font-size:12px}}.small{{color:#52696f;font-size:13px}}@media(max-width:650px){{body{{padding:10px}}main{{padding:20px}}}}@media print{{body{{background:white;padding:0}}main{{border:0;padding:0}}tr{{break-inside:avoid}}}}
</style><main><p class="small">KRR / OULAD · Session 4 · Run {esc(summary['run_id'])}</p>
<h1>SHACL validation report</h1><p class="status"><b>Gate: {'PASS' if summary['gate_passed'] else 'FAIL'}</b> · {counts['Violation']} violations · {counts['Warning']} warnings · {counts['Info']} information results<br>
Strict SHACL conforms: <b>{summary['conforms_shacl']}</b>. The project gate permits warnings but blocks violations and empty required targets.</p>
<p>Validation uses asserted facts and the RDFS class hierarchy. Domain/range and OWL inference are disabled. Warnings stay visible; no data was repaired.</p>
<p><a href="summary.json">Run summary and fingerprints</a> · <a href="results.csv">Results CSV</a> · <a href="report.ttl">SHACL report</a> · <a href="provenance.ttl">PROV-O record</a></p>
<h2>Review queue</h2><div class="scroll"><table><tr><th>Severity</th><th>Focus node</th><th>Property</th><th>Constraint</th><th>Meaning</th></tr>{results or '<tr><td colspan="5">No SHACL validation results.</td></tr>'}</table></div>
<h2>Target coverage</h2><p>A required target with zero nodes fails the gate. Optional activity may have zero nodes in the core build.</p><ul>{failures}</ul>
<table><tr><th>Shape</th><th>Focus nodes</th><th>Coverage policy</th></tr>{coverage}</table>
<h2>Inputs to this run</h2><div class="scroll"><table><tr><th>Role</th><th>File</th><th>SHA-256</th></tr>{files}</table></div>
<p class="small">pySHACL {esc(summary['versions']['pyshacl'])} · RDFLib {esc(summary['versions']['rdflib'])} · Python {esc(summary['versions']['python'])}<br>Started {esc(summary['started_at_utc'])}; finished {esc(summary['finished_at_utc'])}. Duration {summary['duration_seconds']:.2f} s.</p></main></html>'''
    (out / 'report.html').write_text(document, encoding='utf-8')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    write_provenance(out, summary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data', type=Path, default=ROOT / 'data/processed/oulad.ttl')
    parser.add_argument('--schema', type=Path, default=ROOT / 'ontology/education.rdfs.ttl')
    parser.add_argument('--shapes', type=Path, default=ROOT / 'shapes/oulad-shapes.ttl')
    parser.add_argument('--out', type=Path, default=ROOT / 'outputs/shacl/full')
    args = parser.parse_args(argv)
    started = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    try:
        validator_digest = sha256(__file__)
        inputs = [{'role': role, 'path': str(path.resolve()), 'sha256': sha256(path)}
                  for role, path in [('data', args.data), ('schema', args.schema), ('shapes', args.shapes)]]
        data = Graph().parse(args.data)
        asserted_count = len(data)
        data.parse(args.schema)
        shapes = Graph().parse(args.shapes)
        for row in focus_counts(data, shapes):
            print(f"Focus nodes {row['focus_nodes']:5d}: {row['label']}" + (' (optional)' if row['optional_target'] else ''), flush=True)
        summary, report, report_text = evaluate(data, shapes)
        # Check files were stable while validation was in progress.
        if any(sha256(i['path']) != i['sha256'] for i in inputs):
            raise RuntimeError('An input changed during validation. Rerun on stable files.')
        if sha256(__file__) != validator_digest:
            raise RuntimeError('The validator changed during the run. Rerun with stable code.')
        summary.update({'run_id': uuid.uuid4().hex, 'started_at_utc': started,
                        'finished_at_utc': datetime.now(timezone.utc).isoformat(),
                        'duration_seconds': round(time.perf_counter() - start, 3),
                        'data_triples': asserted_count, 'validation_graph_triples': len(data),
                        'inference': 'none', 'inputs': inputs, 'validator_sha256': validator_digest,
                        'versions': {'python': platform.python_version(), 'pyshacl': importlib.metadata.version('pyshacl'),
                                     'rdflib': importlib.metadata.version('rdflib')}})
        write_reports(args.out.resolve(), summary, report, report_text)
        print('Strict SHACL conforms:', summary['conforms_shacl'])
        print('Results:', summary['severity_counts'])
        print('GATE:', 'PASS' if summary['gate_passed'] else 'FAIL')
        print('Report:', args.out.resolve() / 'report.html')
        return 0 if summary['gate_passed'] else 1
    except Exception as exc:
        print(f'VALIDATION ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
