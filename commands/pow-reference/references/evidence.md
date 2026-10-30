# Small evidence briefs and reusable facts

Use this when preparing a reference handoff, a history-free consultation, or a durable project note. Keep the representation proportional to the decision; a few sentences can be enough.

## Evidence brief

Include:

- **Goal and constraints:** the required observable outcome, compatibility obligations, and permission limits.
- **Source identity:** repository/document, commit or version, file/symbol/line range, and any relevant local delta. For an unversioned source record the retrieval date and avoid claiming immutability.
- **Primary evidence:** the short passage, schema, literal, input/output, or observed command result that answers the unknown. Distinguish source inspection from actual execution.
- **Conditions and uncertainty:** where the evidence applies, what remains unresolved, and the smallest check that would resolve it.
- **Retrieval pointers:** locations of details omitted for brevity. Keep errors and constraints intact; do not trim them into a false success.

An independent analyst receives this neutral material without the parent's preferred design, ranking, or interpretation disguised as a fact. Repository instructions still apply. Do not transmit unrelated private content to an external service just to assemble the brief.

## Reusable fact entry

Keep one entry for a stable, useful fact with: claim, evidence locator/version, applicable conditions, observed verification level (`inspected`, `compiled`, or `executed`), and an invalidation trigger. Keep interpretations or preferences explicitly labelled alongside, not merged into the claim.

For example, a format's byte order can be `inspected` from a pinned serializer and `executed` after the real reader accepts a produced file. Do not write that execution happened because a test or helper exists in the source.

Before reuse, compare the referenced source/API/schema with the current task. A relevant change makes the entry stale until rechecked; an unrelated repository commit does not require repeating the original work. Replace or retire disproved entries. Do not treat recency, repetition, or an agent's confidence as verification.

Use the repository's maintained notes location, falling back to `docs/engineering-notes.md`. Keep only information likely to save a future investigation. Store compact command/outcome evidence rather than full chat transcripts or unbounded logs. Reading a useful note does not authorize an automatic edit of global Skills or repository rules.
