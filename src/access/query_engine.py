"""Read-only SPARQL guard, process time limit, and structured result values."""
import json, subprocess, sys
from decimal import Decimal
from rdflib import URIRef, Variable, RDF, RDFS
from rdflib.paths import Path as RDFPath
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parserutils import CompValue
from common import GRAPH, SCHEMA, PREFIXES, EDU

def walk(node):
    yield node
    if isinstance(node,dict):
        for k,v in node.items():
            if k!='_vars': yield from walk(v)
    elif isinstance(node,(list,tuple,set)):
        for v in node: yield from walk(v)
    elif isinstance(node,RDFPath):
        for v in vars(node).values(): yield from walk(v)

def check_query(query, grounding, vocabulary=True):
    if len(query)>20000: return ['Query exceeds 20,000 characters.']
    try: algebra=prepareQuery(query,initNs=PREFIXES).algebra
    except Exception as e: return ['Invalid SPARQL: '+str(e).splitlines()[0][:180]]
    problems=[]
    if algebra.name not in ('SelectQuery','AskQuery'): problems.append('Only SELECT and ASK are supported.')
    for node in walk(algebra):
        if isinstance(node,CompValue):
            if node.name in ('ServiceGraphPattern','Graph','DatasetClause') or node.get('datasetClause') not in (None,'datasetClause',[]):
                problems.append('SERVICE, GRAPH and FROM are outside this local default graph interface.')
            if node.name=='BGP' and vocabulary:
                for s,p,o in node['triples']:
                    for term in walk(p):
                        if isinstance(term,URIRef) and str(term) not in grounding['properties'] | {str(RDF.type),str(RDFS.subClassOf),str(RDFS.label),str(RDFS.comment)}:
                            problems.append('Unknown or unavailable predicate: '+str(term))
                    if p==RDF.type and isinstance(o,URIRef) and str(o).startswith(EDU) and str(o) not in grounding['classes']:
                        problems.append('Unknown or unavailable class: '+str(o))
        if vocabulary and isinstance(node,URIRef) and str(node).startswith(EDU) and str(node) not in grounding['classes']|grounding['properties']:
            problems.append('Unknown or unavailable vocabulary term: '+str(node))
    return sorted(set(problems))

def full_query(query):
    return '\n'.join(f'PREFIX {p}: <{iri}>' for p,iri in PREFIXES.items())+'\n'+query

def run_query(query, timeout=15):
    # The isolated process can actually be terminated, unlike a timed-out Python thread.
    try:
        r=subprocess.run([sys.executable,__file__,'--worker'],input=json.dumps({'query':query}),
                         capture_output=True,text=True,encoding='utf-8',timeout=timeout)
    except subprocess.TimeoutExpired as e: raise RuntimeError(f'Query exceeded {timeout} seconds.') from e
    if r.returncode: raise RuntimeError(r.stderr.strip()[-400:] or 'Query worker failed.')
    return json.loads(r.stdout)

def worker(query):
    import pyoxigraph as ox
    store=ox.Store(); store.load(path=str(GRAPH),format=ox.RdfFormat.TURTLE)
    store.load(path=str(SCHEMA),format=ox.RdfFormat.TURTLE)
    result=store.query(query,prefixes=PREFIXES)
    if isinstance(result,ox.QueryBoolean): return {'boolean':bool(result)}
    columns=[v.value for v in result.variables]; rows=[]
    for row in result:
        if len(rows)>=10000: raise ValueError('Query exceeds the 10,000-row limit; aggregate or use LIMIT.')
        rows.append({c:row[c].value if row[c] is not None else None for c in columns})
    return {'columns':columns,'rows':rows}

if __name__=='__main__':
    try: print(json.dumps(worker(json.loads(sys.stdin.read())['query'])))
    except Exception as e: print(str(e),file=sys.stderr);sys.exit(1)
