import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'commands/optimize-latency/native/scripts/inspect_desktop.py'
spec = importlib.util.spec_from_file_location('inspect_desktop', SCRIPT)
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)


class InspectionTests(unittest.TestCase):
    def test_reads_known_entries_without_extracting_source(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            path = Path(temp) / 'app.asar'
            content = b'const name="CODEX_CLI_PATH";'
            header = {'files': {'.vite': {'files': {'build': {'files': {
                'main-test.js': {'offset': '0', 'size': len(content)}}}}}}}
            raw = json.dumps(header).encode()
            payload = ((len(raw) + 7) // 4) * 4
            path.write_bytes(struct.pack('<4I', 4, payload + 4, payload, len(raw))
                             + raw + b'\0' * (payload - 4 - len(raw)) + content)
            before = path.read_bytes()
            result = inspector.scan_asar(path)
            self.assertEqual(result['observed_keys'], ['CODEX_CLI_PATH'])
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual([p.name for p in Path(temp).iterdir()], ['app.asar'])

    def test_rejects_truncated_or_unbounded_header(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            path = Path(temp) / 'app.asar'
            for raw in (b'bad', struct.pack('<4I', 4, 0x7fffffff, 0x7ffffffb, 0x7ffffff0)):
                path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    inspector.scan_asar(path)


if __name__ == '__main__':
    unittest.main()
