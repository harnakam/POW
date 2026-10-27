"""Short workspace commands backed by cached read-only workers and command DAGs."""
import argparse
import json
import math
from pathlib import Path
import re
import sys
import uuid

sys.dont_write_bytecode = True
from resident import inside
from resident_rpc import directories, request, serve, state_info

BUILTINS = {'init', 'aliases', 'serve', 'start', 'status', 'stop', 'index', 'symbols', 'tree', 'plan', 'wait', 'result'}


def configuration(root):
    config = json.loads((root / '.codex-dispatch.json').read_text(encoding='utf-8-sig'))
    if (not isinstance(config, dict) or type(config.get('version')) is not int or config['version'] != 1
            or not isinstance(config.get('source_roots'), list) or not config['source_roots']):
        raise ValueError('unsupported .codex-dispatch.json schema')
    if any(not isinstance(path, str) or not inside(root, path).is_dir()
           for path in config['source_roots']):
        raise ValueError('source roots must be existing workspace directories')
    presets = config.get('presets', {})
    if not isinstance(presets, dict):
        raise ValueError('presets must be an object')
    for name, preset in presets.items():
        if (not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', name)
                or name in BUILTINS):
            raise ValueError('preset names must be lowercase, filename-safe, and not built-in commands')
        if not isinstance(preset, dict) or not isinstance(preset.get('jobs'), list) or not preset['jobs']:
            raise ValueError(f'{name}: preset must contain a nonempty jobs list')
    return config


def prepare_preset(root, name, extra_jobs=()):
    root = Path(root).resolve()
    config = configuration(root)
    preset = config.get('presets', {}).get(name)
    if not isinstance(preset, dict):
        raise ValueError(f'unknown preset {name}; use cxd aliases')
    manifest = json.loads(json.dumps(preset))
    manifest['jobs'].extend(extra_jobs)
    for job in manifest['jobs']:
        if not isinstance(job, dict):
            raise ValueError('each job must be an object')
        if 'argv' in job:
            if not isinstance(job['argv'], list):
                raise ValueError('argv must be a list')
            job['argv'] = [sys.executable if arg == '{python}' else arg for arg in job['argv']]
        cwd = job.get('cwd', '.')
        if not isinstance(cwd, str) or not cwd:
            raise ValueError('cwd must be a nonempty directory path')
        job['cwd'] = str(inside(root, cwd))
    return manifest


def run_prepared(root, manifest, output=None, concurrency=3, emit_events=False):
    from command_actors import run_manifest_sync, validate_manifest
    root = Path(root).resolve()
    output = (root / '.cxd/runs' / uuid.uuid4().hex) if output is None else Path(output)
    output = inside(root, output)
    def read_operation(operation, parameters):
        value = request(root, operation, parameters)
        return value['message'] if operation in {'syntax', 'timing'} else json.dumps(value, ensure_ascii=False)

    handlers = {name: (lambda parameters, op=name: read_operation(op, parameters))
                for name in ('syntax', 'timing', 'index', 'symbols', 'tree')}
    validate_manifest(manifest, concurrency, root, handlers)
    directories(root)
    return run_manifest_sync(manifest, output, concurrency, emit_events=emit_events, handlers=handlers)


def run_preset(root, name, output=None, concurrency=3, emit_events=False, extra_jobs=()):
    return run_prepared(root, prepare_preset(root, name, extra_jobs), output, concurrency, emit_events)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', default='aliases')
    parser.add_argument('argument', nargs='?')
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--concurrency', type=int, default=3)
    parser.add_argument('--events', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--idle-seconds', type=float, default=900)
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--compact', action='store_true')
    parser.add_argument('--attached', action='store_true')
    args = parser.parse_args(argv)
    root = args.workspace.resolve()
    if args.argument is not None and args.command not in {'symbols', 'plan', 'start', 'wait', 'result'}:
        parser.error('this command does not accept a positional argument')
    if not math.isfinite(args.idle_seconds) or args.idle_seconds <= 0:
        parser.error('--idle-seconds must be positive and finite')
    try:
        if args.command == 'init':
            with (root / '.codex-dispatch.json').open('x', encoding='utf-8') as file:
                json.dump({'version': 1, 'source_roots': ['.'], 'presets': {}}, file, indent=2)
            result = {'configured': str(root)}
        elif args.command == 'aliases':
            config = configuration(root)
            result = {'commands': ['init', 'index', 'symbols QUERY', 'tree', 'serve', 'start PRESET', 'plan PRESET', 'wait ID', 'result ID', 'status', 'stop'],
                      'presets': sorted(config.get('presets', {}))}
        elif args.command == 'serve':
            configuration(root)
            serve(root, idle_seconds=args.idle_seconds)
            return 0
        elif args.command == 'plan':
            from command_actors import scheduling_plan
            result = scheduling_plan(prepare_preset(root, args.argument), args.concurrency, root,
                                     dict.fromkeys(('syntax', 'timing', 'index', 'symbols', 'tree')))
        elif args.command == 'start' and args.argument:
            from async_jobs import start
            result = start(root, args.argument, args.concurrency, attached=args.attached)
            if args.compact:
                result.pop('summary', None)
            print(json.dumps(result, ensure_ascii=False))
            return 1 if result['status'] in {'failed', 'interrupted'} else 0
        elif args.command in {'wait', 'result'}:
            from async_jobs import result as read_result, wait
            result = (wait(root, args.argument, args.timeout) if args.command == 'wait'
                      else read_result(root, args.argument))
            if args.compact and 'summary' in result:
                summary = result.pop('summary')
                result.update(elapsed_s=summary['elapsed_s'], jobs={name: {
                    'status': job['status'], 'returncode': job['returncode']}
                    for name, job in summary['jobs'].items()})
            print(json.dumps(result, ensure_ascii=False))
            return 124 if result.get('wait_timed_out') else (1 if result['status'] in {'failed', 'interrupted'} else 0)
        elif args.command in {'start', 'status', 'stop'}:
            result = request(root, 'status' if args.command == 'start' else args.command,
                             start=args.command == 'start')
            if args.command == 'stop' and result.get('running'):
                result = {'stop_requested': True, 'worker_pid': result['worker_pid']}
        elif args.command in {'index', 'symbols', 'tree'}:
            configuration(root)
            result = request(root, args.command, {'query': args.argument or '', 'limit': args.limit})
        else:
            summary = run_preset(root, args.command, output=args.output,
                                 concurrency=args.concurrency, emit_events=args.events)
            result = {'status': summary['status'], 'elapsed_s': summary['elapsed_s'],
                      'jobs': {name: job['status'] for name, job in summary['jobs'].items()},
                      'worker_pid': state_info(root).get('pid'),
                      'result_path': str(Path(next(iter(summary['jobs'].values()))['stdout_path']).parent / 'result.json')}
            operations = {job['id']: job.get('operation')
                          for job in configuration(root)['presets'][args.command]['jobs']}
            result['results'] = {
                name: json.loads(Path(job['stdout_path']).read_text(encoding='utf-8'))
                for name, job in summary['jobs'].items()
                if operations.get(name) in {'index', 'symbols', 'tree'} and job['status'] == 'completed'}
            print(json.dumps(result, ensure_ascii=False))
            return 0 if summary['status'] == 'completed' else 1
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(f'cxd: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
