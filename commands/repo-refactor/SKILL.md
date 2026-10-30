---
name: repo-refactor
description: Improve repository-wide structure, readability, maintainability, and debugging through prioritized modular refactoring, class and function extraction, and evidence-based cleanup while preserving behavior and compatibility. Use for structural maintenance, not feature delivery or formatting alone.
---

# Refactor a repository continuously

Make responsibilities, dependencies, and failures easier to understand and change. Prefer clear, extensible structure over the fewest files or lines. Actively introduce useful classes, reusable functions, and modules that hide existing complexity; retain intentional architecture and externally observable behavior.

This Skill guides the host agent's work with the repository's existing tools. It needs no service, parser package, other Skill, or background process. Creating or installing the Skill does not invoke refactoring on POW or any other repository.

## Establish scope and behavior

Use the user's repository or the active project. Read its instructions, working-tree state, public entry points, manifests, build configuration, and existing maintenance notes. Identify generated, vendored, separately owned, and nested-project boundaries before surveying source. Preserve unrelated user changes.

For an audit-only request, return findings and priorities without editing. A request to improve or refactor authorizes coherent local implementation within its scope; proceed after explaining the chosen slice without inventing another approval checkpoint. It does not authorize publishing, new dependencies, deleting unrelated work, or scheduling recurring mutations.

Start with a repository-level map, then inspect the paths relevant to the change. Map entry points, domain responsibilities, state owners, external effects, module dependencies, and representative failure paths. Follow actual imports/callers, initialization, framework discovery, and build/runtime configuration. Reuse existing symbol indexes and scripts; do not install an analysis framework or dump the whole tree into context.

Name the behavior that must survive: relevant API/import paths, CLI arguments and output/exit codes, configuration/defaults, stored formats, side effects, error behavior, ordering and asynchronous lifecycle. An existing problem is evidence to investigate, not permission to silently change semantics.

## Evaluate and prioritize

Use the following questions with concrete file/symbol/caller evidence. Mark an area `sound`, `needs-work`, or `unobserved`; uninspected is not defective. Read [the decision guide](references/decisions.md) for boundary, class/function, compatibility, and cleanup decisions that need more detail.

| Dimension | Observable question |
| --- | --- |
| Responsibility | Can the module's purpose and state owner be named? Which unrelated reasons for change are mixed together? |
| Readability | Can a reader trace input, decision, state change, effect, result, and failure without hidden control flow or misleading names? |
| Encapsulation | Does a small interface hide meaningful implementation complexity, or must callers understand and synchronize its internals? |
| Dependency structure | Are dependency directions deliberate? Do cycles, global state, or imports across internal boundaries cause avoidable change propagation? |
| Extension | Does the next concrete variation have a clear location, or require scattered edits and growing condition/flag combinations? |
| Debuggability | Can a failure be localized to its operation and owner while preserving the original cause and relevant context? |
| Redundancy and freshness | Is duplication the same changing rule, and is allegedly unused or stale material proven unnecessary for its consumers? |
| Compatibility | Which observable contracts and discovery conventions could a move, extraction, or deletion affect, and how will they be checked? |

File length, function size, dependency counts, or change frequency can identify investigation leads. They are not automatic failure thresholds. Do not optimize toward a numerical cleanliness score or enforce one preferred directory layout everywhere.

Keep a short ranked list. For each candidate give the symptom and locator, affected callers, recurring maintenance/debugging cost, proposed boundary or cleanup, compatibility risk, and an existing command that can verify it. Prefer demonstrated confusion, repeated bug causes, tangled state, and widely duplicated rules over cosmetic renaming. Choose high practical benefit relative to migration and verification risk; do not invent time or performance savings.

## Design one coherent change

A normal invocation starts with one complete responsibility slice, which may span several files. State its scope and observable completion condition. For a larger explicitly requested refactoring, divide it into such slices and continue until that requested scope is handled; do not substitute the first slice for the whole objective.

Actively use these boundaries:

- Put coherent mutable state, invariants, resource lifetime, and related operations in a class or equivalent language-native type with a clear owner.
- Extract named, reusable functions for domain decisions, transformations, repeated rules, and meaningful effects. A single current caller is enough when extraction makes an existing responsibility understandable or hides real complexity.
- Group code by the responsibility that changes together. Expose a deliberate module interface and keep implementation details internal. Directory names should help locate a behavior and its failure owner.
- Separate policy from transport, persistence, rendering, or process execution when that removes a concrete dependency or tangled decision. Keep orchestration easy to follow instead of distributing it across tiny forwarding layers.

For a material extraction, identify the public entry, new owner/interface, internal collaborators, dependency direction, and one success/failure path. Describe where a known next change would go. Preserve an existing facade or compatibility adapter when consumers need it, with one authoritative implementation and a clear removal condition.

Allow extra files and a little indirection when they make the boundary clearer. Avoid namespace-only classes, inheritance without a real substitutability requirement, speculative plugin systems, catchall utility modules, or generic flag-driven abstractions that hide the rules. Do not require a second caller before making a useful abstraction, and do not create abstractions merely to raise a reuse count.

## Refactor, simplify, and preserve diagnostics

Move one responsibility, update all in-scope callers and discovery/build references, and keep the repository runnable between slices. Preserve public signatures and effects unless the user explicitly requests their change. Do not mix a structural migration with unrelated behavioral fixes or broad formatting.

Keep error provenance across boundaries: the original cause, relevant operation/state, existing correlation identifiers, and stack or typed error information where supported. Return failures to the right owner; do not turn a broad catch into empty data, ignored errors, or success. Add only diagnostics needed to distinguish a concrete failure, without duplicating logs at every layer or exposing sensitive values.

Consolidate genuinely shared rules at their owner and remove obsolete paths introduced by the refactor. Before deleting existing code, dependencies, files, or documents, establish their purpose, all known consumers, discovery mechanisms, and replacement or regeneration path. Static search misses, age, byte identity, and low usage alone do not establish redundancy. Preserve necessary validation, unique documentation, licenses, migrations, and intentional entry points. If use remains unresolved, retain the artifact and record the uncertainty.

## Verify and review the result

Choose the narrowest existing compilation/build or direct execution that exercises the affected public path and its important effects. Use a finite timeout and an expected observable result. Inspect related failure paths and compatibility surfaces in code; directly reproduce a known failure when necessary. A build-only result establishes compilation, not runtime equivalence.

Do not add or expand tests, fixtures, snapshots, benchmark suites, or verification harnesses unless explicitly requested. Do not routinely run a broad test suite, weaken existing checks, or repeat successful commands to accumulate confidence. After an observed failure, preserve evidence, fix its concrete cause, and rerun only the affected verification. Stop at a persistent blocker rather than cycling unchanged attempts.

Review the diff against the chosen boundary and original behavior. Trace the representative success and failure paths again. Confirm one state owner and source of truth, updated consumers, usable diagnostics, no abandoned implementations, and a clear location for the next known extension. Compare the selected assessment dimensions with source evidence; smaller code alone is not success. Use a bounded independent read-only review when its value justifies it, not a standing reviewer loop.

## Maintain continuity and stop deliberately

Update an existing maintenance issue or note when it will save another investigation. If none exists and continuing work needs a record, use one compact `docs/maintenance.md`; do not generate a report per pass. Retain the selected objective, status, changed boundary, evidence locators and verification result, unresolved compatibility/usage questions, and at most three next candidates. Consolidate completed history rather than growing an activity log.

On the next invocation, verify the relevant source identities and outstanding findings before reusing that record. A changed source can invalidate a finding; repetition, an earlier approval, or a completed build is not fresh proof. Prefer root-cause improvements and correction of disproved findings over adding more rules or abstractions.

Finish when the chosen slice is integrated, the relevant verification has succeeded, and the structural review is satisfied, or report the exact remaining blocker. Do not continue searching for edits after that completion condition. Continuous improvement means useful progress across bounded invocations and requested slices, not an endless autonomous cleanup loop.

Report the changed responsibilities and files, concrete before/after structural or debugging benefit, preserved compatibility, commands actually run and their results, and remaining uncertainty or the next useful candidate. Distinguish inspected, compiled, and executed evidence; do not claim repository-wide coverage from a local slice.
