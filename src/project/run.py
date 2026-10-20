"""Run existing OULAD stages, enforce SHACL, then open the local access page.

The browser server runs in this process: Ctrl+C stops it. Docker services retain
their data and stay running. No evaluation sends new provider requests here.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import uuid
import webbrowser

ROOT = Path(__file__).resolve().parents[2]
DATASET = 'https://example.org/oulad/'


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--access-only', action='store_true')
    p.add_argument('--mode', choices=['live', 'record', 'replay', 'catalog'], default='live')
    p.add_argument('--port', type=int, default=8009)
    p.add_argument('--model', default='gemini-3.5-flash-lite')
    p.add_argument('--max-requests', type=int, default=10)
    p.add_argument('--env-file', type=Path)
    p.add_argument('--lab-compose', type=Path)
    p.add_argument('--skip-graph-services', action='store_true')
    p.add_argument('--check-only', action='store_true', help='Prerequisites and plan only; no pipeline or server.')
    p.add_argument('--no-browser', action='store_true')
    p.add_argument('--no-serve', action='store_true', help='Run/check the pipeline, then exit before starting a server.')
    a = p.parse_args(argv)
    if not 1024 <= a.port <= 65525:
        p.error('Port must be 1024..65525 (up to ten following ports may be tried).')
    if not 1 <= a.max_requests <= 1000:
        p.error('Request limit must be 1..1000.')
    return a


def preflight(a):
    prefix = os.environ.get('CONDA_PREFIX')
    if not prefix or Path(prefix).resolve() != Path(sys.prefix).resolve():
        raise RuntimeError('Activate M2ENV and run with that environment\'s Python. No environment is installed automatically.')
    modules = ['pandas', 'rdflib', 'pyshacl', 'requests', 'dotenv', 'pyoxigraph', 'yaml']
    if not a.access_only:
        modules += ['owlrl', 'owlready2', 'nbformat', 'nbclient', 'nbconvert', 'ipykernel',
                    'morph_kgc', 'psycopg2', 'sqlalchemy', 'torch', 'torch_geometric', 'pykeen',
                    'sklearn', 'numpy', 'matplotlib']
        if not a.skip_graph_services:
            modules += ['neo4j']
    missing = [m for m in modules if importlib.util.find_spec(m) is None]
    if missing:
        raise RuntimeError('Missing packages in the active environment: ' + ', '.join(missing) + '. See the corresponding README stage.')
    if a.access_only:
        for name in ['data/processed/oulad.ttl', 'ontology/education.rdfs.ttl', 'shapes/oulad-shapes.ttl']:
            if not (ROOT / name).is_file():
                raise RuntimeError(name + ' is missing. First run the full launcher without -AccessOnly.')
    else:
        for executable in ['java', 'docker', 'powershell']:
            if not shutil.which(executable):
                raise RuntimeError(executable + ' is missing from PATH. See the README prerequisites.')
        try:
            result = subprocess.run(['docker', 'info', '--format', '{{.ServerVersion}}'], capture_output=True, timeout=15)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('Docker did not respond. Open Docker Desktop, wait for its engine, and retry.') from exc
        if result.returncode:
            raise RuntimeError('Docker is not ready. Open Docker Desktop, wait for its engine, and retry; -AccessOnly does not need Docker.')
    a.lab_compose = (a.lab_compose or ROOT.parent / 'KRR/demos/docker-compose.yml').resolve()
    if not a.access_only and not a.skip_graph_services and not a.lab_compose.is_file():
        raise RuntimeError('Lab Compose file is missing. Supply -LabCompose PATH or use -SkipGraphServices to omit Neo4j/Fuseki.')
    if a.env_file:
        a.env_file = a.env_file.resolve()
        if not a.env_file.is_file():
            raise RuntimeError('The supplied environment file does not exist.')
    elif (ROOT / '.env.access').is_file():
        a.env_file = ROOT / '.env.access'
    elif (ROOT.parent / 'KRR/demos/.env').is_file():
        a.env_file = ROOT.parent / 'KRR/demos/.env'
    # Match Model's precedence; print neither the key nor the environment file.
    from dotenv import load_dotenv
    if a.env_file:
        load_dotenv(a.env_file, override=False)
    load_dotenv(ROOT / '.env.access', override=False)
    if a.mode in ('live', 'record') and not a.no_serve and not (os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')):
        raise RuntimeError('No Gemini key. Supply -EnvFile PATH, configure ignored .env.access, or choose -Mode catalog.')


def plan(a):
    python = sys.executable
    ps = shutil.which('powershell') or 'powershell'
    steps = []

    def py(label, *args):
        steps.append((label, [python, *args]))

    def script(label, name, *args):
        steps.append((label, [ps, '-NoProfile', '-File', str(ROOT / name), *args]))

    if not a.access_only:
        script('Data download, profiling, RDF, core SHACL gate and competency queries', 'run-core.ps1')
        py('Prepare OWL ontology and local imports', 'src/graph/prepare_ontology.py')
        py('Reason over the OWL sample', 'src/graph/owl_reasoner.py')
        py('Reason over the complete asserted graph', 'src/graph/owl_reasoner.py', '--full-data')
        py('Verify ontology semantics and counts', 'evaluation/verify_ontology.py')
        py('Execute ontology notebook and export its HTML', 'src/graph/build_ontology_notebook.py')
        script('SHACL good/bad examples, triage and verification', 'run-shacl.ps1')
        script('PostgreSQL, mappings, materialization and virtualization', 'run-integration.ps1')
        script('Learning experiments and evidence verification', 'run-learning.ps1')
        if not a.skip_graph_services:
            steps.append(('Start the existing lab Neo4j service', ['docker', 'compose', '-f', str(a.lab_compose), 'up', '-d', '--wait', '--wait-timeout', '120', 'neo4j']))
            py('Wait for authenticated Neo4j readiness', 'src/project/wait_neo4j.py')
            py('Load and verify the OULAD Neo4j projection', 'src/graph/neo4j_comparison.py')
            script('Start Fuseki with its OULAD dataset', 'start-fuseki.ps1', '-LabCompose', str(a.lab_compose))
            py('Load and verify the OULAD Fuseki graph', 'src/graph/load_fuseki.py')
    # This gate is mandatory in both modes, even when existing RDF is reused.
    py('Final SHACL gate before opening access', 'src/validation/validate.py')
    py('Generate current VoID and schema description', 'src/access/grounding.py')
    py('Verify access locally without provider calls', 'evaluation/verify_access.py', '--local-only')
    return steps


def execute_steps(steps, receipt, receipt_path):
    child_env = os.environ.copy()
    child_env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + child_env.get('PATH', '')
    child_env['PYTHONUNBUFFERED'] = '1'
    for index, (label, command) in enumerate(steps, 1):
        print(f'\n[{index}/{len(steps)}] {label}', flush=True)
        entry = {'stage': label, 'command': command, 'started_at_utc': now(), 'status': 'running'}
        receipt['stages'].append(entry)
        save(receipt_path, receipt)
        result = subprocess.run(command, cwd=ROOT, env=child_env)
        entry.update(finished_at_utc=now(), exit_code=result.returncode,
                     status='passed' if result.returncode == 0 else 'failed')
        save(receipt_path, receipt)
        if result.returncode:
            raise RuntimeError(f'Stage failed: {label}. No later stage or new access server was started.')


def bind_server(layer, mode, requested_port, factory):
    # Bind directly: avoid a check-then-bind race and never terminate another process.
    for port in range(requested_port, requested_port + 11):
        try:
            return factory(layer, mode, port)
        except OSError as exc:
            if exc.errno not in (48, 98, 10048) and getattr(exc, 'winerror', None) != 10048:
                raise
    raise RuntimeError('No free local port in the requested range. Retry with -Port 8020 (or another free port).')


def launch(a, receipt, receipt_path):
    sys.path.insert(0, str(ROOT / 'src/access'))
    from access_layer import AccessLayer, Model
    from serve import create_server
    model = Model(a.mode, str(a.env_file) if a.env_file else None, a.model, a.max_requests)
    layer = AccessLayer(model)
    server = bind_server(layer, a.mode, a.port, create_server)
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    receipt.update(status='serving', url=url, server_started_at_utc=now(), server_pid=os.getpid())
    save(receipt_path, receipt)
    print(f'\nOpen {url} | mode={a.mode} | model={a.model}', flush=True)
    print(f'Limit: {a.max_requests} provider requests for this server, up to 3 per question. Opening the page makes no call.', flush=True)
    print('Keep this terminal open. Ctrl+C stops this page; Docker services stay running.', flush=True)
    try:
        if not a.no_browser:
            try:
                if not webbrowser.open(url, new=2):
                    print('Browser did not open automatically; use the URL above.', flush=True)
            except webbrowser.Error:
                print('Browser could not open; use the URL above.', flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nAccess server stopped.', flush=True)
    finally:
        server.server_close()
        receipt.update(status='stopped', server_stopped_at_utc=now(), api_requests=model.requests)
        save(receipt_path, receipt)


def main(argv=None):
    a = parse_args(argv)
    try:
        preflight(a)
        steps = plan(a)
        print(f'Environment: {sys.executable}\nProfile: {"access only" if a.access_only else "full project"}', flush=True)
        for index, (label, _) in enumerate(steps, 1):
            print(f'  {index}. {label}', flush=True)
        if a.check_only:
            print('Prerequisites passed. Check-only: no pipeline stages, server, browser or Gemini calls.', flush=True)
            return 0
    except (RuntimeError, OSError) as exc:
        print('Cannot start: ' + str(exc), file=sys.stderr)
        return 1
    run_id = uuid.uuid4().hex
    path = ROOT / 'outputs/project/runs' / run_id / 'summary.json'
    receipt = {'run_id': run_id, 'started_at_utc': now(), 'status': 'running',
               'profile': 'access-only' if a.access_only else 'full', 'mode': a.mode,
               'graph_services': not a.access_only and not a.skip_graph_services,
               'python': sys.executable, 'model': a.model, 'max_requests': a.max_requests,
               'launcher_sha256': sha(__file__), 'stages': [], 'api_requests': 0,
               'note': 'JSON orchestration receipt; individual stages retain their own reports and PROV. API count updates on orderly server shutdown.'}
    print('Launcher receipt: ' + str(path), flush=True)
    save(path, receipt)
    try:
        execute_steps(steps, receipt, path)
        receipt.update(status='pipeline-passed', pipeline_finished_at_utc=now(),
                       validated_snapshot={name: sha(ROOT / name) for name in [
                           'data/processed/oulad.ttl', 'ontology/education.rdfs.ttl', 'shapes/oulad-shapes.ttl']})
        # State describes this launch, not a new model benchmark or a Docker-only deployment.
        save(path, receipt)
        save(ROOT / 'outputs/project/latest.json', {'run_id': run_id, 'directory': path.parent.relative_to(ROOT).as_posix(), 'profile': receipt['profile']})
        if not a.no_serve:
            launch(a, receipt, path)
        return 0
    except KeyboardInterrupt:
        receipt.update(status='interrupted', finished_at_utc=now())
        save(path, receipt)
        print('\nPipeline interrupted. No success is claimed.', file=sys.stderr)
        return 130
    except Exception as exc:
        receipt.update(status='failed', finished_at_utc=now(), error=str(exc))
        save(path, receipt)
        print('Project stopped: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
