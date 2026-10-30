"""Review or trust only the exact hooks owned by the POW installer.

The default prints a plan. ``--apply`` uses Codex's native hooks/list hashes and
the same config/batchWrite request as its /hooks interface. No model turn starts.
"""
import argparse
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time

from install_codex_hooks import EVENTS, document, inspect, owned_receipt, read
from install_cxd import digest, transact


class AppServer:
    """Bounded stdio transport, following native/prove_native_dispatch.py."""

    def __init__(self, binary, home, timeout):
        environment = dict(os.environ, CODEX_HOME=str(home))
        self.timeout = timeout
        self.pending = queue.Queue()
        self.errors = []
        self.next_id = 0
        self.process = subprocess.Popen(
            [str(binary), '-c', 'features.apps=false', '-c', 'features.plugins=false',
             '-c', 'analytics.enabled=false', 'app-server', '--listen', 'stdio://'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', env=environment,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        self.readers = [threading.Thread(target=self._stdout, daemon=True),
                        threading.Thread(target=self._stderr, daemon=True)]
        for reader in self.readers:
            reader.start()
        try:
            self.request('initialize', {
                'clientInfo': {'name': 'pow-hook-trust', 'version': '1'},
                'capabilities': {'experimentalApi': True}})
            self.send({'method': 'initialized'})
        except BaseException as error:
            self.close()
            if isinstance(error, (OSError, ValueError, RuntimeError)):
                detail = '\n'.join(self.errors[-8:])
                raise RuntimeError(f'{error}' + (f'\nApp-server diagnostics:\n{detail}' if detail else '')) from error
            raise

    def _stdout(self):
        for line in self.process.stdout:
            try:
                self.pending.put(json.loads(line))
            except ValueError:
                self.pending.put({'transport_error': 'Non-JSON app-server output'})
        self.pending.put({'transport_error': 'App-server closed stdout'})

    def _stderr(self):
        for line in self.process.stderr:
            self.errors.append(line.rstrip())
            del self.errors[:-20]

    def send(self, message):
        self.process.stdin.write(json.dumps({'jsonrpc': '2.0', **message}) + '\n')
        self.process.stdin.flush()

    def request(self, method, params):
        self.next_id += 1
        identity = self.next_id
        self.send({'id': identity, 'method': method, 'params': params})
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                message = self.pending.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty as error:
                raise RuntimeError(f'{method} timed out after {self.timeout}s') from error
            if message.get('transport_error'):
                raise RuntimeError(message['transport_error'])
            if 'method' in message and 'id' in message:
                raise RuntimeError('Unexpected app-server client action; no approval was granted')
            if message.get('id') == identity:
                if 'error' in message:
                    raise RuntimeError(f'{method}: {message["error"]}')
                return message['result']

    def close(self):
        if self.process.stdin and not self.process.stdin.closed:
            try:
                self.process.stdin.close()
            except OSError:
                pass
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        for reader in self.readers:
            reader.join(timeout=1)


def installation(home):
    receipt_path = home / '.pow/native-hooks/receipt.json'
    receipt_raw = read(receipt_path)
    receipt = owned_receipt(receipt_raw, home, receipt_path)
    if receipt is None:
        raise ValueError(f'POW hook installation receipt is missing: {receipt_path}')
    hooks_path = home / 'hooks.json'
    hooks_raw = read(hooks_path)
    current = document(hooks_raw, hooks_path)
    positions = inspect(current, receipt)
    return receipt, positions, (receipt_raw, hooks_raw)


def path_key(value):
    return os.path.normcase(os.path.abspath(value))


def backup_config(home):
    config_path = home / 'config.toml'
    original = read(config_path)
    if original is None:
        return None, None
    backup = home / '.pow/native-hooks/backups' / f'config-{digest(original)}.toml'
    existing = read(backup)
    if existing is not None and existing != original:
        raise ValueError(f'Config backup differs from its content hash: {backup}')
    if existing is None:
        transact({backup: (original, config_path.stat().st_mode & 0o777)}, [])
    if read(config_path) != original:
        raise ValueError('User config changed while backing it up; rerun the plan')
    return str(backup), original


def select_hooks(response, cwd, home, receipt, positions):
    entries = [entry for entry in response['data'] if path_key(entry['cwd']) == path_key(cwd)]
    if len(entries) != 1 or entries[0]['errors']:
        raise ValueError('hooks/list did not return one error-free workspace entry')
    entry = entries[0]
    selected = []
    for event in EVENTS:
        handler = receipt['entries'][event]['group']['hooks'][0]
        event_name = event[0].lower() + event[1:]
        matches = [hook for hook in entry['hooks']
                   if path_key(hook['sourcePath']) == path_key(home / 'hooks.json')
                   and hook['eventName'] == event_name
                   and hook.get('statusMessage') == handler['statusMessage']]
        if len(matches) != 1:
            raise ValueError(f'Expected one native {event} handler from the installed source')
        hook = matches[0]
        command = handler.get('commandWindows', handler['command']) if os.name == 'nt' else handler['command']
        event_key = re.sub(r'(?<!^)(?=[A-Z])', '_', event).lower()
        expected_key = f'{hook["sourcePath"]}:{event_key}:{positions[event]}:0'
        if (hook['key'] != expected_key or hook.get('handlerType') != 'command'
                or hook.get('command') != command or hook.get('async', False) != handler.get('async', False)
                or hook.get('matcher') != receipt['entries'][event]['group'].get('matcher')
                or hook['timeoutSec'] != handler['timeout'] or hook['isManaged']
                or not hook['enabled'] or hook['trustStatus'] not in ('untrusted', 'modified', 'trusted')
                or not re.fullmatch(r'sha256:[0-9a-f]{64}', hook['currentHash'])):
            raise ValueError(f'Native {event} metadata differs from the reviewed installation')
        selected.append(hook)
    return selected, entry['warnings']


def operate(binary, home, cwd, apply, timeout):
    receipt, positions, snapshot = installation(home)
    server = AppServer(binary, home, timeout)
    try:
        hooks, warnings = select_hooks(server.request('hooks/list', {'cwds': [str(cwd)]}),
                                       cwd, home, receipt, positions)
        pending = [hook for hook in hooks if hook['trustStatus'] != 'trusted']
        result = {'action': 'apply' if apply else 'plan', 'codex_binary': str(binary),
                  'codex_home': str(home), 'cwd': str(cwd), 'warnings': warnings,
                  'model_turns_started': 0, 'hooks': hooks, 'trust_updates': len(pending),
                  'config_backup': None}
        if apply and pending:
            if installation(home) != (receipt, positions, snapshot):
                raise ValueError('Hook installation changed during review; rerun the plan')
            refreshed, _ = select_hooks(server.request('hooks/list', {'cwds': [str(cwd)]}),
                                        cwd, home, receipt, positions)
            if refreshed != hooks:
                raise ValueError('Native hook metadata changed during review; rerun the plan')
            result['config_backup'], config_original = backup_config(home)
            result['config_original_exists'] = config_original is not None
            if read(home / 'config.toml') != config_original:
                raise ValueError('User config changed before trust update; rerun the plan')
            server.request('config/batchWrite', {
                'edits': [{'keyPath': 'hooks.state', 'mergeStrategy': 'upsert',
                           'value': {hook['key']: {'trusted_hash': hook['currentHash']}
                                     for hook in pending}}],
                'filePath': None, 'expectedVersion': None, 'reloadUserConfig': True})
            verified, _ = select_hooks(server.request('hooks/list', {'cwds': [str(cwd)]}),
                                       cwd, home, receipt, positions)
            if (any(hook['trustStatus'] != 'trusted' for hook in verified)
                    or [hook['currentHash'] for hook in verified] != [hook['currentHash'] for hook in hooks]):
                raise RuntimeError('Codex did not confirm all installed hooks trusted at the reviewed hashes')
            result['hooks'] = verified
        result['status'] = 'trusted' if all(hook['trustStatus'] == 'trusted' for hook in result['hooks']) else 'review-required'
        return result
    except (OSError, ValueError, RuntimeError) as error:
        detail = '\n'.join(server.errors[-8:])
        raise RuntimeError(f'{error}' + (f'\nApp-server diagnostics:\n{detail}' if detail else '')) from error
    finally:
        server.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Persist native trust for these exact owned hooks')
    parser.add_argument('--codex-home', default=os.environ.get('CODEX_HOME') or str(Path.home() / '.codex'))
    parser.add_argument('--codex-binary', default='codex')
    parser.add_argument('--cwd', default=os.getcwd())
    parser.add_argument('--timeout', type=int, default=60)
    args = parser.parse_args()
    try:
        if not 1 <= args.timeout <= 120:
            raise ValueError('--timeout must be between 1 and 120 seconds')
        binary_value = shutil.which(args.codex_binary) or args.codex_binary
        binary = Path(binary_value).expanduser().resolve(strict=True)
        home = Path(args.codex_home).expanduser().resolve(strict=True)
        cwd = Path(args.cwd).expanduser().resolve(strict=True)
        if not binary.is_file() or not home.is_dir() or not cwd.is_dir():
            raise ValueError('Expected an executable file and existing home/workspace directories')
        print(json.dumps(operate(binary, home, cwd, args.apply, args.timeout), ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError) as error:
        print(f'Codex hook trust: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
