# Per-path decision guide

For every proposed removal, answer these questions in the plan rationale:

- What purpose does this file currently serve, and what cited evidence establishes redundancy or obsolescence?
- Which authoritative file or behavior preserves its unique information and consumers? Inspect imports, literal references, package/build scripts and framework discovery; absence of a literal reference proves nothing about external users.
- For generated content, what source and command reproduce it, and was reproduction actually observed?
- For a test or verification script, which failure/scenario does it detect, where does that check survive, and what actual command/result supports that decision? Identical tests can run with different configuration. Retain when uncertain.
- Are license obligations, secrets, instructions, user modifications or important filesystem metadata involved? Select protected files individually only when authorized; backups contain original bytes and must remain private.
- What existing verification will reveal a mistaken decision, and which run ID restores the bytes?

The CLI emits conservative review leads. Do not reinterpret `no-observed-inbound-reference` as dead code, `generated-marker` as disposable output, `unresolved-local-link` as definitive staleness, or token overlap as semantic equivalence. Resolve references explicitly in a separate reviewed edit if consolidation requires it; apply deliberately does not rewrite them.

Use source control to review the resulting diff and existing build/type/lint/direct execution commands to check behavior. Do not add a new test suite or run broad checks merely to justify smaller line counts. Stop cleanup when the marginal benefit is uncertain. Retaining a necessary explanation or verification is a valid result.
