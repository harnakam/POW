import contextlib
from contextlib import closing
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import datetime as dt

SCRIPT = Path(__file__).resolve().parents[1] / 'commands/optimize-latency/scripts/measurement/analyze_timeline.py'
spec = importlib.util.spec_from_file_location('analyze_timeline', SCRIPT)
meter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(meter)
BASE = 1700000000
PRIVATE = 'private-message-secret'


def stamp(seconds):
    return dt.datetime.fromtimestamp(BASE + seconds, dt.timezone.utc).isoformat()


def event(seconds, kind, payload):
    return {'timestamp': stamp(seconds), 'type': kind, 'payload': payload}


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session = self.root / 'private-session.jsonl'
        self.database = self.root / 'private-logs.sqlite'
        self.output = self.root / 'summary.json'
        self.rows = [
            event(-2, 'event_msg', {'type': 'task_started', 'turn_id': 'other-private-turn'}),
            event(0, 'event_msg', {'type': 'task_started', 'turn_id': 'selected-private-turn'}),
            event(1, 'response_item', {'type': 'function_call', 'call_id': 'private-call', 'name': PRIVATE, 'arguments': PRIVATE}),
            event(3, 'response_item', {'type': 'function_call_output', 'call_id': 'private-call', 'output': PRIVATE}),
            event(4, 'event_msg', {'type': 'item_completed', 'item': {'type': 'AgentMessage', 'text': PRIVATE}, 'started_at_ms': (BASE + 3) * 1000, 'completed_at_ms': (BASE + 4) * 1000}),
            event(5, 'event_msg', {'type': 'task_complete', 'turn_id': 'selected-private-turn'}),
        ]
        self.write_session()
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('CREATE TABLE logs(id INTEGER PRIMARY KEY, ts INTEGER, ts_nanos INTEGER, target TEXT, feedback_log_body TEXT, thread_id TEXT)')
            records = [
                (.1, 'feedback_tags', 'endpoint="/responses" ' + PRIVATE),
                (.2, 'codex_core::stream_events_utils', 'Output item item_type="reasoning" item_id="private-reason"'),
                (.4, 'codex_core::stream_events_utils', 'handle_output_item_done: Output item item_type="reasoning" item_id="private-reason"'),
                (.4, 'codex_core::stream_events_utils', 'Output item item_type="function_call" item_id="private-argument"'),
                (1, 'codex_core::stream_events_utils', 'ToolCall: ' + PRIVATE),
            ]
            for index, (seconds, target, body) in enumerate(records):
                db.execute('INSERT INTO logs VALUES(?,?,?,?,?,?)', (index, BASE + int(seconds), round((seconds % 1) * 1e9), target, body, 'private-thread'))

    def write_session(self):
        self.session.write_text(''.join(json.dumps(row) + '\n' for row in self.rows), encoding='utf-8')

    def analyze(self, database=True, cutoff=None):
        return meter.analyze(self.session, self.database if database else None,
                             'private-thread', 'selected-private-turn', cutoff)

    def test_exclusive_arithmetic_and_observed_counts(self):
        result = self.analyze()
        self.assertTrue(result['complete'])
        self.assertEqual(result['total_s'], 5)
        self.assertEqual(result['model_requests'], 1)
        self.assertEqual(result['tool_calls'], 1)
        self.assertEqual(result['argument_characters'], len(PRIVATE))
        spans = result['exclusive_categories_s']
        self.assertAlmostEqual(spans['tool_wait'], 2)
        self.assertAlmostEqual(spans['assistant_message_stream'], 1)
        self.assertAlmostEqual(spans['reasoning_item_stream'], .2, places=6)
        self.assertAlmostEqual(spans['tool_argument_stream'], .6, places=6)
        self.assertAlmostEqual(spans['request_to_first_item'], .1, places=6)
        self.assertAlmostEqual(sum(spans.values()), 5)
        self.assertEqual(result['model_event_gaps']['pending_output_items'], 0)

    def test_export_has_no_content_identifiers_paths_or_absolute_timestamps(self):
        result = json.dumps(self.analyze())
        for private in (PRIVATE, 'private-thread', 'selected-private-turn', 'private-call',
                        'private-reason', 'private-argument', str(self.root), str(BASE)):
            self.assertNotIn(private, result)

    def test_database_remains_byte_for_byte_unchanged(self):
        before = self.database.read_bytes()
        self.analyze()
        self.assertEqual(self.database.read_bytes(), before)
        self.assertFalse(Path(str(self.database) + '-journal').exists())

    def test_missing_database_is_unknown_instead_of_zero_requests(self):
        result = self.analyze(database=False)
        self.assertIsNone(result['model_requests'])
        self.assertFalse(result['model_log_available'])
        self.assertNotIn('reasoning_item_stream', result['exclusive_categories_s'])
        self.assertAlmostEqual(sum(result['exclusive_categories_s'].values()), 5)

    def test_live_wal_database_is_rejected_instead_of_ignoring_uncheckpointed_rows(self):
        wal = Path(str(self.database) + '-wal')
        wal.write_bytes(b'live data')
        with self.assertRaisesRegex(ValueError, 'standalone snapshot'):
            self.analyze()

    def test_unfinished_requires_explicit_cutoff_and_retains_pending_work(self):
        self.rows = self.rows[:3]
        self.write_session()
        with self.assertRaisesRegex(ValueError, 'cutoff'):
            self.analyze(database=False)
        result = self.analyze(database=False, cutoff=BASE + 2)
        self.assertFalse(result['complete'])
        self.assertEqual(result['pending_tool_calls'], 1)
        self.assertEqual(result['completed_tool_calls'], 0)
        self.assertAlmostEqual(result['exclusive_categories_s']['tool_wait'], 1)

    def test_only_incomplete_final_json_line_is_ignored(self):
        self.rows = self.rows[:3]
        self.write_session()
        with self.session.open('a', encoding='utf-8') as stream:
            stream.write('{"partial":')
        self.assertTrue(self.analyze(database=False, cutoff=BASE + 2)['ignored_partial_session_tail'])
        with self.session.open('a', encoding='utf-8') as stream:
            stream.write('\n')
        with self.assertRaisesRegex(ValueError, 'invalid session JSON'):
            self.analyze(database=False, cutoff=BASE + 2)

    def test_missing_turn_and_invalid_intervals_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'start was not found'):
            meter.analyze(self.session, None, 'thread', 'absent')
        with self.assertRaisesRegex(ValueError, 'ends before'):
            meter.exclusive_totals(0, 1, {'tool_wait': [(1, 0)]})
        with self.assertRaises(ValueError):
            meter.finite(float('nan'))

    def test_ambiguous_dispatch_is_counted_without_guessing_an_item(self):
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('DELETE FROM logs WHERE id=4')
            db.execute('INSERT INTO logs VALUES(?,?,?,?,?,?)', (6, BASE, 500000000,
                'codex_core::stream_events_utils',
                'Output item item_type="custom_tool_call" item_id="another-private-id"', 'private-thread'))
            db.execute('INSERT INTO logs VALUES(?,?,?,?,?,?)', (7, BASE + 1, 100000000,
                'codex_core::stream_events_utils', 'ToolCall: private', 'private-thread'))
        result = self.analyze()
        self.assertEqual(result['model_event_gaps']['ambiguous_dispatch_events'], 1)
        self.assertEqual(result['model_event_gaps']['pending_output_items'], 2)

    def test_cli_creates_sanitized_new_output_and_preserves_existing_baseline(self):
        arguments = ['--session', str(self.session), '--database', str(self.database),
                     '--thread', 'private-thread', '--turn', 'selected-private-turn',
                     '--output', str(self.output)]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(meter.main(arguments), 0)
            before = self.output.read_bytes()
            self.assertEqual(meter.main(arguments), 1)
        self.assertEqual(self.output.read_bytes(), before)
        self.assertNotIn(PRIVATE, stdout.getvalue() + stderr.getvalue())
        self.assertNotIn(str(self.root), stdout.getvalue() + stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
