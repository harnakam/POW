"""A small JSON-backed TODO CLI using only the Python standard library."""
import argparse
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, default=Path('tasks.json'))
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('add')
    add.add_argument('title')
    commands.add_parser('list')
    done = commands.add_parser('done')
    done.add_argument('id', type=int)
    args = parser.parse_args(argv)
    try:
        tasks = json.loads(args.file.read_text(encoding='utf-8')) if args.file.exists() else []
        if not isinstance(tasks, list) or any(
            not isinstance(t, dict) or type(t.get('id')) is not int
            or not isinstance(t.get('title'), str) or type(t.get('done')) is not bool
            for t in tasks
        ):
            raise ValueError('invalid task data')
        if args.command == 'list':
            for task in tasks:
                print(f"{task['id']} [{'x' if task['done'] else ' '}] {task['title']}")
            return
        if args.command == 'add':
            if not args.title.strip():
                parser.error('title must not be blank')
            task = {'id': max((t['id'] for t in tasks), default=0) + 1,
                    'title': args.title.strip(), 'done': False}
            tasks.append(task)
        else:
            task = next((t for t in tasks if t['id'] == args.id), None)
            if task is None:
                parser.error('task ID does not exist')
            task['done'] = True
        args.file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(task['id'])
    except (OSError, ValueError) as error:
        parser.exit(1, f'error: {error}\n')


if __name__ == '__main__':
    main()
