"""Record actual integration inputs, database snapshot, tools, reports and generated files."""
from pathlib import Path
from rdflib import Graph, Namespace, RDF, Literal, URIRef, XSD
from common import sha,now
PROV=Namespace('http://www.w3.org/ns/prov#');DCT=Namespace('http://purl.org/dc/terms/')
def record(out,summary,inputs):
    g=Graph();g.bind('prov',PROV);g.bind('dcterms',DCT)
    run=URIRef('https://example.org/oulad/run/integration/'+summary['run_id'])
    g.add((run,RDF.type,PROV.Activity));g.add((run,PROV.startedAtTime,Literal(summary['started_at_utc'],datatype=XSD.dateTime)))
    g.add((run,PROV.endedAtTime,Literal(now(),datatype=XSD.dateTime)))
    agent=URIRef('https://example.org/oulad/software/integration/'+sha(Path(__file__).with_name('run.py')))
    g.add((agent,RDF.type,PROV.SoftwareAgent));g.add((agent,DCT.description,Literal(str(summary['versions']))));g.add((run,PROV.wasAssociatedWith,agent))
    for path in inputs:
        node=URIRef('urn:sha256:'+sha(path));g.add((node,RDF.type,PROV.Entity));g.add((node,PROV.atLocation,URIRef(path.resolve().as_uri())));g.add((run,PROV.used,node))
    database=URIRef('urn:oulad:database:sha256:'+summary['database']['sha256'])
    g.add((database,RDF.type,PROV.Entity));g.add((database,DCT.description,Literal(str(summary['connection']))));g.add((run,PROV.used,database))
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name not in ('provenance.ttl','provenance-check.json'):
            node=URIRef('urn:sha256:'+sha(path));g.add((node,RDF.type,PROV.Entity));g.add((node,DCT.title,Literal(path.relative_to(out).as_posix())));g.add((node,PROV.wasGeneratedBy,run))
    g.serialize(out/'provenance.ttl',format='turtle')
