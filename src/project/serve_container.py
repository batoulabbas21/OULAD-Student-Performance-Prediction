"""Freeze the mounted graph, enforce SHACL, then serve Gemini inside Docker."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]


def main():
    mode = os.getenv('OULAD_ACCESS_MODE', 'live')
    if mode not in ('live', 'record', 'catalog'):
        raise ValueError('Docker mode must be live, record or catalog.')
    limit = int(os.getenv('OULAD_ACCESS_MAX_REQUESTS', '10'))
    if not 1 <= limit <= 1000:
        raise ValueError('Request limit must be between 1 and 1000.')
    key_file = Path('/run/secrets/gemini_env')
    from dotenv import dotenv_values
    # Load only the Google key from the mounted lab file; never copy or log it.
    secrets = dotenv_values(key_file) if key_file.is_file() else {}
    key = secrets.get('GOOGLE_API_KEY') or secrets.get('GEMINI_API_KEY')
    if mode in ('live', 'record') and not key:
        raise ValueError('The mounted secret file needs GOOGLE_API_KEY or GEMINI_API_KEY.')
    if key:
        os.environ['GOOGLE_API_KEY'] = key
    source_files = {'oulad.ttl': 'data/processed/oulad.ttl',
                    'education.rdfs.ttl': 'ontology/education.rdfs.ttl',
                    'oulad-shapes.ttl': 'shapes/oulad-shapes.ttl'}
    hashes = {}
    for name, target in source_files.items():
        source = Path('/inputs') / name
        # Copy once: queries keep using the validated snapshot even if the host rebuilds.
        destination = ROOT / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        hashes[target] = hashlib.sha256(destination.read_bytes()).hexdigest()
    run_id = uuid.uuid4().hex
    out = ROOT / 'outputs/container/runs' / run_id
    out.mkdir(parents=True, exist_ok=True)
    record = {'run_id': run_id, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'mode': mode, 'model': os.getenv('OULAD_ACCESS_MODEL', 'gemini-3.5-flash-lite'),
              'max_requests': limit, 'snapshot_sha256': hashes,
              'entrypoint_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'status': 'validating', 'api_requests_at_startup': 0}
    def save():
        (out / 'startup.json').write_text(json.dumps(record, indent=2) + '\n')
    save()
    result = subprocess.run([sys.executable, str(ROOT / 'src/validation/validate.py'), '--out', str(out / 'shacl')])
    if result.returncode:
        record.update(status='validation-failed', exit_code=result.returncode)
        save()
        print('SHACL gate failed. The access server has not been started.', file=sys.stderr)
        return result.returncode
    subprocess.run([sys.executable, str(ROOT / 'src/access/grounding.py')], check=True)
    record.update(status='validated-server-starting', validated_at_utc=datetime.now(timezone.utc).isoformat())
    save()
    (ROOT / 'outputs/container/latest.json').write_text(json.dumps({'run_id': run_id, 'directory': out.relative_to(ROOT / 'outputs').as_posix()}, indent=2) + '\n')
    print('Validated snapshot ready. Opening the page sends no Gemini request.', flush=True)
    # Replace this process so Docker signals reach the server directly.
    os.execv(sys.executable, [sys.executable, str(ROOT / 'src/access/serve.py'),
             '--host', '0.0.0.0', '--port', '8000', '--mode', mode,
             '--model', record['model'], '--max-requests', str(limit)])


if __name__ == '__main__':
    raise SystemExit(main())
