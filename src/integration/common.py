"""Shared connection and evidence helpers. No credentials are written to reports."""
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib, json, os, re
from pathlib import Path
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, URL

ROOT=Path(__file__).resolve().parents[2]
TABLES=('courses','student_info','student_registration','assessments','student_assessment','vle')
MAPPING=ROOT/'mappings/oulad-mapping.ttl'
OUT=ROOT/'outputs/integration'
def now(): return datetime.now(timezone.utc).isoformat()
def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def write_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,default=str)+'\n',encoding='utf-8')
def settings():
    local={}
    path=ROOT/'.env.integration'
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.lstrip().startswith('#'):
                k,v=line.split('=',1); local[k.strip()]=v.strip()
    def get(key, default=''): return os.environ.get(key, local.get(key, default))
    cfg=DB(get('OULAD_DB_HOST','127.0.0.1'),int(get('OULAD_DB_PORT','5433')),
           get('OULAD_DB_NAME','oulad'),get('OULAD_DB_USER','oulad'),
           get('OULAD_DB_PASSWORD'),get('OULAD_DB_SCHEMA','oulad'))
    if not cfg.password: raise ValueError('Database password missing: run python src/integration/init_config.py')
    return cfg
@dataclass(frozen=True)
class DB:
    host:str; port:int; name:str; user:str; password:str; schema:str
    def __post_init__(self):
        if not re.fullmatch(r'[a-z][a-z0-9_]*',self.schema): raise ValueError('Invalid project schema name')
    def connect(self):
        return psycopg2.connect(host=self.host,port=self.port,dbname=self.name,user=self.user,
                               password=self.password,options=f'-c search_path={self.schema}',connect_timeout=10)
    def url(self): return URL.create('postgresql+psycopg2',username=self.user,password=self.password,host=self.host,port=self.port,database=self.name,query={'options':f'-csearch_path={self.schema}'})
    def public(self): return {'host':self.host,'port':self.port,'database':self.name,'schema':self.schema}
    def with_schema(self,name): return replace(self,schema=name)
def db_fingerprint(conn):
    h=hashlib.sha256(); counts={}
    with conn.cursor() as c:
        for table in TABLES:
            c.execute(sql.SQL('SELECT t.* FROM {} t ORDER BY to_jsonb(t)::text').format(sql.Identifier(table)))
            rows=c.fetchall(); counts[table]=len(rows)
            h.update(json.dumps([table,[x.name for x in c.description],rows],default=str,ensure_ascii=False,separators=(',',':')).encode())
    return {'sha256':h.hexdigest(),'row_counts':counts}
@contextmanager
def read_guard(cfg):
    conn=cfg.connect()
    try:
        with conn.cursor() as c:
            c.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.SQL(',').join(sql.Identifier(t) for t in TABLES)))
        yield conn
    finally: conn.rollback(); conn.close()
