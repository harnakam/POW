# Decisions for structural maintenance

Read only the relevant sections when choosing a boundary, migrating callers, or deciding whether existing material can be removed. These are evaluation aids, not prescribed layers or universal size limits.

## Choosing classes and reusable functions

| Existing complexity | Useful extraction | What makes it worthwhile |
| --- | --- | --- |
| A connection, cache, session, or worker has state and a start/use/close lifecycle | A class or native resource-owning type | One owner enforces valid transitions and cleanup; callers do not coordinate several mutable collections |
| Related operations must preserve a domain invariant | A domain class/type with meaningful methods | Invalid transitions are prevented at the owner instead of checked inconsistently by every caller |
| A decision or transformation is hidden inside routing, rendering, or storage code | A named function with explicit inputs and result | The rule becomes independently understandable and reusable without importing the transport or I/O owner |
| Several callers implement the same policy and must change together | A shared domain function or policy module | One rule has one implementation, while legitimate caller differences remain explicit |
| A large workflow mixes decisions and external effects | A visible orchestration function plus cohesive collaborators | A reader can follow order and failure propagation without understanding each low-level mechanism |
| A module exposes many details that callers must assemble correctly | A focused interface over internal classes/functions | The public operation is simpler than its implementation and enforces the composition rules itself |

An extraction may be valuable before reuse: a parser, state transition, or cleanup owner can have one caller and still remove substantial conceptual load. State the responsibility it hides and the current reader or caller it helps. Favor composition for collaborators with different lifetimes or policies. Use inheritance only for an actual behavioral contract, and use idiomatic modules/structs/traits where the language does not use classes.

Do not replace a clear function with a class containing only that function to satisfy an object-oriented target. Conversely, do not leave state spread across closures, globals, and unrelated helpers just to avoid classes. Judge the resulting owner and interface, not the syntax.

## Module and directory boundaries

Start from actual change reasons, consumers, and runtime ownership. For example, a file that parses requests, enforces pricing, writes a database, and formats responses has separable domain and effect responsibilities even if it is short. A longer, cohesive format reader can be appropriate when its internal parsing details stay hidden.

A feature directory may keep its orchestration, domain types, and I/O adapters together while exporting one stable entry. A layered layout may suit a repository with established cross-feature contracts. Follow intentional local conventions and improve the touched boundary; do not reorganize the whole project to match a diagram.

Keep internal imports internal. Where a dependency cycle is accidental, identify which responsibility owns the shared contract or operation, then move it there or invert the specific dependency. Moving both sides into `common/` or introducing an interface without changing ownership only hides the cycle. Avoid files named `utils`, `manager`, or `service` when a domain name can explain their responsibility more precisely; do not rename intentional established APIs solely for taste.

Before accepting the layout, answer:

1. Where does a real request enter, and where are its rule, state, external effect, and failure handled?
2. Which details can a caller now ignore, and which invariant has a single owner?
3. Where would the next confirmed variation be added, and which existing consumers would change?
4. Did the split create repeated state, excessive argument plumbing, import cycles, or a chain of forwarding calls?

File count can increase when these answers improve. Reject a smaller layout if it hides dependencies or concentrates unrelated responsibilities.

## Compatibility and migration

Inventory only the surfaces touched by the chosen slice, including external and dynamically discovered consumers. Preserve relevant symbol/import names, signatures, synchronous/asynchronous behavior, error types and causes, CLI stdout/stderr and exit codes, configuration keys/defaults, storage/serialization formats, initialization order, registration names, transaction boundaries, cancellation and cleanup behavior.

Use a small sequence: extract the authoritative implementation behind the existing entry; migrate the known consumers; update packaging/discovery/configuration references; remove the superseded implementation when safe. Keep an adapter when external callers require it, with explicit translation, an owner, and a removal condition tied to those consumers. Do not leave two implementations that can diverge or remove compatibility merely because in-repository search found no caller.

If maintaining behavior needs a data migration, versioned contract, or otherwise broader change, explain the dependency and choose a reversible compatibility path. Do not disguise that work as a harmless file move. Keep unrelated bug fixes separate unless they are necessary for the requested refactoring; state any intentional behavior change and its authorization.

## Debugging and evidence

For a reported bug, trace the triggering input to the first incorrect decision or effect, not merely the last exception. For preventative maintenance, use actual ambiguous ownership, lost error causes, or scattered update paths as evidence. Distinguish the place an error surfaced from its likely cause and affected consumers.

Choose the appropriate failure owner. Add context once where the operation is known, preserve the original exception/typed cause, and propagate the result without converting it to an unrelated failure category. Use existing request/run/entity identifiers when useful; do not add a logging service or dump payloads. A missing observation stays unknown, while an actual failed operation stays failed.

Compare before/after using concrete questions: can the caller now name one operation instead of coordinating internals; can a debugger locate the rule and original cause; can one domain change avoid editing unrelated layers? Record counts only when actually measured and relevant. Never use an invented maintainability percentage or a lower line count as proof.

## Cleanup decisions

| Candidate | Evidence required before removal or consolidation |
| --- | --- |
| Apparently unused code or dependency | Check imports/callers, package exports, scripts, runtime configuration, framework discovery, reflection/dynamic loading, and external contracts. Use existing tooling as leads, not proof of absence |
| Similar functions or classes | Establish the same policy, invariants, failure behavior, and reason for future change. Preserve distinct concepts that happen to look alike |
| Duplicate documents | Identify an authoritative destination and move unique constraints, examples, and audience-specific information before updating incoming links |
| Old documentation | Find a contradiction with current implementation or an explicit successor. Age or one broken link is insufficient |
| Generated or copied output | Establish the actual generator, source, distribution purpose, regeneration command and whether consumers require the checked-in artifact |
| Superseded adapter or module | Confirm all relevant consumers migrated and required compatibility no longer depends on it |

Preserve licenses, migrations, public entry points, user changes, and necessary verification. For existing test files or checks, identify the behavior they protect and where that protection remains; uncertainty means retain, not bulk removal. Remove dependencies through the repository's maintained manifest/lock workflow without silently running install hooks or introducing network effects.

Keep one compact candidate list with locators, benefit, risk, and uncertainty. Revisit it when the relevant source changes, a bug or extension exposes a boundary, or the user invokes maintenance again. Mark obsolete findings resolved or withdrawn so the next pass does not recreate them from stale notes.
