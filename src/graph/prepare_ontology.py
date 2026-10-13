"""Prepare an offline ontology workspace from the authored OWL and existing RDF.

Session 3 pattern: locally resolved imports plus a small real-data sample.
Generated workspace files are reproducible; edit ontology/education.owl.ttl instead.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET

from rdflib import Graph, Literal, Namespace, OWL, RDF, RDFS, URIRef, XSD

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'outputs/ontology/workspace'
EDU = Namespace('https://example.org/oulad/schema#')
FOAF = Namespace('http://xmlns.com/foaf/0.1/')
DATA = 'https://example.org/oulad/id/'
ONTOLOGY = URIRef('https://example.org/oulad/ontology')
BASE = URIRef('https://example.org/oulad/base')
REUSE = URIRef('https://example.org/oulad/imports/foaf-person')


def save(graph, name):
    graph.bind('edu', EDU)
    graph.bind('foaf', FOAF)
    graph.serialize(WORK / name, format='turtle')


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    # Translate RDFS declarations, retaining the same IRIs, hierarchy, domains and ranges.
    base = Graph().parse(ROOT / 'ontology/education.rdfs.ttl')
    for cls in list(base.subjects(RDF.type, RDFS.Class)):
        base.remove((cls, RDF.type, RDFS.Class))
        base.add((cls, RDF.type, OWL.Class))
        base.set((cls, RDFS.label, Literal('OULADPerson' if cls == EDU.Person else str(cls).split('#')[-1])))
    for prop in list(base.subjects(RDF.type, RDF.Property)):
        ranges = list(base.objects(prop, RDFS.range))
        kind = OWL.DatatypeProperty if ranges and all(str(r).startswith(str(XSD)) for r in ranges) else OWL.ObjectProperty
        base.remove((prop, RDF.type, RDF.Property))
        base.add((prop, RDF.type, kind))
        base.set((prop, RDFS.label, Literal(str(prop).split('#')[-1])))
    base.add((BASE, RDF.type, OWL.Ontology))
    base.add((BASE, RDFS.label, Literal('OULAD base declarations from the RDFS schema')))
    save(base, 'education-base.owl.ttl')

    # Explicitly selected fragment, NOT the entire FOAF ontology or all its entailments.
    source_path = ROOT / 'ontology/imports/foaf.rdf'
    source = Graph().parse(source_path, format='xml')
    fragment = Graph()
    for cls in [FOAF.Person, FOAF.Agent]:
        for predicate in [RDF.type, RDFS.label, RDFS.comment]:
            for obj in source.objects(cls, predicate):
                if predicate != RDF.type or obj == OWL.Class:
                    fragment.add((cls, predicate, obj))
    link = (FOAF.Person, RDFS.subClassOf, FOAF.Agent)
    if link not in source:
        raise ValueError('Cached FOAF snapshot does not contain the required Person subclass Agent axiom.')
    fragment.add(link)
    fragment.add((REUSE, RDF.type, OWL.Ontology))
    fragment.add((REUSE, RDFS.label, Literal('Selected FOAF Person/Agent fragment')))
    fragment.add((REUSE, RDFS.isDefinedBy, URIRef('https://xmlns.com/foaf/spec/')))
    fragment.add((REUSE, RDFS.comment, Literal('Selected by the OULAD project from FOAF 0.99. Dan Brickley and Libby Miller; CC BY 1.0. Not a complete FOAF import.')))
    save(fragment, 'foaf-person.ttl')

    shutil.copyfile(ROOT / 'ontology/education.owl.ttl', WORK / 'education.owl.ttl')
    shutil.copyfile(ROOT / 'ontology/exercises/domain-error.ttl', WORK / 'domain-error.ttl')
    graph = Graph().parse(ROOT / 'data/processed/oulad.ttl')
    selected = set()
    reasons = {}

    def choose(candidates, reason):
        items = sorted(set(candidates), key=str)
        if items:
            selected.add(items[0])
            reasons.setdefault(str(items[0]), []).append(reason)

    for outcome in ['Pass', 'Distinction', 'Fail', 'Withdrawn']:
        choose((e for e, value in graph.subject_objects(EDU.finalResult) if str(value) == outcome), 'outcome=' + outcome)
    records = sorted(graph.subjects(RDF.type, EDU.AssessmentRecord), key=str)
    low = [r for r in records if graph.value(r, EDU.score) is not None and float(graph.value(r, EDU.score)) < 40]
    banked = [r for r in records if graph.value(r, EDU.isBanked) == Literal(True)]
    missing = [r for r in records if graph.value(r, EDU.score) is None]
    for pool, reason in [(low, 'has a low score'), (banked, 'has a banked result'), (missing, 'has an unknown score')]:
        if pool:
            choose([graph.value(pool[0], EDU.recordForEnrollment)], reason)
    if not selected:
        raise ValueError('No enrollments selected. Generate the project RDF first.')

    # Traverse outward from selected enrollments and all their records; no fabricated facts.
    pending = list(selected) + [r for r in records if graph.value(r, EDU.recordForEnrollment) in selected]
    seen, sample = set(), Graph()
    while pending:
        subject = pending.pop()
        if subject in seen:
            continue
        seen.add(subject)
        for triple in graph.triples((subject, None, None)):
            sample.add(triple)
            obj = triple[2]
            if isinstance(obj, URIRef) and str(obj).startswith(DATA):
                pending.append(obj)
    source_triples = len(sample)
    for subject in seen:
        sample.add((subject, RDF.type, OWL.NamedIndividual))
        # Readable rendering retains the original IRI and student ID.
        sample.add((subject, RDFS.label, Literal(str(subject).removeprefix(DATA).replace('/', '_'))))
    sample_iri = URIRef('https://example.org/oulad/sample')
    sample.add((sample_iri, RDF.type, OWL.Ontology))
    sample.add((sample_iri, OWL.imports, ONTOLOGY))
    sample.add((sample_iri, RDFS.comment, Literal('Purposeful small real-data teaching sample, not a representative sample of AAA. Labels and NamedIndividual declarations are presentation additions.')))
    save(sample, 'sample-enrollments.ttl')

    bad = Graph()
    bad.add((URIRef('https://example.org/oulad/inconsistent-example'), RDF.type, OWL.Ontology))
    bad.add((URIRef('https://example.org/oulad/inconsistent-example'), OWL.imports, URIRef('https://example.org/oulad/domain-error')))
    bad.add((URIRef('https://example.org/oulad/teaching#fictionalStudent'), RDF.type, URIRef('https://example.org/oulad/teaching#StudentUsingEnrollmentProperty')))
    save(bad, 'domain-inconsistent.ttl')

    mapping = {str(BASE): 'education-base.owl.ttl', str(REUSE): 'foaf-person.ttl',
               str(ONTOLOGY): 'education.owl.ttl', 'https://example.org/oulad/domain-error': 'domain-error.ttl'}
    ns = 'urn:oasis:names:tc:entity:xmlns:xml:catalog'
    ET.register_namespace('', ns)
    catalog = ET.Element('{' + ns + '}catalog', {'prefer': 'public'})
    for iri, filename in mapping.items():
        ET.SubElement(catalog, '{' + ns + '}uri', {'name': iri, 'uri': filename})
    ET.indent(catalog)
    ET.ElementTree(catalog).write(WORK / 'catalog-v001.xml', encoding='utf-8', xml_declaration=True)
    manifest = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
                'sample_source_triples': source_triples, 'sample_individuals': len(seen),
                'selected_enrollments': reasons,
                'foaf_source': 'https://xmlns.com/foaf/spec/index.rdf',
                'foaf_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
                'data_sha256': hashlib.sha256((ROOT / 'data/processed/oulad.ttl').read_bytes()).hexdigest(),
                'reuse': 'Selected Person/Agent fragment, not the complete FOAF ontology.'}
    (WORK.parent / 'preparation.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Prepared {len(selected)} enrollments, {len(seen)} individuals, {source_triples} source triples.')
    print(f'OWL workspace: {WORK / "education.owl.ttl"}')
    print(f'For instance reasoning: {WORK / "sample-enrollments.ttl"}')


if __name__ == '__main__':
    main()
