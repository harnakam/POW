"""Workspace-local, read-only operations cached in one resident interpreter."""
import ast
import hashlib
import json
import math
import os
import uuid
from pathlib import Path
import threading


def inside(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('path must stay inside the workspace')
    return path


def atomic_json(path, data):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class ProjectIndex:
    def __init__(self, root, cache):
        self.root, self.cache = Path(root).resolve(), Path(cache)
        self.lock = threading.Lock()
        self.parsed = 0
        try:
            self.entries = json.loads(self.cache.read_text(encoding='utf-8'))['files']
        except (OSError, ValueError, KeyError):
            self.entries = {}

    def refresh(self, roots):
        files = set()
        for relative in roots:
            directory = inside(self.root, relative)
            for path in directory.rglob('*.py'):
                if any(part in {'.git', '.cxd', '__pycache__', '.venv', 'node_modules'}
                       for part in path.relative_to(self.root).parts):
                    continue
                files.add(inside(self.root, path))
        fresh, reused = {}, 0
        for path in sorted(files):
            key = path.relative_to(self.root).as_posix()
            source = path.read_bytes()
            digest = hashlib.sha256(source).hexdigest()
            previous = self.entries.get(key)
            if previous and previous['sha256'] == digest:
                fresh[key] = previous
                reused += 1
                continue
            entry = {'sha256': digest, 'symbols': [], 'imports': [], 'error': None}
            try:
                tree = ast.parse(source, filename=key)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        entry['symbols'].append({'name': node.name, 'line': node.lineno,
                            'end_line': node.end_lineno, 'kind': type(node).__name__})
                    elif isinstance(node, ast.Import):
                        entry['imports'].extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        entry['imports'].append('.' * node.level + (node.module or ''))
            except SyntaxError as error:
                entry['error'] = {'message': error.msg, 'line': error.lineno}
            self.parsed += 1
            fresh[key] = entry
        changed = fresh != self.entries
        self.entries = fresh
        if changed or not self.cache.exists():
            atomic_json(self.cache, {'version': 1, 'files': fresh})
        return {'files': len(fresh), 'reused_files': reused, 'parsed_total': self.parsed}

    def operate(self, operation, parameters, roots):
        with self.lock:
            stats = self.refresh(roots)
            if operation == 'index':
                return stats
            if operation == 'symbols':
                query = parameters.get('query', '').casefold()
                limit = parameters.get('limit', 20)
                if type(limit) is not int or not 1 <= limit <= 200:
                    raise ValueError('limit must be 1..200')
                matches = [dict(path=path, **symbol) for path, entry in self.entries.items()
                           for symbol in entry['symbols'] if query in symbol['name'].casefold()]
                return {**stats, 'total': len(matches), 'matches': matches[:limit],
                        'truncated': len(matches) > limit}
            if operation == 'tree':
                limit = parameters.get('limit', 20)
                if type(limit) is not int or not 1 <= limit <= 200:
                    raise ValueError('limit must be 1..200')
                paths = sorted(self.entries)
                return {**stats, 'paths': paths[:limit], 'truncated': len(paths) > limit}
            paths = parameters.get('paths')
            if not isinstance(paths, list) or not paths:
                raise ValueError('syntax requires paths')
            errors = []
            for relative in paths:
                key = inside(self.root, relative).relative_to(self.root).as_posix()
                if key not in self.entries:
                    raise ValueError('syntax path is outside configured source roots')
                if self.entries[key]['error']:
                    errors.append(dict(path=key, **self.entries[key]['error']))
            if errors:
                raise ValueError(json.dumps(errors, ensure_ascii=False))
            return {**stats, 'message': f'syntax: {len(paths)} Python files parsed'}


def verify_timing(path):
    """Validate a generic duration artifact without assuming a particular experiment."""
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    def duration(value):
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('durations must be finite nonnegative numbers')
        return value
    total = duration(data['total_s'])
    categories = data.get('exclusive_categories_s')
    if categories is not None:
        if not isinstance(categories, dict):
            raise ValueError('exclusive_categories_s must be an object')
        measured = sum(duration(value) for value in categories.values())
        if not math.isclose(measured, total, rel_tol=1e-9, abs_tol=.001):
            raise ValueError('exclusive_categories_s must sum to total_s')
    return {'message': 'timing JSON: finite durations and optional exclusive arithmetic valid',
            'total_s': total}
