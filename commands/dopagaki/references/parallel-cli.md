# Parallel implementation with Codex CLI

Use this workflow for substantial Dopagaki implementation requests with independent work. The parent stays responsible until the integrated outcome is exercised and reviewed.

## Split around dependencies

1. Inspect repository instructions, current changes, entry points, contracts, and existing compile/run commands. Define the requested completion criteria, expected observations, finite command timeouts, and verification stopping point before splitting work.
2. Create the persistent ledger with the bundled `scripts/tasks.mjs` CLI described below. Record objective, dependencies, owned files, acceptance checks, workspace, worker identity, and status. Keep actual process/session IDs with the worker logs. Do not commit orchestration logs by default.
3. Establish shared schemas, interfaces, and common scaffolding in the parent first. Dispatch only dependency-ready tasks. Give shared files, package manifests, lockfiles, migrations, and global configuration one owner at a time.
4. Start with two independent workers, increasing only when more independent work and available capacity justify it. The parent handles another useful independent part or integration preparation. Workers must not recursively delegate.

## Preflight and isolate

- Check `codex --help` and `codex exec --help` on the installed CLI before choosing flags. Use the configured model and reasoning settings unless the user requests an override. Do not install tools or change account configuration as an implicit part of dispatch.
- Give each writer a separate worktree or isolated checkout and an explicit absolute working directory. Record the common base revision. Prefer explicitly prepared workspaces so the parent knows where to inspect and recover changes.
- A worktree at HEAD does not contain uncommitted work. If tasks depend on local changes, reproduce the relevant tracked and untracked working state in their isolated workspaces, verify it, and record that baseline. Never stash, reset, discard, or commit the user's work just to enable parallelism. If a reliable baseline cannot be prepared, keep dependent work local.
- Workspace isolation must fit the current filesystem permissions. Workers must have no broader effective authority than the parent. Keep sandboxing, approval rules, repository instructions, and hook trust intact; never use bypass, ignore-rules, or ignore-user-config switches to make a blocked worker run.

## Give each worker a complete assignment

CLI workers do not automatically inherit this conversation. Send a self-contained brief containing:

- The user's objective, relevant constraints, acceptance criteria, and the specific assigned outcome.
- The workspace and baseline, files it owns, files it must not edit, and contracts with other tasks.
- Relevant repository instructions and any instructions outside the isolated checkout that still apply.
- The smallest existing compile/run command appropriate to its work, its expected observation and finite timeout. Do not add or expand tests, fixtures, snapshots, benchmarks, or verification harnesses unless the user explicitly requests them; do not routinely invoke a broad test suite.
- A requirement to implement and verify, then report changed files, check results, and unresolved issues. A prose claim alone is not proof of completion.
- No recursive workers, commits, pushes, deployments, or external messages unless separately authorized for that task. Stop and report a cross-task dependency or required approval instead of changing another worker's files.
- Stop verification on success. Retry only the affected command after a relevant edit or a newly observed failure; do not repeat unchanged failures or successful checks for reassurance. Preserve existing tests and required build controls. Report a persistent blocker instead of growing the validation scope.

Write the brief as a UTF-8 file and pass its contents through stdin. Do not interpolate arbitrary task text into a shell command. Select a shell-safe invocation using the locally verified options. The basic invocation shape is:

```text
codex exec -C <absolute-worker-workspace> --sandbox workspace-write --json -o <absolute-result-file> -
```

The angle-bracket values denote actual paths selected by the parent; the final `-` reads the brief from stdin. Use a more restrictive sandbox when the parent requires it, and only use an approval configuration compatible with the current session. Capture stdout JSONL, stderr, process ID, exit status, and the final result separately for each worker. Store outputs inside an authorized task directory. Keep prompt text and logs out of public artifacts.

Launch independent processes concurrently using the available process/session tools, not sequential blocking shell calls. When using PowerShell `Start-Process`, use `-WindowStyle Hidden`, file-based stdin/output redirection, and correctly quoted paths. Preserve process handles so workers can be supervised and stopped.

## Supervise and integrate

1. Watch process status and meaningful output while continuing useful parent work. Avoid busy polling and repeated unchanged updates. Record real session IDs from CLI output when available; never guess an ID or resume `--last` among concurrent workers.
2. An authentication, quota, network, or approval failure is a blocker for that worker. Do not bypass it or start a retry storm. Inspect partial changes, stop the failed/stalled process before reassigning its work, and continue unaffected tasks locally when possible. If CLI execution is unavailable, state the limitation briefly and use direct implementation rather than claiming parallel execution occurred.
3. When a worker exits, inspect its actual diff against its recorded baseline, including new files and file deletions, and read its verification evidence. Check for out-of-scope edits and fake or incomplete wiring. Exit code zero is necessary process evidence, not sufficient product evidence.
4. Integrate one finished task at a time in dependency order. Apply only its intended delta; do not copy whole workspaces or overwrite unrelated user changes. Resolve conflicts against the shared contracts. Do not require worker commits to transfer a change.
5. Compile/build or directly execute the integrated flow once, as needed to cover the combined changes. Reuse current worker evidence for unchanged portions rather than replaying every command. Fix observed integration failures and rerun only the affected operation after a relevant change; stop when it succeeds. If execution is unavailable, state what compiled and what remains unexercised.
6. On cancellation or changed scope, stop affected workers and preserve their partial work for review. Before ending the task, account for every process and pending task. Remove only task-owned temporary workspaces when their changes are safely integrated or explicitly disposable; preserve failed work and explain any cleanup left pending.

Report the shipped result, integrated verification, and any remaining blocker. Do not end with only a task breakdown, launched processes, or worker summaries. Parallel execution can reduce elapsed time; it does not guarantee a speedup and may increase total token usage.

## Executable work ledger

Use Node.js 20+ and the absolute path of this installed skill's `scripts/tasks.mjs`. The examples below use `<cli>` for that path. Create a task-local directory first, then write `plan.json` as UTF-8:

```json
{
  "goal": "Implement the requested API and its consumer",
  "baseline": "actual base commit SHA and location of any uncommitted baseline snapshot",
  "tasks": [
    {
      "id": "api",
      "objective": "Implement the agreed API contract",
      "dependsOn": [],
      "owns": ["src/api"],
      "acceptance": ["Run the existing API entry point once and observe the required authorized result"]
    },
    {
      "id": "consumer",
      "objective": "Wire the UI to the verified API",
      "dependsOn": ["api"],
      "owns": ["src/ui"],
      "acceptance": ["Run the connected UI flow once; inspect loading and failure handling in the code"]
    }
  ]
}
```

Replace illustrative paths and criteria with the real repository's. Use literal repository-relative ownership paths, no globs, traversal, absolute paths, or symlink aliases. Declare a shared directory under its canonical repository path. Paths compare case-insensitively on every platform so plans remain portable to Windows.

```text
node <cli> init <ledger.json> <plan.json>
node <cli> status <ledger.json>
node <cli> start <ledger.json> api <absolute-worker-workspace> worker-api
node <cli> finish <ledger.json> api <evidence.json>
node <cli> block <ledger.json> consumer "Required credential unavailable; worker stopped"
node <cli> retry <ledger.json> consumer
node <cli> add <ledger.json> <additional-tasks.json>
```

`additional-tasks.json` is an array of task contracts, with the same five fields as plan tasks. Input statuses/evidence are rejected. New tasks can reference each other; unknown dependencies and cycles reject the entire addition. `status` returns the state plus `ready`, excluding tasks whose dependencies are unfinished or whose ownership overlaps a running task.

Reserve a task with `start` before launching its writer. The final argument is an assigned worker identity, not an invented process ID. Capture the actual process/session ID separately after launch. If launch fails, stop any partial process and `block` with its failure reason. Before `block` or `retry` on a previously running task, confirm that its writer has stopped; these commands do not terminate processes. Pending tasks cannot finish. Completed tasks cannot be reopened; add a new corrective task if needed.

The parent calls `finish` only after checking the actual diff, integrating the intended delta, and passing the relevant checks. `evidence.json` contains:

```json
{
  "integration": "Describe the reviewed and integrated delta and the acceptance criteria exercised",
  "checks": [
    { "command": "actual repository check command", "exitCode": 0, "artifact": "api-check.log" }
  ]
}
```

Artifact paths resolve relative to the ledger directory. Each must be an existing nonempty file; `finish` records its absolute path, byte length, and SHA-256. The command records reported checks and fingerprints their logs; it does not execute tests, interpret logs, prove that the recorded exit code is truthful, or check edits outside declared ownership. The parent verifies those facts. `done` releases dependent tasks; do not finish on worker self-report alone.

Mutations acquire `<ledger>.lock` and replace the JSON atomically. Concurrent mutation fails explicitly; reread `status` before retrying. A crashed process can leave a lock containing its PID and timestamp. Inspect that specific process and the ledger, preserve partial logs, then remove only its stale lock after confirming no writer remains. Never auto-expire locks. Interrupted writes may also leave a uniquely named `.tmp` beside the ledger; preserve it for inspection. No command deletes a workspace or launches a process.
