"""Prepare an explicit, reversible per-user Desktop native runtime override."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading

OWNER = 'pow-desktop-native-activation-v1'
NAMES = ('CODEX_CLI_PATH', 'CODEX_NATIVE_TOOL_CONCURRENCY')
MARKERS = (b'CODEX_NATIVE_TOOL_CONCURRENCY', b'review_limit')
STRING_TYPES = (1, 2)  # REG_SZ, REG_EXPAND_SZ
VERSION = re.compile(r'codex-cli (?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)'
                     r'(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?'
                     r'(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?')


def validate_version(value):
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ValueError('expected a single codex-cli semantic version')
    return value


class Registry:
    """Only the two approved values under HKCU\\Environment are writable."""
    def __init__(self):
        import winreg
        self.winreg = winreg

    def get(self, name):
        assert name in NAMES
        w = self.winreg
        try:
            with w.OpenKey(w.HKEY_CURRENT_USER, 'Environment') as key:
                value, kind = w.QueryValueEx(key, name)
                return {'value': value, 'type': kind}
        except FileNotFoundError:
            return None

    def put(self, name, value):
        assert name in NAMES
        w = self.winreg
        with w.CreateKeyEx(w.HKEY_CURRENT_USER, 'Environment', 0, w.KEY_SET_VALUE) as key:
            if value is None:
                try:
                    w.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
            else:
                w.SetValueEx(key, name, 0, value['type'], value['value'])


def valid_value(value):
    return value is None or (isinstance(value, dict) and set(value) == {'value', 'type'}
        and isinstance(value['value'], str) and type(value['type']) is int
        and value['type'] in STRING_TYPES)


def fingerprint(path):
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError('binary must be a regular file')
    digest, found, tail = hashlib.sha256(), set(), b''
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            window = tail + chunk
            found.update(marker for marker in MARKERS if marker in window)
            tail = window[-max(map(len, MARKERS)):]
    return {'path': str(path), 'sha256': digest.hexdigest()}, found


def version(path):
    result = subprocess.run([str(path), '--version'], capture_output=True,
                            text=True, timeout=10, check=True)
    output = result.stdout.strip()
    return validate_version(output)


def validate_state(data):
    if (not isinstance(data, dict) or set(data) != {
            'owner', 'binary', 'vendor', 'version', 'concurrency', 'before', 'applied'}
            or data['owner'] != OWNER or not isinstance(data['version'], str)
            or not data['version'] or type(data['concurrency']) is not int
            or not 1 <= data['concurrency'] <= 1024):
        raise ValueError('invalid activation ownership state')
    validate_version(data['version'])
    for key in ('binary', 'vendor'):
        record = data[key]
        if (not isinstance(record, dict) or set(record) != {'path', 'sha256'}
                or not isinstance(record['path'], str) or not Path(record['path']).is_absolute()
                or not isinstance(record['sha256'], str)
                or not re.fullmatch('[0-9a-f]{64}', record['sha256'])):
            raise ValueError('invalid binary record')
    for key in ('before', 'applied'):
        values = data[key]
        if (not isinstance(values, dict) or set(values) != set(NAMES)
                or not all(valid_value(value) for value in values.values())):
            raise ValueError('invalid environment record')
    expected = {NAMES[0]: {'value': data['binary']['path'], 'type': 1},
                NAMES[1]: {'value': str(data['concurrency']), 'type': 1}}
    if data['applied'] != expected or data['binary']['path'] == data['vendor']['path']:
        raise ValueError('invalid applied values')
    return data


def load_state(path):
    path = Path(path)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('state must be a regular file')
    try:
        return validate_state(json.loads(path.read_text(encoding='utf-8')))
    except FileNotFoundError:
        return None


def save_state(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.native-activation-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_values(registry):
    values = {name: registry.get(name) for name in NAMES}
    if not all(valid_value(value) for value in values.values()):
        raise ValueError('existing environment values must be strings; preserving them')
    return values


@contextmanager
def mutation_lock(state):
    lock = Path(str(state) + '.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.close(descriptor)
        yield
    finally:
        lock.unlink()


def plan(binary, vendor_binary, concurrency, state, registry, get_version=version):
    if type(concurrency) is not int or not 1 <= concurrency <= 1024:
        raise ValueError('concurrency must be an integer from 1 to 1024')
    owned = load_state(state)
    custom, markers = fingerprint(binary)
    vendor, _ = fingerprint(vendor_binary)
    if custom['path'] == vendor['path'] or custom['sha256'] == vendor['sha256']:
        raise ValueError('custom and vendor binaries must differ')
    if not all(marker in markers for marker in MARKERS):
        raise ValueError('custom binary lacks required native patch markers')
    custom_version = validate_version(get_version(custom['path']))
    if custom_version != validate_version(get_version(vendor['path'])):
        raise ValueError('custom and installed Desktop vendor versions must match exactly')
    # Detect replacement during the version probes rather than trusting a stale hash.
    if fingerprint(binary)[0] != custom or fingerprint(vendor_binary)[0] != vendor:
        raise ValueError('binary changed during verification')
    current = read_values(registry)
    applied = {NAMES[0]: {'value': custom['path'], 'type': 1},
               NAMES[1]: {'value': str(concurrency), 'type': 1}}
    record = {'owner': OWNER, 'binary': custom, 'vendor': vendor, 'version': custom_version,
              'concurrency': concurrency, 'before': current, 'applied': applied}
    if owned:
        if (current != owned['applied'] or any(record[key] != owned[key]
                for key in ('binary', 'vendor', 'version', 'concurrency', 'applied'))):
            raise ValueError('activation state or environment changed; preserving existing values')
        record = owned
    return {'action': 'plan', 'status': 'planned', 'restart_required': True,
            'running_engine_verified': False, 'record': record,
            'registry_already_configured': owned is not None}


def restore(registry, record):
    """Only replace our exact applied value, never an external edit."""
    for name in NAMES:
        current = registry.get(name)
        if current != record['applied'][name] and current != record['before'][name]:
            raise ValueError('environment changed outside this helper; preserving all values')
    for name in reversed(NAMES):
        current = registry.get(name)
        if current == record['applied'][name]:
            registry.put(name, record['before'][name])
        elif current != record['before'][name]:
            raise ValueError('environment changed during restoration; preserving edit')
    if read_values(registry) != record['before']:
        raise ValueError('environment changed during restoration; retaining state')


def enable(binary, vendor_binary, concurrency, state, registry, get_version=version):
    with mutation_lock(state):
        return _enable(binary, vendor_binary, concurrency, state, registry, get_version)


def _enable(binary, vendor_binary, concurrency, state, registry, get_version):
    result = plan(binary, vendor_binary, concurrency, state, registry, get_version)
    if result['registry_already_configured']:
        return {**result, 'action': 'enable', 'status': 'registry_configured'}
    record = result['record']
    # Recheck before claiming ownership and before each mutation.
    if read_values(registry) != record['before'] or load_state(state) is not None:
        raise ValueError('environment or state changed during planning')
    save_state(state, record)
    try:
        for name in NAMES:
            if registry.get(name) != record['before'][name]:
                raise ValueError('environment changed during activation')
            registry.put(name, record['applied'][name])
        if read_values(registry) != record['applied']:
            raise ValueError('environment changed during activation')
    except Exception as original:
        try:
            restore(registry, record)
            Path(state).unlink()
        except Exception as recovery:
            raise RuntimeError(f'activation failed; ownership state retained for recovery: {recovery}') from original
        raise
    return {**result, 'action': 'enable', 'status': 'registry_configured'}


def disable(state, registry):
    with mutation_lock(state):
        return _disable(state, registry)


def _disable(state, registry):
    record = load_state(state)
    if record is None:
        return {'action': 'disable', 'status': 'absent', 'restart_required': True,
                'running_engine_verified': False}
    restore(registry, record)
    Path(state).unlink()
    return {'action': 'disable', 'status': 'restored', 'restart_required': True,
            'running_engine_verified': False}


def broadcast_environment():
    """Send only the standard environment-change notification; no registry writes."""
    if os.name != 'nt':
        raise OSError('Windows notification unavailable')
    import ctypes
    from ctypes import wintypes
    send = ctypes.WinDLL('user32', use_last_error=True).SendMessageTimeoutW
    send.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                     wintypes.LPARAM, wintypes.UINT, wintypes.UINT,
                     ctypes.POINTER(ctypes.c_size_t))
    send.restype = wintypes.LPARAM
    text = ctypes.create_unicode_buffer('Environment')
    response = ctypes.c_size_t()
    ctypes.set_last_error(0)
    delivered = send(0xffff, 0x001a, 0, ctypes.cast(text, ctypes.c_void_p).value,
                     0x0002, 2000, ctypes.byref(response))  # SMTO_ABORTIFHUNG
    return {'status': 'sent' if delivered else 'failed_or_timed_out',
            'win32_error': 0 if delivered else ctypes.get_last_error()}


def with_environment_notification(result, requested=False, send=None, deadline_s=3):
    if not requested:
        return result
    if result['action'] not in ('enable', 'disable'):
        raise ValueError('environment notification is supported only after enable or disable')
    if not 0 < deadline_s <= 3:
        raise ValueError('notification deadline must be positive and at most three seconds')
    outcome = {}
    def notify():
        try:
            outcome.update((send or broadcast_environment)())
        except Exception as error:
            outcome.update(status='failed', error_type=type(error).__name__)
    # HWND_BROADCAST's native timeout is per window. Bound the whole wait too.
    worker = threading.Thread(target=notify, daemon=True)
    try:
        worker.start()
        worker.join(deadline_s)
    except Exception as error:
        outcome.update(status='failed', error_type=type(error).__name__)
    notification = ({'status': 'wait_timed_out', 'delivery_unknown': True}
                    if worker.is_alive() else dict(outcome))
    return {**result, 'environment_notification': {
        **notification, 'api_timeout_ms': 2000, 'wait_limit_ms': round(deadline_s * 1000),
        'running_process_environment_changed': False}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'enable', 'disable'))
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--vendor-binary', type=Path)
    parser.add_argument('--concurrency', type=int, default=3)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--notify-environment', action='store_true',
                        help='notify Windows after enable/disable; does not restart Desktop')
    args = parser.parse_args(argv)
    try:
        if args.notify_environment and args.action == 'plan':
            raise ValueError('--notify-environment cannot be used with plan')
        if os.name != 'nt':
            raise ValueError('real registry operations require Windows')
        if args.action != 'disable' and (args.binary is None or args.vendor_binary is None):
            raise ValueError('--binary and --vendor-binary are required')
        registry = Registry()
        result = (disable(args.state, registry) if args.action == 'disable' else
                  globals()[args.action](args.binary, args.vendor_binary, args.concurrency,
                                         args.state, registry))
        result = with_environment_notification(result, args.notify_environment)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'native activation: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
