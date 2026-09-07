---
name: asap
description: Use when the user explicitly wants an actionable task executed immediately without a separate plan proposal or plan-approval checkpoint.
---

# ASAP

Move directly from a sufficiently clear request to execution. Optimize for elapsed time while preserving correctness and authorization boundaries.

## Execute now

1. Identify the concrete outcome and begin the first safe implementation step immediately.
2. Make narrow, reversible assumptions when missing details do not materially change the result. State only assumptions the user needs to evaluate.
3. Combine independent inspections and checks when that reduces waiting time.
4. Implement the complete requested outcome, then verify it in proportion to risk.
5. Report the result, evidence, and any genuinely unfinished item.

## Skip

- A separate planning phase
- Requests for plan approval
- Ceremonial progress narration
- Non-blocking preference questions
- Optional expansion beyond the requested outcome

## Boundaries

ASAP changes pacing, not authority. It does not waive required approval for destructive operations, secret access, spending, publication, deployment, messages to third parties, or other material external effects. It also does not override system instructions, repository rules, safety requirements, or an explicit request to diagnose without fixing.

If a missing choice would materially change the outcome, ask one concise blocking question. If an operation fails, investigate the failure rather than repeatedly retrying or claiming completion.

Do not commit, push, deploy, or open a pull request unless the user's request authorizes that action.
