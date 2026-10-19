"""Local correctness tests and verification of the latest saved API evaluation."""
import sys,json,yaml,argparse,threading
from urllib.request import urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/access'))
from common import ROOT,CONFIG,OUT,now,sources,sha,read_json,write_json
from access_layer import AccessLayer
from grounding import generate
from query_engine import check_query,run_query
from oracle import expected
from scoring import score,lab_f1
from report import page,esc

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--local-only',action='store_true');args=parser.parse_args()
    checks=[]
    def check(name,condition,detail=None):
        checks.append({'name':name,'passed':bool(condition),'detail':detail})
        if not condition:raise AssertionError(name+': '+str(detail))
    d=generate();layer=AccessLayer();questions=yaml.safe_load((CONFIG/'questions.yaml').read_text());gold=expected()
    check('Example and held-out question wording are disjoint',not {q['question'].lower() for q in questions}&{q['question'].lower() for q in layer.examples})
    check('Graph contains the complete AAA asserted extract',d['fact_triples']==28470)
    check('Available classes include Assessment via subclasses', 'https://example.org/oulad/schema#Assessment' in d['classes'])
    check('Unloaded interaction data is not advertised','https://example.org/oulad/schema#DailyInteraction' not in d['classes'])
    for q in questions:
        if q['refuse']:continue
        check(q['id']+' gold passes query validation',not check_query(q['gold'],d))
        check(q['id']+' RDF agrees with independent CSV answer',score(run_query(q['gold']),gold[q['oracle']])['exact'],gold[q['oracle']])
    for example in layer.examples:
        r=layer.answer(example['question'],catalog=True)
        check('Catalog '+example['id']+' executes',r['status']=='answered' and bool(r['result']['rows']))
    rejected={
        'syntax':'SELECT WHERE {',
        'invented predicate':'SELECT ?s WHERE {?s edu:grade ?v}',
        'alias predicate':'PREFIX x:<https://example.org/oulad/schema#> SELECT ?s WHERE {?s x:grade ?v}',
        'invented class':'SELECT ?s WHERE {?s a edu:Teacher}',
        'unavailable class':'SELECT ?s WHERE {?s a edu:DailyInteraction}',
        'unknown full IRI':'SELECT ?s WHERE {?s <https://example.org/oulad/schema#grade> ?v}',
        'foreign predicate':'SELECT ?s WHERE {?s <https://unknown.test/p> ?v}',
        'SERVICE':'SELECT ?s WHERE {SERVICE <https://example.test/sparql> {?s ?p ?o}}',
        'FROM':'SELECT ?s FROM <file:///secret.ttl> WHERE {?s ?p ?o}',
        'named GRAPH':'SELECT ?s WHERE {GRAPH <https://example.test/g> {?s ?p ?o}}',
        'update':'DELETE WHERE {?s ?p ?o}',
        'construct':'CONSTRUCT {?s ?p ?o} WHERE {?s ?p ?o}'}
    for name,query in rejected.items():check('Reject '+name,bool(check_query(query,d)),check_query(query,d))
    literal='SELECT ?e WHERE {?e edu:region "edu:FakeClass SERVICE"}'
    check('Literal text is not mistaken for a predicate or operation',not check_query(literal,d))
    empty=run_query('SELECT ?s WHERE {?s a edu:Student FILTER(false)}');negative=run_query('ASK {FILTER(false)}')
    check('Empty result equals empty gold',score(empty,empty)['f1']==1)
    check('Failed execution is not a correct empty answer',score(None,empty)['f1']==0)
    check('ASK false is a valid false answer',negative=={'boolean':False} and score(negative,negative)['f1']==1)
    p={'columns':['offering','count'],'rows':[{'offering':'2013J','count':'365'},{'offering':'2014J','count':'383'}]}
    g={'columns':['offering','count'],'rows':[{'offering':'2013J','count':'383'},{'offering':'2014J','count':'365'}]}
    check('Row scorer detects swapped presentation counts that the lab set misses',score(p,g)['f1']==0 and lab_f1(p,g)==1)
    class Scripted:
        def __init__(self,replies):self.replies=iter(replies);self.prompts=[]
        def ask(self,prompt):self.prompts.append(prompt);return next(self.replies)
    m=Scripted(['SELECT ?r WHERE {?r edu:grade ?v}',questions[5]['gold']]);layer.model=m
    repaired=layer.answer(questions[5]['question'])
    check('Scripted invalid predicate is repaired using feedback',len(repaired['attempts'])==2 and score(repaired['result'],gold['low'])['exact'])
    check('Repair prompt includes previous query and diagnostics','edu:grade' in m.prompts[1] and 'CHECK FEEDBACK' in m.prompts[1])
    layer.model=Scripted(['SELECT ?s WHERE {?s edu:bad ?x}']*3);invalid=layer.answer('Test invalid generation')
    check('Three failed attempts are invalid, not grounded refusal',invalid['status']=='invalid' and len(invalid['attempts'])==3)
    layer.model=Scripted(['REFUSE: Personal causes are not recorded.']);check('Explicit model refusal is distinguishable',layer.answer('Why did students withdraw?')['status']=='refused')
    check('Semantically wrong but legal queries need answer evaluation',not check_query('SELECT (COUNT(?e) AS ?count) WHERE {?e a edu:Enrollment}',d))
    try: run_query('SELECT ?s WHERE {?s ?p ?o}',timeout=0.001)
    except RuntimeError as e:check('A slow worker can be terminated','exceeded' in str(e))
    else:check('A slow worker can be terminated',False)
    from serve import create_server
    server=create_server(layer,port=0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    try:
        check('HTTP browser page is available','Ask the OULAD graph' in urlopen(base).read().decode())
        check('HTTP health reports catalog mode',json.load(urlopen(base+'/health'))['mode']=='catalog')
        response=json.load(urlopen(base+'/?'+urlencode({'question':layer.examples[0]['question']})))
        check('TEXT2SPARQL contract returns dataset, question, query and evidence',response['status']=='answered' and all(k in response for k in ['dataset','question','query','result','attempts']))
        response=json.load(urlopen(base+'/?'+urlencode({'question':'unrecognized catalog wording'})))
        check('Unsupported catalog question is explicit, not an AI refusal',response['status']=='unsupported' and 'FILTER(false)' in response['query'])
        try:urlopen(base+'/?'+urlencode({'question':'hello','dataset':'wrong'}))
        except HTTPError as e:check('Wrong dataset returns HTTP 400',e.code==400)
        else:check('Wrong dataset returns HTTP 400',False)
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
    latest=OUT/'latest-evaluation.json'
    if latest.exists() and not args.local_only:
        pointer=read_json(latest);folder=(ROOT/pointer['directory']).resolve();check('Latest path remains within access runs',folder.is_relative_to(OUT/'runs'))
        s=read_json(folder/'summary.json');manifest=read_json(folder/'manifest.json')
        check('Saved evaluation completed',s['completed'])
        check('Saved evaluation inputs match current files',s['source_sha256']==sources())
        check('Saved evaluation outputs match fingerprints',all(sha(folder/n)==h for n,h in manifest['files'].items()))
        answers=read_json(folder/'answers.json')
        check('Stored answer scores independently recompute',all(score(r['response']['result'],r['expected_result'])==r['score'] for r in answers if not r['expected_refusal']))
    result={'checked_at_utc':now(),'passed':all(c['passed'] for c in checks),'checks':checks,'count':len(checks),'scope':'Local implementation tests; scripted model responses are fault injections, never an LLM benchmark.'}
    write_json(OUT/'verification.json',result)
    body='<p>All '+str(len(checks))+' checks passed. Scripted repair tests verify the mechanism; they do not measure Gemini accuracy.</p><ul>'+''.join('<li>'+esc(c['name'])+'</li>' for c in checks)+'</ul>'
    (OUT/'local-results.html').write_text(page('Session 7 · local verification',body),encoding='utf-8')
    print(f'{len(checks)}/{len(checks)} access checks passed. See outputs/access/local-results.html.')

if __name__=='__main__':main()
