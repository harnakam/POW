# Hatarake engine contract (version 1)

Run with Node 20+ using the absolute installed `scripts/hatarake.mjs` path. All inputs and outputs are UTF-8 JSON. Unknown fields are rejected. No dependency installation is needed.

```json
{
  "version": 1,
  "objective": "Convert the existing input.txt to the required uppercase output.txt",
  "limits": {
    "maxAttempts": 5,
    "maxWallMs": 900000,
    "maxNoChange": 2,
    "maxRepeatedFailure": 2
  },
  "work": [],
  "checks": [
    {"id": "convert", "argv": ["node", "convert.mjs", "input.txt", "output.txt"], "timeoutMs": 10000}
  ],
  "effects": [{"path": "output.txt", "exactText": "HELLO\n"}],
  "watch": ["convert.mjs", "input.txt"]
}
```

This illustrates a real direct-run contract, not a file to execute blindly. Use the project's actual commands and inputs. `checks` must contain at least one real compile/build/run command; `effects` must contain at least one regular file with exactly one `exactText` or lowercase SHA-256 `sha256`. Existence alone, stdout completion promises and exit zero alone never pass. Inputs/source needed to interpret execution belong in `watch`, including compiler configuration and relevant dependencies. Artifact paths automatically join the progress fingerprint. A missing file is recorded as null; directories, symlinks, paths outside the workspace, `.pow` evidence and files over 8 MiB are refused. Exact text is limited to 1 MiB. Paths are relative to the canonical workspace; watch up to 100 explicit files and up to 100 effects. For a task without a stable meaningful artifact, this gate cannot establish acceptance; retain human review instead of fabricating evidence.

`work` and `checks` contain unique IDs, string argv and per-command `timeoutMs` (50..300000). At most 30 total commands. Execution uses `shell:false`, inherited environment, workspace cwd, closed stdin, hidden Windows windows and no interpolation. An executable may itself be a shell, script, compiler or paid AI client: review its semantics and permissions. Prefer absolute executable paths for repeatability. Windows `.cmd` launchers need an explicitly reviewed shell argv or their underlying JavaScript entry point; do not silently enable shell execution. The engine is not a sandbox or command allowlist and inherits the caller's privileges.

Limits: `maxAttempts` 1..100, `maxWallMs` 100..86400000, circuit thresholds 1..100. Wall time starts at init, includes idle time/review and survives restarts. Each verification consumes one attempt before executing. Commands run sequentially; the first failure stops the attempt. Timeout and 1 MiB combined stdout/stderr limits terminate the child process tree where supported, with a 2-second cleanup grace. Unconfirmed cleanup blocks the run; inspect the recorded PID. Escaped/detached grandchildren and external side effects cannot be reliably revoked. Never use this engine to supervise untrusted code or commands whose effects require rollback.

Progress hashes observed watched/artifact bytes, not git status, output length or agent claims. Repeated-failure hashes command IDs, exits/signals/errors/stderr and failing effect identities; timings and success prose do not reset it. Hard attempt/time limits still apply if diagnostics vary. Output may contain sensitive data: use local ignored state, redact secrets at source, and do not upload logs automatically.

## CLI

```text
node /absolute/skill/scripts/hatarake.mjs init /absolute/contract.json /workspace
node /absolute/skill/scripts/hatarake.mjs status /workspace/.pow/hatarake/<id>
node /absolute/skill/scripts/hatarake.mjs step /workspace/.pow/hatarake/<id>
node /absolute/skill/scripts/hatarake.mjs verify /workspace/.pow/hatarake/<id>
node /absolute/skill/scripts/hatarake.mjs run /workspace/.pow/hatarake/<id>
node /absolute/skill/scripts/hatarake.mjs review-package /workspace/.pow/hatarake/<id>
node /absolute/skill/scripts/hatarake.mjs review /workspace/.pow/hatarake/<id> /absolute/review.json
node /absolute/skill/scripts/hatarake.mjs recover /workspace/.pow/hatarake/<id> /absolute/recovery.json
```

`step` executes optional work then checks once. `verify` skips work and explicitly invalidates an old passing/approved candidate before another attempt. `run` repeats within limits only when work argv exists; with host-managed work it returns after one attempt. Exit codes: 0 initialized/help or complete, 1 invalid command/configuration/state, 2 blocked, 3 continue/running/review_required. `status` returns persisted status as of the recorded evidence, not a fresh execution or liveness assertion. Use `verify` after changes. No git commands run automatically.

Run files live at `.pow/hatarake/<uuid>/`: frozen `contract.json`, atomic `state.json`, exclusive `lock.json` while operating, `active-process.json` with the last launched PID/argv, and immutable-by-convention `attempt-N.json`. State includes contract/evidence SHA-256, attempt counters, fingerprint, reason, deadline, reviews, and `tokens:null`, `cost:null`. Keep `.pow/` out of commits. Hashes detect ordinary contract/evidence drift, not adversarial edits by a process with the same filesystem privileges. Include relevant source in `watch`; unobserved source/environment changes are outside the approval binding.

## Independent review

`review-package <run-directory>` emits a neutral JSON capsule for a fresh reviewer without executing commands or consuming an attempt. It uses the same evidence identity and current-file snapshot checks as approval. A temporary exclusive run lock prevents packaging a concurrent engine attempt; no contract, state or evidence file is modified. Exporting the capsule does not grant authority, request an LLM call, or imply acceptance. The capsule includes the original objective, frozen contract summary and mandatory full-contract locator, absolute file locators with JSON pointers, latest real argv/outcomes/effects, recorded/current watched hashes, execution identity and deadline freshness. It deliberately excludes prior review conclusions and the implementer's preferred verdict.

The serialized capsule is capped at 64 KiB. `contract.summary` preserves objective, limits, IDs, argv and watched paths; artifact `exactText` bodies are replaced by expected SHA-256 and original `/effects/N` locators. If that summary exceeds 24 KiB, export fails with `Review brief too large` rather than truncating goal or constraints. Execution stdout, stderr and error text use `{bytes, excerpt, excerptBytes, truncated, source}` with at most 256 UTF-8 bytes per field and an 8 KiB shared excerpt budget. The original evidence field remains available at its file/JSON pointer, including text omitted after budget exhaustion. `limits` reports the caps and actual excerpt bytes. Large paths or remaining metadata that exceed the final cap also fail explicitly; read the underlying contract/evidence directly in bounded portions. A truncated excerpt never means the original output was empty or that a reviewer inspected its omitted portion.

Coverage retains the denominator: each check is `passed`, `failed`, or `unknown` (no recorded execution). Effects distinguish failed observations from no observation. Current watched files distinguish readable, missing, and unknown; if a snapshot fails, all current file observations conservatively become unknown and `candidate.observationError` explains why. Old outcomes remain labeled by their evidence attempt; `freshness.sameAttempt:false` identifies a newer interrupted attempt. Semantic/visual correctness, unobserved files/environment, reviewer independence and provider usage are explicitly unknown. A failed command is not a missing observation, and a readable source locator does not establish that a reviewer read it. No aggregate quality score is generated.

Send this capsule and accessible source/output locators to the independent reviewer. Its `reviewInput` contains null decision/identity/rationale slots as a schema reminder, not a valid verdict or an approval template. The reviewer must inspect real files and fill an explicit `approve` or `reject` decision, nonempty identity/rationale and the exact evidenceHash. Neither `"false"`, a boolean nor an unknown value is a verdict. The capsule is a point-in-time view; approval independently rechecks evidence identity, strict verdict types, actual passing checks/effects, candidate hashes and deadline. File changes or missing current execution require fresh verification; exporting another capsule never refreshes execution evidence. Existing review JSON remains compatible.

```json
{
  "decision": "reject",
  "reviewer": "human:alice",
  "rationale": "The runtime output matches, but the CLI drops a required error branch.",
  "evidenceHash": "copy the state evidenceHash being reviewed"
}
```

Use `approve` only after independent review of the real objective and candidate. Approval requires passing execution, unchanged recorded evidence, unchanged watched/artifact hashes and an unexpired wall budget. Rejection is allowed even after approval and returns to `continue`; previous reviews remain in state. Neither decision resets budgets. A new execution is required before approval after rejection. Reviewer identity is an attestation supplied by the caller; the engine cannot prove the reviewer is a different person/model, or prevent a privileged caller forging local state. Do not present this as a security boundary. The host workflow must preserve independence. No review verdict is inferred from worker output.

## Restart and crash recovery

Normal `continue` resumes with the same `step` command and retained counters. `review_required` resumes with review. `complete` is historical; rerun `verify` for a changed candidate. `blocked` never resets automatically.

If killed during execution, state stays `running` and the lock remains. Inspect `lock.json`, `active-process.json`, OS process ownership/start time and the workspace before doing anything; PIDs can be reused. Stop the original parent and its process tree yourself if required. Only after confirming neither owner nor worker remains active, remove that specific stale `lock.json` (preserve all other evidence). Supply recovery JSON `{"processesStopped":true,"reason":"describe process inspection and cleanup"}` to `recover`. Recovery consumes the interrupted attempt already counted, retains the original deadline and circuit counters, and resumes only if budget remains. It does not automatically kill a guessed PID or re-run a possibly live command. Inspect actual effects and perform a fresh verification. If cleanup is uncertain, leave the run blocked and report it. A disk failure/corrupt state requires manual inspection; the engine never discards evidence or reconstructs a success.
