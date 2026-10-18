"""Platform-independent resident regressions; Linux watcher runs on Linux CI."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'commands/optimize-latency/scripts/cxd'))
from resident import ProjectIndex, atomic_json, verify_timing
from resident_rpc import Changes, acquire_lock, alive, directories, request


class PlatformTests(unittest.TestCase):
    def test_index_reuses_unchanged_content_and_invalidates_edits(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory).resolve()
            source = root / 'example.py'
            source.write_text('def first(): pass\n', encoding='utf-8')
            index = ProjectIndex(root, root / 'index.json')
            first = index.operate('symbols', {'query': 'first'}, ['.'])
            self.assertEqual(first['total'], 1)
            stamp = index.cache.stat().st_mtime_ns
            self.assertEqual(index.operate('index', {}, ['.'])['reused_files'], 1)
            self.assertEqual(index.cache.stat().st_mtime_ns, stamp)
            source.write_text('def other(): pass\n', encoding='utf-8')
            self.assertEqual(index.operate('symbols', {'query': 'other'}, ['.'])['total'], 1)
            self.assertEqual(index.parsed, 2)
            source.write_text('def broken(\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                index.operate('syntax', {'paths': ['example.py']}, ['.'])
            source.unlink()
            self.assertEqual(index.operate('symbols', {'query': ''}, ['.'])['total'], 0)

    def test_bom_configuration_is_supported_by_worker(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory)
            (root / 'example.py').write_text('def hello(): pass\n', encoding='utf-8')
            (root / '.codex-dispatch.json').write_text(json.dumps({
                'version': 1, 'source_roots': ['.'], 'presets': {}}), encoding='utf-8-sig')
            try:
                self.assertEqual(request(root, 'symbols', {'query': 'hello'})['total'], 1)
            finally:
                request(root, 'stop', start=False)

    def test_stale_metadata_with_reused_live_pid_recovers(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory)
            state = directories(root)
            atomic_json(state / 'worker.json', {'pid': os.getpid(), 'token': 'stale'})
            try:
                result = request(root, 'status', timeout=5)
                self.assertTrue(result['running'])
                self.assertNotEqual(result['worker_pid'], os.getpid())
            finally:
                # Never send stop to the fabricated current-process identity.
                if (state / 'worker.json').exists() and json.loads((state / 'worker.json').read_text())['pid'] != os.getpid():
                    request(root, 'stop', start=False)

    def test_generic_timing(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory) / 'timing.json'
            for data in ({'total_s': 0}, {'total_s': 1, 'exclusive_categories_s': {'work': 1}}):
                path.write_text(json.dumps(data))
                self.assertEqual(verify_timing(path)['total_s'], data['total_s'])
            for data in ({'total_s': float('nan')}, {'total_s': -1},
                         {'total_s': 2, 'exclusive_categories_s': {'work': 1}}):
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    verify_timing(path)

    def test_lock_excludes_another_owner_and_can_be_reused(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory) / 'worker.lock'
            first = acquire_lock(path)
            self.assertIsNotNone(first)
            try:
                self.assertIsNone(acquire_lock(path))
            finally:
                first.close()
            second = acquire_lock(path)
            self.assertIsNotNone(second)
            second.close()

    def test_notifications_and_lifecycle(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory)
            state = directories(root)
            changes = Changes(state / 'responses')
            try:
                self.assertFalse(changes.wait(.01))
                timer = threading.Timer(.05, lambda: (state / 'responses/wake').write_text('yes'))
                timer.start()
                self.assertTrue(changes.wait(2))
                timer.join()
            finally:
                changes.close()
            self.assertTrue(alive(os.getpid()))
            try:
                info = request(root, 'status', timeout=10)
                self.assertTrue(info['running'])
                self.assertEqual(request(root, 'status')['worker_pid'], info['worker_pid'])
            finally:
                changes = Changes(state)
                try:
                    request(root, 'stop', start=False)
                    while (state / 'worker.json').exists():
                        if not changes.wait(2):
                            self.fail('worker did not remove state after stop')
                finally:
                    changes.close()

    @unittest.skipUnless(os.name == 'posix', 'POSIX permissions and symlinks')
    def test_private_directories_and_redirect_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory, tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as outside:
            root = Path(directory)
            (root / '.cxd').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                directories(root)
            (root / '.cxd').unlink()
            state = directories(root)
            self.assertEqual(state.stat().st_mode & 0o777, 0o700)

    @unittest.skipUnless(os.name == 'posix', 'POSIX process inspection')
    def test_pid_permission_denied_is_unknown(self):
        with patch('os.kill', side_effect=PermissionError):
            self.assertIsNone(alive(123))


if __name__ == '__main__':
    unittest.main()
