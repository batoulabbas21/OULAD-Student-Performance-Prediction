"""Value-set score from the lab plus row-aware scoring that preserves associations."""
from collections import Counter
from decimal import Decimal, InvalidOperation

def canonical(value):
    if value is None:return ('unbound',)
    # Normalize numeric lexical differences without changing IDs with leading zeroes.
    try:
        n=Decimal(str(value))
        if n.is_finite() and not (str(value).startswith('0') and len(str(value))>1 and str(value)[1].isdigit()): return ('number',str(n.normalize()))
    except InvalidOperation: pass
    return ('term',str(value))

def rows(result):
    if result is None:return Counter()
    if 'boolean' in result:return Counter({('ASK',bool(result['boolean'])):1})
    return Counter(tuple(canonical(r.get(c)) for c in result['columns']) for r in result['rows'])

def score(predicted,gold):
    p,g=rows(predicted),rows(gold); n=sum((p&g).values())
    precision=n/sum(p.values()) if p else (1. if not g and predicted is not None else 0.)
    recall=n/sum(g.values()) if g else (1. if not p and predicted is not None else 0.)
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.
    return {'precision':precision,'recall':recall,'f1':f1,'exact':predicted is not None and p==g}

def flat_values(result):
    if result is None:return set()
    if 'boolean' in result:return {'true' if result['boolean'] else 'false'}
    return {str(v) for row in result['rows'] for v in row.values() if v is not None}

def lab_f1(predicted,gold):
    p,g=flat_values(predicted),flat_values(gold)
    return 2*len(p&g)/(len(p)+len(g)) if p or g else 0.
