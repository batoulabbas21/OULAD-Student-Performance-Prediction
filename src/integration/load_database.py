"""Load six CSV tables transactionally into the explicitly selected project schema."""
import argparse, csv
from decimal import Decimal
from pathlib import Path
from psycopg2 import sql
from psycopg2.extras import execute_values
from common import ROOT, OUT, TABLES, settings, sha, now, write_json, db_fingerprint
FILES={'courses':'courses','student_info':'studentInfo','student_registration':'studentRegistration','assessments':'assessments','student_assessment':'studentAssessment','vle':'vle'}
INTS={'module_presentation_length','num_of_prev_attempts','studied_credits','date_registration','date_unregistration','date','date_submitted','week_from','week_to'}
IDS={'id_student','id_assessment','id_site'}
def parse(key,value):
    if value in ('','?'): return None
    if key in INTS or key in IDS:
        n=Decimal(value)
        if n!=n.to_integral_value(): raise ValueError('Non-integral '+key+': '+value)
        return str(int(n)) if key in IDS else int(n)
    if key in ('score','weight'): return Decimal(value)
    if key=='is_banked':
        if value not in ('0','1'): raise ValueError('Banked flag must be 0 or 1')
        return value=='1'
    return value
def load(cfg, source, out):
    source=Path(source); out=Path(out); started=now()
    inputs={str((source/(f+'.csv')).resolve()):sha(source/(f+'.csv')) for f in FILES.values()}
    conn=cfg.connect()
    try:
        with conn:
            with conn.cursor() as c:
                c.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(cfg.schema)))
                c.execute((ROOT/'config/postgres/schema.sql').read_text(encoding='utf-8'))
                # Replaces only these six managed tables, inside one transaction.
                for t in reversed(TABLES): c.execute(sql.SQL('DELETE FROM {}').format(sql.Identifier(t)))
                for table,name in FILES.items():
                    with (source/(name+'.csv')).open(encoding='utf-8-sig',newline='') as f:
                        reader=csv.DictReader(f); fields=reader.fieldnames
                        columns=['deadline_day' if table=='assessments' and k=='date' else k for k in fields]
                        rows=[tuple(parse(k,r[k]) for k in fields) for r in reader]
                    statement=sql.SQL('INSERT INTO {} ({}) VALUES %s').format(sql.Identifier(table),sql.SQL(',').join(map(sql.Identifier,columns))).as_string(conn)
                    if rows: execute_values(c,statement,rows,page_size=1000)
                c.execute('SELECT COUNT(*) FROM v_assessment_records r LEFT JOIN student_info i USING(code_module,code_presentation,id_student) WHERE i.id_student IS NULL')
                if c.fetchone()[0]: raise ValueError('Assessment record has no enrollment in its assessment offering')
                if any(sha(p)!=digest for p,digest in inputs.items()): raise ValueError('Input changed during load')
            signature=db_fingerprint(conn)
    finally: conn.close()
    result={'started_at_utc':started,'finished_at_utc':now(),'connection':cfg.public(),'inputs':inputs,
            'schema_sha256':sha(ROOT/'config/postgres/schema.sql'),'database':signature,'mode':'replace-six-managed-tables-in-one-transaction'}
    write_json(out/'load.json',result); print('Loaded PostgreSQL: '+str(signature['row_counts']),flush=True)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--source',type=Path,default=ROOT/'data/interim'); p.add_argument('--out',type=Path,default=OUT); a=p.parse_args()
    load(settings(),a.source,a.out)
