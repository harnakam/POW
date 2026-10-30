"""Install the bundled cxd runtime without changing PATH or global settings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile

LEGACY_FILES = ('dispatch.py', 'command_actors.py', 'resident.py', 'resident_rpc.py')
PREVIOUS_FILES = (*LEGACY_FILES, 'async_jobs.py', 'ctx.py')
HOOK_FILES = (*PREVIOUS_FILES, 'hooks.py')
FILES = (*HOOK_FILES, 'native_hooks.py')
RECEIPT = '.pow-cxd-install.json'
OWNER = 'pow-cxd-standalone-v1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data, mode):
    fd, name = tempfile.mkstemp(prefix='.cxd-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def check_regular(path):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f'Expected a regular owned file: {path}')


def inspect(package, shim):
    ctx_shim = shim.with_name('ctx.cmd' if os.name == 'nt' else 'ctx')
    receipt = package / RECEIPT
    check_regular(receipt)
    if not receipt.exists():
        if any(p.exists() or p.is_symlink() for p in (shim, ctx_shim)):
            raise ValueError(f'Refusing unowned shim: {shim}')
        if package.exists() and any(package.iterdir()):
            raise ValueError(f'Refusing unowned package directory: {package}')
        return None
    data = json.loads(receipt.read_text(encoding='utf-8'))
    expected = {str(package / name) for name in FILES} | {str(shim), str(ctx_shim)}
    previous = {str(package / name) for name in PREVIOUS_FILES} | {str(shim), str(ctx_shim)}
    hook_previous = {str(package / name) for name in HOOK_FILES} | {str(shim), str(ctx_shim)}
    legacy = {str(package / name) for name in LEGACY_FILES} | {str(shim)}
    if (not isinstance(data, dict) or data.get('owner') != OWNER or data.get('package_dir') != str(package)
            or data.get('bin_dir') != str(shim.parent)
            or not isinstance(data.get('files'), dict)
            or set(data['files']) not in (expected, hook_previous, previous, legacy)):
        raise ValueError(f'Invalid ownership receipt: {receipt}')
    # Never follow paths from the receipt: enumerate only our configured targets.
    for path in [*(package / name for name in FILES), shim, ctx_shim]:
        if str(path) not in data['files']:
            continue
        check_regular(path)
        if not path.exists() or digest(path.read_bytes()) != data['files'][str(path)]:
            raise ValueError(f'Owned file is missing or locally modified; preserving it: {path}')
    return data


def transact(writes, deletes=()):
    """Stage each replacement atomically; restore previous files on any failure."""
    targets = list(writes) + list(deletes)
    snapshots = {p: (p.read_bytes(), p.stat().st_mode & 0o777) if p.exists() else None
                 for p in targets}
    created = []
    changed = []
    try:
        for path in targets:
            missing = []
            parent = path.parent
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for directory in reversed(missing):
                directory.mkdir()
                created.append(directory)
        for path, (content, mode) in writes.items():
            atomic_write(path, content, mode)
            changed.append(path)
        for path in deletes:
            path.unlink()
            changed.append(path)
    except Exception as original:
        failures = []
        for path in reversed(changed):
            try:
                old = snapshots[path]
                if old is None:
                    path.unlink()
                else:
                    atomic_write(path, *old)
            except OSError as error:
                failures.append(str(error))
        for directory in reversed(created):
            try:
                directory.rmdir()
            except OSError:
                pass
        if failures:
            raise RuntimeError(f'{original}; rollback failed: {failures}') from original
        raise


def operate(action, bin_dir, package_dir):
    package = Path(package_dir).expanduser().absolute()
    binary = Path(bin_dir).expanduser().absolute()
    # Reject symlinked targets and ancestors rather than accidentally claiming their contents.
    for target in (package, binary):
        if any(p.is_symlink() for p in (target, *target.parents)):
            raise ValueError(f'Symlinked installation paths are unsupported: {target}')
        if target.exists() and not target.is_dir():
            raise ValueError(f'Expected directory: {target}')
    package = package.resolve()
    binary = binary.resolve()
    if package == binary or package in binary.parents or binary in package.parents:
        raise ValueError('Package and bin directories must be separate, non-nested targets')
    shim = binary / ('cxd.cmd' if os.name == 'nt' else 'cxd')
    ctx_shim = binary / ('ctx.cmd' if os.name == 'nt' else 'ctx')
    if os.name == 'nt' and any(c in str(p) for p in (package, binary, Path(sys.executable))
                               for c in ('%', '!', '"', '\r', '\n')):
        raise ValueError('Windows installation paths cannot contain %, !, quotes, or newlines')
    owned = inspect(package, shim)
    result = {'status': 'installed' if owned else 'absent', 'shim': str(shim), 'ctx_shim': str(ctx_shim),
              'package_dir': str(package), 'bin_dir': str(binary)}
    if action == 'status':
        return result
    if action == 'uninstall':
        if owned:
            targets = [shim, ctx_shim, *(package / name for name in FILES)]
            transact({}, [*(p for p in targets if str(p) in owned['files']), package / RECEIPT])
            # Leave directories in place, including unknown files. No recursive removal.
        return {**result, 'status': 'absent'}
    source = Path(__file__).resolve().parent / 'cxd'
    for target in [ctx_shim, *(package / name for name in FILES)]:
        if owned and str(target) not in owned['files'] and (target.exists() or target.is_symlink()):
            raise ValueError(f'Refusing unowned new target during upgrade: {target}')
    writes = {package / name: ((source / name).read_bytes(), 0o644) for name in FILES}
    for target, entry in ((shim, 'dispatch.py'), (ctx_shim, 'ctx.py')):
        if os.name == 'nt':
            script = f'@echo off\r\n"{sys.executable}" -B -S "{package / entry}" %*\r\n'
        else:
            script = f'#!/bin/sh\nexec {shlex.quote(sys.executable)} -B -S {shlex.quote(str(package / entry))} "$@"\n'
        writes[target] = (script.encode('utf-8'), 0o755)
    receipt = {'owner': OWNER, 'package_dir': str(package), 'bin_dir': str(binary),
               'files': {str(p): digest(content) for p, (content, _) in writes.items()}}
    writes[package / RECEIPT] = ((json.dumps(receipt, indent=2) + '\n').encode(), 0o644)
    transact(writes)
    return {**result, 'status': 'installed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('install', 'status', 'uninstall'):
        cmd = sub.add_parser(action)
        cmd.add_argument('--bin-dir', default=str(Path.home() / '.local/bin'))
        cmd.add_argument('--package-dir', default=str(Path.home() / '.local/share/pow-cxd'))
    args = parser.parse_args()
    try:
        print(json.dumps(operate(args.action, args.bin_dir, args.package_dir), indent=2))
    except (OSError, ValueError, RuntimeError) as error:
        print(f'cxd installer: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
