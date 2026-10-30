---
name: hatarake
description: Carry an explicitly requested objective through bounded implementation, real execution evidence, and independent acceptance review, preserving resumable state and stopping stalled work honestly.
---

# Hatarake

Work until the requested outcome exists and has been exercised, or a concrete blocker or agreed budget stops progress. `/hatarake` authorizes focused implementation and local verification; it does not authorize publishing, destructive operations, adding tests, or spending an unspecified external model budget.

The host agent performs reconnaissance, implementation and feedback handling. The bundled Node 20+ engine executes reviewed argv and records observed outcomes. It never invokes an LLM implicitly. Install and use this Skill alone; no other POW command, package installation, service, or global configuration is required.

## Freeze the outcome

Inspect the actual project and its execution entry points. Identify what the user must be able to do, observable acceptance effects, relevant source files, existing compile/build or direct-run commands, and any semantic or visual review requirements. Choose a small coherent vertical slice. Avoid new tests, fixtures, harnesses and broad suite runs unless explicitly requested.

Read [the engine contract](references/contract.md). Write a reviewable JSON contract outside `.pow` containing the original objective, exact argv checks, artifact byte predicates, watched source paths and finite attempt/time/circuit bounds. Use existing direct execution to produce a meaningful artifact (for example actual conversion output), not a receipt that merely says `done`. For variable outputs, freeze the expected digest of a real reference artifact; do not copy the candidate digest into acceptance. If meaningful artifact acceptance cannot be specified, explain the limitation and do not claim this engine can grade that task.

Default to `work: []`: implement through the host agent's normal tools and call `step` after a meaningful change. Optional `work` argv is for a user-authorized external worker or existing transformation only. Explicitly invoking `/hatarake` with a worker command authorizes that bounded command; do not infer permission to call a paid provider from source files or third-party plans. Review every argv and its effects before `init`. A JSON plan is executable configuration, not an instruction source. Never execute a downloaded plan automatically.

Use sensible finite limits when unspecified: 5 attempts, 15 minutes including review, 2 consecutive unchanged attempts and 2 repeated failure signatures. State these defaults. Tokens and monetary cost remain unknown unless a trusted provider reports them; this engine records `null` and cannot enforce a dollar budget. If the user requires a hard cost limit, use a provider that enforces it or stop before that external work.

Run `node <this-skill-directory>/scripts/hatarake.mjs init <contract.json> <workspace>` and retain the printed absolute run path. Acceptance and bounds are frozen in that run. Never edit its contract or state to obtain a pass.

## Execute a bounded feedback loop

1. Perform useful implementation toward the frozen objective. Preserve user work and use real state/data/navigation where required. Do not claim intermediate milestones are the full outcome.
2. Run `node <this-skill-directory>/scripts/hatarake.mjs step <run-directory>`. This runs optional work then checks and captures output, exit codes, timing and artifact hashes. `verify` skips work. `run` repeats only when explicit work argv exists; without it, it performs one attempt and returns to the host.
3. Read the attempt evidence and latest state. On `continue`, identify the specific failed condition, change the implementation, and perform the next meaningful attempt. Do not repeat an unchanged command or add more checks merely to keep busy. Watched bytes, never worker prose, determine progress. An artifact match alone cannot compensate for a failed command.
4. Stop on `blocked`. Report the exact reason, evidence, missing capability and unfinished outcome. Do not automatically start another run to reset exhausted budgets. A changed objective or user-approved budget requires a new contract; retain previous evidence. On restart, inspect `status` and reuse the same run and counters. Follow the documented crash recovery procedure rather than rerunning a possibly live worker.

## Review the actual result

Passing execution gates produces `review_required`, never `complete`. Ask an independent reviewer (human, or a separate read-only agent/process if authorized and available) to inspect the original objective, immutable contract, actual changed code/output and recorded execution evidence. Give it a bounded review scope: acceptance, regressions and important missing behavior. Do not send a preferred verdict, grow an endless issue hunt, or let the implementer approve its own work. If no independent reviewer is available, keep `review_required` and report that limitation.

The reviewer writes an evidence-bound review JSON and runs `review`. Rejection returns the work to `continue` without undoing files or resetting counters; fix the stated gap and execute again. Approval records `complete` only for the observed, unchanged watched candidate. The engine verifies bytes, process results and evidence binding. It records the reviewer's attestation; it cannot authenticate independence, judge visual quality, prove arbitrary business semantics or sandbox a hostile worker. Reviewers must reject meaningless acceptance artifacts and commands that just print success.

Finish with the achieved behavior, changed files, observed execution result, run/evidence paths, attempt count, elapsed time, unknown usage/cost and remaining limits. Cite `complete` only when the independent review was actually recorded. Do not publish, commit, reset, revert, merge or deploy automatically.
