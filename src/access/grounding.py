"""Describe observed facts, retain every target type, and distinguish schema from data."""
from collections import defaultdict
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, XSD
from common import GRAPH, SCHEMA, EDU, DATASET, OUT, sha, write_json

VOID = Namespace('http://rdfs.org/ns/void#')
VEXT = Namespace('http://ldf.fi/void-ext#')
SH = Namespace('http://www.w3.org/ns/shacl#')

def describe():
    data = Graph().parse(GRAPH); schema = Graph().parse(SCHEMA)
    classes = defaultdict(set); properties = defaultdict(lambda: defaultdict(set))
    observed = set()
    for subject, cls in data.subject_objects(RDF.type):
        if str(cls).startswith(EDU): classes[str(cls)].add(subject)
    g = Graph(); g.bind('void', VOID); g.bind('vext', VEXT); g.bind('edu', Namespace(EDU))
    ds = URIRef(DATASET+'void'); g.add((ds, RDF.type, VOID.Dataset))
    g.add((ds, VOID.triples, Literal(len(data))))
    lines = [f'Observed asserted fact triples: {len(data)}. Counts below are direct types, without OWL inference.']
    for cls, subjects in sorted(classes.items()):
        part = URIRef(cls+'/partition'); g.add((ds, VOID.classPartition, part))
        g.add((part, VOID['class'], URIRef(cls))); g.add((part, VOID.entities, Literal(len(subjects))))
        lines.append(f'{cls.replace(EDU,"edu:")}: {len(subjects)} directly typed instances')
        counts = defaultdict(int)
        for subject in subjects:
            for p,o in data.predicate_objects(subject):
                if p == RDF.type: continue
                observed.add(str(p)); counts[str(p)] += 1
                targets = ([('datatype',str(o.datatype or (RDF.langString if o.language else XSD.string)))]
                           if isinstance(o,Literal) else [('class',str(c)) for c in data.objects(o,RDF.type)])
                if not targets: targets = [('iri','IRI')]
                properties[str(p)][cls].update(targets)
        for p, count in sorted(counts.items()):
            pp = URIRef(str(part)+'/'+p.split('#')[-1]); g.add((part,VOID.propertyPartition,pp))
            g.add((pp,VOID.property,URIRef(p))); g.add((pp,VOID.triples,Literal(count)))
            targets = sorted(properties[p][cls])
            for i,(kind,t) in enumerate(targets):
                if kind == 'iri': continue
                tp = URIRef(str(pp)+'/'+str(i))
                g.add((pp,VOID.classPartition if kind=='class' else VEXT.datatypePartition,tp))
                g.add((tp,VOID['class'] if kind=='class' else VEXT.datatype,URIRef(t)))
            lines.append(f"  {p.replace(EDU,'edu:')} -> "+' or '.join(t.replace(EDU,'edu:').replace(str(XSD),'xsd:') for _,t in targets))
    available = set(classes)
    for c in list(available):
        available.update(str(t) for t in schema.transitive_objects(URIRef(c),RDFS.subClassOf))
    for child,parent in sorted(schema.subject_objects(RDFS.subClassOf)):
        lines.append(f'{str(child).replace(EDU,"edu:")} rdfs:subClassOf {str(parent).replace(EDU,"edu:")}')
    declared = {str(c) for c in schema.subjects(RDF.type,RDFS.Class)}
    lines.append('Declared but no instances or subclass instances loaded: '+', '.join(sorted(c.replace(EDU,'edu:') for c in declared-available)))
    return {'graph': g, 'text': '\n'.join(lines), 'classes':available, 'properties':observed,
            'direct_counts':{c:len(s) for c,s in classes.items()}, 'fact_triples':len(data), 'schema_triples':len(schema)}

def generate(folder=OUT):
    folder.mkdir(parents=True,exist_ok=True); d=describe()
    d['graph'].serialize(folder/'void.ttl',format='turtle')
    (folder/'schema.txt').write_text(d['text']+'\n',encoding='utf-8')
    write_json(folder/'grounding.json',{'data_sha256':sha(GRAPH),'schema_sha256':sha(SCHEMA),
        'fact_triples':d['fact_triples'],'schema_triples':d['schema_triples'],'direct_counts':d['direct_counts'],
        'available_classes':sorted(d['classes']),'observed_properties':sorted(d['properties'])})
    return d

def load_examples(path):
    g=Graph().parse(path)
    return sorted([{'id':str(s).rsplit('/',1)[-1], 'question':str(g.value(s,RDFS.comment)),
        'query':str(g.value(s,SH.select))} for s in g.subjects(RDF.type,SH.SPARQLExecutable)],key=lambda x:x['id'])

if __name__=='__main__':
    d=generate(); print(f"Wrote VoID and schema summary for {d['fact_triples']:,} facts to {OUT}")
