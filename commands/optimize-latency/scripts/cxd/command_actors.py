"""Run a bounded DAG of local commands; completion is awaitable without polling."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import re
import queue
import signal
import subprocess
import sys
import time
import threading


def validate_manifest(manifest, concurrency=4, base_dir=None, handlers=None):
    """Validate the entire command graph before creating files or processes."""
    if type(concurrency) is not int or concurrency < 1:
        raise ValueError('concurrency must be a positive integer')
    if not isinstance(manifest, dict) or not isinstance(manifest.get('jobs'), list) or not manifest['jobs']:
        raise ValueError('manifest must contain a nonempty jobs list')
    if manifest.get('scheduling', 'critical_path') not in {'fifo', 'critical_path'}:
        raise ValueError('scheduling must be fifo or critical_path')
    base_dir = Path.cwd() if base_dir is None else Path(base_dir)
    jobs = {}
    handlers = handlers or {}
    folded_ids = set()
    for raw in manifest['jobs']:
        if not isinstance(raw, dict):
            raise ValueError('each job must be an object')
        job_id = raw.get('id')
        if not isinstance(job_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', job_id):
            raise ValueError('job id must be 1-64 filename-safe ASCII characters')
        if job_id.casefold() in folded_ids:
            raise ValueError(f'duplicate job id: {job_id}')
        argv = raw.get('argv')
        operation = raw.get('operation')
        if operation is not None:
            if (not isinstance(operation, str) or operation not in handlers or argv is not None
                    or not isinstance(raw.get('parameters', {}), dict)):
                raise ValueError(f'{job_id}: unsupported operation or invalid parameters')
        elif (not isinstance(argv, list) or not argv
                or any(not isinstance(arg, str) or '\0' in arg for arg in argv)
                or not argv[0].strip()):
            raise ValueError(f'{job_id}: argv must be a nonempty list of strings')
        dependencies = raw.get('depends_on', [])
        if (not isinstance(dependencies, list)
                or any(not isinstance(item, str) for item in dependencies)
                or len(set(dependencies)) != len(dependencies)):
            raise ValueError(f'{job_id}: depends_on must contain unique job ids')
        timeout = raw.get('timeout_s', 60)
        if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout) or timeout <= 0):
            raise ValueError(f'{job_id}: timeout_s must be finite and positive')
        cwd = raw.get('cwd')
        if cwd is not None:
            if not isinstance(cwd, str) or not cwd or '\0' in cwd:
                raise ValueError(f'{job_id}: cwd must be a directory path')
            cwd = Path(cwd)
            cwd = (base_dir / cwd).resolve() if not cwd.is_absolute() else cwd.resolve()
            if not cwd.is_dir():
                raise ValueError(f'{job_id}: cwd directory does not exist')
            cwd = str(cwd)
        jobs[job_id] = {'id': job_id, 'cwd': cwd,
                        'depends_on': list(dependencies), 'timeout_s': float(timeout)}
        estimate = raw.get('estimated_s', 1)
        if (isinstance(estimate, bool) or not isinstance(estimate, (int, float))
                or not math.isfinite(estimate) or estimate <= 0):
            raise ValueError(f'{job_id}: estimated_s must be finite and positive')
        jobs[job_id]['estimated_s'] = float(estimate)
        for claim in ('reads', 'writes'):
            values = raw.get(claim, [])
            if (not isinstance(values, list) or any(not isinstance(value, str)
                    or not value.strip() or '\0' in value for value in values)
                    or len(set(values)) != len(values)):
                raise ValueError(f'{job_id}: {claim} must contain unique nonempty resource keys')
            jobs[job_id][claim] = list(values)
        if operation is not None:
            jobs[job_id].update(operation=operation, parameters=raw.get('parameters', {}))
        else:
            jobs[job_id]['argv'] = list(argv)
        folded_ids.add(job_id.casefold())
    visiting, visited = set(), set()

    def visit(job_id):
        if job_id in visiting:
            raise ValueError(f'dependency cycle at {job_id}')
        if job_id in visited:
            return
        visiting.add(job_id)
        for dependency in jobs[job_id]['depends_on']:
            if dependency not in jobs:
                raise ValueError(f'{job_id}: unknown dependency {dependency}')
            visit(dependency)
        visiting.remove(job_id)
        visited.add(job_id)

    for job_id in jobs:
        visit(job_id)
    if not math.isfinite(sum(job['estimated_s'] for job in jobs.values())):
        raise ValueError('total estimated duration must be finite')
    return jobs


def critical_path_scores(jobs):
    children = {name: [] for name in jobs}
    for name, job in jobs.items():
        for dependency in job['depends_on']:
            children[dependency].append(name)
    scores = {}
    def score(name):
        if name not in scores:
            scores[name] = jobs[name]['estimated_s'] + max(
                (score(child) for child in children[name]), default=0)
        return scores[name]
    for name in jobs:
        score(name)
    return scores


def resources_conflict(first, second):
    return bool(set(first['writes']) & (set(second['reads']) | set(second['writes']))
                or set(second['writes']) & set(first['reads']))


def scheduling_plan(manifest, concurrency=4, base_dir=None, handlers=None):
    jobs = validate_manifest(manifest, concurrency, base_dir, handlers)
    scores = critical_path_scores(jobs)
    policy = manifest.get('scheduling', 'critical_path')
    order = sorted(jobs, key=lambda name: -scores[name]) if policy == 'critical_path' else list(jobs)
    return {'scheduling': policy, 'concurrency': concurrency,
            'estimated_lower_bound_s': max(max(scores.values(), default=0),
                sum(job['estimated_s'] for job in jobs.values()) / concurrency),
            'priority_order': order, 'critical_path_scores': scores,
            'resource_conflicts': [[a, b] for i, a in enumerate(jobs)
                                   for b in list(jobs)[i + 1:] if resources_conflict(jobs[a], jobs[b])]}


def _atomic_json(path, data):
    temporary = path.with_suffix('.json.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    os.replace(temporary, path)


def _terminate_tree(process, stderr):
    """Terminate only the process tree created for this job."""
    if os.name == 'nt':
        if process.returncode is None:
            try:
                killer = subprocess.Popen(
                    ['taskkill.exe', '/PID', str(process.pid), '/T', '/F'],
                    stdout=stderr, stderr=stderr,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                try:
                    killer.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    killer.kill()
                    killer.wait()
            except OSError as error:
                stderr.write(f'taskkill unavailable: {error}\n'.encode('utf-8'))
            finally:
                if process.poll() is None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait()


def run_manifest_sync(manifest, output, concurrency=4, *, emit_events=True,
                      completion_queue=None, on_event=None, handlers=None):
    """Execute jobs and return their summary.

    A supplied thread-safe Queue receives terminal events. on_event receives all
    events synchronously. This API needs no event loop or loopback socket.
    Paths in a file manifest are resolved relative to that manifest.
    """
    base_dir = Path.cwd()
    if isinstance(manifest, (str, Path)):
        manifest_path = Path(manifest).resolve()
        base_dir = manifest_path.parent
        manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    handlers = handlers or {}
    jobs = validate_manifest(manifest, concurrency, base_dir, handlers)
    policy = manifest.get('scheduling', 'critical_path')
    scores = critical_path_scores(jobs)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    started_utc = datetime.now(timezone.utc).isoformat()
    results = {}
    messages = queue.Queue()
    process_lock = threading.Lock()
    processes = {}
    running_processes = 0
    max_running_processes = 0

    def emit(event, job_id, **fields):
        item = {'event': event, 'job_id': job_id,
                'elapsed_s': time.monotonic() - started, **fields}
        if emit_events:
            print(json.dumps(item, ensure_ascii=False), flush=True)
        if completion_queue is not None and event != 'start':
            completion_queue.put_nowait(item)
        if on_event is not None:
            on_event(item)

    def execute(job):
        nonlocal running_processes, max_running_processes
        job_id = job['id']
        stdout_path = output / f'job-{job_id}.stdout.log'
        stderr_path = output / f'job-{job_id}.stderr.log'
        result = {'status': None, 'returncode': None, 'start_s': None,
                  'end_s': None, 'duration_s': 0.0,
                  'process_started_s': None, 'process_ended_s': None, 'process_id': None,
                  'stdout_path': str(stdout_path), 'stderr_path': str(stderr_path)}
        begin = time.monotonic()
        result['start_s'] = begin - started
        messages.put(('event', 'start', job_id))
        process = None
        with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
            try:
                if 'operation' in job:
                    value = handlers[job['operation']](job['parameters'])
                    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                    stdout.write((text + '\n').encode('utf-8'))
                    result.update(status='completed', returncode=0)
                    return result
                options = ({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
                           if os.name == 'nt' else {'start_new_session': True})
                process = subprocess.Popen(job['argv'], cwd=job['cwd'],
                                           stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, **options)
                result['process_started_s'] = time.monotonic() - started
                result['process_id'] = process.pid
                with process_lock:
                    processes[job_id] = process
                    running_processes += 1
                    max_running_processes = max(max_running_processes, running_processes)
                try:
                    process.wait(timeout=job['timeout_s'])
                    result['status'] = 'completed' if process.returncode == 0 else 'failed'
                except subprocess.TimeoutExpired:
                    _terminate_tree(process, stderr)
                    stderr.write(f'\ncommand timed out after {job["timeout_s"]} seconds\n'.encode())
                    result['status'] = 'timed_out'
                result['returncode'] = process.returncode
            except Exception as error:
                stderr.write(f'{type(error).__name__}: {error}\n'.encode('utf-8'))
                result['status'] = 'failed'
                if 'operation' in job:
                    result['returncode'] = 1
            finally:
                if process is not None:
                    if process.poll() is None:
                        _terminate_tree(process, stderr)
                    with process_lock:
                        processes.pop(job_id, None)
                        running_processes -= 1
                    result['process_ended_s'] = time.monotonic() - started
                result['end_s'] = time.monotonic() - started
                result['duration_s'] = time.monotonic() - begin
        return result

    pending = dict(jobs)
    active = {}
    pool = ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix='command-actor')
    try:
        while pending or active:
            candidates = list(pending)
            if policy == 'critical_path':
                candidates.sort(key=lambda name: -scores[name])
            for job_id in candidates:
                job = pending[job_id]
                if not all(dependency in results for dependency in job['depends_on']):
                    continue
                failed = [dependency for dependency in job['depends_on']
                          if results[dependency]['status'] != 'completed']
                if failed:
                    stdout_path = output / f'job-{job_id}.stdout.log'
                    stderr_path = output / f'job-{job_id}.stderr.log'
                    stdout_path.touch()
                    stderr_path.write_text('blocked by: ' + ', '.join(failed) + '\n', encoding='utf-8')
                    results[job_id] = {'status': 'blocked', 'returncode': None, 'start_s': None,
                                      'end_s': time.monotonic() - started, 'duration_s': 0.0,
                                      'process_started_s': None, 'process_ended_s': None,
                                      'process_id': None, 'stdout_path': str(stdout_path),
                                      'stderr_path': str(stderr_path), 'blocked_by': failed}
                    emit('blocked', job_id, returncode=None)
                else:
                    if len(active) >= concurrency or any(
                            resources_conflict(job, jobs[name]) for name in active):
                        continue
                    future = pool.submit(execute, job)
                    active[job_id] = future
                    future.add_done_callback(lambda done, jid=job_id: messages.put(('finished', jid, done)))
                del pending[job_id]
            if not active:
                continue
            message = messages.get()
            if message[0] == 'event':
                emit(message[1], message[2])
            else:
                _, job_id, future = message
                results[job_id] = future.result()
                del active[job_id]
                emit(results[job_id]['status'], job_id, returncode=results[job_id]['returncode'])
    finally:
        if pending or active:
            for future in active.values():
                future.cancel()
            with process_lock:
                owned = list(processes.values())
            for process in owned:
                with (output / 'cleanup.stderr.log').open('ab') as stderr:
                    _terminate_tree(process, stderr)
        pool.shutdown(wait=True, cancel_futures=True)
    summary = {'schema_version': 1, 'status': 'completed' if all(
        result['status'] == 'completed' for result in results.values()) else 'failed',
        'started_utc': started_utc, 'elapsed_s': time.monotonic() - started,
        'max_running_processes': max_running_processes,
        'process_interval_scope': 'parent-observed child handles after spawn returns until wait/cleanup returns',
        'concurrency': concurrency, 'scheduling': policy,
        'critical_path_scores': scores,
        'jobs': {job_id: results[job_id] for job_id in jobs}}
    _atomic_json(output / 'result.json', summary)
    return summary


async def run_manifest(manifest, output, concurrency=4, *, emit_events=True,
                       completion_queue=None, on_event=None):
    """Adapter for an existing event loop; CLI uses run_manifest_sync directly.

    Cancelling this await does not cancel commands already running in the worker.
    Use per-job timeouts to bound their lifetime.
    """
    loop = asyncio.get_running_loop()

    def forward(item):
        if completion_queue is not None and item['event'] != 'start':
            loop.call_soon_threadsafe(completion_queue.put_nowait, item)
        if on_event is not None:
            loop.call_soon_threadsafe(on_event, item)

    return await asyncio.to_thread(run_manifest_sync, manifest, output, concurrency,
                                   emit_events=emit_events, on_event=forward)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--concurrency', type=int, default=4)
    args = parser.parse_args(argv)
    try:
        summary = run_manifest_sync(args.manifest, args.output, args.concurrency)
    except (ValueError, OSError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 2
    return 0 if summary['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
