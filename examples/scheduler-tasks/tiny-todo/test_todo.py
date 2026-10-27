from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from todo import main


class TodoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / 'tasks.json'

    def cli(self, *args):
        command = ['--file', str(self.file), *args]
        stdout, stderr = io.StringIO(), io.StringIO()
        returncode = 0
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                main(command)
            except SystemExit as error:
                returncode = error.code
        return subprocess.CompletedProcess(command, returncode, stdout.getvalue(), stderr.getvalue())

    def test_process_entrypoint_reads_persisted_data(self):
        self.assertEqual(self.cli('add', 'saved by another invocation').returncode, 0)
        listed = subprocess.run(
            [sys.executable, str(Path(__file__).with_name('todo.py')),
             '--file', str(self.file), 'list'], capture_output=True, text=True,
        )
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(listed.stdout.strip(), '1 [ ] saved by another invocation')

    def test_persistent_lifecycle(self):
        self.assertEqual(self.cli('list').stdout, '')
        added = self.cli('add', 'measure latency')
        self.assertEqual(added.returncode, 0, added.stderr)
        self.assertEqual(added.stdout.strip(), '1')
        self.assertIn('1 [ ] measure latency', self.cli('list').stdout)
        self.assertEqual(self.cli('done', '1').returncode, 0)
        self.assertIn('1 [x] measure latency', self.cli('list').stdout)
        self.assertTrue(json.loads(self.file.read_text())[0]['done'])

    def test_invalid_input_preserves_data(self):
        self.cli('add', 'keep')
        original = self.file.read_bytes()
        self.assertNotEqual(self.cli('done', '99').returncode, 0)
        self.assertNotEqual(self.cli('add', ' ').returncode, 0)
        self.assertEqual(self.file.read_bytes(), original)

    def test_corrupted_file_is_not_overwritten(self):
        self.file.write_text('{broken', encoding='utf-8')
        self.assertNotEqual(self.cli('add', 'test').returncode, 0)
        self.assertEqual(self.file.read_text(), '{broken')


if __name__ == '__main__':
    unittest.main()
