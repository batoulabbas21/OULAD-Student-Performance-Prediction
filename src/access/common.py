"""Session 7 paths and auditable inputs; no credentials are included in receipts."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'config/access'
OUT = ROOT / 'outputs/access'
GRAPH = ROOT / 'data/processed/oulad.ttl'
SCHEMA = ROOT / 'ontology/education.rdfs.ttl'
EDU = 'https://example.org/oulad/schema#'
DATASET = 'https://example.org/oulad/'
PREFIXES = {'edu': EDU, 'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#', 'xsd': 'http://www.w3.org/2001/XMLSchema#'}

def now(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
def sources():
    paths = [GRAPH, SCHEMA, *CONFIG.glob('*'), * (ROOT/'src/access').glob('*.py'),
             *(ROOT/'src/access/ui').glob('*'), ROOT/'evaluation/verify_access.py', * (ROOT/'data/interim').glob('*.csv')]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths) if p.is_file()}
