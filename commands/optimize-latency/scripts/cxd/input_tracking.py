"""Bounded input observations; stat reuse is not verification evidence.

Keep one snapshot open while collecting all hook definitions. Call ``finish``
only after every declared input was inspected, and use a context manager so an
incomplete scan releases its lock without publishing partial state. Completion
boundaries must pass ``force=True`` to read bytes rather than trust file stats.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

from resident import atomic_json
from resident_rpc import acquire_lock


SCHEMA = 1
TREE_FILE_BYTES = 2 * 1024 * 1024
EXPLICIT_FILE_BYTES = 8 * 1024 * 1024
TREE_BYTES = 32 * 1024 * 1024
SKIPPED = {'.git', '.cxd', '.pow', 'node_modules', '__pycache__', '.venv', 'dist', 'build', 'coverage'}
MAX_CACHE_FILES = 8192
MAX_CACHE_TREES = 64
MAX_STATE_BYTES = 8 * 1024 * 1024


class InputStateBusy(ValueError):
    """Another input snapshot owns the workspace writer lock."""


class _UnstableInput(ValueError):
    pass


def _signature(value):
    return [value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns,
            value.st_ctime_ns, value.st_mode]


def _linked(value):
    return stat.S_ISLNK(value.st_mode) or bool(
        getattr(value, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))


class InputSnapshot:
    """Collect workspace input hashes under an exclusive, lifetime OS lock.

    ``changed_paths`` is an optional bounded hint that forces matching files or
    descendants to be read. Every tree is enumerated regardless of hints, so
    additions and deletions do not depend on tool payloads. Tree keys use POSIX
    workspace-relative paths. ``file`` accepts exact workspace-relative files;
    its caller retains the existing limit of 64 explicit inputs per hook.
    """
    def __init__(self, root, force=False, changed_paths=()):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError('input snapshot requires a workspace directory')
        self.force = bool(force)
        self._lock = None
        self._finished = None
        self._observed, self._trees = {}, {}
        self._hashed, self._reused, self._deleted = set(), set(), set()
        self._bytes_read = self._bytes_hashed = self._hash_reads = 0
        self._hints = set()
        for index, relative in enumerate(changed_paths):
            if index >= MAX_CACHE_FILES:
                break
            try:
                candidate = Path(relative)
                if candidate.is_absolute():
                    candidate = candidate.relative_to(self.root)
                self._hints.add(self._normalize(candidate))
            except (TypeError, ValueError):
                continue
        try:
            directory = self._path('.cxd', missing=True)
            directory.mkdir(mode=0o700, exist_ok=True)
            directory = self._path('.cxd/hooks', missing=True)
            directory.mkdir(mode=0o700, exist_ok=True)
            self._state_file = self._path('.cxd/hooks/input-state.json', missing=True)
            lock_file = self._path('.cxd/hooks/input-state.lock', missing=True)
            self._lock = acquire_lock(lock_file)
            if self._lock is None:
                raise InputStateBusy('hook input state busy; retry after the current snapshot finishes')
            # Recheck the path after acquiring the lock before reading state.
            self._path('.cxd/hooks/input-state.lock')
            self._state, self._rebuilt = self._load()
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self._lock is not None:
            self._lock.close()
            self._lock = None

    def _normalize(self, relative):
        if not isinstance(relative, (str, Path)):
            raise ValueError('hook inputs must be workspace-relative paths')
        value = Path(relative)
        if value.is_absolute() or value.anchor:
            raise ValueError('hook inputs must be workspace-relative paths')
        parts = []
        for part in value.parts:
            if part == '..':
                if not parts:
                    raise ValueError('input path must stay inside the workspace')
                parts.pop()
            elif part != '.':
                parts.append(part)
        return '/'.join(parts)

    def _path(self, relative, missing=False):
        key = self._normalize(relative)
        current = self.root
        for part in Path(key).parts:
            current = current / part
            try:
                value = current.lstat()
            except FileNotFoundError:
                if missing:
                    continue
                raise
            if _linked(value):
                raise ValueError('hook inputs cannot traverse symlinks or junctions')
        if not current.resolve(strict=not missing).is_relative_to(self.root):
            raise ValueError('input path must stay inside the workspace')
        return current

    def _empty(self):
        return {'schema': SCHEMA, 'root': os.path.normcase(str(self.root)),
                'generation': 0, 'files': {}, 'trees': {}, 'activeTrees': []}

    def _load(self):
        try:
            if self._state_file.stat().st_size > MAX_STATE_BYTES:
                return self._empty(), True
            state = json.loads(self._state_file.read_text(encoding='utf-8'))
        except FileNotFoundError:
            return self._empty(), False
        except (UnicodeError, ValueError, RecursionError):
            return self._empty(), True
        try:
            if (not isinstance(state, dict)
                    or set(state) != {'schema', 'root', 'generation', 'files', 'trees', 'activeTrees'}
                    or state.get('schema') != SCHEMA
                    or state.get('root') != os.path.normcase(str(self.root))
                    or type(state.get('generation')) is not int or state['generation'] < 0
                    or not isinstance(state.get('files'), dict) or len(state['files']) > MAX_CACHE_FILES
                    or not isinstance(state.get('trees'), dict) or len(state['trees']) > MAX_CACHE_TREES
                    or not isinstance(state.get('activeTrees'), list) or len(state['activeTrees']) > 32
                    or any(not isinstance(key, str) or len(key) != 64
                           or any(char not in '0123456789abcdef' for char in key) for key in state['activeTrees'])):
                raise ValueError('invalid input state')
            for key, value in state['files'].items():
                if (self._normalize(key) != key or not key or not isinstance(value, dict)
                        or set(value) != {'signature', 'sha256', 'seen'}
                        or not isinstance(value.get('signature'), list) or len(value['signature']) != 6
                        or any(type(item) is not int for item in value['signature'])
                        or not isinstance(value.get('sha256'), str) or len(value['sha256']) != 64
                        or any(char not in '0123456789abcdef' for char in value['sha256'])
                        or type(value.get('seen')) is not int):
                    raise ValueError('invalid cached input')
            for key, value in state['trees'].items():
                if (not isinstance(value, dict) or set(value) != {'roots', 'paths', 'seen'}
                        or not isinstance(value.get('roots'), list)
                        or len(value['roots']) > 8 or not isinstance(value.get('paths'), list)
                        or len(value['paths']) > 2000 or type(value.get('seen')) is not int
                        or any(self._normalize(path) != path for path in value['roots'])
                        or any(not path or self._normalize(path) != path for path in value['paths'])
                        or self._tree_key(value['roots']) != key):
                    raise ValueError('invalid cached tree')
        except (TypeError, ValueError):
            return self._empty(), True
        return state, False

    def _check_open(self):
        if self._lock is None or self._finished is not None:
            raise ValueError('input snapshot is already closed')

    def _read(self, key, max_bytes):
        for attempt in range(2):
            try:
                file = self._path(key)
                before = file.lstat()
                if not stat.S_ISREG(before.st_mode):
                    raise ValueError('hook input must be an existing regular file')
                if before.st_size > max_bytes:
                    raise ValueError('hook input exceeds its declared size limit')
                flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
                descriptor = os.open(file, flags)
                with os.fdopen(descriptor, 'rb') as stream:
                    opened = os.fstat(stream.fileno())
                    data = stream.read(max_bytes + 1)
                    self._bytes_read += len(data)
                    after = os.fstat(stream.fileno())
                final = self._path(key).lstat()
                # Some Windows Python builds expose different ctime meanings
                # through lstat and fstat. Check each source's complete stable
                # signature, then cross-check file identity without that field.
                before_id, opened_id = _signature(before), _signature(opened)
                before_id.pop(4)
                opened_id.pop(4)
                if (len(data) > max_bytes or before_id != opened_id
                        or _signature(opened) != _signature(after)
                        or _signature(before) != _signature(final) or len(data) != final.st_size):
                    raise _UnstableInput('hook input changed while being read')
                self._bytes_hashed += len(data)
                self._hash_reads += 1
                return _signature(final), hashlib.sha256(data).hexdigest()
            except (FileNotFoundError, _UnstableInput) as error:
                if attempt:
                    raise ValueError('hook input did not remain stable during its bounded read') from error
        raise ValueError('hook input could not be read')

    def _file(self, relative, max_bytes):
        self._check_open()
        key = self._normalize(relative)
        if not key or type(max_bytes) is not int or not 0 <= max_bytes <= EXPLICIT_FILE_BYTES:
            raise ValueError('invalid exact input or size limit')
        file = self._path(key)
        value = file.lstat()
        if not stat.S_ISREG(value.st_mode) or value.st_size > max_bytes:
            raise ValueError('hook input must be an existing regular file within its size limit')
        signature = _signature(value)
        previous = self._observed.get(key)
        if previous is not None and previous['signature'] == signature:
            return key, previous
        previous = self._state['files'].get(key)
        hinted = any(not hint or key == hint or key.startswith(hint + '/') for hint in self._hints)
        if not self.force and not self._rebuilt and not hinted and previous and previous['signature'] == signature:
            digest = previous['sha256']
            self._reused.add(key)
        else:
            signature, digest = self._read(key, max_bytes)
            self._hashed.add(key)
        entry = {'signature': signature, 'sha256': digest, 'seen': self._state['generation'] + 1}
        self._observed[key] = entry
        return key, entry

    def file(self, relative, max_bytes=EXPLICIT_FILE_BYTES):
        """Hash one regular file, reading bytes in forced snapshots."""
        return self._file(relative, max_bytes)[1]['sha256']

    @staticmethod
    def _tree_key(roots):
        return hashlib.sha256(json.dumps(roots, separators=(',', ':')).encode()).hexdigest()

    def tree(self, roots):
        """Enumerate at most 8 roots / 2000 files / 32 MiB, with 2 MiB files."""
        self._check_open()
        if not isinstance(roots, list) or len(roots) > 8 or any(not isinstance(path, str) for path in roots):
            raise ValueError('inputRoots must list at most 8 workspace-relative directories')
        roots = [self._normalize(path) for path in roots]
        scope = self._tree_key(roots)
        if scope not in self._trees and len(self._trees) >= 32:
            raise ValueError('input snapshot is limited to 32 declared tree scopes')
        files, total = {}, 0
        def walk_error(error):
            raise error
        for relative in roots:
            folder = self._path(relative)
            if not folder.is_dir():
                raise ValueError('inputRoots must be existing directories')
            for current, directories, names in os.walk(folder, followlinks=False, onerror=walk_error):
                self._path(Path(current).relative_to(self.root))
                directories[:] = sorted(name for name in directories if name not in SKIPPED)
                for name in directories:
                    self._path(Path(current, name).relative_to(self.root))
                for name in sorted(names):
                    key = self._normalize(Path(current, name).relative_to(self.root))
                    if key in files:
                        continue
                    if len(files) >= 2000:
                        raise ValueError('inputRoots scan limit reached; narrow the declared scope')
                    key, value = self._file(key, TREE_FILE_BYTES)
                    total += value['signature'][2]
                    if total > TREE_BYTES:
                        raise ValueError('inputRoots scan limit reached; narrow the declared scope')
                    files[key] = value['sha256']
        previous = self._state['trees'].get(scope, {})
        self._deleted.update(set(previous.get('paths', ())) - files.keys())
        self._trees[scope] = {'roots': roots, 'paths': sorted(files), 'seen': self._state['generation'] + 1}
        return files

    def _bounded(self, state):
        state['files'] = dict(sorted(state['files'].items(), key=lambda item: item[1]['seen'], reverse=True)[:MAX_CACHE_FILES])
        state['trees'] = dict(sorted(state['trees'].items(), key=lambda item: item[1]['seen'], reverse=True)[:MAX_CACHE_TREES])
        # Very long names can exhaust the serialized byte bound before counts.
        while len(json.dumps(state, ensure_ascii=False).encode('utf-8')) > MAX_STATE_BYTES:
            for field in ('trees', 'files'):
                entries = state[field]
                if entries:
                    keep = len(entries) * 3 // 4
                    state[field] = dict(list(entries.items())[:keep])
        return state

    def finish(self):
        """Publish a complete observation, return delta/stats, and release lock."""
        if self._finished is not None:
            return dict(self._finished)
        self._check_open()
        try:
            previous = self._state['files']
            old_paths = {path for tree in self._state['trees'].values() for path in tree['paths']}
            added, changed = [], []
            for key, value in self._observed.items():
                if key not in previous and key not in old_paths:
                    added.append(key)
                elif key not in previous or value['sha256'] != previous[key]['sha256']:
                    changed.append(key)
            deleted = self._deleted - self._observed.keys()
            files = {key: value for key, value in previous.items() if key not in deleted}
            files.update(self._observed)
            trees = {**self._state['trees'], **self._trees}
            active = sorted(self._trees)
            state = {**self._state, 'generation': self._state['generation'] + 1,
                     'files': files, 'trees': trees, 'activeTrees': active}
            self._path('.cxd/hooks/input-state.json', missing=True)
            atomic_json(self._state_file, self._bounded(state))
            self._finished = {'mode': 'full' if self.force else 'stat',
                              'cacheRebuilt': self._rebuilt, 'filesObserved': len(self._observed),
                              'filesHashed': len(self._hashed), 'filesReused': len(self._reused - self._hashed),
                              'hashReads': self._hash_reads, 'bytesRead': self._bytes_read,
                              'bytesHashed': self._bytes_hashed, 'added': sorted(added),
                              'changed': sorted(changed), 'deleted': sorted(deleted),
                              'rootsChanged': active != sorted(self._state['activeTrees'])}
            return dict(self._finished)
        finally:
            self.close()
