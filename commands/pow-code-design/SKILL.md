---
name: pow-code-design
description: Design or refactor code for readability and concrete extension requirements when planning module boundaries, untangling responsibilities, or adding variants to existing behavior. Use for software structure decisions, not visual design or formatting-only edits.
---

# Readable, extensible code design

Make the current behavior easy to trace and the requested next change easy to localize. Extensibility means a known variation has a clear place to live; it does not mean every part needs an interface, plugin, or configuration layer.

## Scope and outcome

Use the supplied target or the active software task. A bare invocation without either needs one focused question about the code or feature to design. Creating or editing this Skill does not activate it against POW itself.

Match the requested deliverable: design advice produces a concrete proposal; an implementation request produces integrated code and verification. Do not turn advice into a rewrite or stop an authorized implementation at a plan checkpoint. Preserve the requested behavior, public contracts, and unrelated working-tree changes.

## Ground the design in a change

Inspect applicable repository instructions and follow the relevant execution path: entry point, orchestration, domain decisions, state owner, and external effects. Locate callers, contracts, tests, and existing extension mechanisms before proposing replacements. Read only enough surrounding code to establish the affected boundaries.

Identify:

- What must remain true, including input/output shapes, failure behavior, authorization, and state transitions.
- The actual readability problem: for example, a caller must inspect three modules to understand one decision, or a name conceals a side effect. Cite the relevant code rather than judging by file length.
- The requested variation and where it currently causes edits. Separate confirmed requirements from hypothetical future needs.

For new code, derive these from the requested use case and repository conventions. Do not fabricate existing files or consumers. If no extension is requested, keep the design direct and identify a possible extraction boundary without implementing speculative infrastructure.

## Choose boundaries by responsibility

Keep things together when they express one rule or change for the same reason. Separate them when they have distinct invariants, lifetimes, external effects, or independent variation. Directory structure and class count are consequences of these boundaries, not design goals.

- Keep domain decisions independent of transport, rendering, and storage details where that separation simplifies the touched path. Let orchestration coordinate those decisions and effects.
- Give mutable state one authoritative owner. Derive values when practical; avoid copies that require callers to synchronize them. Make state transitions and their failure behavior visible.
- Use domain names and explicit inputs/outputs. A reader should be able to tell whether a function computes a value, changes state, or performs an external effect without opening every helper.
- Extract a helper when its name captures a meaningful rule or isolates an effect. Avoid chains of single-use wrappers that merely move lines away from the caller. Do not impose arbitrary line limits.
- Keep dependencies directed toward stable contracts. Pass a needed value or capability explicitly when it avoids hidden globals or concrete infrastructure coupling; do not introduce a dependency-injection framework for that alone.
- Preserve public entry points during internal refactors. If a requested behavior requires a contract change, identify affected callers and update them together rather than leaving two divergent paths.

## Select the smallest extension mechanism

Start with the direct implementation, then add a seam only for an observed need. Compare an alternative when the choice materially affects complexity or compatibility.

| Observed variation | Usually sufficient | Evidence that justifies more |
| --- | --- | --- |
| Different constant values with identical behavior | Explicit data or typed configuration | Validation or lifecycle differs across variants |
| A small, closed set of behaviors | A local exhaustive branch with clear cases | Cases become independently maintained implementations |
| The same decision structure with distinct algorithms | Named functions behind a narrow common input/output contract | Implementations must be selected or supplied independently |
| External storage, time, or network access | A boundary exposing only the capability the caller needs | Multiple real providers or isolated verification need substitution |
| Independently supplied extensions | A registry or plugin contract only when loading, ownership, and lifecycle are required | An actual consumer supplies extensions without editing the core |

Treat this table as decision criteria, not a mandate to replace established architecture. A language's normal functions, modules, or types may already provide the seam.

Shared syntax alone does not establish a shared concept. Before deduplicating, check whether the rules evolve together. Prefer limited duplication to a generic abstraction whose flags and callbacks combine unrelated policies. Conversely, extract a demonstrated common rule even within one caller when doing so makes its invariant explicit.

For every new abstraction, name its current consumer, the variation it contains, and the dependency it removes. If none can be identified, simplify it. Avoid catchall utility modules, pass-through service layers, untyped option bags, and configurable behavior without a concrete requirement.

## Make the proposal reviewable

Scale the explanation to the change. For a substantial design decision, provide:

- The current problem and the behavior to preserve, with file/symbol references when available.
- The proposed responsibility boundaries, state owner, and dependency direction.
- One representative path from input through decisions and effects to result, including a relevant failure path.
- The known extension: what gets added or edited, which callers are affected, and why. Do not claim zero core changes unless the design supports them.
- The tradeoff and the smallest implementation sequence that keeps callers working.

Use a short dependency sketch or before/after example when it clarifies a boundary. Do not prescribe layers, patterns, diagrams, or a separate design document for a small edit.

## Implement and challenge the result

When implementation is requested, make the smallest coherent change through the real entry point. Reuse existing contracts and tooling; add no production dependency unless the design demonstrably needs it. Remove obsolete paths created by the change.

Verify externally observable behavior and relevant invariants with repository-defined checks. Exercise the affected normal path and a meaningful failure or boundary case. For a refactor, establish behavior preservation; for a new variant, verify selection and behavior alongside an existing variant. Do not add tests that only mirror helper structure or enforce wording.

Review the diff with two concrete challenges:

1. **Reading challenge:** trace the representative request. Are the decision, state owner, and effects easy to find? Does indirection hide the rule the new design was meant to clarify?
2. **Extension challenge:** walk through the confirmed variation. Does it stay within the proposed boundary, or does it require unrelated modules to know variant details? Use a reasoning walkthrough when enough; use an isolated executable case when correctness depends on substitutability. Do not ship fake providers or unused scaffolding as proof.

If the design fails either challenge, narrow or revise it before handoff. Report what changed, the key files, checks actually run, and any unresolved contract or verification gap. Distinguish a design walkthrough from executed behavioral evidence; validation of this Skill's format alone does not prove better generated code.
