"""Run the complete Session 6 protocol; retain separate evidence for every execution."""
import argparse,importlib.metadata,json,sys,uuid,traceback
from pathlib import Path
from rdflib import Graph,Namespace,URIRef,Literal,RDF,XSD
from common import ROOT,OUT,sha,now,read_json,write_json,source_graph
from build_graph import build
from checks import verify
import classification,link_prediction
from report import render

def run():
    protocol_path=ROOT/'config/learning/protocol.json';protocol=read_json(protocol_path)
    source,receipts=source_graph();run_id=uuid.uuid4().hex;out=OUT/'runs'/run_id;out.mkdir(parents=True)
    inputs=[source,protocol_path,ROOT/'ontology/education.rdfs.ttl',ROOT/'evaluation/verify_learning.py']+receipts
    inputs+=sorted((ROOT/'src/learning').glob('*.py'))+sorted((ROOT/'data/interim').glob('*.csv'))
    source_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    started=now()
    try:
        write_json(out/'protocol.json',protocol);g=Graph().parse(source)
        rows,a,records,early,cohort=build(g,out/'graph',protocol)
        checks=verify(g,rows,a,records,early,out/'graph',protocol)
        print(f'Input checks: {len(checks)} passed; {cohort["eligible_day60"]} eligible enrollments.',flush=True)
        clf=classification.execute(rows,a,early,out/'classification',protocol)
        links=link_prediction.execute(rows,a,records,out/'links',protocol)
        def check(name,condition):
            checks.append({'check':name,'passed':bool(condition)})
            if not condition:raise AssertionError(name)
        check('Temporal split has no shared students',clf['split']['student_overlap']==0)
        check('Every temporal prediction uses the same held-out population',all(m['n']==clf['split']['test_rows'] and m['actual_unsuccessful']==clf['split']['test_unsuccessful'] for m in clf['metrics'] if m['split']=='temporal'))
        check('All three predefined GraphSAGE seeds ran',sorted(m['seed'] for m in clf['metrics'] if m['split']=='temporal' and m['model']=='GraphSAGE')==protocol['classification_seeds'])
        check('Deliberately invalid label control exposes perfect ranking',next(m for m in clf['metrics'] if m['split']=='leak_control')['average_precision']==1)
        check('All three TransE splits retain the complete link partition',all(r['train_links']+r['validation_links']+r['test_links']==3107 and r['cold_entity_test_links']==0 for r in links['seeds']))
        check('Source inputs unchanged during learning',all(sha(ROOT/n)==h for n,h in source_hashes.items()))
        versions={p:importlib.metadata.version(p) for p in ['torch','torch-geometric','pykeen','scikit-learn','rdflib','pandas','numpy','matplotlib']}
        summary={'run_id':run_id,'started_at_utc':started,'finished_at_utc':now(),'passed':True,'source_graph':source.relative_to(ROOT).as_posix(),'source_sha256':source_hashes,'protocol':protocol,'cohort':cohort,'classification':clf,'link_prediction':links,'checks':checks,'versions':versions}
        summary['interpretation']=render(out,summary);write_json(out/'summary.json',summary);write_json(out/'checks.json',checks)
        prov=Namespace('http://www.w3.org/ns/prov#');dct=Namespace('http://purl.org/dc/terms/');pg=Graph();pg.bind('prov',prov);pg.bind('dcterms',dct)
        activity=URIRef('https://example.org/oulad/run/learning/'+run_id);pg.add((activity,RDF.type,prov.Activity))
        pg.add((activity,prov.startedAtTime,Literal(started,datatype=XSD.dateTime)));pg.add((activity,prov.endedAtTime,Literal(now(),datatype=XSD.dateTime)))
        agent=URIRef('urn:oulad:learning-software:sha256:'+sha(Path(__file__)));pg.add((agent,RDF.type,prov.SoftwareAgent));pg.add((agent,dct.description,Literal(json.dumps(versions))));pg.add((activity,prov.wasAssociatedWith,agent))
        for n,h in source_hashes.items():
            e=URIRef('urn:sha256:'+h);pg.add((e,RDF.type,prov.Entity));pg.add((e,prov.atLocation,URIRef((ROOT/n).as_uri())));pg.add((activity,prov.used,e))
        outputs={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
        for n,h in outputs.items():
            e=URIRef('urn:sha256:'+h);pg.add((e,RDF.type,prov.Entity));pg.add((e,dct.title,Literal(n)));pg.add((e,prov.wasGeneratedBy,activity))
        pg.serialize(out/'provenance.ttl',format='turtle');outputs['provenance.ttl']=sha(out/'provenance.ttl')
        write_json(out/'manifest.json',{'run_id':run_id,'inputs':source_hashes,'outputs':outputs,'note':'Manifest and repeatable verification.json excluded from self-fingerprinting.'})
        # Verify before publishing the successful-run pointer.
        sys.path.insert(0,str(ROOT/'evaluation'))
        from verify_learning import verify_saved
        verify_saved(out)
        write_json(OUT/'latest.json',{'run_id':run_id,'directory':out.relative_to(ROOT).as_posix(),'passed':True})
        (OUT/'learning-results.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=runs/'+run_id+'/report.html"><a href="runs/'+run_id+'/report.html">Open latest learning results</a>',encoding='utf-8')
        print(f'{len(checks)}/{len(checks)} learning checks passed. Report: {out/"report.html"}',flush=True)
    except Exception as e:
        write_json(out/'failure.json',{'run_id':run_id,'failed_at_utc':now(),'error':str(e)});print('FAILED evidence: '+str(out),flush=True);raise
if __name__=='__main__':run()
