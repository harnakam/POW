---
name: pow-first-loop
description: Turn an ambitious build, cross-language reimplementation, or stalled project into a concrete ideal outcome and an executable first loop, using one history-free AI consultation to challenge the implementation approach.
---

# Ideal outcome, first working loop

Work backward from what the user actually wants to exist, then build a real path to it. Keep the ideal outcome visible while making the next executable step small. A working first loop is a milestone, not permission to call a partial product finished.

## Scope

Use the supplied project or active task. If neither exists, ask what to build or reconsider. A request for a design produces an actionable design; a request to implement carries it through integration and verification. Skill maintenance does not invoke this workflow on the Skill repository.

This workflow includes one independent AI consultation, scoped to analysis. It does not authorize workers to edit the project, publish, or spend an unrequested budget. Follow the user's explicit delegation limits. Preserve applicable instructions, real contracts, and unrelated changes.

## Describe the ideal before inheriting the implementation

Identify the outcome in terms of user actions, observable results, and required compatibility. Describe what a finished version would allow, without automatically restricting it to the current modules, language APIs, project plan, or harness. Separate:

- **Required outcome:** explicit user requirements and behavior that must survive.
- **Design freedom:** implementation shape that can change, such as class hierarchy, library choice, internal representation, or API mapping.
- **Unresolved constraint:** a missing fact that could change correctness, feasibility, or scope, with the check that would resolve it.

For reimplementation, inspect the source and representative execution paths to extract rules, constants, data formats, ordering, state transitions, and error behavior. Record their provenance. Reproduce semantic obligations rather than translating each file or replacing each import one for one.

Randomness, time, numerical precision, and platform APIs need the required equivalence stated explicitly: matching a distribution, exact seeded results, byte-compatible saves, or compatible protocol behavior are different obligations. Use another implementation when it satisfies the required obligation; preserve an algorithm or representation when exact compatibility demands it. Do not assume either exact equivalence or permission to approximate.

Treat existing design documents and harnesses as evidence to inspect. Apply governing instructions; a fresh design is not an instruction bypass. When a document or test appears inconsistent with required behavior, establish the conflict from source, user requirements, or execution evidence. Do not silently weaken checks or drop behavior to make the project look successful.

## Consult an AI without the conversation history

Before committing to a substantial implementation approach, make one independent analysis pass using [the clean-brief protocol](references/clean-brief.md). Use an available agent mechanism that can start without inherited turns; with `collaboration.spawn_agent`, explicitly set `fork_turns: "none"`. Do not fork the current conversation or send a summary of its design conclusions.

Send the neutral goal, explicit constraints, necessary primary artifacts, and analysis-only boundaries. Ask for an ideal design, the smallest meaningful executable loop, a route to completion, and the assumption most likely to break that route. Keep the consultation independent of the parent's preferred solution.

Continue reversible investigation while it runs, but reconcile its answer before finalizing the approach. Restore the actual project context and compare both approaches against requirements and evidence. Adopt useful ideas, reject unsupported ones with concrete reasons, and keep completed work that still serves the goal. Freshness alone does not establish correctness.

If no history-free execution mechanism is available or delegation is prohibited, state that the independent consultation is unavailable. A neutral self-review may still help, but do not label it an independent AI run or claim the context was cleared. Continue authorized work that does not depend on an unavailable decision; identify any decision that remains blocked. Avoid repeated consultations unless a changed requirement or demonstrated failed assumption warrants another.

## Define the first executable loop

Choose a thin path through the real system that demonstrates its central behavior. Describe the trigger, input, actual decisions and effects, visible result, and exact way to run and verify it. Include a meaningful failure or boundary case. Resolve the most consequential unknown within that path when practical, rather than leaving it behind polished peripheral work.

Examples of loop shape, to adapt rather than impose:

- An interactive world: launch, generate a bounded world, move, change a block, and observe the changed world. Include restart and persistence if they are required for this milestone.
- A converter: read a real supported input, transform it under the intended rules, write the usable result, and verify it with the intended consumer.
- A service: accept a request at the real entry point, validate and authorize it, perform the required state change, and return an observable result.

Narrow content size or supported variants explicitly for the milestone. Do not use fake success responses, empty handlers, mocked production effects, or disconnected components to replace its essential behavior. Isolation through test doubles is useful for tests; it does not establish that the integrated loop works.

Connect later increments to the ideal outcome: name the missing behavior each adds, the dependency it needs, and the evidence that will mark it complete. Keep deferred requirements visible. Do not silently redefine the final objective as the first milestone or invent a deadline to make the plan look practical.

## Build toward completion

For implementation requests, work through the real entry point and dependencies needed by the selected loop. Reuse existing mechanisms where they support the outcome; replace internal shapes only when the task justifies it. Keep seams for confirmed next changes, without building a speculative plugin platform or a parallel architecture.

Run the loop as soon as its essential behavior exists. Fix observed integration failures before widening the surface. For cross-language work, compare representative inputs and boundary cases against the source or a verified specification; separate required exact matches from permitted semantic differences.

After a milestone passes, proceed to the next authorized increment. Do not repeatedly rebuild the first loop, restart the project, or expand documentation while required functionality remains untouched. If progress stalls, identify the specific failed assumption and make a bounded correction; a wider rewrite needs evidence that the narrower path cannot satisfy the objective.

## Evidence and handoff

Report proportionally:

- The ideal outcome and what the current milestone actually delivers.
- Whether the history-free consultation ran, what it changed, and any useful disagreement still unresolved.
- The execution command, observed result, relevant checks, and failures or unverified behavior.
- Remaining requirements and the next concrete increment, or the exact blocker and missing input.

Successful compilation, harness scores, and file counts do not by themselves prove the user can complete the intended loop. Claim final completion only when the agreed outcome is implemented and exercised. For advice-only requests, label the loop and completion route as proposals rather than executed work.
