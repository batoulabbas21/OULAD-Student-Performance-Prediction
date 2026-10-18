"""Paths, fingerprints and JSON helpers for reproducible learning experiments."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/learning'
os.environ.setdefault('PYSTOW_HOME',str(ROOT/'.runtime/learning/pystow'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.runtime/learning/matplotlib'))
def now():return datetime.now(timezone.utc).isoformat()
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write_json(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,indent=2,default=str,allow_nan=False)+'\n',encoding='utf-8')
def read_json(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def source_graph():
    latest=ROOT/'outputs/integration/latest-full.json'
    if latest.exists():
        info=read_json(latest);folder=(ROOT/info['directory']).resolve()
        if not folder.is_relative_to(ROOT/'outputs/integration/runs'):raise ValueError('Unexpected integration source location')
        summary=read_json(folder/'summary.json');p=folder/'oulad-mapped.nt'
        if not summary['passed'] or sha(p)!=summary['materialization']['output_sha256']:raise ValueError('Mapped RDF does not match successful integration receipt')
        for n,h in summary['source_sha256'].items():
            if n.startswith('data/interim/') and n.endswith('.csv') and sha(ROOT/n)!=h:raise ValueError('Integration graph is stale against '+n)
        return p,[latest,folder/'summary.json']
    return ROOT/'data/processed/oulad.ttl',[]
