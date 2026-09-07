---
name: soso
description: Use when the user approves a recent working pattern and wants the useful behavior preserved as a durable repository rule.
---

# So-so

Convert positive feedback into a precise repeatable practice. Preserve what worked without turning a single success into a broad or ceremonial rule.

**REQUIRED SUB-SKILL:** Use `add-repo-rules` to persist the resulting rule.

## Workflow

1. Identify the exact recent behavior the user approved. Use nearby evidence rather than guessing from the entire conversation.
2. State the useful pattern in one sentence and distinguish it from incidental details.
3. Convert it into an affirmative repository rule with a trigger and an observable action.
4. Apply `add-repo-rules` immediately. The explicit command authorizes this repository-instruction edit; do not request duplicate approval.
5. Show the rules diff and briefly name the behavior that will be repeated.

## Good rule shape

Prefer: “When adding several independent commands, validate each command immediately after creation, then run one full validation pass.”

Avoid praise transcripts, vague rules such as “keep doing good work,” preferences that apply only to one person, or accidental details that do not affect the outcome.

## Boundaries

- Add only a pattern supported by the user's feedback and the immediately relevant work.
- Consolidate with a semantically equivalent existing rule instead of duplicating it.
- Do not turn approval into standing permission for commits, pushes, deployments, destructive operations, spending, or external communication.
- If it is unclear which behavior was approved, ask one focused question before editing.
- Leave repository history untouched unless the user separately requests a commit or push.
