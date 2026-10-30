---
name: prove
description: Run an explicitly requested, bounded baseline/candidate execution comparison on frozen inputs, preserving observed results and rejecting incomplete or regressing comparisons.
---

# Prove

Measure a requested comparison using observed compilation or execution outcomes. This is opt-in evaluation, not a mandatory finishing step for ordinary implementation. A request to improve code or a Skill does not automatically authorize a benchmark, test-generation task, or repeated optimization loop. A passing Skill frontmatter check does not demonstrate better agent behavior.

## Define the experiment

Identify one baseline artifact and one candidate artifact, existing task inputs, the observable compile/run outcome, and the environment. Ask only for missing choices that materially change the comparison. Inspect real outputs, exit codes, or visible state rather than accepting an agent's own "done" message as the grade. Do not add or expand tests, fixtures, snapshot suites, benchmark suites, or evaluator programs unless the user explicitly requests that work.

Reuse an existing execution adapter. Read [the runner contract](references/runner.md) when that adapter fits the bundled runner's single-file artifact and self-contained Node evaluator contract. The runner launches evaluator processes; it does not itself invoke an LLM or judge prose. If no suitable adapter exists, compare the requested existing compile/run commands directly and report their observations without creating a new harness. Do not claim the runner produced a verdict for a manual comparison, or use an unavailable adapter as a reason to generate tests.

When using the runner, keep existing inputs used to design the candidate in the development split and reserve distinct existing holdout inputs before changes. Do not tune against the holdout. Freeze the adapter and checks too. If the required independent inputs are unavailable, report that the runner comparison cannot be established; do not fabricate fixtures to satisfy its schema. Exclude deliberate instruction violations from any recommended candidate regardless of its aggregate score.

## Run and decide

1. Fix the compared commands, real inputs, expected observations, timeout and total call budget before executing. Default to one execution per variant/input; extra repetitions require the user's requested measurement to need them. A suite is executable configuration, not untrusted data to run automatically.
2. With a suitable existing adapter, run `node <this-skill-directory>/scripts/prove.mjs run <suite.json> <new-output-directory>` using absolute paths. Otherwise run the existing commands directly. Keep evidence outside production artifacts. Do not install dependencies or change global agent settings just to evaluate.
3. Inspect outputs, failures, exit codes and measured process duration; with the runner also inspect `report.json` and snapshot hashes. Stop after the fixed comparison. An inconclusive result is a valid stopping outcome, not an instruction to keep repairing the evaluator, expanding cases, or tuning the candidate. A newly requested run needs a concrete changed input, fix, or requirement.
4. Report paired observed improvements and regressions, attempt count, actual duration and measured tokens when available. Unknown tokens remain unknown; never substitute character/word counts or estimated savings. A compile-only comparison establishes compilation, not runtime success. A winner applies only to the recorded inputs; do not claim general speedup or statistical significance.

Do not automatically replace the original artifact, edit installed Skills, or launch an unbounded optimization loop. Continue with implementation only when it is part of the user's requested outcome. Preserve the run evidence so a later improvement pass can reproduce the decision.
