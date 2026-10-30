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

Keep outcome separate from verification level. An observed failing command remains a failure; a command not run, unreadable evidence, or a missing review is `unobserved`, not a failed product or a pass. For a comparison, report required items, observed results, failures, and unobserved or incomparable items without removing missing evidence from the denominator.

## Reusable fact entry

Keep one entry for a stable, useful fact with: stable ID, claim, source/evidence locators and versions or hashes, applicable conditions and exclusions, observed verification level (`inspected`, `compiled`, or `executed`), outcome, lifecycle state, and invalidation trigger. Keep interpretations or preferences explicitly labelled alongside, not merged into the claim. Scope identities to the project or namespace so similarly named facts from another workspace cannot replace them.

For example, a format's byte order can be `inspected` from a pinned serializer and `executed` after the real reader accepts a produced file. Do not write that execution happened because a test or helper exists in the source.

Use four states:

- `candidate`: a useful observation or proposed generalization awaiting evidence for reuse. It is not an instruction or a successful application.
- `active`: its source identity and applicability have been checked and its evidence supports the claim. A procedural success must refer to an actual run after the final relevant change, not the agent's final answer or the mere existence of a command.
- `stale`: a relevant source, API/schema, content hash, platform, or tool capability changed. Re-read the affected evidence before reuse; an unrelated repository commit alone need not invalidate it.
- `revoked`: the claim was disproved or deliberately withdrawn. Keep its ID, affected claim/source hash, and short reason so extraction or a new ID does not silently resurrect the same entry.

Check source/version/hash, applicability and exclusions before ranking by usefulness; retrieve at most three relevant entries. Frequency, previous success counts, stars, and confidence cannot override those checks. Changed content invalidates the earlier evidence and trust decision even if its path or ID stays the same. A matching hash establishes content identity, not authenticity or permission. Resolve stale evidence within the authorized task; do not repeat successful checks just to promote an entry.

## Compaction and handoff

Carry the current goal and unresolved constraints plus a bounded index of neutral artifact IDs, exact locators, versions/hashes, and observation states. Include only decision-relevant raw excerpts; leave retrieval pointers for omitted material. IDs such as `source-01` or `run-02` identify artifacts without embedding a verdict. Preserve material errors and revoked/stale warnings, not the parent's ranking or favored explanation.

After compaction or handoff, re-read the current artifacts and applicable instructions before relying on a remembered claim. A locator, prior `active` state, or hash reminder is not proof that the new worker retrieved or verified it. Keep an unavailable artifact `unobserved`; do not recreate its contents from the parent's summary or replay completed commands merely to recover context.

Use the repository's maintained notes location, falling back to `docs/engineering-notes.md`. Keep only information likely to save a future investigation. Store compact command/outcome evidence rather than full chat transcripts or unbounded logs. Reading a useful note does not authorize an automatic edit of global Skills or repository rules.
