"""Exact RDF-term comparison after explicit lexical normalization; answer multisets retain duplicates."""
from collections import Counter
from decimal import Decimal
import csv
from rdflib import URIRef,Literal,XSD
from common import write_json
NUMERIC={'enrollments','students','deadline','weight','submitted','daysLate','score','count','low'}
def scalar(name,value):
    if value is None or value=='': return None
    if name in NUMERIC: return str(Decimal(str(value)).normalize())
    if name=='banked':
        if str(value).lower() not in ('true','false','1','0'): raise ValueError('Unexpected boolean value')
        return str(value).lower() in ('true','1')
    return str(value)
def answers(fields,rows): return Counter(tuple(scalar(k,row.get(k)) for k in fields) for row in rows)
def term(t):
    if isinstance(t,URIRef): return ('IRI',str(t))
    if isinstance(t,Literal):
        dtype=t.datatype or (None if t.language else XSD.string)
        value=str(t)
        if dtype==XSD.integer:
            n=Decimal(value)
            if n!=n.to_integral_value(): raise ValueError('Invalid integer literal: '+t.n3())
            value=str(int(n))
        if dtype==XSD.decimal: value=str(Decimal(value).normalize())
        if dtype==XSD.boolean:
            if value not in ('true','false','1','0'): raise ValueError('Invalid boolean literal')
            value='true' if value in ('true','1') else 'false'
        return ('literal',value,str(dtype or ''),t.language or '')
    return ('blank',str(t))
def graph_terms(g): return {tuple(term(t) for t in row) for row in g}
def compare_graphs(reference,mapped,path):
    a,b=graph_terms(reference),graph_terms(mapped)
    result={'reference_triples':len(reference),'mapped_triples':len(mapped),
        'only_reference':len(a-b),'only_mapped':len(b-a),'equal':a==b,
        'raw_term_differences':{'only_reference':len(set(reference)-set(mapped)),'only_mapped':len(set(mapped)-set(reference))},
        'normalization':'RDF 1.1 simple literals and xsd:string are equivalent; canonical integer/decimal/boolean lexical forms. Datatype IRIs, language tags, IRI identities and values are preserved.',
        'examples_only_reference':[repr(t) for t in sorted(a-b)[:10]],'examples_only_mapped':[repr(t) for t in sorted(b-a)[:10]]}
    write_json(path,result);return result
def rdf_rows(graph,query):
    result=graph.query(query);fields=[str(v) for v in result.vars]
    return fields,[{k:(None if v is None else str(v)) for k,v in zip(fields,row)} for row in result]
def save_csv(path,fields,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
