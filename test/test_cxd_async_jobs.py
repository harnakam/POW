import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'commands/optimize-latency/scripts/cxd'))
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from async_jobs import start, result, wait


class AsyncJobsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def configure(self, jobs):
        (self.root / '.codex-dispatch.json').write_text(json.dumps({
            'version': 1, 'source_roots': ['.'], 'presets': {'probe': {'jobs': jobs}}}))

    def job(self, name, code, **kwargs):
        return {'id': name, 'argv': [sys.executable, '-S', '-c', code], **kwargs}

    def test_cli_start_survives_launcher_and_wait_timeout_does_not_cancel(self):
        release = self.root / 'release'
        code = ('import pathlib,sys,time; gate=pathlib.Path(sys.argv[1]); end=time.monotonic()+60\n'
                'while not gate.exists():\n'
                ' if time.monotonic()>end: raise RuntimeError("release gate timed out")\n'
                ' time.sleep(.02)\n'
                'print("persisted")')
        job = self.job('slow', code)
        job['argv'].append(str(release))
        self.configure([job])
        import dispatch
        cli = Path(dispatch.__file__)
        process = subprocess.run([sys.executable, '-S', str(cli), 'start', 'probe',
                                  '--workspace', str(self.root)], capture_output=True, text=True, timeout=60)
        self.assertEqual(process.returncode, 0, process.stderr)
        run_id = json.loads(process.stdout)['run_id']
        try:
            self.assertEqual(result(self.root, run_id)['status'], 'running')
            self.assertTrue(wait(self.root, run_id, 0)['wait_timed_out'])
        finally:
            release.touch()
            final = wait(self.root, run_id, 60)
        self.assertEqual(final['status'], 'completed')
        self.assertEqual(Path(final['summary']['jobs']['slow']['stdout_path']).read_text().strip(), 'persisted')
        self.assertEqual(result(self.root, run_id), final)

    def test_failure_dependency_and_job_timeout_are_preserved(self):
        self.configure([self.job('bad', 'raise SystemExit(7)'),
                        self.job('blocked', 'print("must not run")', depends_on=['bad']),
                        self.job('timeout', 'import time; time.sleep(5)', timeout_s=0.1)])
        final = wait(self.root, start(self.root, 'probe')['run_id'], 60)
        self.assertEqual(final['status'], 'failed')
        jobs = final['summary']['jobs']
        self.assertEqual(jobs['bad']['returncode'], 7)
        self.assertEqual(jobs['blocked']['status'], 'blocked')
        self.assertEqual(jobs['timeout']['status'], 'timed_out')

    def test_validation_precedes_launch_and_ids_are_scoped(self):
        self.configure([self.job('bad', 'pass', depends_on=['missing'])])
        with self.assertRaises(ValueError):
            start(self.root, 'probe')
        self.assertFalse((self.root / '.cxd/async').exists())
        for run_id in ('../outside', 'x' * 32, 'a' * 32, None):
            with self.assertRaises(ValueError):
                result(self.root, run_id)

    def test_ctx_routing_and_attached_failure_exit(self):
        from unittest.mock import patch
        import ctx
        with patch('ctx.dispatch', return_value=0) as dispatch:
            ctx.main(['probe'])
            dispatch.assert_called_with(['start', 'probe'])
            ctx.main(['-wait', 'probe'])
            dispatch.assert_called_with(['probe'])
            ctx.main(['result', 'a' * 32])
            dispatch.assert_called_with(['result', 'a' * 32])
        self.configure([self.job('bad', 'raise SystemExit(7)')])
        process = subprocess.run([sys.executable, '-S', str(Path(ctx.__file__)),
                                  'probe', '--attached', '--compact', '--workspace', str(self.root)],
                                 capture_output=True, text=True, timeout=60)
        self.assertEqual(process.returncode, 1, process.stderr)
        final = json.loads(process.stdout.splitlines()[-1])
        self.assertEqual(final['status'], 'failed')
        self.assertNotIn('summary', final)


if __name__ == '__main__':
    unittest.main()
