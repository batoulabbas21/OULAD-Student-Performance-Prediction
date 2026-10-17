"""Run Session 5 end to end and stop on any unexplained mapping/query/validation difference."""
import argparse,html,importlib.metadata,json,subprocess,sys,uuid
from pathlib import Path
from rdflib import Graph
from common import ROOT,OUT,MAPPING,TABLES,settings,sha,now,write_json,read_guard,db_fingerprint
from load_database import load
from materialize import materialize
from run_ontop import run_query
from compare import compare_graphs,rdf_rows,answers,save_csv
from freshness import demonstrate
from provenance import record,PROV
from rdflib import URIRef

def execute(fixture=False,skip_freshness=False):
    cfg=settings()
    if fixture: cfg=cfg.with_schema(cfg.schema+'_fixture')
    source=ROOT/('evaluation/fixtures/integration' if fixture else 'data/interim')
    reference_path=ROOT/('evaluation/fixtures/integration/expected.ttl' if fixture else 'data/processed/oulad.ttl')
    run_id=uuid.uuid4().hex
    out=OUT/'runs'/run_id;out.mkdir(parents=True)
    started=now();checks=[];comparisons=[]
    def check(name,condition,detail=None):
        checks.append({'check':name,'passed':bool(condition),'detail':detail})
        if not condition: raise AssertionError(name+': '+str(detail))
        print('PASS: '+name,flush=True)
    inputs=[reference_path,MAPPING,ROOT/'config/postgres/schema.sql',ROOT/'ontology/education.rdfs.ttl',ROOT/'shapes/oulad-shapes.ttl',ROOT/'src/validation/validate.py']+sorted((ROOT/'src/integration').glob('*.py'))+sorted(source.glob('*.csv'))
    inputs+=sorted((ROOT/'queries').glob('0[1-6]*.rq'))+sorted((ROOT/'queries/integration').glob('*.rq'))+sorted((ROOT/'queries/integration/sql').glob('*.sql'))
    # Include pinned runtime download evidence and the runner's declared dependencies.
    inputs += [ROOT/'requirements-integration.txt', ROOT/'evaluation/verify_integration.py']
    runtime_manifest=ROOT/'.runtime/ontop/download-manifest.json'
    if runtime_manifest.exists(): inputs.append(runtime_manifest)
    fingerprints={str(p.relative_to(ROOT).as_posix()):sha(p) for p in inputs}
    try:
        loaded=load(cfg,source,out)
        with read_guard(cfg) as conn:
            signature=db_fingerprint(conn)
            check('Database matches the load receipt',signature==loaded['database'])
            with conn.cursor() as c:
                for name,statement in [
                    ('Duplicate enrollment key is rejected','INSERT INTO student_info SELECT * FROM student_info LIMIT 1'),
                    ('Score 101 is rejected','UPDATE student_assessment SET score=101 WHERE (id_student,id_assessment)=(SELECT id_student,id_assessment FROM student_assessment LIMIT 1)'),
                    ('Unknown offering is rejected',"UPDATE assessments SET code_presentation='NOT_REAL' WHERE id_assessment=(SELECT id_assessment FROM assessments LIMIT 1)")]:
                    c.execute('SAVEPOINT invalid_example');rejected=False
                    try: c.execute(statement)
                    except Exception as exc:
                        if getattr(exc,'pgcode',None) not in ('23505','23514','23503'): raise
                        rejected=True
                    finally: c.execute('ROLLBACK TO SAVEPOINT invalid_example');c.execute('RELEASE SAVEPOINT invalid_example')
                    check(name,rejected)
            # SHARE locks protect a common database state across Morph and Ontop connections.
            reference=Graph().parse(reference_path)
            mapped,mat=materialize(cfg,out)
            difference=compare_graphs(reference,mapped,out/'graph-comparison.json')
            check('Mapped graph matches the reference RDF terms',difference['equal'],difference)
            check('Expected snapshot triple count',len(mapped)==(299 if fixture else 28470))
            reference.parse(ROOT/'ontology/education.rdfs.ttl')
            materialized=mapped+Graph().parse(ROOT/'ontology/education.rdfs.ttl')
            for original in sorted((ROOT/'queries').glob('0[1-6]*.rq')):
                query=ROOT/'queries/integration'/original.name if original.name.startswith('02_') else original
                fields,expected=rdf_rows(reference,original.read_text(encoding='utf-8'))
                _,mapped_rows=rdf_rows(materialized,query.read_text(encoding='utf-8'))
                vfields,virtual,meta=run_query(cfg,query,out/'virtual')
                sql_path=ROOT/'queries/integration/sql'/(original.stem+'.sql')
                with conn.cursor() as c:
                    c.execute(sql_path.read_text(encoding='utf-8'));sf=[d.name for d in c.description];sql_rows=[dict(zip(sf,row)) for row in c.fetchall()]
                check(original.stem+': SQL, RDF and virtual answers match',set(fields)==set(vfields)==set(sf) and answers(fields,expected)==answers(fields,mapped_rows)==answers(fields,virtual)==answers(fields,sql_rows),{'rows':len(expected)})
                check(original.stem+': generated SQL captured',meta['sql_captured'])
                save_csv(out/'reference'/(original.stem+'.csv'),fields,expected);save_csv(out/'sql'/(original.stem+'.csv'),fields,sql_rows)
                save_csv(out/'materialized'/(original.stem+'.csv'),fields,mapped_rows)
                comparisons.append({'query':original.stem,'rows':len(expected),'all_equal':True,'ontop_seconds':meta['duration_seconds']})
            cmd=[sys.executable,str(ROOT/'src/validation/validate.py'),'--data',str(out/'oulad-mapped.nt'),'--out',str(out/'shacl')]
            validation=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=600)
            (out/'shacl-command.log').write_text(validation.stdout+'\n'+validation.stderr,encoding='utf-8')
            check('Mapped graph passes the existing SHACL gate',validation.returncode==0)
            shacl=json.loads((out/'shacl/summary.json').read_text(encoding='utf-8'))
            check('Expected SHACL warnings remain visible',shacl['severity_counts']=={'Violation':0,'Warning':3 if fixture else 5,'Info':0})
            check('Database unchanged during baseline comparisons',db_fingerprint(conn)==signature)
        freshness=demonstrate(cfg,source,out/'freshness') if not skip_freshness else None
        if freshness: check('Committed database changes and stale RDF snapshots are distinguished',freshness['passed'] and freshness['database_restored'])
        check('Evidence inputs unchanged during the run',all(sha(ROOT/name)==digest for name,digest in fingerprints.items()))
        summary={'run_id':run_id,'started_at_utc':started,'finished_at_utc':now(),'passed':True,'scope':'fixture' if fixture else 'AAA full',
                 'connection':cfg.public(),'database':signature,'checks':checks,'query_comparisons':comparisons,'materialization':mat,
                 'graph_comparison':difference,'shacl':{'severity_counts':shacl['severity_counts'],'gate_passed':shacl['gate_passed'],'run_id':shacl['run_id']},
                 'freshness':freshness,'source_sha256':fingerprints,'versions':{n:importlib.metadata.version(n) for n in ('morph-kgc','rdflib','pyshacl','SQLAlchemy','psycopg2-binary')},
                 'ontop_version':'5.5.0','inference_policy':'Asserted mapping comparison; no ontology supplied to Ontop; RDFS hierarchy available to local query 02 and SHACL.'}
        write_json(out/'summary.json',summary)
        rows=''.join('<tr><td>'+html.escape(c['check'])+'</td><td>PASS</td></tr>' for c in checks)
        links=''.join('<li><a href="virtual/'+x['query']+'.csv">'+x['query']+'</a>: '+str(x['rows'])+' matching rows · <a href="virtual/'+x['query']+'.sql.txt">generated SQL</a></li>' for x in comparisons)
        report=f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OULAD integration results</title>
<style>body{{font:16px/1.65 Segoe UI,Arial;margin:40px auto;max-width:1000px;padding:0 24px;color:#173b3b;background:#f3f7f5}}main{{background:white;padding:32px;border-radius:12px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;border-bottom:1px solid #dce6e5;text-align:left}}a{{color:#087064}}code{{overflow-wrap:anywhere}}.pass{{color:#087064}}</style>
<main><h1>PostgreSQL → RDF and live SPARQL</h1><p class="pass"><b>PASS · {len(checks)} checks · {summary['scope']}</b></p>
<p>{len(mapped):,} mapped triples agree with the reference graph after documented RDF literal normalization. All six answer multisets agree across SQL, the reference graph, the mapped graph and Ontop.</p>
<p>SHACL: 0 violations and {3 if fixture else 5} warnings. Gate passes; unknown values remain unknown.</p>
<h2>Two uses of the same mapping</h2><p>Morph-KGC stores an RDF snapshot. Ontop translates each SPARQL request to SQL over PostgreSQL. No full OWL ontology was supplied to Ontop.</p>
<h2>Questions and SQL</h2><ul>{links}</ul><h2>Freshness experiment</h2><pre>{html.escape(json.dumps(freshness,indent=2))}</pre>
<p>The experiment uses a separate teaching schema. Its edited score was restored. Timings include local runtime startup and are not a general performance benchmark.</p>
<h2>Verification</h2><table><tr><th>Check</th><th>Result</th></tr>{rows}</table>
<h2>Evidence</h2><p><a href="summary.json">Run summary</a> · <a href="graph-comparison.json">Graph comparison</a> · <a href="shacl/report.html">SHACL report</a> · <a href="provenance.ttl">Run provenance</a></p>
<p>Run <code>{run_id}</code><br>Started {started}<br>Finished {summary['finished_at_utc']} (UTC)</p></main></html>"""
        (out/'report.html').write_text(report,encoding='utf-8');record(out,summary,inputs)
        # Independently re-read the PROV record and verify all generated file hashes.
        prov=Graph().parse(out/'provenance.ttl');activity=URIRef('https://example.org/oulad/run/integration/'+run_id)
        expected={URIRef('urn:sha256:'+sha(p)) for p in out.rglob('*') if p.is_file() and p.name not in ('provenance.ttl','provenance-check.json')}
        assert set(prov.subjects(PROV.wasGeneratedBy,activity))==expected
        expected_inputs={URIRef('urn:sha256:'+sha(p)) for p in inputs}
        expected_inputs.add(URIRef('urn:oulad:database:sha256:'+signature['sha256']))
        assert set(prov.objects(activity,PROV.used))==expected_inputs
        write_json(out/'provenance-check.json',{'passed':True,'generated_entities_checked':len(expected),'input_entities_checked':len(expected_inputs)})
        write_json(OUT/('latest-fixture.json' if fixture else 'latest-full.json'),{'run_id':run_id,'directory':out.relative_to(ROOT).as_posix(),'passed':True})
        # A stable landing page keeps old run directories and links intact.
        (OUT/('fixture-results.html' if fixture else 'integration-results.html')).write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=runs/'+run_id+'/report.html"><a href="runs/'+run_id+'/report.html">Open the latest successful integration report</a>',encoding='utf-8')
        print(f'{len(checks)}/{len(checks)} checks passed. Report: {out/"report.html"}',flush=True)
        return summary
    except Exception as exc:
        write_json(out/'failure.json',{'run_id':run_id,'failed_at_utc':now(),'passed':False,'error':str(exc).replace(cfg.password,'[REDACTED]'),'checks':checks})
        print('FAILED run evidence: '+str(out),flush=True);raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',action='store_true');p.add_argument('--skip-freshness',action='store_true');a=p.parse_args();execute(a.fixture,a.skip_freshness)
