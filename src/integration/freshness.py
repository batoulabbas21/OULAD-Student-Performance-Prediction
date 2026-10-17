"""Demonstrate freshness on a separately loaded teaching schema, restoring the edited score."""
from decimal import Decimal
from common import ROOT, write_json, db_fingerprint, read_guard
from load_database import load
from materialize import materialize
from run_ontop import run_query
from compare import rdf_rows,answers
QUERY='PREFIX edu: <https://example.org/oulad/schema#> SELECT (COUNT(?r) AS ?low) WHERE { ?r a edu:AssessmentRecord; edu:score ?score . FILTER(?score < 40) }'
def demonstrate(cfg,source,out):
    cfg=cfg.with_schema(cfg.schema+'_demo');out.mkdir(parents=True,exist_ok=True)
    load(cfg,source,out);query=out/'freshness.rq';query.write_text(QUERY,encoding='utf-8')
    with read_guard(cfg) as c:
        original=db_fingerprint(c)
        old,_=materialize(cfg,out/'before')
        fields,before,_=run_query(cfg,query,out/'virtual-before')
    conn=cfg.connect()
    try:
        with conn,conn.cursor() as cur:
            cur.execute('SELECT id_student,id_assessment,score FROM student_assessment WHERE score<40 ORDER BY id_student,id_assessment LIMIT 1')
            student,assessment,score=cur.fetchone()
            cur.execute('UPDATE student_assessment SET score=99 WHERE id_student=%s AND id_assessment=%s',(student,assessment))
        try:
            with read_guard(cfg):
                _,after,_=run_query(cfg,query,out/'virtual-after')
                _,stale=rdf_rows(old,QUERY)
                new,_=materialize(cfg,out/'after');_,refreshed=rdf_rows(new,QUERY)
                assert answers(fields,before)==answers(fields,stale)
                assert int(before[0]['low'])==int(after[0]['low'])+1
                assert answers(fields,after)==answers(fields,refreshed)
        finally:
            with conn,conn.cursor() as cur:
                cur.execute('UPDATE student_assessment SET score=%s WHERE id_student=%s AND id_assessment=%s',(score,student,assessment))
        with read_guard(cfg) as c: restored=db_fingerprint(c)==original
        assert restored
    finally: conn.close()
    result={'teaching_schema':cfg.schema,'original_score':str(score),'temporary_score':'99',
        'virtual_before':int(before[0]['low']),'virtual_after_commit':int(after[0]['low']),
        'old_snapshot_after_commit':int(stale[0]['low']),'new_snapshot':int(refreshed[0]['low']),
        'database_restored':restored,'passed':True,'note':'Separate database schema; example outputs retain before/after teaching states.'}
    write_json(out/'freshness.json',result);return result
