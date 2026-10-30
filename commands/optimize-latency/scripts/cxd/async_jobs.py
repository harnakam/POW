"""Persistent command runs using the existing scheduler and file notifications."""
import asyncio
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import threading
import traceback
import uuid

sys.dont_write_bytecode = True
from resident import atomic_json, inside
from resident_rpc import Changes, alive, directories, response_io
from outcomes import failure, summary_failure

_processes = {}


def read_json(file, deadline=None):
    """Read published metadata through the existing bounded Windows I/O guard.

    Retry file access only, never a command. A permanent access failure keeps
    the execution unobserved; it is not a failed check or invalid configuration.
    """
    budget = time.monotonic() + .25
    try:
        raw = response_io(lambda: file.read_text(encoding='utf-8-sig'),
                          budget if deadline is None else min(deadline, budget))
    except PermissionError as error:
        error.failure = failure('evidence-unavailable', evidence_path=file, next_action='inspect-access')
        raise
    return json.loads(raw)


def record_failure(directory, kind, error, exit_code=None):
    """Keep diagnostics in local evidence, rather than echoing them in metadata."""
    log_path = directory / 'runner.log'
    with log_path.open('a', encoding='utf-8') as log:
        traceback.print_exception(type(error), error, error.__traceback__, file=log)
    atomic_json(directory / 'failure.json', {
        'status': 'interrupted' if kind == 'worker-interrupted' else 'failed',
        'error': f'{kind} ({type(error).__name__}); inspect runner.log',
        'errorType': type(error).__name__,
        'failure': failure(kind, exit_code=exit_code, evidence_path=log_path)})


def process_alive(pid):
    if pid == os.getpid():
        return False  # Attached runner is returning its own final result.
    owned = _processes.get(pid)
    if owned is not None:
        return owned.poll() is None
    if os.name == 'nt':
        return alive(pid)
    if sys.platform.startswith('linux'):
        try:
            if Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] == 'Z':
                return False
        except (OSError, IndexError):
            pass
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return None


def run_directory(root, run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r'[0-9a-f]{32}', run_id):
        raise ValueError('a 32-character run ID is required')
    directory = inside(Path(root).resolve(), '.cxd/async/' + run_id)
    if not (directory / 'request.json').is_file():
        raise ValueError('unknown run ID')
    return directory


def start(root, preset, concurrency=3, attached=False):
    from dispatch import prepare_preset
    return start_prepared(root, prepare_preset(root, preset), preset, concurrency, attached)


def start_prepared(root, manifest, preset, concurrency=3, attached=False, hook=False):
    """Submit an already reviewed manifest through the existing worker."""
    from command_actors import validate_manifest
    root = Path(root).resolve()
    operations = {name: None for name in ('syntax', 'timing', 'index', 'symbols', 'tree')}
    validate_manifest(manifest, concurrency, root, operations)
    directories(root)
    run_id = uuid.uuid4().hex
    directory = inside(root, '.cxd/async/' + run_id)
    directory.mkdir(mode=0o700, parents=True)
    atomic_json(directory / 'request.json', {'manifest': manifest, 'concurrency': concurrency,
                'preset': preset, 'submitted_unix_s': time.time()})
    if attached:
        atomic_json(directory / 'owner.json', {'pid': os.getpid()})
        print(json.dumps({'run_id': run_id, 'status': 'started', 'pid': os.getpid(),
                          'run_directory': str(directory)}), flush=True)
        worker(root, run_id)
        return result(root, run_id)
    options = ({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt'
               else {'start_new_session': True})
    try:
        environment = os.environ.copy()
        if hook:
            environment['POW_HOOK_ACTIVE'] = '1'
        with (directory / 'runner.log').open('ab') as log:
            process = subprocess.Popen([sys.executable, '-B', '-S', str(Path(__file__).resolve()),
                                        str(root), run_id], cwd=root, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=log, close_fds=True,
                                       env=environment, **options)
        atomic_json(directory / 'owner.json', {'pid': process.pid})
        _processes[process.pid] = process
        threading.Thread(target=process.wait, daemon=True).start()
    except OSError as error:
        record_failure(directory, 'spawn-failed', error)
        raise
    return {'run_id': run_id, 'status': 'submitted', 'pid': process.pid,
            'run_directory': str(directory)}


def result(root, run_id, deadline=None):
    directory = run_directory(root, run_id)
    result_path = directory / 'run/result.json'
    response = {'run_id': run_id, 'run_directory': str(directory)}
    if result_path.is_file():
        summary = read_json(result_path, deadline)
        cause = summary.get('failure')
        if cause is None and summary['status'] != 'completed':
            cause = summary_failure(summary.get('jobs', {}), result_path)
            if cause is None:
                cause = failure('unknown-failure', evidence_path=result_path)
        return {**response, 'status': summary['status'], 'result_path': str(result_path),
                'summary': summary, 'failure': cause}
    if (directory / 'failure.json').is_file():
        recorded = read_json(directory / 'failure.json', deadline)
        return {**response, 'status': 'failed',
                **recorded, 'failure': recorded.get('failure') or
                failure('worker-failed', evidence_path=directory / 'failure.json')}
    owner_path = directory / 'owner.json'
    if owner_path.exists():
        pid = read_json(owner_path, deadline)['pid']
        living = process_alive(pid)
        if living is False:
            # Recheck the atomic result after observing process exit.
            if result_path.exists() or (directory / 'failure.json').exists():
                return result(root, run_id, deadline)
            owned = _processes.get(pid)
            exit_code = owned.returncode if owned is not None else None
            log_path = directory / 'runner.log'
            return {**response, 'status': 'interrupted', 'error': 'runner exited without a result',
                    'failure': failure('worker-exited-missing-result', exit_code=exit_code,
                                       evidence_path=log_path if log_path.is_file() else owner_path)}
    return {**response, 'status': 'running'}


def wait(root, run_id, timeout=60):
    if not math.isfinite(timeout) or timeout < 0:
        raise ValueError('timeout must be finite and nonnegative')
    directory = run_directory(root, run_id)
    deadline = time.monotonic() + timeout
    # Register before inspecting state, avoiding a completion-notification race.
    changes = Changes(directory) if os.name == 'nt' or sys.platform.startswith('linux') else None
    try:
        while True:
            value = result(root, run_id, deadline)
            if value['status'] != 'running':
                owner = directory / 'owner.json'
                pid = read_json(owner, deadline)['pid'] if owner.exists() else None
                if pid is None or process_alive(pid) is False:
                    return value
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {**value, 'wait_timed_out': True}
            if changes:
                changes.wait(min(remaining, 1))
            else:
                time.sleep(min(remaining, 0.05))
    finally:
        if changes:
            changes.close()


def worker(root, run_id, close_logs=False):
    directory = run_directory(root, run_id)
    try:
        from dispatch import run_prepared
        request = read_json(directory / 'request.json')
        run_prepared(root, request['manifest'], directory / 'run', request['concurrency'], True)
    except (KeyboardInterrupt, asyncio.CancelledError) as error:
        record_failure(directory, 'worker-interrupted', error, 130)
        return 130
    except Exception as error:
        record_failure(directory, 'worker-failed', error, 1)
        return 1
    finally:
        if close_logs:
            sys.stdout.close()
            sys.stderr.close()
            # CPython standard streams can have closefd=False. Release the
            # inherited OS descriptors too, before publishing completion.
            for descriptor in (1, 2):
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        atomic_json(directory / 'done.json', {'finished_unix_s': time.time()})
    return 0


if __name__ == '__main__':
    raise SystemExit(worker(Path(sys.argv[1]), sys.argv[2], close_logs=True))
