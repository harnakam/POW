---
name: fuck-off
description: Use when the user explicitly rejects the AI's behavior and wants the failure analyzed and converted into a durable repository rule.
---

# Fuck off

Treat sharp negative feedback as a demand for concrete correction, not performative apology. Find the failure, repair the working rule, and make recurrence less likely.

**REQUIRED SUB-SKILL:** Use `add-repo-rules` to persist the resulting rule.

## Workflow

1. Stop the behavior that triggered the command.
2. Acknowledge the specific miss in one sentence without excuses, flattery, or self-defense.
3. Compare what the user asked for with what actually happened. Identify the earliest controllable decision that caused the mismatch.
4. State the correction as one reusable repository rule with a concrete trigger and required action.
5. Apply `add-repo-rules` immediately. The explicit command authorizes this repository-instruction edit; do not ask for a second confirmation.
6. Show the rules diff and resume the original task only if the correction leaves a clear next step.

## Good rule shape

Prefer: “When the user supplies a batch of named deliverables, treat the list as the requested scope before asking item-level questions.”

Avoid emotional transcripts, blame, vague promises such as “be more careful,” and rules tied only to one conversation. Preserve the useful behavioral lesson without storing insults or personal data.

## Boundaries

- Change only the applicable repository instruction file unless the user separately requests a product or code fix.
- Do not weaken safety, authorization, testing, or higher-priority instructions to appease the feedback.
- Do not claim the lesson is remembered until the repository rule has been written and its diff shown.
- If the requested lesson conflicts with governing instructions, explain that conflict and offer the closest compliant rule.
