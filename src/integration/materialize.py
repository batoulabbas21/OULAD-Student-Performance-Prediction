"""Execute the shared R2RML mapping with Morph-KGC, saving an asserted RDF snapshot."""
import argparse, time
from pathlib import Path
import morph_kgc
from common import ROOT, OUT, MAPPING, settings, sha, now, write_json, read_guard, db_fingerprint
def materialize(cfg, out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
    # URL includes a schema-specific search_path; credentials never enter reports.
    config='[CONFIGURATION]\nlogging_level=WARNING\nnumber_of_processes=1\n\n[OULAD]\n'
    config+='mappings='+str(MAPPING)+'\ndb_url='+cfg.url().render_as_string(hide_password=False)+'\n'
    graph=morph_kgc.materialize(config)
    target=out/'oulad-mapped.nt';graph.serialize(target,format='nt',encoding='utf-8')
    result={'finished_at_utc':now(),'triples':len(graph),'duration_seconds':round(time.perf_counter()-start,3),
            'mapping_sha256':sha(MAPPING),'output_sha256':sha(target),'inference':'none; asserted mapping output only'}
    write_json(out/'materialization.json',result)
    print(f'Materialized {len(graph)} triples.',flush=True)
    return graph,result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT/'full');a=p.parse_args()
    cfg=settings()
    with read_guard(cfg) as conn:
        graph,result=materialize(cfg,a.out);result['database']=db_fingerprint(conn);write_json(a.out/'materialization.json',result)
