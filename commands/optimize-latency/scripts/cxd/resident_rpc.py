"""Workspace-local file IPC with blocking Windows/Linux notifications; no TCP or eval."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import select
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid

sys.dont_write_bytecode = True
from resident import ProjectIndex, atomic_json, inside, verify_timing


_children = {}


class Changes:
    def __init__(self, directory):
        self.fd = None
        if sys.platform.startswith('linux'):
            api = ctypes.CDLL(None, use_errno=True)
            api.inotify_init1.argtypes = [ctypes.c_int]
            api.inotify_init1.restype = ctypes.c_int
            api.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
            api.inotify_add_watch.restype = ctypes.c_int
            self.fd = api.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
            if self.fd < 0:
                raise OSError(ctypes.get_errno(), 'inotify_init1 failed')
            if api.inotify_add_watch(self.fd, os.fsencode(directory), 0x100 | 0x80 | 0x8) < 0:
                error = ctypes.get_errno()
                os.close(self.fd)
                raise OSError(error, 'inotify_add_watch failed')
            return
        if os.name != 'nt':
            raise OSError('resident notifications support Windows and Linux only')
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.FindFirstChangeNotificationW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL, wintypes.DWORD]
        self.api.FindFirstChangeNotificationW.restype = wintypes.HANDLE
        self.api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.api.FindNextChangeNotification.argtypes = [wintypes.HANDLE]
        self.api.FindCloseChangeNotification.argtypes = [wintypes.HANDLE]
        self.handle = self.api.FindFirstChangeNotificationW(str(directory), False, 0x1 | 0x10)
        if self.handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())

    def wait(self, seconds):
        if self.fd is not None:
            readable, _, _ = select.select([self.fd], [], [], max(0, seconds))
            if readable:
                try:
                    os.read(self.fd, 65536)
                except BlockingIOError:
                    pass
            return bool(readable)
        status = self.api.WaitForSingleObject(self.handle, max(1, int(seconds * 1000)))
        if status == 0:
            if not self.api.FindNextChangeNotification(self.handle):
                raise ctypes.WinError(ctypes.get_last_error())
            return True
        if status != 258:
            raise ctypes.WinError(ctypes.get_last_error())
        return False

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
        else:
            self.api.FindCloseChangeNotification(self.handle)


def alive(pid):
    if type(pid) is not int or pid <= 0:
        return False
    if os.name != 'nt':
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return None
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = api.OpenProcess(0x1000, False, pid)
    if not handle:
        # Another sandbox may deny process inspection while file IPC works.
        return None if ctypes.get_last_error() == 5 else False
    try:
        code = wintypes.DWORD()
        return bool(api.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
    finally:
        api.CloseHandle(handle)


def directories(root):
    root = Path(root).resolve()
    state = inside(root, '.cxd')
    for relative in ('.cxd', '.cxd/requests', '.cxd/responses'):
        directory = inside(root, relative)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name == 'posix':
            directory.chmod(0o700)
            if directory.stat().st_mode & 0o777 != 0o700:
                raise OSError('cxd state requires POSIX permissions; use a native Linux filesystem, not a WSL Windows mount')
    ignore = inside(root, '.cxd/.gitignore')
    try:
        descriptor = os.open(ignore, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write('*\n')
    return state


def state_info(root):
    path = inside(Path(root).resolve(), '.cxd/worker.json')
    try:
        info = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(info, dict) or type(info.get('pid')) is not int or info['pid'] <= 0:
            return {}
        return info
    except (OSError, ValueError):
        return {}


def acquire_lock(path):
    """Keep the inode and OS lock for the entire worker lifetime; never steal it."""
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    stream = os.fdopen(descriptor, 'r+', encoding='utf-8')
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        stream.close()
        return None
    stream.seek(0)
    stream.truncate()
    json.dump({'pid': os.getpid()}, stream)
    stream.flush()
    return stream


def request(root, operation, parameters=None, *, timeout=30, start=True):
    root = Path(root).resolve()
    info = state_info(root)
    state = directories(root)
    # PID reuse is not proof of ownership. The lifetime OS lock is authoritative.
    probe = acquire_lock(inside(root, '.cxd/worker.lock'))
    locked = probe is None
    if probe is not None:
        probe.close()
    if not locked:
        if not start:
            return {'running': False}
        log_path = inside(root, '.cxd/worker.log')
        descriptor = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, 'ab') as log:
            child = subprocess.Popen([sys.executable, '-B', '-S', str(Path(__file__).resolve()), str(root)],
                stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                **({'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
                   if os.name == 'nt' else {'start_new_session': True}))
            _children[child.pid] = child
    identifier = uuid.uuid4().hex
    response_path = state / 'responses' / (identifier + '.json')
    changes = Changes(state / 'responses')
    try:
        parameters = dict(parameters or {})
        if operation == 'stop':
            parameters['expected_pid'] = info.get('pid')
            parameters['expected_token'] = info.get('token')
        atomic_json(state / 'requests' / (identifier + '.json'),
                    {'operation': operation, 'parameters': parameters})
        deadline = time.monotonic() + timeout
        while not response_path.exists():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f'resident operation {operation} timed out; see {state / "worker.log"}')
            changes.wait(remaining)
        result = json.loads(response_path.read_text(encoding='utf-8'))
        response_path.unlink()
        if not result['ok']:
            raise RuntimeError(result['error'])
        if operation == 'stop':
            child = _children.pop(result['result'].get('worker_pid'), None)
            if child is not None:
                child.wait(timeout=max(.1, deadline - time.monotonic()))
        for pid, child in list(_children.items()):
            if child.poll() is not None:
                _children.pop(pid, None)
        return result['result']
    finally:
        changes.close()


def serve(root, idle_seconds=900):
    root = Path(root).resolve()
    state = directories(root)
    lock = inside(root, '.cxd/worker.lock')
    stream = acquire_lock(lock)
    if stream is None:
        return
    index = ProjectIndex(root, inside(root, '.cxd/index.json'))
    info = {'running': True, 'pid': os.getpid(), 'workspace': str(root),
            'idle_seconds': idle_seconds, 'started_ns': time.time_ns(), 'token': uuid.uuid4().hex,
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    atomic_json(inside(root, '.cxd/worker.json'), info)
    print(json.dumps({'event': 'resident_ready', **info}), flush=True)
    changes = Changes(state / 'requests')
    running, last_request = True, time.monotonic()
    try:
        while running:
            for path in sorted((state / 'requests').glob('*.json')):
                try:
                    uuid.UUID(hex=path.stem)
                except ValueError:
                    continue
                claimed = path.with_suffix('.working')
                try:
                    path.rename(claimed)
                except (FileNotFoundError, FileExistsError):
                    continue
                last_request = time.monotonic()
                try:
                    inside(root, claimed)
                    if claimed.stat().st_size > 1048576:
                        raise ValueError('request exceeds 1 MiB')
                    data = json.loads(claimed.read_text(encoding='utf-8'))
                    operation, parameters = data['operation'], data['parameters']
                    if operation in {'status', 'stop'}:
                        if operation == 'stop' and (parameters.get('expected_pid') != os.getpid() or
                            parameters.get('expected_token') != info['token']):
                            raise ValueError('stop request targets a different worker')
                        value = {**info, 'parsed_total': index.parsed,
                                 'indexed_files': len(index.entries)}
                        if operation == 'stop':
                            running = False
                    elif operation == 'timing':
                        value = verify_timing(inside(root, parameters['path']))
                    elif operation in {'index', 'symbols', 'tree', 'syntax'}:
                        config = json.loads(inside(root, '.codex-dispatch.json').read_text(encoding='utf-8-sig'))
                        value = index.operate(operation, parameters, config['source_roots'])
                    else:
                        raise ValueError('unsupported resident operation')
                    response = {'ok': True, 'result': {**value, 'worker_pid': os.getpid()}}
                except Exception as error:
                    response = {'ok': False, 'error': f'{type(error).__name__}: {error}\n{traceback.format_exc()}'}
                atomic_json(state / 'responses' / path.name, response)
                claimed.unlink()
            remaining = idle_seconds - (time.monotonic() - last_request)
            if not running or remaining <= 0:
                break
            changes.wait(remaining)
    finally:
        changes.close()
        if state_info(root).get('token') == info['token']:
            (state / 'worker.json').unlink(missing_ok=True)
        stream.close()



if __name__ == '__main__':
    serve(sys.argv[1])
