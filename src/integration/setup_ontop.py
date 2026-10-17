"""Install the course-pinned Ontop/JDBC runtime; downloads are fingerprinted."""
import argparse, json, os, shutil, subprocess, zipfile
from pathlib import Path
from urllib.request import urlopen
from common import ROOT, sha, now, write_json
URL='https://github.com/ontop/ontop/releases/download/ontop-5.5.0/ontop-cli-5.5.0.zip'
JDBC='https://github.com/pgjdbc/pgjdbc/releases/download/REL42.7.13/postgresql-42.7.13.jar'
def setup(home):
    home=Path(home).resolve(); home.mkdir(parents=True,exist_ok=True)
    manifest=home/'download-manifest.json'
    records=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {'ontop':'5.5.0','jdbc':'42.7.13','downloads':{}}
    for url,dest in [(URL,home/'ontop-cli.zip'),(JDBC,home/'jdbc'/JDBC.rsplit('/',1)[1])]:
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            print('Downloading '+dest.name,flush=True)
            temporary=dest.with_suffix(dest.suffix+'.part')
            with urlopen(url,timeout=60) as source, temporary.open('wb') as target: shutil.copyfileobj(source,target)
            temporary.replace(dest)
        digest=sha(dest)
        previous=records['downloads'].get(dest.name)
        if previous and previous['sha256']!=digest: raise ValueError('Runtime download changed: '+dest.name)
        records['downloads'][dest.name]={'url':url,'sha256':digest,'bytes':dest.stat().st_size}
    if not (home/'ontop.bat').exists():
        with zipfile.ZipFile(home/'ontop-cli.zip') as archive:
            for member in archive.infolist():
                if not (home/member.filename).resolve().is_relative_to(home): raise ValueError('Unsafe archive path')
            archive.extractall(home)
    (home/'ontop').chmod(0o755)
    records['checked_at_utc']=now(); records['note']='Locally computed download fingerprints, not publisher signatures.'
    write_json(manifest,records)
    print('Ontop 5.5.0 and PostgreSQL JDBC driver ready: '+str(home))
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--home',type=Path,default=ROOT/'.runtime/ontop'); a=p.parse_args()
    if not shutil.which('java'): raise SystemExit('Java 21 is required.')
    setup(a.home)
