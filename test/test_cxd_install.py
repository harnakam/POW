import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'commands/optimize-latency/scripts/install_cxd.py'
spec = importlib.util.spec_from_file_location('install_cxd', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='install spaces ', dir=ROOT / 'test')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binary = self.root / 'bin space'
        self.package = self.root / 'package space'
        self.shim = self.binary / ('cxd.cmd' if os.name == 'nt' else 'cxd')

    def run_install(self, action='install', ok=True):
        result = subprocess.run([sys.executable, '-S', str(SCRIPT), action,
                                 '--bin-dir', str(self.binary), '--package-dir', str(self.package)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def test_install_repeat_status_and_actual_shim(self):
        self.run_install()
        original = self.snapshot()
        self.run_install()
        self.assertEqual(original, self.snapshot())
        status = json.loads(self.run_install('status').stdout)
        self.assertEqual(status['shim'], str(self.shim))
        workspace = self.root / "workspace 'quote' space"
        workspace.mkdir()
        for command in ('init', 'aliases'):
            argv = [str(self.shim), command, '--workspace', str(workspace)]
            if os.name == 'nt':
                # cmd /s requires outer quotes around a command with a quoted executable.
                argv = ('"' + os.environ.get('COMSPEC', 'cmd.exe') + '" /d /s /c "'
                        + subprocess.list2cmdline(argv) + '"')
            result = subprocess.run(argv,
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIsInstance(json.loads(result.stdout), dict)
        self.assertTrue((workspace / '.codex-dispatch.json').exists())
        self.assertFalse((self.package / '__pycache__').exists())
        self.run_install('uninstall')
        self.run_install()
        self.run_install('status')

    def test_refuses_unowned_shim_before_writes(self):
        self.binary.mkdir()
        self.shim.write_text('mine')
        before = self.snapshot()
        self.run_install(ok=False)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.package.exists())

    def test_refuses_unowned_package(self):
        self.package.mkdir()
        (self.package / 'dispatch.py').write_text('mine')
        before = self.snapshot()
        for action in ('install', 'uninstall', 'status'):
            self.run_install(action, ok=False)
        self.assertEqual(before, self.snapshot())

    def test_modified_runtime_or_shim_preserved(self):
        for name in ('dispatch.py', 'shim'):
            with self.subTest(name=name):
                self.run_install()
                target = self.shim if name == 'shim' else self.package / name
                original = target.read_bytes()
                target.write_bytes(original + b'\n# local edit\n')
                before = self.snapshot()
                for action in ('install', 'uninstall', 'status'):
                    self.run_install(action, ok=False)
                    self.assertEqual(before, self.snapshot())
                target.write_bytes(original)
                self.run_install('uninstall')

    def test_uninstall_preserves_unknown_files_and_is_idempotent(self):
        self.run_install()
        unknown = self.package / 'custom' / 'notes.txt'
        unknown.parent.mkdir()
        unknown.write_text('keep')
        self.run_install('uninstall')
        self.assertFalse(self.shim.exists())
        self.assertEqual(unknown.read_text(), 'keep')
        self.assertFalse((self.package / installer.RECEIPT).exists())
        # Unknown nonempty package is now unowned and must not be adopted or removed.
        self.run_install('uninstall', ok=False)
        self.assertEqual(unknown.read_text(), 'keep')

    def test_clean_uninstall_repeat(self):
        self.run_install()
        self.run_install('uninstall')
        self.run_install('uninstall')
        self.assertEqual(json.loads(self.run_install('status').stdout)['status'], 'absent')

    def test_receipt_cannot_redirect_deletion(self):
        self.run_install()
        foreign = self.root / 'foreign.txt'
        foreign.write_text('keep')
        receipt = self.package / installer.RECEIPT
        data = json.loads(receipt.read_text())
        data['files'][str(foreign)] = installer.digest(foreign.read_bytes())
        receipt.write_text(json.dumps(data))
        before = self.snapshot()
        self.run_install('uninstall', ok=False)
        self.assertEqual(before, self.snapshot())

    def test_owned_update_and_unknown_file_survival(self):
        self.run_install()
        unknown = self.package / 'notes.txt'
        unknown.write_text('keep')
        source_file = SCRIPT.parent / 'cxd' / 'dispatch.py'
        replacement = source_file.read_bytes() + b'\n# new bundled revision\n'
        original_read = Path.read_bytes

        def changed_source(path):
            return replacement if path == source_file else original_read(path)

        with patch.object(Path, 'read_bytes', changed_source):
            installer.operate('install', self.binary, self.package)
        self.assertEqual((self.package / 'dispatch.py').read_bytes(), replacement)
        self.assertEqual(unknown.read_text(), 'keep')
        self.run_install('status')
        self.run_install('uninstall')

    def test_malformed_receipt_is_rejected(self):
        self.run_install()
        (self.package / installer.RECEIPT).write_text('[]')
        before = self.snapshot()
        self.run_install('uninstall', ok=False)
        self.assertEqual(before, self.snapshot())

    def test_failed_update_restores_previous_files(self):
        self.run_install()
        before = self.snapshot()
        real_write = installer.atomic_write
        calls = 0

        def fail_once(path, content, mode):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise PermissionError('test denied')
            return real_write(path, content, mode)

        with patch.object(installer, 'atomic_write', side_effect=fail_once):
            with self.assertRaises(PermissionError):
                installer.operate('install', self.binary, self.package)
        self.assertEqual(before, self.snapshot())

    @unittest.skipUnless(os.name == 'nt', 'Windows batch path rules')
    def test_windows_expansion_paths_refused_before_writes(self):
        self.package = self.root / 'percent%PATH%'
        self.run_install(ok=False)
        self.assertFalse(self.package.exists())
        self.assertFalse(self.binary.exists())


if __name__ == '__main__':
    unittest.main()
