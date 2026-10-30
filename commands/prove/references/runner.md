# Local comparison runner

Requires Node.js 20+, no packages. It works from an installed Skill folder without the POW checkout. It compares two **single files**, not entire Skill trees or repositories. Reuse a compatible existing evaluator; when the real task needs multiple files, directly execute its existing compile/run commands instead of building a new harness merely to fit this runner. External dependencies and model configuration are not frozen automatically.

Use this runner only for an explicitly requested comparison. Compilation/execution evidence is enough for ordinary implementation; do not add tests or evaluators or run successive suites unless the user requested that work. Default to one repetition and the smallest fixed input set that satisfies the comparison, then stop even if the result is inconclusive. The runner's larger supported limits are capacity bounds, not recommended amounts of verification.

## Suite

Paths resolve relative to the suite file. Both splits are required. Each case must have unique input (object key order is normalized), a unique ID, and at least one named check.

```json
{
  "version": 1,
  "name": "parser boundary cases",
  "environment": "Node 22 on Windows; deterministic evaluator; no model",
  "evaluator": "evaluate.mjs",
  "baseline": "baseline.mjs",
  "candidate": "candidate.mjs",
  "repetitions": 1,
  "timeoutMs": 10000,
  "maxCalls": 4,
  "cases": [
    {"id": "ordinary", "split": "development", "input": {"text": "1,2"}, "checks": ["values"]},
    {"id": "empty", "split": "holdout", "input": {"text": ""}, "checks": ["values"]}
  ]
}
```

This illustrates the schema; select an existing evaluator and artifacts for the actual task. An executable controlled example lives in the POW checkout at `examples/prove/`. A request to run a comparison is not automatically a request to create new evaluation programs or fixtures.

## Evaluator protocol

The runner starts `node evaluator.mjs` with shell disabled in a fresh run directory. The evaluator must be self-contained: it is copied to a snapshot directory, so relative imports of undeclared helper files will not work. Read one JSON object from stdin:

```json
{"version":1,"artifact":"absolute path to the selected snapshot","input":{"text":"1,2"}}
```

Write one JSON object to stdout and diagnostics to stderr. Return every declared check exactly once. `passed` must be boolean and `evidence` must be a nonempty description of the actual observation. Optional `tokens` is a measured nonnegative integer or null; never put characters in this field.

```json
{"checks":[{"id":"values","passed":true,"evidence":"Actual parsed array [1,2] matches expected [1,2]"}],"tokens":null}
```

The evaluator owns semantic correctness. The runner validates shape and evidence presence, not whether its prose is true. For agent evaluation, inspect generated artifacts independently; do not let the candidate write its own verdict. Record exact model/settings in the environment description and have the evaluator verify them when possible. The environment field is a declaration, not runtime model detection.

## Execution and results

- Planned calls are `cases × repetitions × 2`; reject an insufficient budget before executing. Repetition is 1..20; maxCalls is 2..1000. No implicit paid model calls are made by the runner itself.
- Baseline and candidate order alternates across cases/repetitions. Each call has an empty cwd. The selected artifact, evaluator, and suite have recorded SHA-256 hashes. Artifact snapshots are checked after each call.
- Unknown tokens are null. Measured duration is evaluator-process wall time, including startup and checks; it is not automatically model inference latency. Duration does not select the winner.
- Timeout, nonzero exit, malformed JSON, missing/duplicate checks, missing evidence, output over 1 MiB (stdout + stderr), or snapshot mutation makes the comparison inconclusive and stops further calls. Remaining missing pairs stay invalid.
- `candidate-better-on-suite` requires a holdout improvement and no regressing check in either split. A development-only gain or tie is `no-demonstrated-improvement`. Any regressing check returns `regression`. No statistical significance is inferred.
- Exit codes: 0 = valid comparison (including a tie); 1 = invalid configuration or harness failure; 2 = inconclusive comparison or regression. Read the verdict, not just the exit code.
- `manifest.json` stores identity; `suite.json` and `snapshots/` freeze inputs; `run-NNNN/` holds stdout, stderr and structured results; `report.json` holds the aggregate. Existing output directories are rejected. Partial directories from interrupted/harness failures are retained and never treated as a completed run.

## Process and trust boundary

Only run reviewed evaluators. Separate directories are not a security sandbox: an evaluator inherits the launching process's permissions and environment and can access sibling files, including both artifacts and holdout inputs. Keep holdout selection separate from candidate authoring; use an external sandbox for hostile candidates. Do not put credentials or private conversations in a suite or commit its logs.

On timeout or interruption, the runner attempts to stop the process tree (Windows taskkill or POSIX process-group signal). A second deadline prevents indefinite pipe waits. If cleanup cannot be confirmed, the run records the PID for inspection and is inconclusive; clean up that process before retrying. This runner does not provide Windows Job Object containment.
