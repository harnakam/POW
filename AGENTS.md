# Repository instructions

## Repository rules

- When a repository change request explicitly includes delivery through commit and push, do not stop after editing: run relevant verification, commit only the scoped changes, push the current branch, and report the commit and remote status.

## Verification scope

- Verify with compilation/build or direct execution of the changed behavior. For Skill text changes, run the existing `node scripts/pow.mjs validate` command and inspect the edited instructions.
- Do not add or expand tests, fixtures, snapshot suites, benchmark suites, or verification harnesses unless the user explicitly requests that work. Do not routinely invoke `npm test` or broaden verification after a successful command.
- Stop verification on success. Retry only after a relevant change or a concrete new failure; preserve failure evidence and report persistent blockers instead of repeating unchanged attempts. Do not delete existing tests, disable checks, or hide failures. Report compilation-only results as such.
