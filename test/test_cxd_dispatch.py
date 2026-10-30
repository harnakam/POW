from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'commands/optimize-latency/scripts/cxd'))
from dispatch import configuration, main, run_preset


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = {'version': 1, 'source_roots': ['.'], 'presets': {
            'check': {'jobs': [{'id': 'cwd', 'argv': ['{python}', '-c',
                'from pathlib import Path; print(Path.cwd())']}]}}}
        self.save()

    def save(self):
        (self.root / '.codex-dispatch.json').write_text(json.dumps(self.config), encoding='utf-8')

    def test_default_cwd_is_workspace_and_config_is_unchanged(self):
        before = (self.root / '.codex-dispatch.json').read_bytes()
        result = run_preset(self.root, 'check')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(Path(result['jobs']['cwd']['stdout_path']).read_text().strip(), str(self.root))
        self.assertEqual((self.root / '.codex-dispatch.json').read_bytes(), before)

    def test_invalid_schema_and_reserved_preset_names(self):
        for change in ({'version': True}, {'presets': []}, {'presets': {'stop': {'jobs': []}}},
                       {'presets': {'../escape': {'jobs': []}}}, {'source_roots': []}):
            with self.subTest(change=change):
                original = dict(self.config)
                self.config.update(change)
                self.save()
                with self.assertRaises(ValueError):
                    configuration(self.root)
                self.config = original

    def test_invalid_graph_does_not_create_run_directory(self):
        self.config['presets']['check']['jobs'][0]['depends_on'] = ['missing']
        self.save()
        with self.assertRaisesRegex(ValueError, 'unknown dependency'):
            run_preset(self.root, 'check')
        self.assertFalse((self.root / '.cxd').exists())

    def test_paths_must_stay_within_workspace(self):
        self.config['presets']['check']['jobs'][0]['cwd'] = '..'
        self.save()
        with self.assertRaisesRegex(ValueError, 'inside'):
            run_preset(self.root, 'check')
        self.config['source_roots'] = ['..']
        self.save()
        with self.assertRaises(ValueError):
            configuration(self.root)

    def test_read_operations_reuse_handlers_and_keep_dependency_order(self):
        self.config['presets']['read'] = {'jobs': [
            {'id': 'index', 'operation': 'index'},
            {'id': 'symbols', 'operation': 'symbols', 'depends_on': ['index'],
             'parameters': {'query': 'main', 'limit': 5}}]}
        self.save()
        with patch('dispatch.request', return_value={'matches': [], 'worker_pid': 123}) as request:
            result = run_preset(self.root, 'read')
        self.assertEqual([call.args[1] for call in request.call_args_list], ['index', 'symbols'])
        self.assertIsNone(result['jobs']['index']['process_id'])
        self.assertEqual(json.loads(Path(result['jobs']['symbols']['stdout_path']).read_text())['matches'], [])
        with patch('dispatch.request', side_effect=RuntimeError('failed read')):
            failed = run_preset(self.root, 'read')
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['jobs']['symbols']['status'], 'blocked')

    def test_failed_command_is_nonzero_and_keeps_logs(self):
        self.config['presets']['check']['jobs'] = [
            {'id': 'bad', 'argv': ['{python}', '-c', 'import sys; print("failure reason",file=sys.stderr); sys.exit(7)']},
            {'id': 'after', 'argv': ['{python}', '-c', 'print("never")'], 'depends_on': ['bad']}]
        self.save()
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(['check', '--workspace', str(self.root)])
        self.assertEqual(code, 1)
        summary = json.loads(Path(json.loads(output.getvalue())['result_path']).read_text())
        self.assertEqual(summary['jobs']['bad']['returncode'], 7)
        self.assertEqual(summary['jobs']['after']['status'], 'blocked')
        self.assertIn('failure reason', Path(summary['jobs']['bad']['stderr_path']).read_text())

    def test_init_does_not_overwrite_existing_configuration(self):
        before = (self.root / '.codex-dispatch.json').read_bytes()
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(['init', '--workspace', str(self.root)]), 1)
        self.assertEqual((self.root / '.codex-dispatch.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
