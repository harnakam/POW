"""Merge owned POW lifecycle handlers into CODEX_HOME/hooks.json.

No operation changes feature flags, permissions, or Codex hook trust. Review
``plan`` before explicitly running ``install``; trust is managed by Codex.
"""
import argparse
import base64
import copy
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import sys

from install_cxd import digest, transact

OWNER = 'pow-native-hooks-v1'
MARKER = '[pow-native-hooks:v1] '
EVENTS = ('SessionStart', 'UserPromptSubmit', 'PostToolUse', 'Stop', 'SessionEnd')
TIMEOUTS = {'SessionStart': 5, 'UserPromptSubmit': 5, 'PostToolUse': 60,
            'Stop': 60, 'SessionEnd': 3}


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def group_digest(group):
    return digest(json.dumps(group, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':')).encode('utf-8'))


def regular(path):
    """Reject links, junctions, and non-files without following receipt paths."""
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError(f'Linked installation paths are unsupported: {item}')
    if path.exists() and not path.is_file():
        raise ValueError(f'Expected a regular file: {path}')


def read(path):
    regular(path)
    return path.read_bytes() if path.exists() else None


def document(raw, path):
    try:
        value = json.loads(raw.decode('utf-8-sig')) if raw is not None else {}
    except (UnicodeError, ValueError) as error:
        raise ValueError(f'Invalid JSON; preserving {path}: {error}') from error
    if not isinstance(value, dict):
        raise ValueError(f'Expected a JSON object; preserving {path}')
    hooks = value.get('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError(f'Expected a hooks object; preserving {path}')
    for event in EVENTS:
        if event in hooks and not isinstance(hooks[event], list):
            raise ValueError(f'Expected a {event} matcher-group array; preserving {path}')
    return value


def marked(group):
    if not isinstance(group, dict) or not isinstance(group.get('hooks'), list):
        return False
    return any(isinstance(handler, dict)
               and str(handler.get('statusMessage', '')).startswith(MARKER)
               for handler in group['hooks'])


def owned_receipt(raw, home, receipt_path):
    if raw is None:
        return None
    try:
        value = json.loads(raw.decode('utf-8'))
        entries = value['entries']
        valid = (value['owner'] == OWNER and value['hooks_path'] == str(home / 'hooks.json')
                 and isinstance(value['original_exists'], bool)
                 and isinstance(value['original_sha256'], str)
                 and len(value['original_sha256']) == 64
                 and all(character in '0123456789abcdef' for character in value['original_sha256'])
                 and isinstance(value['runtime_path'], str) and isinstance(value['python_path'], str)
                 and isinstance(entries, dict) and set(entries) == set(EVENTS))
        for event, entry in entries.items():
            group = entry['group']
            valid = (valid and entry['sha256'] == group_digest(group)
                     and isinstance(group, dict) and isinstance(group.get('hooks'), list)
                     and len(group['hooks']) == 1
                     and group['hooks'][0].get('statusMessage') == MARKER + event)
        if not valid:
            raise ValueError('invalid ownership fields')
    except (KeyError, TypeError, UnicodeError, ValueError, AttributeError) as error:
        raise ValueError(f'Invalid ownership receipt; preserving {receipt_path}: {error}') from error
    return value


def inspect(current, owned):
    """An entire owned matcher group must remain exact before replacing it."""
    found = {}
    for event, groups in current.get('hooks', {}).items():
        if not isinstance(groups, list):
            continue
        for index, group in enumerate(groups):
            if marked(group):
                if not owned or event not in owned['entries']:
                    raise ValueError(f'Unowned POW marker in {event}; refusing to claim it')
                if event in found or group != owned['entries'][event]['group']:
                    raise ValueError(f'Owned {event} handler was modified or duplicated; preserving it')
                found[event] = index
    if owned and set(found) != set(owned['entries']):
        missing = sorted(set(owned['entries']) - set(found))
        raise ValueError(f'Owned handlers are missing or modified; preserving configuration: {missing}')
    return found


def executable(value):
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        resolved = shutil.which(value)
        if not resolved:
            raise ValueError(f'Python executable is unavailable: {value}')
        candidate = Path(resolved)
    candidate = candidate.resolve(strict=True)
    if not candidate.is_file():
        raise ValueError(f'Expected a Python executable file: {candidate}')
    return candidate


def powershell_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def windows_command(python, runtime, event):
    # Both cmd and PowerShell accept this executable token. Avoid an extra
    # shell process on the common path while keeping argument expansion inert.
    if (re.fullmatch(r'[A-Za-z0-9_:/\\.\-]+', str(python))
            and not any(character in str(runtime) for character in ('$','`', '%', '!', '"', '\r', '\n'))):
        return f'{python} -B -S "{runtime}" --event {event}'
    # An encoded child PowerShell survives either selected outer shell, with
    # spaces, Unicode, apostrophes, %, and ! in executable or runtime paths.
    script = (f'& {powershell_quote(python)} -B -S {powershell_quote(runtime)} '
              f'--event {event}; exit $LASTEXITCODE')
    encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
    return 'powershell.exe -NoLogo -NoProfile -NonInteractive -EncodedCommand ' + encoded


def handlers(runtime, python):
    runtime = Path(runtime).expanduser().resolve(strict=True)
    if not runtime.is_file():
        raise ValueError(f'Expected the installed native hook runtime: {runtime}')
    python = executable(python)
    groups = {}
    for event in EVENTS:
        argv = [str(python), '-B', '-S', str(runtime), '--event', event]
        handler = {'type': 'command', 'command': shlex.join(argv),
                   'timeout': TIMEOUTS[event],
                   'statusMessage': MARKER + event}
        if os.name == 'nt':
            handler['commandWindows'] = windows_command(python, runtime, event)
            if handler['commandWindows'].startswith('powershell.exe ') and not shutil.which('powershell.exe'):
                raise ValueError('These Windows hook paths require powershell.exe for safe quoting')
        if event == 'PostToolUse':
            # The bridge honors each project's sync/async policy itself. Native
            # async would prevent configured synchronous hooks blocking a tool.
            handler['async'] = False
        groups[event] = {'hooks': [handler]}
    return runtime, python, groups


@contextmanager
def mutation_lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / 'install.lock'
    regular(lock)
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise ValueError(f'Another installer owns {lock}; inspect it before removing a stale lock') from error
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(str(os.getpid()) + '\n')
        yield
    finally:
        lock.unlink()


def feature_state(home):
    """Report explicit local feature selection; never rewrite config.toml."""
    path = home / 'config.toml'
    try:
        import tomllib
        raw = read(path)
        features = tomllib.loads(raw.decode('utf-8-sig')).get('features', {}) if raw else {}
        for key in ('hooks', 'codex_hooks'):
            if key in features:
                return {'key': key, 'value': features[key]}
        return {'key': None, 'value': None}
    except (ImportError, OSError, UnicodeError, ValueError, TypeError, AttributeError):
        return {'key': None, 'value': None, 'note': 'Local feature configuration could not be read'}


def operate(action, codex_home, runtime, python):
    home = Path(codex_home).expanduser().absolute()
    if home == Path(home.anchor):
        raise ValueError('CODEX_HOME must be a dedicated directory, not a filesystem root')
    hooks_path = home / 'hooks.json'
    state_dir = home / '.pow' / 'native-hooks'
    receipt_path = state_dir / 'receipt.json'
    regular(hooks_path)
    regular(receipt_path)
    if action in ('install', 'uninstall'):
        with mutation_lock(state_dir):
            return operation(action, home, runtime, python, hooks_path, state_dir, receipt_path)
    return operation(action, home, runtime, python, hooks_path, state_dir, receipt_path)


def operation(action, home, runtime, python, hooks_path, state_dir, receipt_path):
    raw = read(hooks_path)
    current = document(raw, hooks_path)
    receipt_raw = read(receipt_path)
    owned = owned_receipt(receipt_raw, home, receipt_path)
    positions = inspect(current, owned)
    result = {'status': 'installed' if owned else 'absent', 'codex_home': str(home),
              'hooks_path': str(hooks_path), 'receipt_path': str(receipt_path),
              'feature_configuration': feature_state(home),
              'trust': 'Review and register hooks using Codex; this installer never changes hook trust',
              'entries': {event: entry['group'] for event, entry in owned['entries'].items()} if owned else {}}
    if owned:
        result.update({'runtime_path': owned['runtime_path'], 'python_path': owned['python_path'],
                       'original_backup_path': str(state_dir / 'backups' / f"hooks-{owned['original_sha256']}.json")
                       if owned['original_exists'] else None})
    if action == 'status' or (action == 'uninstall' and not owned):
        return result

    changed = copy.deepcopy(current)
    entries = changed.setdefault('hooks', {})
    writes = {}
    deletes = []
    original_exists = owned['original_exists'] if owned else raw is not None
    original_sha = owned['original_sha256'] if owned else digest(raw or b'')
    original_path = state_dir / 'backups' / f'hooks-{original_sha}.json'
    if owned and original_exists:
        original_raw = read(original_path)
        if original_raw is None or digest(original_raw) != original_sha:
            raise ValueError(f'Original configuration backup is missing or modified: {original_path}')
    else:
        original_raw = raw if original_exists else None
    original = document(original_raw, original_path)

    if action == 'uninstall':
        for event, index in positions.items():
            del entries[event][index]
            if not entries[event] and event not in original.get('hooks', {}):
                del entries[event]
        if not entries and 'hooks' not in original:
            del changed['hooks']
        replacement = original_raw if changed == original else encode(changed)
        if replacement is None:
            deletes.append(hooks_path)
        elif replacement != raw:
            writes[hooks_path] = (replacement, hooks_path.stat().st_mode & 0o777)
        deletes.append(receipt_path)
        next_status = 'absent'
        planned_entries = result['entries']
    else:
        runtime, python, planned_entries = handlers(runtime, python)
        for event, group in planned_entries.items():
            if event in positions:
                entries[event][positions[event]] = group
            else:
                entries.setdefault(event, []).append(group)
        if changed != current:
            writes[hooks_path] = (encode(changed), hooks_path.stat().st_mode & 0o777 if raw is not None else 0o600)
        receipt = {'owner': OWNER, 'hooks_path': str(hooks_path),
                   'runtime_path': str(runtime), 'python_path': str(python),
                   'original_exists': original_exists, 'original_sha256': original_sha,
                   'entries': {event: {'group': group, 'sha256': group_digest(group)}
                               for event, group in planned_entries.items()}}
        if owned != receipt:
            writes[receipt_path] = (encode(receipt), 0o600)
        next_status = 'installed'

    if raw is not None and hooks_path in set(writes) | set(deletes):
        backup = state_dir / 'backups' / f'hooks-{digest(raw)}.json'
        previous = read(backup)
        if previous is not None and previous != raw:
            raise ValueError(f'Backup differs from its content hash: {backup}')
        if previous is None:
            # A durable snapshot precedes replacement of the active configuration.
            writes = {backup: (raw, 0o600), **writes}
    if read(hooks_path) != raw or read(receipt_path) != receipt_raw:
        raise ValueError('Hook configuration changed during planning; retry after the other writer finishes')
    result.update({'action': action, 'entries': planned_entries,
                   'writes': [{'path': str(path), 'sha256': digest(data), 'bytes': len(data)}
                              for path, (data, _) in writes.items()],
                   'deletes': [str(path) for path in deletes]})
    if action == 'plan':
        return result
    transact(writes, deletes)
    result['status'] = next_status
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('plan', 'install', 'status', 'uninstall'):
        command = sub.add_parser(action)
        command.add_argument('--codex-home', default=os.environ.get('CODEX_HOME') or str(Path.home() / '.codex'))
        command.add_argument('--runtime', default=str(Path.home() / '.local/share/pow-cxd/native_hooks.py'))
        command.add_argument('--python', default=sys.executable)
    args = parser.parse_args()
    try:
        print(json.dumps(operate(args.action, args.codex_home, args.runtime, args.python),
                         ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError) as error:
        print(f'Codex hook installer: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
