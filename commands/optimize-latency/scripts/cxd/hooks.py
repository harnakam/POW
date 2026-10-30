"""Per-hook scheduling and measured suggestions, using the existing cxd worker."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
import time

sys.dont_write_bytecode = True
from async_jobs import start_prepared, result, wait, process_alive
from command_actors import validate_manifest, resources_conflict
from dispatch import configuration, prepare_preset
from resident import atomic_json, inside
from resident_rpc import directories
from outcomes import failure, summary_failure
from input_tracking import InputSnapshot, InputStateBusy


class HookError(ValueError):
    def __init__(self, kind, message, *, evidence=None, next_action='inspect'):
        super().__init__(message)
        self.failure = failure(kind, evidence_path=evidence, next_action=next_action)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def definitions(root, config_override=None, snapshot=None):
    if snapshot is None:
        try:
            # Manual dispatch/authorization uses the same stable path policy,
            # always reading bytes and never publishing a partial observation.
            with InputSnapshot(root, force=True) as fresh:
                return definitions(root, config_override, fresh)
        except InputStateBusy as error:
            raise HookError('busy', str(error), next_action='wait') from error
    config = configuration(root, config_override)
    limit = config.get('hooksConcurrency', 2)
    if type(limit) is not int or not 1 <= limit <= 8:
        raise ValueError('hooksConcurrency must be 1..8')
    entries = config.get('hooks', [])
    if not isinstance(entries, list) or len(entries) > 32:
        raise ValueError('hooks must be a list of at most 32 entries')
    hooks, names, trees = [], set(), {}
    for raw in entries:
        if not isinstance(raw, dict) or set(raw) - {'id', 'event', 'preset', 'mode', 'onFailure', 'requiredAt', 'independent', 'inputs', 'inputRoots'}:
            raise ValueError('unsupported hook fields')
        hook = dict(raw)
        for key in ('id', 'event', 'preset'):
            if not isinstance(hook.get(key), str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,63}', hook[key]):
                raise ValueError('hook id/event/preset must be filename-safe labels')
        if hook['id'].casefold() in names:
            raise ValueError('duplicate hook id')
        names.add(hook['id'].casefold())
        hook.setdefault('mode', 'sync')
        hook.setdefault('onFailure', 'block')
        hook.setdefault('requiredAt', [])
        hook.setdefault('independent', False)
        hook.setdefault('inputs', [])
        hook.setdefault('inputRoots', [])
        if hook['mode'] not in {'sync', 'async'} or hook['onFailure'] not in {'block', 'record'} or type(hook['independent']) is not bool:
            raise ValueError('invalid hook mode/onFailure/independent')
        events = hook['requiredAt']
        if (not isinstance(events, list) or len(events) > 16 or len(set(events)) != len(events)
                or any(not isinstance(event, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,63}', event) for event in events)):
            raise ValueError('requiredAt must contain unique event labels')
        if hook['mode'] == 'async' and hook['onFailure'] == 'block' and not events:
            raise ValueError('blocking async hook requires a requiredAt join event')
        if hook['event'] in events:
            raise ValueError('requiredAt must be a later event, not the launch event')
        if not isinstance(hook['inputs'], list) or len(hook['inputs']) > 64:
            raise ValueError('inputs must list at most 64 exact workspace files')
        inputs = {}
        for relative in hook['inputs']:
            if not isinstance(relative, str) or Path(relative).is_absolute():
                raise ValueError('hook inputs must be workspace-relative files')
            file = inside(root, relative)
            if not file.is_file() or file.stat().st_size > 8 * 1024 * 1024:
                raise ValueError('hook input must be an existing file <=8 MiB')
            inputs[relative] = snapshot.file(relative)
        tree_key = json.dumps(hook['inputRoots'], sort_keys=True)
        if tree_key not in trees:
            trees[tree_key] = snapshot.tree(hook['inputRoots'])
        manifest = prepare_preset(root, hook['preset'], config_override=config)
        if len(manifest['jobs']) > 32:
            raise ValueError('hook preset is limited to 32 jobs')
        # Hooks run commands only; read-only resident operations have different lifetimes.
        jobs = validate_manifest(manifest, limit, root)
        if any(job['timeout_s'] > 300 for job in jobs.values()):
            raise ValueError('hook jobs require timeout_s <=300')
        entrypoints = {}
        for job in manifest['jobs']:
            for arg in job.get('argv', []):
                candidate = Path(job['cwd']) / arg
                if candidate.suffix.lower() in {'.py', '.js', '.mjs', '.cjs', '.sh', '.ps1'} and candidate.is_file() and candidate.stat().st_size <= 2 * 1024 * 1024:
                    relative = candidate.absolute().relative_to(root) if candidate.absolute().is_relative_to(root) else None
                    entrypoints[str(candidate)] = snapshot.file(str(relative), max_bytes=2 * 1024 * 1024) if relative is not None else hashlib.sha256(candidate.read_bytes()).hexdigest()
        hooks.append({**hook, 'manifest': manifest,
                      'profileKey': fingerprint({'hook': hook, 'manifest': manifest, 'entrypoints': entrypoints, 'platform': sys.platform, 'python': sys.version}),
                      'fingerprint': fingerprint({'hook': hook, 'manifest': manifest, 'inputs': inputs, 'tree': trees[tree_key]})})
    return hooks, limit


@contextmanager
def state_lock(root):
    directories(root)
    directory = inside(root, '.cxd/hooks')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = directory / 'lock.json'
    try:
        handle = lock.open('x', encoding='utf-8')
    except FileExistsError:
        raise HookError('busy', 'hook state busy; inspect lock PID before deliberate crash recovery', evidence=lock, next_action='wait')
    try:
        with handle:
            json.dump({'pid': os.getpid()}, handle)
        yield directory / 'state.json'
    finally:
        lock.unlink()


def load(file):
    state = json.loads(file.read_text(encoding='utf-8')) if file.exists() else {'version': 1, 'runs': [], 'cycles': {}}
    if state.get('version') != 1 or not isinstance(state.get('runs'), list) or not isinstance(state.get('cycles'), dict):
        raise ValueError('invalid hook state')
    return state


def observe(root, run):
    if run['status'] != 'running' and 'failure' in run:
        return run
    value = result(root, run['run_id'])
    prior_status = run['status']
    owner = inside(root, '.cxd/async/' + run['run_id'] + '/owner.json')
    done = owner.with_name('done.json').is_file()
    living = process_alive(json.loads(owner.read_text())['pid']) if owner.exists() and not done else None
    # done is written after this worker closes its logs; it avoids confusing a reused PID with unfinished work.
    run['status'] = prior_status if prior_status != 'running' else value['status'] if done or living is False else 'running'
    if run['status'] != 'running':
        summary = value.get('summary', {})
        run['elapsed_s'] = summary.get('elapsed_s')
        run['jobs'] = {name: {'duration_s': job.get('duration_s'), 'status': job.get('status')}
                       for name, job in summary.get('jobs', {}).items()}
        run['failure'] = None if run['status'] == 'completed' else value.get('failure') or summary_failure(summary.get('jobs', {}), value.get('result_path')) or failure('unknown-failure', evidence_path=value.get('run_directory'))
        run.setdefault('finished_unix_s', time.time())
    return run


def live(root, state):
    return [run for run in state['runs'] if observe(root, run)['status'] == 'running']


def conflict(first, second):
    return any(resources_conflict({'reads': [], 'writes': [], **a}, {'reads': [], 'writes': [], **b})
               for a in first['jobs'] for b in second['jobs'])


def public(run):
    return {key: run[key] for key in ('hook', 'cycle', 'run_id', 'mode', 'onFailure', 'status', 'elapsed_s', 'wait_s', 'deduplicated', 'failure') if key in run}


def pending_failure(root, run):
    return failure('pending', evidence_path=inside(root, '.cxd/async/' + run['run_id']), next_action='wait') if run['status'] == 'running' else run.get('failure')


def visible(state):
    finished = [run for run in state['runs'] if run['status'] != 'running'][-20:]
    active = [run for run in state['runs'] if run['status'] == 'running']
    return [public(run) for run in finished + active]


def join(root, state, hooks, event, cycle, deadline):
    outcomes = []
    for hook in hooks:
        if event not in hook['requiredAt']:
            continue
        matches = [run for run in state['runs'] if run['hook'] == hook['id'] and run['cycle'] == cycle]
        if not matches or matches[-1]['fingerprint'] != hook['fingerprint']:
            outcomes.append({'hook': hook['id'], 'status': 'missing-or-stale', 'blocking': True,
                             'failure': failure('stale-generation', next_action='rescan')})
            continue
        run = matches[-1]
        started = time.monotonic()
        if run['status'] == 'running':
            wait(root, run['run_id'], max(0, deadline - started))
        run['wait_s'] = run.get('wait_s', 0) + time.monotonic() - started
        observe(root, run)
        outcomes.append({**public(run), 'failure': pending_failure(root, run),
                         'blocking': run['status'] == 'running' or (hook['onFailure'] == 'block' and run['status'] != 'completed')})
    return outcomes


def report(state, hooks):
    proposals = []
    for hook in hooks:
        samples = [run for run in state['runs'] if run['hook'] == hook['id'] and run.get('profileKey', run['fingerprint']) == hook.get('profileKey', hook['fingerprint'])
                   and run['status'] != 'running']
        durations = sorted(run['elapsed_s'] for run in samples if isinstance(run.get('elapsed_s'), (int, float)))
        item = {'hook': hook['id'], 'samples': len(samples), 'failures': sum(run['status'] != 'completed' for run in samples),
                'inputVariants': len({run['fingerprint'] for run in samples}),
                'deduplicated': sum(run.get('deduplicated', 0) for run in samples), 'proposals': []}
        if durations:
            item.update(p50_s=statistics.median(durations), p95_s=durations[max(0, math.ceil(len(durations) * .95) - 1)],
                        observed_wait_s=sum(run.get('wait_s', 0) for run in samples))
        if item['failures']:
            item['proposals'].append('Investigate failures before changing scheduling or timeouts.')
        elif len(durations) < 3:
            item['proposals'].append('Insufficient comparable samples; collect normal-use outcomes, not repeated verification.')
        else:
            if hook['mode'] == 'sync' and hook['independent']:
                item['proposals'].append('Consider async; retain requiredAt and onFailure. Review all callers and resource claims first.')
                item['modeCandidate'] = {'mode': 'async', 'requiredAt': hook['requiredAt'],
                                         'requiresJoinEvent': hook['onFailure'] == 'block' and not hook['requiredAt']}
            item['timeoutCandidates'] = []
            for job in hook['manifest']['jobs']:
                times = sorted(run.get('jobs', {}).get(job['id'], {}).get('duration_s') for run in samples
                               if run.get('jobs', {}).get(job['id'], {}).get('status') == 'completed'
                               and isinstance(run.get('jobs', {}).get(job['id'], {}).get('duration_s'), (int, float)))
                if len(times) >= 3:
                    item['timeoutCandidates'].append({'job': job['id'], 'samples': len(times), 'current_s': job.get('timeout_s', 60),
                        'observedMax_s': times[-1], 'candidate_s': min(300, max(1, math.ceil(times[-1] * 2 + 1)))})
            item['proposals'].append('Timeout candidates use twice the observed job maximum plus one second; review representative load and failure behavior before applying.')
        proposals.append(item)
    return {'hooks': proposals, 'automaticChanges': False,
            'scope': 'Same hook/config/entrypoint/platform cohort; input variants are counted. Different inputs can have different costs. No cached verification or estimated speedup.'}


def main(argv=None, *, selected_ids=None, skip_joins=False, expected_identity=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'emit', 'join', 'status', 'profile'])
    parser.add_argument('event', nargs='?')
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--cycle')
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--resume', action='store_true', help='Reuse recorded results only within this same cycle/input identity')
    args = parser.parse_args(argv)
    try:
        root = args.workspace.resolve()
        hooks, limit = ([], 2) if args.action == 'status' else definitions(root)
        if selected_ids is not None and not set(selected_ids).issubset({hook['id'] for hook in hooks}):
            raise HookError('invalid-config', 'Selected hook ID does not exist')
        if expected_identity is not None and expected_identity != fingerprint({'hooks': hooks, 'limit': limit}):
            raise HookError('stale-generation', 'Declared inputs changed before dispatch; recompute the latest generation', next_action='rescan')
        if not math.isfinite(args.timeout) or not 0 <= args.timeout <= 60:
            raise ValueError('caller timeout must be 0..60 seconds; jobs keep their configured timeout')
        if args.action == 'plan':
            print(json.dumps({'hooks': hooks, 'maxActiveRuns': limit})); return 0
        if args.action == 'status':
            file = inside(root, '.cxd/hooks/state.json')
            state = load(file)
            for run in state['runs']:
                observe(root, run)
            print(json.dumps({'runs': visible(state),
                              'writerLocked': file.with_name('lock.json').exists()})); return 0
        if args.action in {'emit', 'join'} and (not args.event or not args.cycle or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,64}', args.cycle)):
            raise ValueError('emit/join need event and --cycle unique-task-label')
        if args.action == 'emit' and os.environ.get('POW_HOOK_ACTIVE'):
            raise HookError('policy-denied', 'recursive hook emission refused', next_action='fix')
        deadline = time.monotonic() + args.timeout
        with state_lock(root) as file:
            state = load(file)
            active = live(root, state)
            if args.action in {'emit', 'join'}:
                identity = fingerprint({'hooks': hooks, 'limit': limit})
                previous = state['cycles'].get(args.cycle)
                if previous and previous['fingerprint'] != identity:
                    raise HookError('stale-generation', 'cycle configuration or declared inputs changed; inspect retained jobs and start a new cycle', next_action='rescan')
                if args.action == 'emit' and not previous:
                    if len(state['cycles']) >= 200:
                        busy_cycles = {run['cycle'] for run in active}
                        oldest = next((cycle for cycle in state['cycles'] if cycle not in busy_cycles), None)
                        if oldest is None:
                            raise ValueError('cycle capacity reached with active work; join it before starting more')
                        del state['cycles'][oldest]
                        state['runs'] = [run for run in state['runs'] if run['cycle'] != oldest]
                    state['cycles'][args.cycle] = {'fingerprint': identity}
                    atomic_json(file, state)
                if args.action == 'join' and not previous:
                    raise HookError('stale-generation', 'unknown cycle; emit an event before joining', next_action='rescan')
            outcomes = []
            if args.action in {'emit', 'join'} and not skip_joins:
                outcomes = join(root, state, hooks, args.event, args.cycle, deadline)
            blocked = any(item['blocking'] for item in outcomes)
            if args.action == 'emit' and not blocked:
                for hook in hooks:
                    if hook['event'] != args.event or selected_ids is not None and hook['id'] not in selected_ids:
                        continue
                    active = live(root, state)
                    same = [run for run in active if run['hook'] == hook['id']]
                    previous = [run for run in state['runs'] if run['hook'] == hook['id'] and run['cycle'] == args.cycle
                                and run['fingerprint'] == hook['fingerprint']]
                    if args.resume and previous and previous[-1]['status'] != 'running':
                        run = previous[-1]
                        is_blocking = run['onFailure'] == 'block' and run['status'] != 'completed'
                        outcomes.append({**public(run), 'blocking': is_blocking})
                        if is_blocking:
                            blocked = True; break
                        continue
                    if same and (same[0]['cycle'] != args.cycle or same[0]['fingerprint'] != hook['fingerprint']):
                        outcomes.append({'hook': hook['id'], 'status': 'busy-other-input-or-cycle', 'blocking': True,
                                         'failure': failure('busy', next_action='wait')}); blocked = True; break
                    if same:
                        run = same[0]
                        run['deduplicated'] = run.get('deduplicated', 0) + 1
                    else:
                        if len(active) >= limit or any(conflict(hook['manifest'], run['manifest']) for run in active):
                            outcomes.append({'hook': hook['id'], 'status': 'busy-resource-or-capacity', 'blocking': True,
                                             'failure': failure('busy', next_action='wait')}); blocked = True; break
                        submitted = start_prepared(root, hook['manifest'], 'hook:' + hook['id'], 1, hook=True)
                        run = {key: hook[key] for key in ('fingerprint', 'profileKey', 'manifest', 'mode', 'onFailure', 'requiredAt')}
                        run.update(hook=hook['id'], cycle=args.cycle, run_id=submitted['run_id'], status='running', submitted_unix_s=time.time())
                        state['runs'].append(run)
                        atomic_json(file, state)
                    if hook['mode'] == 'sync':
                        started = time.monotonic()
                        wait(root, run['run_id'], max(0, deadline - started))
                        run['wait_s'] = run.get('wait_s', 0) + time.monotonic() - started
                    observe(root, run)
                    is_blocking = run['mode'] == 'sync' and (run['status'] == 'running' or
                              (run['onFailure'] == 'block' and run['status'] != 'completed'))
                    outcomes.append({**public(run), 'failure': pending_failure(root, run), 'blocking': is_blocking})
                    if is_blocking:
                        blocked = True; break
            # Retain all active runs; bound historical metadata without removing execution logs.
            active = live(root, state)
            finished = [run for run in state['runs'] if run not in active]
            state['runs'] = sorted(finished[-200:] + active, key=lambda run: run['submitted_unix_s'])
            atomic_json(file, state)
            response = report(state, hooks) if args.action == 'profile' else {'blocked': blocked, 'outcomes': outcomes,
                        'runs': visible(state)}
            print(json.dumps(response))
            return 2 if blocked else 0
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as error:
        print(json.dumps({'error': str(error), 'failure': getattr(error, 'failure', failure('invalid-config', next_action='fix'))}), file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
