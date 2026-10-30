"""Bridge Codex lifecycle stdin to reviewed cxd hooks and bounded completion gates."""
import argparse
from contextlib import contextmanager, redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import uuid

sys.dont_write_bytecode = True
import hooks
from async_jobs import wait
from resident import atomic_json, inside
from resident_rpc import Changes, directories

EVENTS = {'SessionStart': 'sessionStart', 'UserPromptSubmit': 'turnStart',
          'PostToolUse': 'afterChange', 'Stop': 'beforeComplete', 'SessionEnd': 'sessionEnd'}


def read(file, default):
    return json.loads(file.read_text(encoding='utf-8-sig')) if file.exists() else default


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def registry(home):
    return home / '.pow/native-hooks/projects.json'


def authorize(home, root, session_root=None):
    native_definitions(root)  # Validate commands and native control semantics before authorization.
    file = registry(home)
    file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    data = read(file, {'version': 1, 'projects': {}})
    if data.get('version') != 1 or not isinstance(data.get('projects'), dict):
        raise ValueError('Invalid project authorization registry')
    previous = data['projects'].get(str(root), {})
    sessions = previous.get('sessionRoots', [])
    if session_root:
        session_root = session_root.resolve(strict=True)
        if not root.is_relative_to(session_root):
            raise ValueError('session-root must contain the selected project')
        sessions = sorted(set(sessions + [str(session_root)]))
    data['projects'][str(root)] = {'sha256': digest(root / '.codex-dispatch.json'), 'sessionRoots': sessions}
    atomic_json(file, data)
    return {'authorized': str(root), 'sessionRoots': sessions, 'scope': 'Exact project commands/settings; not native Codex hook trust'}


def project(home, cwd):
    data = read(registry(home), {'version': 1, 'projects': {}})
    if data.get('version') != 1 or not isinstance(data.get('projects'), dict):
        raise ValueError('Invalid project authorization registry')
    candidates = [(Path(root), entry) for root, entry in data['projects'].items()
                  if cwd.is_relative_to(Path(root)) or str(cwd) in entry.get('sessionRoots', [])]
    if not candidates:
        return None
    direct = [item for item in candidates if cwd.is_relative_to(item[0])]
    if direct:
        root, entry = max(direct, key=lambda item: len(item[0].parts))
    elif len(candidates) == 1:
        root, entry = candidates[0]
    else:
        raise ValueError('Ambiguous project mapping; select a project working directory')
    if root.resolve(strict=True) != root or digest(root / '.codex-dispatch.json') != entry['sha256']:
        raise ValueError('Project hook configuration changed; review and run /hooks native authorize again')
    return root


def settings(root, config_override=None):
    config = read(root / '.codex-dispatch.json', {}) if config_override is None else config_override
    value = config.get('codexHooks', {})
    if not isinstance(value, dict) or set(value) - {'enabled', 'events', 'waitSeconds', 'maxStopContinuations', 'profileOnStop', 'verifyReadOnlyTurns'}:
        raise ValueError('Invalid codexHooks settings')
    merged = {'enabled': False, 'events': EVENTS, 'waitSeconds': 30, 'maxStopContinuations': 1, 'profileOnStop': True, 'verifyReadOnlyTurns': False, **value}
    if any(type(merged[key]) is not bool for key in ('enabled', 'profileOnStop', 'verifyReadOnlyTurns')):
        raise ValueError('codexHooks enabled/profileOnStop must be boolean')
    if type(merged['waitSeconds']) not in (int, float) or not 0 <= merged['waitSeconds'] <= 45:
        raise ValueError('codexHooks waitSeconds must be 0..45')
    if type(merged['maxStopContinuations']) is not int or not 0 <= merged['maxStopContinuations'] <= 3:
        raise ValueError('maxStopContinuations must be 0..3')
    if not isinstance(merged['events'], dict) or set(merged['events']) - set(EVENTS):
        raise ValueError('Unsupported native event mapping')
    for event in merged['events'].values():
        if not isinstance(event, str) or not event or len(event) > 64:
            raise ValueError('Invalid logical event mapping')
    return merged


def native_definitions(root, config_override=None):
    config = settings(root, config_override)
    definitions, limit = hooks.definitions(root, config_override)
    change_event, final_event = config['events'].get('PostToolUse'), config['events'].get('Stop')
    turn_event = config['events'].get('UserPromptSubmit')
    if any(hook['event'] == change_event and not (hook['inputs'] or hook['inputRoots']) for hook in definitions):
        raise ValueError('Automatic after-change hooks require explicit input scope')
    if any(final_event in hook['requiredAt'] and hook['event'] not in {change_event, turn_event} for hook in definitions):
        raise ValueError('Native completion gates must launch on turnStart or afterChange')
    if any(hook['mode'] == 'async' and hook['onFailure'] == 'block' and final_event not in hook['requiredAt'] for hook in definitions):
        raise ValueError('Blocking async native hooks require the mapped Stop event as a join point')
    if any(hook['event'] == config['events'].get('SessionEnd') and hook['onFailure'] == 'block' for hook in definitions):
        raise ValueError('SessionEnd is advisory; configure its hooks onFailure:record')
    return config, definitions, limit


@contextmanager
def session_lock(directory, deadline):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    file = directory / 'writer.lock'
    changes = Changes(directory) if os.name == 'nt' or sys.platform.startswith('linux') else None
    try:
        while True:
            try:
                with file.open('x', encoding='utf-8') as stream:
                    json.dump({'pid': os.getpid()}, stream)
                break
            except FileExistsError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError('Native hook session is busy; inspect retained worker/lock before retry')
                changes.wait(min(remaining, .5)) if changes else time.sleep(min(remaining, .05))
        try:
            yield
        finally:
            file.unlink()
    finally:
        if changes:
            changes.close()


def invoke(root, action, event, cycle, deadline, definitions):
    if not any(hook['event'] == event or event in hook['requiredAt'] for hook in definitions):
        return 0, {'outcomes': []}
    output, errors = io.StringIO(), io.StringIO()
    with redirect_stdout(output), redirect_stderr(errors):
        code = hooks.main([action, event, '--workspace', str(root), '--cycle', cycle,
                           '--timeout', str(max(0, min(45, deadline - time.monotonic())))] + (['--resume'] if action == 'emit' else []))
    data = json.loads(output.getvalue()) if output.getvalue().strip() else {}
    if code == 1:
        raise ValueError('cxd hook dispatch failed; inspect .cxd/hooks state and configuration')
    return code, data


def drain(root, deadline):
    state = hooks.load(inside(root, '.cxd/hooks/state.json'))
    for run in hooks.live(root, state):
        wait(root, run['run_id'], max(0, deadline - time.monotonic()))
        if hooks.observe(root, run)['status'] == 'running':
            raise ValueError('Hook work remains pending; finish or inspect the recorded run before completion')


def blocking_failure(data):
    return any(item.get('onFailure') == 'block' and item.get('status') in {'failed', 'interrupted'}
               for item in data.get('outcomes', []))


def run_event(home, payload, event):
    if payload.get('hook_event_name') != event or not isinstance(payload.get('cwd'), str):
        raise ValueError('Native event input identity mismatch')
    if os.environ.get('POW_HOOK_ACTIVE'):
        return {}
    root = project(home, Path(payload['cwd']).resolve(strict=True))
    if root is None:
        return {}
    config = settings(root)
    if not config['enabled'] or event not in config['events']:
        return {}
    sid, tid = payload.get('session_id'), payload.get('turn_id', 'session')
    if not isinstance(sid, str) or not sid or not isinstance(tid, str) or not tid:
        raise ValueError('Native hook needs session_id and turn_id')
    directories(root)
    directory = inside(root, '.cxd/hooks/native/' + hooks.fingerprint(sid)[:24])
    budget = 1 if event == 'SessionEnd' else min(config['waitSeconds'], 3) if event in {'SessionStart', 'UserPromptSubmit'} else config['waitSeconds']
    deadline = time.monotonic() + budget
    started = time.monotonic()
    with session_lock(directory, deadline):
        if project(home, Path(payload['cwd']).resolve(strict=True)) != root:
            raise ValueError('Authorized project changed while waiting')
        config, definitions, limit = native_definitions(root)
        if not definitions:
            return {}
        change_event = config['events'].get('PostToolUse')
        final_event = config['events'].get('Stop')
        turn_event = config['events'].get('UserPromptSubmit')
        file = directory / 'state.json'
        state = read(file, {'version': 1, 'turns': {}, 'events': []})
        if state.get('version') != 1 or not isinstance(state.get('turns'), dict):
            raise ValueError('Invalid native hook state')
        key = hooks.fingerprint(tid)[:24]
        turn = state['turns'].setdefault(key, {'fired': {}, 'continuations': 0})
        identity = hooks.fingerprint({'hooks': definitions, 'limit': limit})
        if event == 'UserPromptSubmit':
            turn.setdefault('initialIdentity', identity)
        elif event == 'PostToolUse' and turn.get('initialIdentity') != identity:
            turn['touched'] = True
        cycle = hooks.fingerprint([sid, tid, identity])[:48]
        logical = config['events'][event]
        reason = None
        terminal_failure = False
        block_tool = False
        try:
            if event == 'Stop':
                drain(root, deadline)
            readonly = (not config['verifyReadOnlyTurns'] and turn.get('initialIdentity') == identity
                        and not turn.get('touched') and not any(hook['event'] == turn_event and final_event in hook['requiredAt'] for hook in definitions))
            if event in {'Stop', 'PostToolUse'} and readonly:
                pass
            elif event == 'Stop':
                if turn.get('failedIdentity') == identity:
                    raise ValueError('The same hook already failed on unchanged inputs; fix its cause before verification')
                # Preserve required turn-start checks when edits create a newer input generation.
                if turn_event and any(hook['event'] == turn_event and final_event in hook['requiredAt'] for hook in definitions):
                    phase = cycle + ':' + turn_event
                    if not turn['fired'].get(phase):
                        code, data = invoke(root, 'emit', turn_event, cycle, deadline, definitions)
                        if code:
                            terminal_failure = blocking_failure(data)
                            raise ValueError('Required turn-start hook failed or remains pending')
                        turn['fired'][phase] = True
                # A delayed async native callback cannot make Stop skip the final changed inputs.
                if change_event and any(hook['event'] == change_event for hook in definitions):
                    changed = cycle + ':' + change_event
                    if not turn['fired'].get(changed):
                        code, data = invoke(root, 'emit', change_event, cycle, deadline, definitions)
                        if code:
                            terminal_failure = blocking_failure(data)
                            raise ValueError('Changed-input hook failed or is pending; inspect its recorded result')
                        turn['fired'][changed] = True
                final = cycle + ':' + logical
                if not turn['fired'].get(final):
                    code, data = invoke(root, 'emit', logical, cycle, deadline, definitions)
                    if code:
                        terminal_failure = blocking_failure(data)
                        raise ValueError('Required completion hook failed or remains pending; inspect .cxd/hooks state')
                    turn['fired'][final] = True
                if config['profileOnStop']:
                    recorded = hooks.load(inside(root, '.cxd/hooks/state.json'))
                    for run in recorded['runs']:
                        hooks.observe(root, run)
                    profile = hooks.report(recorded, definitions)
                    atomic_json(directory / 'profile.json', profile)
            elif event == 'SessionEnd':
                # Advisory event cannot hold the thread open; retain actual state without claiming success.
                drain(root, deadline)
                if any(hook['event'] == logical for hook in definitions):
                    code, data = invoke(root, 'emit', logical, cycle, deadline, definitions)
                    if code:
                        raise ValueError('Session-end work is pending or failed; inspect its retained result')
            else:
                phase = cycle + ':' + logical
                if not turn['fired'].get(phase):
                    code, data = invoke(root, 'emit', logical, cycle, deadline, definitions)
                    if code:
                        block_tool = any(hook['onFailure'] == 'block' and
                                         (hook['event'] == logical and hook['mode'] == 'sync' or logical in hook['requiredAt'])
                                         for hook in definitions)
                        raise ValueError('Event hook failed, is busy or pending; completion will inspect the final inputs')
                    turn['fired'][phase] = True
        except ValueError as error:
            reason = str(error)
        if event == 'Stop' and not reason:
            if project(home, Path(payload['cwd']).resolve(strict=True)) != root:
                reason = 'Authorized project changed during completion'
            elif identity != hooks.fingerprint({'hooks': hooks.definitions(root)[0], 'limit': limit}):
                reason = 'Declared sources changed during completion; inspect the new input generation'
        if terminal_failure:
            turn['failedIdentity'] = identity
        state['events'] = (state['events'] + [{'event': event, 'turn': key, 'cycle': cycle,
                           'duration_s': time.monotonic() - started, 'outcome': 'incomplete' if reason else 'observed'}])[-100:]
        # Keep current plus recent turns; never remove the cxd execution records here.
        state['turns'] = dict(list(state['turns'].items())[-20:])
        turn['fired'] = dict(list(turn['fired'].items())[-64:])
        if reason and event == 'Stop':
            if turn['continuations'] < config['maxStopContinuations']:
                turn['continuations'] += 1
                response = {'decision': 'block', 'reason': 'POW: ' + reason + '. Fix a concrete cause; do not repeat successful checks.'}
            else:
                response = {'continue': False, 'stopReason': 'POW completion remains unverified; continuation budget exhausted',
                            'systemMessage': 'POW: ' + reason + '. Work is incomplete; inspect local hook evidence.'}
        elif reason and (event == 'UserPromptSubmit' or event == 'PostToolUse' and block_tool):
            response = {'decision': 'block', 'reason': 'POW: ' + reason}
        elif reason and event == 'SessionStart':
            response = {'continue': False, 'stopReason': 'POW: ' + reason}
        else:
            response = {'systemMessage': 'POW: ' + reason} if reason else {}
        atomic_json(file, state)
        return response


def configure(home, root, args):
    if project(home, root) != root:
        raise ValueError('Authorize this project before changing hook settings')
    file = root / '.codex-dispatch.json'
    original = file.read_bytes()
    config = read(file, {})
    matching = [entry for entry in config.get('hooks', []) if entry['id'] == args.hook]
    if len(matching) != 1:
        raise ValueError('Select one configured hook ID')
    hook = matching[0]
    if args.mode:
        hook['mode'] = args.mode
    if args.required_at is not None:
        hook['requiredAt'] = args.required_at
    if hook.get('mode', 'sync') == 'async' and hook.get('onFailure', 'block') == 'block' and not hook.get('requiredAt'):
        raise ValueError('Select a required-at join event for a blocking async hook')
    if args.timeout_s is not None:
        if not 0 < args.timeout_s <= 300:
            raise ValueError('job timeout must be >0 and <=300 seconds')
        for job in config['presets'][hook['preset']]['jobs']:
            job['timeout_s'] = args.timeout_s
    native_definitions(root, config)
    if not args.apply:
        return {'apply': False, 'hook': hook, 'preset': config['presets'][hook['preset']]}
    backup = inside(root, '.cxd/hooks/native/config-' + digest(file) + '.json')
    backup.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not backup.exists():
        with backup.open('xb') as stream:
            stream.write(original)
    if backup.read_bytes() != original or file.read_bytes() != original:
        raise ValueError('Configuration changed during planning; preserving it')
    mode = file.stat().st_mode & 0o777
    try:
        atomic_json(file, config)
        file.chmod(mode)
        authorize(home, root)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        temp = file.with_name(file.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with temp.open('xb') as stream:
                stream.write(original)
            temp.chmod(mode)
            temp.replace(file)
        finally:
            temp.unlink(missing_ok=True)
        raise
    return {'apply': True, 'hook': hook['id'], 'backup': str(backup), 'next': 'Settings apply to the next native event; active cycles remain immutable'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='event', choices=['event', 'authorize', 'status', 'profile', 'configure'])
    parser.add_argument('--event', choices=list(EVENTS))
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')))
    parser.add_argument('--session-root', type=Path)
    parser.add_argument('--hook')
    parser.add_argument('--mode', choices=['sync', 'async'])
    parser.add_argument('--required-at', action='append', default=None)
    parser.add_argument('--timeout-s', type=float)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    try:
        home = args.codex_home.resolve()
        if args.action == 'event':
            raw = sys.stdin.buffer.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024 or not args.event:
                raise ValueError('Native event input too large or missing --event')
            payload = json.loads(raw.decode('utf-8-sig'))
            response = run_event(home, payload, args.event)
        else:
            root = args.workspace.resolve(strict=True)
            if args.action == 'authorize':
                response = authorize(home, root, args.session_root)
            elif args.action == 'configure':
                response = configure(home, root, args)
            elif args.action == 'profile':
                return hooks.main(['profile', '--workspace', str(root)])
            else:
                response = {'authorized': str(project(home, root)) if project(home, root) else None,
                            'nativeHookState': str(inside(root, '.cxd/hooks/native')),
                            'note': 'Codex hook trust is separate; inspect native hooks/list or /hooks'}
        print(json.dumps(response)); return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        if args.action == 'event':
            # Failed parsing/authorization must not silently approve a configured completion gate.
            output = {'continue': False, 'stopReason': 'POW native hook failed; completion unverified',
                      'systemMessage': str(error)} if args.event == 'Stop' else {'systemMessage': 'POW: ' + str(error)}
            print(json.dumps(output)); return 0
        print(json.dumps({'error': str(error)}), file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
