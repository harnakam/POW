"""Bundle only the fixed, reviewed local scheduler modules for functions.exec.

This intentionally is not a general JavaScript bundler. Fail closed when the
known module declarations change. Never pass user input or tool output as source.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
MODULES = (
    ("scheduler.mjs", "import { performance } from 'node:perf_hooks';", "runJobs"),
    ("tasks.mjs", "import { runJobs } from './scheduler.mjs';", "runTasks"),
    ("router.mjs", "import { runJobs } from './scheduler.mjs';", "runToolTasks"),
)


def build_source():
    parts = ['"use strict";', "const performance = { now: () => Date.now() };"]
    for filename, expected_import, function_name in MODULES:
        source = (ROOT / filename).read_text(encoding="utf-8")
        lines = source.splitlines(keepends=True)
        if not lines or lines[0].rstrip("\r\n") != expected_import:
            raise ValueError(f"{filename}: unexpected leading import")
        source = "".join(lines[1:])
        expected_export = f"export async function {function_name}("
        if source.count(expected_export) != 1:
            raise ValueError(f"{filename}: expected exactly one known export")
        source = source.replace(expected_export, f"async function {function_name}(", 1)
        # Deliberately conservative: even new import/export words in comments
        # require review rather than silently broadening this fixed-source build.
        if re.search(r"\b(?:import|export)\b", source):
            raise ValueError(f"{filename}: unexpected import/export token")
        parts.append(f"// Source: {filename}\n{source.rstrip()}")
    parts.append("return { runJobs, runTasks, runToolTasks };")
    return "\n\n".join(parts) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', action='store_true', help='export verified local source and task fixture without writing files')
    parser.add_argument('--workspace', type=Path, default=Path.cwd() / 'examples/scheduler-tasks',
                        help='directory containing the published verification projects')
    args = parser.parse_args(argv)
    source = build_source()
    payload = source.encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    if args.export:
        tasks = json.loads((ROOT / 'real-tasks.json').read_text(encoding='utf-8'))
        workspace = args.workspace.resolve()
        for task in tasks:
            folder = (workspace / task.pop('directory')).resolve()
            if not folder.is_relative_to(workspace) or not folder.is_dir():
                parser.error('verification project must exist inside --workspace')
            task['arguments']['workdir'] = str(folder)
            if os.name != 'nt':
                task['arguments']['cmd'] = task['arguments']['cmd'].replace('python ', 'python3 ', 1)
            task['source_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted(folder.glob('*.py'))}
        print(json.dumps({'bundle': {'sha256': digest, 'source': source}, 'tasks': tasks}))
        return
    (ROOT / "runtime.bundle.js").write_bytes(payload)
    (ROOT / "runtime-bundle.json").write_text(
        json.dumps({"sha256": digest, "source": source}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"sha256": digest, "bytes": len(payload)}))


if __name__ == "__main__":
    main()
