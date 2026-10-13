"""Session 3 lab logic: resolve local imports, merge with RDFLib, run HermiT via Owlready2."""
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET

import owlready2
from rdflib import Graph, OWL, RDF, URIRef

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'outputs/ontology/workspace'


def merged_graph(path):
    path = Path(path).resolve()
    catalog = path.parent / 'catalog-v001.xml'
    mapping = {}
    for entry in ET.parse(catalog).getroot().iter('{urn:oasis:names:tc:entity:xmlns:xml:catalog}uri'):
        mapping[entry.attrib['name']] = (catalog.parent / entry.attrib['uri']).resolve()
    result, pending, seen = Graph(), [path], set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        part = Graph().parse(current)
        for imported in part.objects(None, OWL.imports):
            if str(imported) not in mapping:
                raise ValueError(f'Import not in local catalog: {imported}')
            pending.append(mapping[str(imported)])
        part.remove((None, OWL.imports, None))
        result += part
    return result


def reason(graph):
    world = owlready2.World()
    # RDF class assertions can omit an explicit NamedIndividual declaration.
    # Add it for Owlready2's individual enumeration without changing the caller's graph.
    loading = Graph()
    loading += graph
    for subject, cls in graph.subject_objects(RDF.type):
        if isinstance(subject, URIRef) and (cls, RDF.type, OWL.Class) in graph:
            loading.add((subject, RDF.type, OWL.NamedIndividual))
    # fileobj avoids Owlready2's file:///C:/ Windows path handling problem.
    serialized = loading.serialize(format='nt', encoding='utf-8')
    ontology = world.get_ontology('https://example.org/oulad/reasoning-run').load(
        fileobj=BytesIO(serialized), format='ntriples')
    try:
        with ontology:
            # HermiT still uses inverse properties while classifying individuals.
            # Exporting every inferred property assertion is unnecessary here.
            owlready2.sync_reasoner_hermit(world, infer_property_values=False, debug=0)
    except owlready2.OwlReadyInconsistentOntologyError:
        world.close()
        return {'consistent': False, 'unsatisfiable_classes': None, 'types': None}
    impossible = sorted(c.iri for c in world.inconsistent_classes() if c != owlready2.Nothing)
    types = {}
    for individual in world.individuals():
        if individual.iri.startswith('https://example.org/oulad/'):
            types[individual.iri] = sorted(c.iri for c in individual.INDIRECT_is_a if hasattr(c, 'iri'))
    parents = {cls.iri: sorted(c.iri for c in cls.is_a if hasattr(c, 'iri'))
               for cls in world.classes() if cls.iri.startswith('https://example.org/oulad/schema#')}
    world.close()
    return {'consistent': True, 'unsatisfiable_classes': impossible, 'types': types,
            'class_parents': parents}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', type=Path, default=WORK / 'sample-enrollments.ttl')
    parser.add_argument('--full-data', action='store_true', help='Reason over all generated OULAD facts with the clean ontology.')
    args = parser.parse_args()
    if args.full_data:
        graph = merged_graph(WORK / 'education.owl.ttl')
        graph.parse(ROOT / 'data/processed/oulad.ttl')
        for subject in list(set(graph.subjects())):
            if isinstance(subject, URIRef) and str(subject).startswith('https://example.org/oulad/id/'):
                graph.add((subject, RDF.type, OWL.NamedIndividual))
        title = 'full'
    else:
        graph = merged_graph(args.input)
        title = args.input.stem
    result = reason(graph)
    result['scope'] = title
    result['verified_at_utc'] = datetime.now(timezone.utc).isoformat()
    inputs = [ROOT / 'data/processed/oulad.ttl', ROOT / 'ontology/education.owl.ttl',
              ROOT / 'ontology/education.rdfs.ttl', ROOT / 'ontology/imports/foaf.rdf']
    result['source_sha256'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    out = ROOT / 'outputs/ontology'
    out.mkdir(parents=True, exist_ok=True)
    target = out / ('reasoned-' + title + '.json')
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('Consistent:', result['consistent'])
    if result['consistent']:
        print('Unsatisfiable named classes:', ', '.join(result['unsatisfiable_classes']) or 'none')
        print('Individuals with inferred type information:', len(result['types']))
        inferred = Graph()
        for individual, classes in result['types'].items():
            for cls in classes:
                triple = (URIRef(individual), RDF.type, URIRef(cls))
                if triple not in graph and cls != str(OWL.Thing):
                    inferred.add(triple)
        inferred.serialize(out / ('inferred-types-' + title + '.ttl'), format='turtle')
        print('New named type assertions:', len(inferred))
    print('Report:', target)
    if not result['consistent'] or result['unsatisfiable_classes']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
