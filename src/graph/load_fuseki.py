"""Lab-style HTTP loading and SPARQL, restricted to the project's /oulad dataset.

Loads facts and schema together, backs up an existing changed default graph,
and compares live query answers with RDFLib. Does not materialize RDFS closure.
"""
from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import sys

import requests
from rdflib import Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.query import Result

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'outputs' / 'fuseki'
COUNT_QUERY = 'SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }'


def query(session, endpoint, sparql):
    reply = session.post(endpoint, data={'query': sparql},
                         headers={'Accept': 'application/sparql-results+json'}, timeout=120)
    reply.raise_for_status()
    return Result.parse(source=BytesIO(reply.content), format='json')


def get_default_graph(session, dataset):
    reply = session.get(dataset + '/data', params={'default': ''},
                        headers={'Accept': 'text/turtle'}, timeout=120)
    reply.raise_for_status()
    return Graph().parse(data=reply.content, format='turtle'), reply.content


def row_key(row):
    # Compare RDF values rather than numeric lexical forms (e.g. 1.0 vs 1.00).
    return tuple(('iri', str(term)) if isinstance(term, URIRef) else
                 ('literal', term.language, term.toPython()) if isinstance(term, Literal)
                 else ('other', term) for term in row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=os.environ.get('FUSEKI_BASE', 'http://localhost:3030'))
    parser.add_argument('--check-only', action='store_true', help='Verify the live graph without uploading.')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    dataset = base + '/oulad'  # Never target /kr or accept a dataset override.
    endpoint = dataset + '/sparql'
    paths = [ROOT / 'data/processed/oulad.ttl', ROOT / 'ontology/education.rdfs.ttl']
    graph = Graph()
    source_counts = {}
    hashes = {}
    for path in paths:
        source = Graph().parse(path, format='turtle')
        source_counts[path.relative_to(ROOT).as_posix()] = len(source)
        hashes[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        graph += source
    metadata = json.loads((ROOT / 'data/processed/graph_summary.json').read_text(encoding='utf-8'))
    if metadata['triples'] != source_counts['data/processed/oulad.ttl']:
        raise ValueError('RDF and graph_summary.json disagree. Rebuild RDF first.')

    # Establish local expected answers before changing the server.
    expected = {}
    checks = {}
    for path in sorted((ROOT / 'queries').glob('*.rq')):
        if path.name == '07_early_activity.rq' and not metadata['selection']['include_activity']:
            checks[path.name] = {'status': 'unavailable', 'reason': 'Activity was not included in this RDF build.'}
            continue
        sparql = path.read_text(encoding='utf-8')
        result = graph.query(sparql)
        expected[path.name] = (sparql, list(result.vars), list(result))

    with requests.Session() as session:
        # A missing dataset fails before any upload.
        query(session, endpoint, 'ASK { ?s ?p ?o }')
        previous, previous_bytes = get_default_graph(session, dataset)
        same_graph = isomorphic(previous, graph)
        backup_path = None
        if args.check_only and not same_graph:
            raise ValueError('Live /oulad default graph differs from the local RDF/schema. Run without --check-only to reload.')
        if not args.check_only and not same_graph:
            if len(previous):
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                backup_path = OUTPUT / 'backups' / f'oulad-default-{stamp}.ttl'
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                backup_path.write_bytes(previous_bytes)
                print(f'Previous /oulad default graph saved to {backup_path}')
            # PUT replaces only /oulad's default graph. Named graphs and /kr are untouched.
            reply = session.put(dataset + '/data', params={'default': ''},
                                data=graph.serialize(format='turtle', encoding='utf-8'),
                                headers={'Content-Type': 'text/turtle'}, timeout=600)
            reply.raise_for_status()
            live_graph, _ = get_default_graph(session, dataset)
            if not isomorphic(live_graph, graph):
                raise ValueError('Uploaded graph does not match the local RDF/schema.')
        live_count = int(next(iter(query(session, endpoint, COUNT_QUERY)))[0])
        if live_count != len(graph):
            raise ValueError(f'Triple count mismatch: local={len(graph)}, Fuseki={live_count}')

        OUTPUT.mkdir(parents=True, exist_ok=True)
        for name, (sparql, variables, local_rows) in expected.items():
            live_result = query(session, endpoint, sparql)
            live_rows = list(live_result)
            if list(live_result.vars) != variables or Counter(map(row_key, live_rows)) != Counter(map(row_key, local_rows)):
                raise ValueError(f'Fuseki/RDFLib answers differ for {name}')
            with (OUTPUT / (Path(name).stem + '.csv')).open('w', encoding='utf-8', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(map(str, variables))
                writer.writerows(['' if value is None else str(value) for value in row] for row in live_rows)
            checks[name] = {'status': 'passed', 'rows': len(live_rows)}
            print(f'{name}: {len(live_rows)} rows, matches RDFLib')

    # Avoid presenting old activity answers as current after returning to a core build.
    if checks.get('07_early_activity.rq', {}).get('status') == 'unavailable':
        (OUTPUT / '07_early_activity.csv').unlink(missing_ok=True)
    summary = {
        'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'dataset': dataset, 'query_endpoint': endpoint,
        'mode': 'check-only' if args.check_only else 'unchanged' if same_graph else 'uploaded',
        'source_triples': source_counts, 'default_graph_triples': live_count,
        'source_sha256': hashes, 'rdfs_inference': False,
        'previous_graph_backup': str(backup_path) if backup_path else None,
        'queries': checks,
    }
    (OUTPUT / 'import-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(f'Verified {live_count:,} triples in {dataset}. Open {base}/ and select /oulad.')


if __name__ == '__main__':
    try:
        main()
    except requests.RequestException as exc:
        print(f'Fuseki request failed: {exc}\nStart Docker Desktop, then run ./start-fuseki.ps1.', file=sys.stderr)
        sys.exit(1)
    except (FileNotFoundError, ValueError) as exc:
        print(f'Cannot load Fuseki: {exc}', file=sys.stderr)
        sys.exit(1)
