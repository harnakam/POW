import copy
import contextlib
import ctypes
from ctypes import wintypes
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch, Mock

import importlib.util
SCRIPT = Path(__file__).resolve().parents[1] / 'commands/optimize-latency/native/scripts/activate_desktop.py'
spec = importlib.util.spec_from_file_location('activate_desktop', SCRIPT)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class FakeRegistry:
    def __init__(self, values=None):
        self.values = copy.deepcopy(values or dict.fromkeys(a.NAMES))
        self.writes = []
        self.fail = None

    def get(self, name):
        return copy.deepcopy(self.values[name])

    def put(self, name, value):
        self.writes.append((name, copy.deepcopy(value)))
        self.values[name] = copy.deepcopy(value)
        if self.fail == len(self.writes):
            raise OSError('simulated partial write')


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binary = self.root / 'custom.exe'
        self.vendor = self.root / 'vendor.exe'
        self.binary.write_bytes(b'custom ' + b' '.join(a.MARKERS))
        self.vendor.write_bytes(b'vendor')
        self.state = self.root / 'activation.json'
        self.reg = FakeRegistry()
        self.version = lambda _: 'codex-cli 0.164.0-alpha.11.1'

    def plan(self, **kwargs):
        return a.plan(self.binary, self.vendor, kwargs.get('concurrency', 3), self.state,
                      self.reg, kwargs.get('get_version', self.version))

    def enable(self):
        return a.enable(self.binary, self.vendor, 3, self.state, self.reg, self.version)

    def test_plan_is_read_only_and_reports_exact_hashes(self):
        result = self.plan()
        self.assertTrue(result['restart_required'])
        self.assertFalse(result['running_engine_verified'])
        self.assertEqual(result['record']['binary']['sha256'], hashlib.sha256(self.binary.read_bytes()).hexdigest())
        self.assertEqual(result['record']['vendor']['sha256'], hashlib.sha256(b'vendor').hexdigest())
        self.assertFalse(self.state.exists())
        self.assertEqual(self.reg.writes, [])

    def test_version_mismatch_and_missing_markers_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'match exactly'):
            self.plan(get_version=lambda path: 'codex-cli 0.164.0-alpha.11.1' if path == str(self.binary) else 'codex-cli 0.156.1')
        self.binary.write_bytes(b'not patched')
        with self.assertRaisesRegex(ValueError, 'markers'):
            self.plan()
        self.assertFalse(self.state.exists())
        self.assertEqual(self.reg.writes, [])

    def test_invalid_limits_and_binary_mutation_fail_closed(self):
        for value in (0, 1025, True, 1.5):
            with self.assertRaises(ValueError):
                self.plan(concurrency=value)
        def mutate(path):
            self.binary.write_bytes(b'changed')
            return self.version(path)
        with self.assertRaisesRegex(ValueError, 'changed during verification'):
            self.plan(get_version=mutate)

    def test_version_probe_is_bounded_and_uses_only_version_argument(self):
        with patch.object(a.subprocess, 'run') as run:
            run.return_value.stdout = 'codex-cli 0.164.0-alpha.11.1\n'
            self.assertEqual(a.version(self.binary), self.version(None))
            self.assertEqual(run.call_args.args[0], [str(self.binary), '--version'])
            self.assertEqual(run.call_args.kwargs['timeout'], 10)
            self.assertTrue(run.call_args.kwargs['check'])

    def test_arbitrary_matching_versions_are_rejected_in_plan_and_state(self):
        for value in ('matching-output', 'codex-cli 1.2', 'codex-cli 1.2.3\nextra', 'codex 1.2.3'):
            with self.assertRaisesRegex(ValueError, 'semantic version'):
                self.plan(get_version=lambda _, v=value: v)
        self.enable()
        data = json.loads(self.state.read_text())
        data['version'] = 'matching-output'
        self.state.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'semantic version'):
            a.disable(self.state, self.reg)

    def test_enable_and_disable_restore_expand_type_and_absence(self):
        original = {a.NAMES[0]: {'value': '%LOCALAPPDATA%\\old.exe', 'type': 2}, a.NAMES[1]: None}
        self.reg = FakeRegistry(original)
        enabled = self.enable()
        self.assertEqual(enabled['status'], 'registry_configured')
        self.assertFalse(enabled['running_engine_verified'])
        self.assertEqual(self.reg.values[a.NAMES[0]], {'value': str(self.binary), 'type': 1})
        self.assertEqual(self.enable()['registry_already_configured'], True)
        self.assertEqual(a.disable(self.state, self.reg)['status'], 'restored')
        self.assertEqual(self.reg.values, original)
        self.assertFalse(self.state.exists())
        self.assertEqual(a.disable(self.state, self.reg)['status'], 'absent')

    def test_external_edits_are_preserved_and_state_retained(self):
        self.enable()
        self.reg.values[a.NAMES[1]] = {'value': 'external', 'type': 2}
        before = copy.deepcopy(self.reg.values)
        for operation in (self.enable, lambda: a.disable(self.state, self.reg)):
            with self.assertRaises(ValueError):
                operation()
            self.assertEqual(self.reg.values, before)
            self.assertTrue(self.state.exists())

    def test_partial_write_failure_rolls_back_environment_and_state(self):
        original = copy.deepcopy(self.reg.values)
        self.reg.fail = 2
        with self.assertRaisesRegex(OSError, 'partial write'):
            self.enable()
        self.assertEqual(self.reg.values, original)
        self.assertFalse(self.state.exists())

    def test_rollback_failure_retains_recovery_state(self):
        self.reg.fail = 2
        original_put = self.reg.put
        def fail_restore(name, value):
            if len(self.reg.writes) >= 2:
                raise OSError('restore failed')
            original_put(name, value)
        self.reg.put = fail_restore
        with self.assertRaisesRegex(RuntimeError, 'retained for recovery'):
            self.enable()
        self.assertTrue(self.state.exists())

    def test_existing_ownership_cannot_be_changed_or_redirected(self):
        self.enable()
        before = copy.deepcopy(self.reg.values)
        with self.assertRaisesRegex(ValueError, 'changed'):
            a.enable(self.binary, self.vendor, 4, self.state, self.reg, self.version)
        data = json.loads(self.state.read_text())
        data['applied'][a.NAMES[0]]['value'] = 'unrelated.exe'
        self.state.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'invalid applied'):
            a.disable(self.state, self.reg)
        self.assertEqual(self.reg.values, before)

    def test_concurrent_mutation_is_refused_without_registry_writes(self):
        lock = Path(str(self.state) + '.lock')
        lock.write_text('another invocation')
        with self.assertRaises(FileExistsError):
            self.enable()
        self.assertEqual(lock.read_text(), 'another invocation')
        self.assertEqual(self.reg.writes, [])
        self.assertFalse(self.state.exists())

    def test_state_write_failure_prevents_registry_mutation(self):
        with patch.object(a, 'save_state', side_effect=OSError('state unavailable')):
            with self.assertRaises(OSError):
                self.enable()
        self.assertEqual(self.reg.writes, [])

    def test_concurrent_external_edit_after_plan_is_not_overwritten(self):
        save = a.save_state
        def save_then_edit(path, record):
            save(path, record)
            self.reg.values[a.NAMES[0]] = {'value': 'external.exe', 'type': 2}
        with patch.object(a, 'save_state', side_effect=save_then_edit):
            with self.assertRaisesRegex(RuntimeError, 'retained for recovery'):
                self.enable()
        self.assertEqual(self.reg.values[a.NAMES[0]], {'value': 'external.exe', 'type': 2})
        self.assertEqual(self.reg.writes, [])
        self.assertTrue(self.state.exists())

    def test_unknown_state_keys_and_nonstring_registry_values_are_rejected(self):
        self.enable()
        data = json.loads(self.state.read_text())
        data['redirect'] = str(self.root / 'unrelated')
        self.state.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'ownership state'):
            a.disable(self.state, self.reg)
        self.state.unlink()
        self.reg.values[a.NAMES[1]] = {'value': 7, 'type': 4}
        with self.assertRaisesRegex(ValueError, 'must be strings'):
            self.plan()

    def test_markers_across_stream_chunk_boundary(self):
        self.binary.write_bytes(b'x' * (1024 * 1024 - 5) + b' '.join(a.MARKERS))
        self.assertEqual(a.fingerprint(self.binary)[1], set(a.MARKERS))

    def test_notification_is_opt_in_and_separate_from_registry_result(self):
        enabled = self.enable()
        send = Mock(return_value={'status': 'sent', 'win32_error': 0})
        self.assertIs(a.with_environment_notification(enabled, send=send), enabled)
        send.assert_not_called()
        result = a.with_environment_notification(enabled, True, send)
        self.assertEqual(result['status'], 'registry_configured')
        self.assertEqual(result['environment_notification']['status'], 'sent')
        self.assertFalse(result['running_engine_verified'])
        self.assertFalse(result['environment_notification']['running_process_environment_changed'])

    def test_notification_failures_do_not_rollback_successful_registry_writes(self):
        enabled = self.enable()
        configured = copy.deepcopy(self.reg.values)
        send = Mock(side_effect=OSError('mock notification error'))
        result = a.with_environment_notification(enabled, True, send)
        self.assertEqual(result['status'], 'registry_configured')
        self.assertEqual(result['environment_notification']['status'], 'failed')
        self.assertEqual(self.reg.values, configured)
        self.assertTrue(self.state.exists())
        restored = a.disable(self.state, self.reg)
        result = a.with_environment_notification(restored, True, send)
        self.assertEqual(result['status'], 'restored')
        self.assertEqual(result['environment_notification']['status'], 'failed')
        self.assertFalse(self.state.exists())

    def test_notification_total_wait_is_bounded_and_delivery_unknown_after_timeout(self):
        release = threading.Event()
        try:
            result = a.with_environment_notification(
                {'action': 'enable', 'status': 'registry_configured'}, True,
                lambda: (release.wait(2) and {'status': 'sent'}), deadline_s=.01)
            self.assertEqual(result['environment_notification']['status'], 'wait_timed_out')
            self.assertTrue(result['environment_notification']['delivery_unknown'])
        finally:
            release.set()

    def test_plan_rejects_notification_before_registry_access(self):
        with patch.object(a, 'Registry') as registry, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(a.main(['plan', '--state', str(self.state), '--notify-environment']), 1)
        registry.assert_not_called()

    def test_standard_environment_message_uses_mocked_windows_api_only(self):
        captured = {}
        def send(*args):
            captured.update(hwnd=args[0], message=args[1], text=ctypes.wstring_at(args[3]),
                            flags=args[4], timeout=args[5])
            return 1
        library = Mock()
        library.SendMessageTimeoutW = Mock(side_effect=send)
        with patch.object(ctypes, 'WinDLL', return_value=library, create=True), \
                patch.object(ctypes, 'set_last_error', create=True), patch.object(a.os, 'name', 'nt'):
            self.assertEqual(a.broadcast_environment()['status'], 'sent')
        self.assertEqual(captured, {'hwnd': 0xffff, 'message': 0x001a, 'text': 'Environment',
                                    'flags': 0x0002, 'timeout': 2000})


if __name__ == '__main__':
    unittest.main()
