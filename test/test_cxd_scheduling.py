import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'commands/optimize-latency/scripts/cxd'))
import threading
import time
import unittest
from pathlib import Path
import tempfile

from command_actors import run_manifest_sync, validate_manifest


class SchedulingTests(unittest.TestCase):
    def run_case(self, jobs, handler, concurrency=2, scheduling='critical_path'):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            return run_manifest_sync({'jobs': jobs, 'scheduling': scheduling},
                Path(directory) / 'run', concurrency=concurrency,
                handlers={'work': handler}, emit_events=False)

    def test_critical_chain_enters_before_independent_leaf(self):
        jobs = [{'id': name, 'operation': 'work', 'parameters': {'name': name},
                 'depends_on': dependencies} for name, dependencies in
                [('leaf', []), ('root', []), ('child', ['root'])]]
        order = []
        self.run_case(jobs, lambda p: order.append(p['name']) or '', concurrency=1)
        self.assertEqual(order, ['root', 'leaf', 'child'])
        order.clear()
        self.run_case(jobs, lambda p: order.append(p['name']) or '', concurrency=1, scheduling='fifo')
        self.assertEqual(order, ['leaf', 'root', 'child'])

    def test_readers_overlap_writer_is_exclusive(self):
        lock = threading.Lock()
        readers = threading.Barrier(2)
        active = []
        violations = []
        def handler(p):
            with lock:
                if p['name'] == 'write' and active or 'write' in active:
                    violations.append(list(active))
                active.append(p['name'])
            if p['name'] != 'write':
                readers.wait(timeout=5)
            time.sleep(0.02)
            with lock:
                active.remove(p['name'])
            return 'ok'
        jobs = [{'id': name, 'operation': 'work', 'parameters': {'name': name},
                 'writes' if name == 'write' else 'reads': ['workspace:source']}
                for name in ('read1', 'read2', 'write')]
        summary = self.run_case(jobs, handler, concurrency=3)
        self.assertEqual(summary['status'], 'completed')
        self.assertEqual(violations, [])
        self.assertGreaterEqual(summary['jobs']['write']['start_s'],
                               max(summary['jobs'][n]['end_s'] for n in ('read1', 'read2')))

    def test_callable_jobs_obey_capacity_and_estimates(self):
        active = maximum = 0
        lock = threading.Lock()
        order = []
        def handler(p):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
                order.append(p['name'])
            time.sleep(0.01)
            with lock:
                active -= 1
            return ''
        jobs = [{'id': name, 'operation': 'work', 'parameters': {'name': name},
                 'estimated_s': estimate} for name, estimate in [('short', 1), ('long', 3)]]
        self.run_case(jobs, handler, concurrency=1)
        self.assertEqual(maximum, 1)
        self.assertEqual(order, ['long', 'short'])

    def test_invalid_policy_and_claims_do_not_run(self):
        for extra in ({'reads': 'file'}, {'writes': [1]}, {'reads': ['a', 'a']},
                      {'estimated_s': True}, {'estimated_s': float('nan')},
                      {'estimated_s': -1}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                validate_manifest({'jobs': [{'id': 'a', 'argv': ['python'], **extra}]})
        with self.assertRaises(ValueError):
            validate_manifest({'jobs': [], 'scheduling': 'unknown'})

    def test_failure_releases_resource_without_blocking_independent_writer(self):
        def handler(parameters):
            if parameters.get('fail'):
                raise RuntimeError('expected')
            return 'ok'
        summary = self.run_case([
            {'id': 'bad', 'operation': 'work', 'writes': ['db'], 'parameters': {'fail': True}},
            {'id': 'independent', 'operation': 'work', 'writes': ['db']},
            {'id': 'dependent', 'operation': 'work', 'depends_on': ['bad'], 'reads': ['db']},
        ], handler)
        self.assertEqual(summary['jobs']['bad']['status'], 'failed')
        self.assertEqual(summary['jobs']['independent']['status'], 'completed')
        self.assertEqual(summary['jobs']['dependent']['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()
