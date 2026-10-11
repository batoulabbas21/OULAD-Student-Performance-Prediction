"""Project-safe adaptation of the lab Neo4j comparison: RDF -> property graph.

No graph deletion. Repeated loads of identical RDF/schema merge the same snapshot.
Different source snapshots remain separate; OULADProject points to the current one.
"""
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
import argparse
import hashlib
import json
import os
import re
import sys

from rdflib import Graph, RDF, RDFS, Literal, URIRef
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_NS = 'https://example.org/oulad/schema#'
RELATIONS = {
    'offeringOf': 'OFFERING_OF', 'hasStudent': 'HAS_STUDENT', 'inOffering': 'IN_OFFERING',
    'assessmentInOffering': 'ASSESSMENT_IN_OFFERING', 'recordForEnrollment': 'RECORD_FOR_ENROLLMENT',
    'forAssessment': 'FOR_ASSESSMENT', 'resourceInOffering': 'RESOURCE_IN_OFFERING',
    'interactionForEnrollment': 'INTERACTION_FOR_ENROLLMENT', 'withResource': 'WITH_RESOURCE'}


def projection(data_path, schema_path):
    graph = Graph().parse(data_path)
    schema = Graph().parse(schema_path)
    # Hash sorted triples, independent of Turtle serialization order.
    content = '\n'.join(sorted(' '.join(t.n3() for t in triple) for triple in graph))
    content += '\n' + '\n'.join(sorted(' '.join(t.n3() for t in triple) for triple in schema))
    snapshot = hashlib.sha256(content.encode()).hexdigest()[:16]
    entities = sorted(set(graph.subjects()), key=str)
    nodes, edges = [], []
    for entity in entities:
        labels = set()
        for kind in graph.objects(entity, RDF.type):
            for ancestor in schema.transitive_objects(kind, RDFS.subClassOf):
                if str(ancestor).startswith(SCHEMA_NS):
                    label = str(ancestor).split('#')[-1]
                    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', label):
                        raise ValueError('Unsafe schema label: ' + label)
                    labels.add(label)
        if not labels:
            raise ValueError(f'No recognized entity type: {entity}')
        properties = {'iri': str(entity), 'snapshot': snapshot,
                      'name': str(entity).split('/id/')[-1]}
        for predicate, value in graph.predicate_objects(entity):
            if predicate == RDF.type:
                continue
            if isinstance(value, Literal):
                key = 'name' if predicate == RDFS.label else str(predicate).split('#')[-1]
                converted = value.toPython()
                if isinstance(converted, Decimal):
                    converted = float(converted)
                if not isinstance(converted, (bool, int, float, str)):
                    converted = str(converted)
                if key in properties and key != 'name':
                    raise ValueError(f'Multiple literal values for {entity} {predicate}; update projection explicitly.')
                properties[key] = converted
            elif isinstance(value, URIRef):
                local = str(predicate).split('#')[-1]
                if local not in RELATIONS:
                    raise ValueError(f'Unmapped relation {predicate}')
                edges.append({'source': str(entity), 'target': str(value), 'type': RELATIONS[local]})
        nodes.append({'iri': str(entity), 'labels': sorted(labels), 'props': properties})
    ids = {n['iri'] for n in nodes}
    if any(edge['source'] not in ids or edge['target'] not in ids for edge in edges):
        raise ValueError('A relationship endpoint is not an entity in the RDF graph.')
    return snapshot, nodes, edges


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Validate/export counts without connecting to Neo4j.')
    parser.add_argument('--rdf', type=Path, default=ROOT/'data/processed/oulad.ttl')
    parser.add_argument('--schema', type=Path, default=ROOT/'ontology/education.rdfs.ttl')
    args = parser.parse_args()
    snapshot, nodes, edges = projection(args.rdf, args.schema)
    node_groups, edge_groups = defaultdict(list), defaultdict(list)
    for node in nodes:
        node_groups[tuple(node['labels'])].append(node)
    for edge in edges:
        edge_groups[edge['type']].append(edge)
    counts = {'snapshot': snapshot, 'nodes': len(nodes), 'relationships': len(edges),
              'node_groups': {','.join(labels): len(rows) for labels, rows in node_groups.items()},
              'relationship_types': {name: len(rows) for name, rows in edge_groups.items()},
              'source': str(args.rdf), 'status': 'dry-run'}
    dest = ROOT / 'outputs/neo4j'
    dest.mkdir(parents=True, exist_ok=True)
    if not args.dry_run:
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        auth = (os.getenv('NEO4J_USER', 'neo4j'), os.getenv('NEO4J_PASSWORD', 'kr-labs-pw'))
        database = os.getenv('NEO4J_DATABASE', 'neo4j')
        with GraphDatabase.driver(uri, auth=auth, connection_timeout=10) as driver:
            driver.verify_connectivity()
            with driver.session(database=database) as session:
                session.run('CREATE CONSTRAINT oulad_entity IF NOT EXISTS FOR (n:OULAD) REQUIRE (n.snapshot,n.iri) IS UNIQUE').consume()
                for labels, rows in node_groups.items():
                    # Labels come only from the validated local schema, not user query text.
                    label_text = ':'.join(labels)
                    statement = ('UNWIND $rows AS row MERGE (n:OULAD {snapshot:$snapshot,iri:row.iri}) '
                                 f'SET n:{label_text} SET n += row.props')
                    for index in range(0, len(rows), 500):
                        session.run(statement, rows=rows[index:index+500], snapshot=snapshot).consume()
                for relation, rows in edge_groups.items():
                    statement = ('UNWIND $rows AS row '
                        'MATCH (a:OULAD {snapshot:$snapshot,iri:row.source}) '
                        'MATCH (b:OULAD {snapshot:$snapshot,iri:row.target}) '
                        f'MERGE (a)-[:{relation}]->(b)')
                    for index in range(0, len(rows), 500):
                        session.run(statement, rows=rows[index:index+500], snapshot=snapshot).consume()
                actual_nodes = session.run('MATCH (n:OULAD {snapshot:$snapshot}) RETURN count(n) AS n',snapshot=snapshot).single()['n']
                actual_edges = session.run('MATCH (a:OULAD {snapshot:$snapshot})-[r]->(b:OULAD {snapshot:$snapshot}) RETURN count(r) AS n',snapshot=snapshot).single()['n']
                if (actual_nodes,actual_edges) != (len(nodes),len(edges)):
                    raise AssertionError(f'Import counts disagree: {(actual_nodes, actual_edges)}')
                late = session.run('''MATCH (a:OULAD:Assessment {snapshot:$snapshot})<-[:FOR_ASSESSMENT]-(r:OULAD:AssessmentRecord)
                  WHERE r.isBanked=false AND r.submissionDay>a.deadlineDay RETURN count(r) AS n''',snapshot=snapshot).single()['n']
                # SPARQL is the independent reference for the Cypher late-record count.
                reference = Graph().parse(args.rdf)
                expected_late = len(list(reference.query((ROOT/'queries/03_late_records.rq').read_text())))
                if late != expected_late:
                    raise AssertionError(f'Cypher late count {late} != SPARQL {expected_late}')
                # Publish only after load and verification complete; old snapshots are retained.
                session.run('MERGE (m:OULADProject {name:"oulad"}) SET m.activeSnapshot=$snapshot',snapshot=snapshot).consume()
                counts.update(status='loaded-and-verified', cypher_late_records=late,
                              neo4j_nodes=actual_nodes, neo4j_relationships=actual_edges)
    (dest/'import-summary.json').write_text(json.dumps(counts,indent=2),encoding='utf-8')
    print(json.dumps(counts,indent=2))
    if not args.dry_run:
        print('Open http://localhost:7474 and run queries/neo4j.cypher one query at a time.')


if __name__ == '__main__':
    try:
        main()
    except ServiceUnavailable:
        raise SystemExit('Neo4j is unavailable. Start Docker Desktop, then the lab neo4j service. See README.')
    except AuthError:
        raise SystemExit('Neo4j credentials differ from the lab defaults. Set NEO4J_USER/NEO4J_PASSWORD to your existing credentials; do not reset the volume.')
