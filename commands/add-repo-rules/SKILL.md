---
name: add-repo-rules
description: Use when the user wants a durable repository-specific instruction added, clarified, or consolidated for future Codex work in that repository.
---

# Add repository rules

Turn a concrete working agreement into a durable, scoped repository instruction. Repository rules are a POW concept; store them where Codex will actually discover them.

## Workflow

1. Confirm the current workspace is inside the intended repository and determine its root. Never write rules to an unrelated parent directory or global Codex configuration.
2. Use the user's explicit invocation as authorization to edit repository instructions. If no rule was supplied, ask for it in one question.
3. Find the applicable `AGENTS.md`, starting in the working directory and walking toward the repository root. Respect the nearest file that governs the affected scope. If none exists, create `AGENTS.md` at the repository root.
4. Convert the request into one concise imperative rule with an observable trigger or outcome. Preserve meaningful wording from the user.
5. Search existing instructions for semantic duplicates and conflicts. Strengthen or consolidate an existing rule instead of appending repetition.
6. Make the smallest edit under a `## Repository rules` section while preserving unrelated content and formatting.
7. Show the resulting `git diff` for the instruction file. Do not stage, commit, or push.

## Rule quality

A useful repository rule states when it applies and what future work must do. Keep project-specific facts here; do not copy general coding advice or temporary task notes into permanent instructions.

Do not add a rule that conflicts with higher-priority instructions, weakens security or verification, exposes secrets, or grants standing authority for destructive or external actions. Explain the conflict instead. If the repository has no trustworthy root or the target file is outside the writable workspace, stop before editing.

## Output

Report the target file, the exact rule added or changed, and whether a duplicate was consolidated. Include the diff and leave repository history untouched.
