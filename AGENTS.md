# Repository instructions

## Repository rules

- When a repository change request explicitly includes delivery through commit and push, do not stop after editing: run relevant verification, commit only the scoped changes, push the current branch, and report the commit and remote status.
- When optimizing Codex task latency, inspect and reuse existing command and measurement entry points before adding tooling; keep simple tasks in the parent, parallelize only independent work whose coordination cost is justified, preserve verification, and report comparable timing boundaries. Use [the latency procedure](commands/optimize-latency/references/workflow.md) for this work rather than loading measurement guidance for every task.

## Verification scope

- Verify with compilation/build or direct execution of the changed behavior. For Skill text changes, run the existing `node scripts/pow.mjs validate` command and inspect the edited instructions.
- Do not add or expand tests, fixtures, snapshot suites, benchmark suites, or verification harnesses unless the user explicitly requests that work. Do not routinely invoke `npm test` or broaden verification after a successful command.
- Stop verification on success. Retry only after a relevant change or a concrete new failure; preserve failure evidence and report persistent blockers instead of repeating unchanged attempts. Do not delete existing tests, disable checks, or hide failures. Report compilation-only results as such.
