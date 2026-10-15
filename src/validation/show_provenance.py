"""Answer: which exact input files and validator produced this validation report?"""
import argparse
from pathlib import Path
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[2]
QUERY = '''
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>
SELECT ?run ?start ?end ?agentLabel ?inputLabel ?fingerprint WHERE {
  ?run a prov:Activity ; prov:startedAtTime ?start ; prov:endedAtTime ?end ;
       prov:wasAssociatedWith ?agent ; prov:used ?input .
  ?agent rdfs:label ?agentLabel .
  ?input rdfs:label ?inputLabel ; dct:identifier ?fingerprint .
} ORDER BY ?inputLabel
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, default=ROOT / 'outputs/shacl/full/provenance.ttl')
    args = parser.parse_args()
    rows = list(Graph().parse(args.file).query(QUERY))
    if not rows:
        raise SystemExit('No validation activity with its inputs was found.')
    print('Run:', rows[0].run)
    print('Started:', rows[0].start)
    print('Finished including report assembly:', rows[0].end)
    print('Software:', rows[0].agentLabel)
    for row in rows:
        print(f'  {row.inputLabel}\n    {row.fingerprint}')

if __name__ == '__main__':
    main()
