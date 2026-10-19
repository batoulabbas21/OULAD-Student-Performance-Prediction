"""Three-condition benchmark: execute held-out gold queries and reconcile with CSV."""
import argparse,statistics,uuid,yaml,sys
from importlib.metadata import version
from rdflib import Graph,Namespace,URIRef,Literal,RDF,XSD
from common import ROOT,CONFIG,OUT,now,sources,sha,write_json
from grounding import generate
from access_layer import AccessLayer,Model
from query_engine import run_query
from oracle import expected
from scoring import score,lab_f1
from report import write_report

def provenance(folder,summary):
    PROV=Namespace('http://www.w3.org/ns/prov#'); EX=Namespace('https://example.org/oulad/provenance#')
    g=Graph();g.bind('prov',PROV);g.bind('ex',EX);run=URIRef('https://example.org/oulad/run/access/'+summary['run_id'])
    g.add((run,RDF.type,PROV.Activity));g.add((run,PROV.startedAtTime,Literal(summary['started_at_utc'],datatype=XSD.dateTime)))
    g.add((run,PROV.endedAtTime,Literal(summary['finished_at_utc'],datatype=XSD.dateTime)))
    g.add((run,EX.mode,Literal(summary['mode'])));g.add((run,EX.model,Literal(summary['model'])))
    for name,fingerprint in summary['source_sha256'].items():
        entity=URIRef(run+'/input/'+name);g.add((run,PROV.used,entity));g.add((entity,RDF.type,PROV.Entity));g.add((entity,EX.path,Literal(name)));g.add((entity,EX.sha256,Literal(fingerprint)))
    for path in sorted(folder.glob('*')):
        if not path.is_file():continue
        entity=URIRef(run+'/output/'+path.name);g.add((entity,PROV.wasGeneratedBy,run));g.add((entity,EX.sha256,Literal(sha(path))))
    g.serialize(folder/'provenance.ttl',format='turtle')

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['live','record','replay'],default='replay');p.add_argument('--env-file');p.add_argument('--model')
    p.add_argument('--max-requests',type=int,default=45);p.add_argument('--setting',choices=['schema','examples','repair'])
    a=p.parse_args();run=uuid.uuid4().hex;folder=OUT/'runs'/run;folder.mkdir(parents=True)
    summary={'run_id':run,'started_at_utc':now(),'mode':a.mode,'source_sha256':sources(),'completed':False,'settings':{},'versions':{x:version(x) for x in ['rdflib','pyoxigraph','requests','pandas','PyYAML']}}
    records=[];model=Model(a.mode,a.env_file,a.model,a.max_requests);summary['model']=model.model
    try:
        generate(folder);layer=AccessLayer(model);questions=yaml.safe_load((CONFIG/'questions.yaml').read_text(encoding='utf-8'));oracles=expected();golds={}
        assert not {q['question'].casefold() for q in questions}&{q['question'].casefold() for q in layer.examples},'Examples overlap test questions.'
        for q in questions:
            if q['refuse']:continue
            golds[q['id']]=run_query(q['gold'])
            if not score(golds[q['id']],oracles[q['oracle']])['exact']:raise ValueError('Gold answer disagrees with independent CSV calculation: '+q['id'])
        write_json(folder/'gold-answers.json',golds)
        for setting in ([a.setting] if a.setting else ['schema','examples','repair']):
            print('Evaluating '+setting,flush=True);rows=[]
            for q in questions:
                response=layer.answer(q['question'],setting)
                row={'setting':setting,'id':q['id'],'question':q['question'],'expected_refusal':q['refuse'],'response':response}
                if q['refuse']:row['correct_refusal']=response['status']=='refused'
                else:
                    row['expected_result']=golds[q['id']];row['score']=score(response['result'],golds[q['id']]);row['lab_value_set_f1']=lab_f1(response['result'],golds[q['id']])
                rows.append(row);records.append(row);write_json(folder/'answers.json',records);write_json(folder/'model-calls.json',model.calls)
                print(f"  {q['id']}: {response['status']}"+(f" F1={row['score']['f1']:.3f}" if 'score' in row else ''),flush=True)
            answerable=[r for r in rows if not r['expected_refusal']];refusals=[r for r in rows if r['expected_refusal']]
            summary['settings'][setting]={'mean_row_f1':statistics.fmean(r['score']['f1'] for r in answerable),
                'mean_lab_value_set_f1':statistics.fmean(r['lab_value_set_f1'] for r in answerable),
                'answerable':len(answerable),'exact_answers':sum(r['score']['exact'] for r in answerable),'unanswerable':len(refusals),
                'correct_refusals':sum(r['correct_refusal'] for r in refusals),'wrong_refusals':sum(r['response']['status']=='refused' for r in answerable),
                'invalid':sum(r['response']['status']=='invalid' for r in rows),
                'successful_repairs':sum(len(r['response']['attempts'])>1 and r['response']['status']=='answered' for r in rows)}
        if sources()!=summary['source_sha256']:raise RuntimeError('An input changed during the evaluation.')
        summary['completed']=True
    except Exception as e:
        summary['error']=str(e); print('Evaluation incomplete: '+str(e),file=sys.stderr)
    finally:
        summary['finished_at_utc']=now();summary['api_requests']=model.requests;summary['recorded_calls']=len(model.calls)
        write_json(folder/'model-calls.json',model.calls);write_json(folder/'answers.json',records);write_json(folder/'summary.json',summary)
        write_report(folder,summary,records);provenance(folder,summary)
        write_json(folder/'manifest.json',{'run_id':run,'files':{f.name:sha(f) for f in sorted(folder.glob('*')) if f.is_file() and f.name!='manifest.json'}})
        if summary['completed']:write_json(OUT/'latest-evaluation.json',{'run_id':run,'directory':folder.relative_to(ROOT).as_posix(),'completed':True})
        print('Report: '+str(folder/'report.html'),flush=True)
    if not summary['completed']:raise SystemExit(1)

if __name__=='__main__':main()
