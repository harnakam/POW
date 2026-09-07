---
name: multi-codex
description: Use when the user explicitly wants independent work items handled in separate Codex Main tasks that inherit the current conversation context.
---

# Multi Codex

Split independent work into separate user-visible Codex Main tasks while preserving the conversation up to the invocation point.

## Workflow

1. Treat the explicit invocation as authorization to create the requested tasks. Do not pause for a decomposition plan approval.
2. Parse the instruction into independent work items. Preserve each requested name, such as `rank01`, when it is usable as a task title.
3. Create one fork of the current Codex task per independent item with the Codex thread-management capability that preserves conversation context.
4. Give each fork one self-contained objective and the relevant division of responsibility. Do not make one fork coordinate another.
5. Leave the current task open as the coordinator and report links or identifiers for every created Main task.

## Boundaries

- Create Main tasks, not subagents. Never use collaboration or subagent delegation tools for this command.
- Do not replace a context-preserving fork with a fresh context. If the required fork capability is unavailable, stop and explain that the same-context guarantee cannot be met.
- Do not split tightly coupled sequential steps. Keep them in one task, or state why they cannot safely run independently.
- Task creation does not authorize commits, pushes, deployments, purchases, destructive changes, or other side effects inside the new tasks.
- If the instruction contains no separable work items, keep the work in the current task and say so.

## Output

Return a compact mapping from each work item to its new Main task. Do not wait for those tasks unless the user also asks for coordination or monitoring.
