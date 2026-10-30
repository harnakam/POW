"""Platform-independent resident regressions; Linux watcher runs on Linux CI."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'commands/optimize-latency/scripts/cxd'))
from resident import ProjectIndex, atomic_json, verify_timing
from resident_rpc import Changes, acquire_lock, alive, directories, request, response_io


class PlatformTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_response_read_recovers_after_real_windows_sharing_handle_closes(self):
        import ctypes
        from ctypes import wintypes
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                   ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        api.CreateFileW.restype = wintypes.HANDLE
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory) / 'response.json'
            atomic_json(path, {'ok': True})
            handle = api.CreateFileW(str(path), 0x80000000, 0, None, 3, 0, None)
            self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
            blocked = threading.Event()

            def release():
                blocked.wait(2)
                api.CloseHandle(handle)

            owner = threading.Thread(target=release)
            owner.start()

            def read():
                try:
                    return path.read_text(encoding='utf-8')
                except PermissionError:
                    blocked.set()
                    raise

            try:
                self.assertEqual(json.loads(response_io(read, time.monotonic() + 3)), {'ok': True})
                self.assertTrue(blocked.is_set())
            finally:
                blocked.set()
                owner.join(timeout=3)
            self.assertFalse(owner.is_alive())

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_stop_retries_visible_response_sharing_race_and_waits_for_child(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory)
            request(root, 'status', timeout=5)
            original_read = Path.read_text
            original_unlink = Path.unlink
            denied = {'read': 0, 'unlink': 0}

            def read(path, *args, **kwargs):
                if path.parent.name == 'responses' and not denied['read']:
                    denied['read'] += 1
                    raise PermissionError(13, 'injected transient sharing violation')
                return original_read(path, *args, **kwargs)

            def unlink(path, *args, **kwargs):
                if path.parent.name == 'responses' and path.suffix == '.json' and not denied['unlink']:
                    denied['unlink'] += 1
                    raise PermissionError(13, 'injected transient sharing violation')
                return original_unlink(path, *args, **kwargs)

            try:
                with patch.object(Path, 'read_text', read), patch.object(Path, 'unlink', unlink):
                    stopped = request(root, 'stop', start=False, timeout=5)
                self.assertEqual(denied, {'read': 1, 'unlink': 1})
                self.assertFalse(alive(stopped['worker_pid']))
                self.assertFalse((root / '.cxd/worker.json').exists())
            finally:
                request(root, 'stop', start=False, timeout=5)

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_response_sharing_retry_is_bounded_and_does_not_hide_other_errors(self):
        denied = PermissionError(13, 'persistent access denial')
        with patch('resident_rpc.time.monotonic', side_effect=[10, 10.01]), patch('resident_rpc.time.sleep') as sleep:
            with self.assertRaises(PermissionError) as caught:
                response_io(lambda: (_ for _ in ()).throw(denied), 10.005)
            self.assertIs(caught.exception, denied)
            sleep.assert_called_once()
            self.assertLessEqual(sleep.call_args.args[0], .0051)
        with patch('resident_rpc.time.sleep') as sleep:
            with self.assertRaises(FileNotFoundError):
                response_io(lambda: (_ for _ in ()).throw(FileNotFoundError()), time.monotonic() + 1)
            sleep.assert_not_called()

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
