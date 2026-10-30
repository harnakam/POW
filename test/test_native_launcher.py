import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


LAUNCHER = Path(__file__).resolve().parents[1] / "commands/optimize-latency/native/scripts/native_launcher.py"


class NativeLauncherTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="native-launcher-", dir=LAUNCHER.parent)
        self.addCleanup(self.directory.cleanup)
        self.receipt = Path(self.directory.name) / "検証 receipt.json"
        hasher = hashlib.sha256()
        with Path(sys.executable).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        self.document = {"binary": {"sha256": digest}, "scheduler": {"environment_variable": "CODEX_NATIVE_TOOL_CONCURRENCY"}}
        self.receipt.write_text(json.dumps(self.document), encoding="utf-8")

    def launch(self, *arguments, **kwargs):
        return subprocess.run([sys.executable, str(LAUNCHER), "--binary", sys.executable, "--receipt", str(self.receipt), *arguments], text=True, capture_output=True, **kwargs)

    def test_non_tty_stdio_arguments_environment_and_child_exit_are_preserved(self):
        script = "import os,sys,json; print(json.dumps([os.environ['CODEX_NATIVE_TOOL_CONCURRENCY'],sys.argv[1:],sys.stdin.read()])); sys.exit(7)"
        original = os.environ.get("CODEX_NATIVE_TOOL_CONCURRENCY")
        result = self.launch("--concurrency", "3", "--", "-c", script, "space argument", "日本語", input="stdin value")
        self.assertEqual(result.returncode, 7)
        self.assertEqual(json.loads(result.stdout), ["3", ["space argument", "日本語"], "stdin value"])
        self.assertEqual(result.stderr, "")
        self.assertEqual(os.environ.get("CODEX_NATIVE_TOOL_CONCURRENCY"), original)

    def test_invalid_limit_fails_before_launch(self):
        for value in ("0", "1025", "bad"):
            with self.subTest(value=value):
                result = self.launch("--concurrency", value, "--", "--version")
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")

    def test_binary_receipt_mismatch_fails_closed(self):
        self.document["binary"]["sha256"] = "0" * 64
        self.receipt.write_text(json.dumps(self.document), encoding="utf-8")
        result = self.launch("--verify-only")
        self.assertEqual(result.returncode, 2)
        self.assertIn("SHA-256", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_verify_only_reports_identity_without_claiming_live_dispatch(self):
        result = self.launch("--verify-only")
        self.assertEqual(result.returncode, 0)
        self.assertIn("does not prove live tool dispatch", json.loads(result.stdout)["verification"])


if __name__ == "__main__":
    unittest.main()
