"""Failure/gate tests for the launcher; no Docker or model calls are made."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('project_runner', ROOT / 'src/project/run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class LauncherChecks(unittest.TestCase):
    def test_failed_stage_stops_before_following_stages(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(runner.subprocess, 'run', return_value=Mock(returncode=1)) as call:
            receipt = {'stages': []}
            path = Path(folder) / 'summary.json'
            with self.assertRaises(RuntimeError):
                runner.execute_steps([('gate', ['python', 'validate.py']), ('must-not-run', ['python', 'serve.py'])], receipt, path)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(json.loads(path.read_text())['stages'][0]['status'], 'failed')

    def test_failed_pipeline_never_opens_browser_or_server(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(runner, 'ROOT', Path(folder)), patch.object(runner, 'preflight'), patch.object(runner, 'execute_steps', side_effect=RuntimeError('gate failed')), patch.object(runner, 'launch') as launch:
            self.assertEqual(runner.main(['--access-only']), 1)
            launch.assert_not_called()
            receipts = list(Path(folder).rglob('summary.json'))
            self.assertEqual(len(receipts), 1)
            self.assertEqual(json.loads(receipts[0].read_text())['status'], 'failed')

    def test_occupied_port_uses_next_without_stopping_process(self):
        server = object()
        factory = Mock(side_effect=[OSError(10048, 'occupied'), server])
        self.assertIs(runner.bind_server(None, 'live', 8009, factory), server)
        self.assertEqual([c.args[2] for c in factory.call_args_list], [8009, 8010])

    def test_other_socket_failure_is_not_hidden(self):
        factory = Mock(side_effect=OSError(13, 'permission denied'))
        with self.assertRaises(OSError):
            runner.bind_server(None, 'live', 8009, factory)
        self.assertEqual(factory.call_count, 1)

    def test_port_search_has_a_bound(self):
        factory = Mock(side_effect=OSError(10048, 'occupied'))
        with self.assertRaises(RuntimeError):
            runner.bind_server(None, 'live', 8009, factory)
        self.assertEqual(factory.call_count, 11)

    def test_access_only_still_requires_gate_and_makes_no_model_evaluation(self):
        a = runner.parse_args(['--access-only'])
        commands = [command for _, command in runner.plan(a)]
        self.assertEqual(commands[0][1], 'src/validation/validate.py')
        self.assertFalse(any('evaluate.py' in str(c) or 'docker' in str(c) for c in commands))
        self.assertIn('--local-only', commands[-1])

    def test_full_profile_reuses_every_completed_layer(self):
        a = runner.parse_args([])
        a.lab_compose = Path('lab-compose.yml')
        commands = [str(c) for _, c in runner.plan(a)]
        for stage in ['run-core.ps1', 'verify_ontology.py', 'run-shacl.ps1', 'run-integration.ps1', 'run-learning.ps1', 'neo4j_comparison.py', 'load_fuseki.py']:
            self.assertTrue(any(stage in c for c in commands), stage)
        self.assertIn('src/validation/validate.py', commands[-3])

    def test_check_only_starts_nothing(self):
        with patch.object(runner, 'preflight'), patch.object(runner, 'execute_steps') as execute, patch.object(runner, 'launch') as launch:
            self.assertEqual(runner.main(['--access-only', '--check-only']), 0)
            execute.assert_not_called()
            launch.assert_not_called()


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LauncherChecks))
    runner.save(ROOT / 'outputs/project/verification.json', {'passed': result.wasSuccessful(), 'checks': result.testsRun, 'api_requests': 0, 'checked_at_utc': runner.now()})
    raise SystemExit(0 if result.wasSuccessful() else 1)
