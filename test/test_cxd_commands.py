import queue
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'commands/optimize-latency/scripts/cxd'))
from command_actors import run_manifest_sync, validate_manifest


def job(job_id, code, **kwargs):
    return {'id': job_id, 'argv': [sys.executable, '-S', '-c', code], **kwargs}


class CommandActorsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_jobs(self, jobs, **kwargs):
        return run_manifest_sync({'jobs': jobs}, self.root / 'run', emit_events=False, **kwargs)

    def test_parallel_overlap_and_dependency_order(self):
        events = []
        completions = queue.Queue()
        summary = self.run_jobs([
            job('a', 'import time; time.sleep(0.12); print("a")'),
            job('b', 'import time; time.sleep(0.12); print("b")'),
            job('after', 'print("after")', depends_on=['a', 'b']),
        ], concurrency=2, on_event=events.append, completion_queue=completions)
        runs = summary['jobs']
        self.assertEqual(summary['status'], 'completed')
        self.assertLess(max(runs['a']['start_s'], runs['b']['start_s']),
                        min(runs['a']['end_s'], runs['b']['end_s']))
        self.assertGreaterEqual(runs['after']['start_s'], max(runs['a']['end_s'], runs['b']['end_s']))
        self.assertEqual(completions.qsize(), 3)
        self.assertEqual(len(events), 6)
        self.assertEqual(Path(runs['after']['stdout_path']).read_text().strip(), 'after')
        saved = json.loads((self.root / 'run/result.json').read_text())
        self.assertEqual(saved, summary)

    def test_failure_blocks_dependents_but_not_independent(self):
        summary = self.run_jobs([
            job('bad', 'import sys; print("reason",file=sys.stderr); sys.exit(7)'),
            job('blocked', 'raise RuntimeError("must not execute")', depends_on=['bad']),
            job('independent', 'print("still ran")'),
        ])
        runs = summary['jobs']
        self.assertEqual(summary['status'], 'failed')
        self.assertEqual(runs['bad']['returncode'], 7)
        self.assertIn('reason', Path(runs['bad']['stderr_path']).read_text())
        self.assertEqual(runs['blocked']['status'], 'blocked')
        self.assertIsNone(runs['blocked']['start_s'])
        self.assertEqual(runs['independent']['status'], 'completed')

    def test_timeout_terminates_job_and_blocks_dependent(self):
        summary = self.run_jobs([
            job('slow', 'import time; time.sleep(20)', timeout_s=0.05),
            job('blocked', 'print("never")', depends_on=['slow']),
        ])
        self.assertEqual(summary['jobs']['slow']['status'], 'timed_out')
        self.assertIsNotNone(summary['jobs']['slow']['returncode'])
        self.assertIn('timed out', Path(summary['jobs']['slow']['stderr_path']).read_text())
        self.assertEqual(summary['jobs']['blocked']['status'], 'blocked')

    def test_validation_precedes_execution_and_output_creation(self):
        with self.assertRaisesRegex(ValueError, 'cycle'):
            self.run_jobs([job('a', 'print(1)', depends_on=['b']),
                                 job('b', 'print(2)', depends_on=['a'])])
        self.assertFalse((self.root / 'run').exists())
        invalid = [
            ({'jobs': [job('a', 'pass', depends_on=['missing'])]}, 1),
            ({'jobs': [job('A', 'pass'), job('a', 'pass')]}, 1),
            ({'jobs': [job('../escape', 'pass')]}, 1),
            ({'jobs': [{'id': 'a', 'argv': 'not a list'}]}, 1),
            ({'jobs': [job('a', 'pass', cwd=str(self.root / 'missing'))]}, 1),
            ({'jobs': [job('a', 'pass', timeout_s=0)]}, 1),
            ({'jobs': [job('a', 'pass')]}, 0),
        ]
        for manifest, concurrency in invalid:
            with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                validate_manifest(manifest, concurrency)

    def test_existing_output_is_not_overwritten(self):
        output = self.root / 'run'
        output.mkdir()
        marker = output / 'keep.txt'
        marker.write_text('keep')
        with self.assertRaises(FileExistsError):
            self.run_jobs([job('a', 'print(1)')])
        self.assertEqual(marker.read_text(), 'keep')

    def test_jobs_receive_eof_instead_of_controller_input(self):
        summary = self.run_jobs([job('stdin', 'import sys; print("EOF" if sys.stdin.read() == "" else "unexpected")')])
        self.assertEqual(summary['jobs']['stdin']['status'], 'completed')
        self.assertEqual(Path(summary['jobs']['stdin']['stdout_path']).read_text().strip(), 'EOF')


if __name__ == '__main__':
    unittest.main()
