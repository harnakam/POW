"""Analyze explicit local Codex timing inputs; export only aggregate metadata.

Adapted from the existing analyze_model_timeline.py and measure_task.py meters.
No watcher, implicit account discovery, raw-content export, or external calls.
"""
import argparse
from collections import defaultdict
from contextlib import closing
import datetime as dt
import json
import math
from pathlib import Path
import re
import sqlite3
import sys

ITEM = re.compile(r'Output item item_type="([^"]+)" item_id="([^"]+)"')
ARGUMENT_TYPES = {'custom_tool_call', 'function_call'}
OUTPUT_TYPES = {'custom_tool_call_output', 'function_call_output'}
LIMITATIONS = [
    'Client task and request event boundaries are not UI paint or server receipt times.',
    'Request-to-first-item combines transport, service waiting and pre-output computation.',
    'Argument and reasoning spans are event envelopes, not pure compute times.',
    'Tool wait combines execution, hooks, process startup and result transport.',
    'Other boundaries include logging gaps and result/next-request preparation.',
    'Parent-thread intervals may overlap sub-agent work; do not add their wall times.',
    'Missing events and log schema changes prevent exact attribution; counts expose known gaps.',
    'This report is not a same-workload speed comparison and includes measurement overhead already in the turn.',
]


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('timing values must be finite numbers')
    return value


def epoch(value):
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('session timestamps must include a timezone')
    return finite(parsed.timestamp())


def session_metadata(path, turn, cutoff=None):
    active, start, end = False, None, None
    pending, tools, messages = {}, [], []
    calls, characters, unknown_sizes, unmatched = 0, 0, 0, 0
    ignored_tail = False
    with Path(path).open(encoding='utf-8') as stream:
        for number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                if not line.endswith('\n'):
                    ignored_tail = True
                    break  # Only a partially appended final line may be ignored.
                raise ValueError(f'invalid session JSON on line {number}') from None
            if not isinstance(row, dict) or not isinstance(row.get('payload'), dict):
                raise ValueError('unsupported session row schema')
            payload, kind = row['payload'], row.get('type')
            if kind == 'event_msg' and payload.get('type') == 'task_started':
                if active:
                    break
                active = payload.get('turn_id') == turn
                if active:
                    start = epoch(row['timestamp'])
            if not active:
                continue
            when = epoch(row['timestamp'])
            if kind == 'response_item':
                call_id, item_type = payload.get('call_id'), payload.get('type')
                if item_type in ARGUMENT_TYPES:
                    if not isinstance(call_id, str) or call_id in pending:
                        raise ValueError('missing or duplicate tool call identifier')
                    pending[call_id] = when
                    calls += 1
                    argument = payload.get('input', payload.get('arguments'))
                    if isinstance(argument, str):
                        characters += len(argument)
                    else:
                        unknown_sizes += 1
                elif item_type in OUTPUT_TYPES:
                    if call_id in pending:
                        tools.append((pending.pop(call_id), when))
                    else:
                        unmatched += 1
            if kind == 'event_msg' and payload.get('type') == 'item_completed':
                if payload.get('item', {}).get('type') == 'AgentMessage':
                    messages.append((finite(payload['started_at_ms']) / 1000,
                                     finite(payload['completed_at_ms']) / 1000))
            if (kind == 'event_msg' and payload.get('type') == 'task_complete'
                    and payload.get('turn_id') in (None, turn)):
                end = when
                break
    if start is None:
        raise ValueError('selected turn start was not found')
    complete = end is not None
    if not complete:
        if cutoff is None:
            raise ValueError('unfinished turn requires explicit --cutoff-unix')
        end = finite(cutoff)
    if end < start:
        raise ValueError('cutoff precedes turn start')
    completed = len(tools)
    tools.extend((begin, end) for begin in pending.values())
    return {'start': start, 'end': end, 'complete': complete, 'tools': tools,
            'messages': messages, 'tool_calls': calls, 'completed_tool_calls': completed,
            'pending_tool_calls': len(pending), 'argument_characters': characters,
            'unknown_argument_sizes': unknown_sizes, 'unmatched_tool_outputs': unmatched,
            'ignored_partial_session_tail': ignored_tail}


def model_metadata(database, thread, start, end):
    database = Path(database).resolve(strict=True)
    if any(Path(str(database) + suffix).exists() for suffix in ('-wal', '-journal')):
        raise ValueError('database must be a consistent standalone snapshot without WAL or journal')
    # Offline immutable snapshots avoid both writes and SQLite sidecar creation.
    uri = database.as_uri() + '?mode=ro&immutable=1'
    requests, items, pending = [], [], {}
    unmatched, ambiguous = 0, 0
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.execute('PRAGMA query_only = ON')
        records = connection.execute(
            'SELECT ts, ts_nanos, target, feedback_log_body FROM logs '
            'WHERE thread_id=? AND ts BETWEEN ? AND ? ORDER BY id',
            (thread, math.floor(start), math.floor(end) + 1))
        for seconds, nanos, target, body in records:
            when = finite(seconds) + finite(nanos) / 1e9
            if not start <= when <= end or not isinstance(body, str):
                continue
            if target == 'feedback_tags' and 'endpoint="/responses"' in body:
                requests.append(when)
            if target != 'codex_core::stream_events_utils':
                continue
            match = ITEM.search(body)
            if match and 'handle_output_item_done:' not in body:
                if match[2] in pending:
                    unmatched += 1
                pending[match[2]] = (when, match[1])
            elif match:
                if match[2] in pending:
                    begin, kind = pending.pop(match[2])
                    items.append((begin, when, kind))
                else:
                    unmatched += 1
            elif 'ToolCall:' in body:
                candidates = [key for key, (_, kind) in pending.items() if kind in ARGUMENT_TYPES]
                if len(candidates) == 1:
                    begin, kind = pending.pop(candidates[0])
                    items.append((begin, when, kind))
                else:
                    ambiguous += 1
    pending_count = len(pending)
    items.extend((begin, end, kind) for begin, kind in pending.values())
    requests.sort()
    waits, missing = [], 0
    for index, request in enumerate(requests):
        boundary = requests[index + 1] if index + 1 < len(requests) else end
        starts = [a for a, _, _ in items if request <= a < boundary]
        if starts:
            waits.append((request, min(starts)))
        else:
            missing += 1
    return {'requests': requests, 'items': items, 'waits': waits,
            'requests_without_output': missing, 'pending_output_items': pending_count,
            'unmatched_output_events': unmatched, 'ambiguous_dispatch_events': ambiguous}


def exclusive_totals(start, end, groups):
    for spans in groups.values():
        for begin, finish in spans:
            finite(begin)
            finite(finish)
            if finish < begin:
                raise ValueError('event interval ends before it starts')
    cuts = sorted({start, end, *[max(start, min(end, value))
                  for spans in groups.values() for pair in spans for value in pair]})
    totals = defaultdict(float)
    for begin, finish in zip(cuts, cuts[1:]):
        middle = (begin + finish) / 2
        category = next((name for name, spans in groups.items()
                         if any(a <= middle < b for a, b in spans)), 'other_boundaries')
        totals[category] += finish - begin
    if not math.isclose(sum(totals.values()), end - start, abs_tol=1e-6):
        raise ValueError('exclusive timing arithmetic failed')
    return dict(totals)


def analyze(session, database, thread, turn, cutoff=None):
    data = session_metadata(session, turn, cutoff)
    start, end = data['start'], data['end']
    model = model_metadata(database, thread, start, end) if database is not None else None
    groups = {'tool_wait': data['tools'], 'assistant_message_stream': data['messages']}
    if model is not None:
        groups.update(tool_argument_stream=[(a, b) for a, b, k in model['items'] if k in ARGUMENT_TYPES],
                      reasoning_item_stream=[(a, b) for a, b, k in model['items'] if k == 'reasoning'],
                      request_to_first_item=model['waits'])
    summary = {key: data[key] for key in ('complete', 'tool_calls', 'completed_tool_calls',
        'pending_tool_calls', 'argument_characters', 'unknown_argument_sizes',
        'unmatched_tool_outputs', 'ignored_partial_session_tail')}
    summary.update(schema_version=1, total_s=end - start,
                   model_log_available=model is not None,
                   model_requests=len(model['requests']) if model is not None else None,
                   exclusive_categories_s=exclusive_totals(start, end, groups),
                   limitations=LIMITATIONS)
    summary['model_event_gaps'] = ({key: model[key] for key in ('requests_without_output',
        'pending_output_items', 'unmatched_output_events', 'ambiguous_dispatch_events')}
        if model is not None else None)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--database', type=Path)
    parser.add_argument('--thread', required=True)
    parser.add_argument('--turn', required=True)
    parser.add_argument('--cutoff-unix', type=float)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = analyze(args.session, args.database, args.thread, args.turn, args.cutoff_unix)
        # Preserve original baselines: output must be a new file.
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        print(json.dumps(report, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        print(f'timing analysis failed ({type(error).__name__}); check input schema, boundaries and output destination', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
