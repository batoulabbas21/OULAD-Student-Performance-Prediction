"""Run SPARQL over PostgreSQL via Ontop. The shared mapping is used without OWL enrichment."""
import argparse,csv,os,re,subprocess,time
from pathlib import Path
from urllib.parse import quote
from common import ROOT, OUT, MAPPING, settings, sha, now, write_json
def runtime(cfg):
    home=Path(os.environ.get('OULAD_ONTOP_HOME',ROOT/'.runtime/ontop')).resolve()
    cli=home/('ontop.bat' if os.name=='nt' else 'ontop')
    if not cli.exists(): raise FileNotFoundError('Run python src/integration/setup_ontop.py first')
    path=ROOT/'.runtime/connections'/f'{cfg.schema}.properties';path.parent.mkdir(parents=True,exist_ok=True)
    def esc(v): return str(v).replace('\\','\\\\').replace('\n','\\n').replace('\r','\\r').replace('=','\\=').replace(':','\\:')
    path.write_text('jdbc.url=jdbc:postgresql://'+cfg.host+':'+str(cfg.port)+'/'+quote(cfg.name,safe='')+'?currentSchema='+cfg.schema+'\n'+
      'jdbc.user='+esc(cfg.user)+'\njdbc.password='+esc(cfg.password)+'\njdbc.driver=org.postgresql.Driver\n',encoding='utf-8')
    return cli,path
def run_query(cfg, query, out):
    query=Path(query).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    cli,properties=runtime(cfg);name=query.stem;result_path=out/(name+'.csv')
    # Ontop parses some paths as URIs; forward slashes work on Windows and Linux.
    rel=lambda p: Path(os.path.relpath(p,ROOT)).as_posix()
    args=[str(cli),'query','-m',rel(MAPPING),'-p',rel(properties),'-q',rel(query),'-o',rel(result_path)]
    started=now();t=time.perf_counter()
    proc=subprocess.run(args,cwd=ROOT,env=dict(os.environ,ONTOP_LOG_LEVEL='DEBUG'),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    log=(proc.stdout+'\n'+proc.stderr).replace(cfg.password,'[REDACTED]')
    (out/(name+'.log')).write_text(log,encoding='utf-8')
    if proc.returncode: raise RuntimeError(f'Ontop failed for {name}; inspect {out/(name+".log")}')
    with result_path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    candidates=[s for s in re.findall(r'(?is)(SELECT\s.+?)(?=\n\d\d:\d\d:\d\d|\Z)',log) if re.search(r'\bFROM\b',s,re.I)]
    sql_text=max(candidates,key=len) if candidates else ''
    if sql_text: (out/(name+'.sql.txt')).write_text(sql_text.strip()+'\n',encoding='utf-8')
    meta={'started_at_utc':started,'finished_at_utc':now(),'duration_seconds':round(time.perf_counter()-t,3),
          'rows':len(rows),'query_sha256':sha(query),'mapping_sha256':sha(MAPPING),'sql_captured':bool(sql_text),
          'ontology_reasoning':'disabled; no -t ontology argument','connection':cfg.public()}
    write_json(out/(name+'.json'),meta)
    print(f'Ontop {name}: {len(rows)} rows',flush=True)
    return fields,rows,meta
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--query',type=Path,default=ROOT/'queries/01_enrollments.rq');p.add_argument('--out',type=Path,default=OUT/'manual-virtual')
    p.add_argument('--serve',action='store_true');p.add_argument('--port',type=int,default=8085);a=p.parse_args();cfg=settings()
    if a.serve:
        cli,props=runtime(cfg)
        raise SystemExit(subprocess.call([str(cli),'endpoint','-m',Path(os.path.relpath(MAPPING,ROOT)).as_posix(),'-p',Path(os.path.relpath(props,ROOT)).as_posix(),'--port',str(a.port)],cwd=ROOT))
    run_query(cfg,a.query,a.out)
