# Clean-brief protocol

Use this reference when preparing the single history-free consultation. The objective is independence from earlier design conclusions, not removal of facts, user requirements, or governing instructions.

## Construct the brief

Include only information needed to solve the problem:

- The user-visible goal and agreed completion conditions.
- Explicit language, platform, compatibility, scope, and permission constraints.
- Necessary source files, schemas, representative inputs/outputs, or artifact locations, with commit/version and file/symbol/line locators. Separate observed facts from assumptions. Provide bounded raw evidence instead of a conclusion-laden synopsis. Keep retrieval pointers for omitted material, and never trim away errors or essential constraints to meet a size target.
- The analysis-only role and allowed reads. For a repository, supply its path and ask the agent to read applicable repository instructions. Do not send credentials, private unrelated material, or every project document merely because it is available.

Exclude the parent's candidate design, favored patterns, earlier recommendations, failed-plan narrative, and pressure to validate a conclusion. If a failure is relevant, supply the triggering input and raw observed output without assigning an explanation.

Existing source code can anchor an analyst, but it may also contain indispensable behavioral evidence. Include the relevant primary material and ask the analyst to distinguish required semantics from replaceable structure. Do not withhold essential compatibility facts to manufacture a blank slate.

## Consultation request

Write a self-contained request in ordinary prose. Ask the independent agent to:

1. Describe the ideal completed behavior under the supplied constraints.
2. Identify what must remain equivalent and what implementation choices are free.
3. Propose the smallest real executable loop, its existing compile/run command, expected observable result, finite timeout and stopping condition, and a route from it to completion. Do not propose extra tests, fixtures, or verification harnesses unless the user requested them.
4. Identify the most consequential unknown or assumption and the smallest source inspection or direct execution that would resolve it, without generating test code.

Tell it to inspect only permitted primary artifacts, produce analysis, and make no edits or external mutations. Do not supply an expected answer. If the available mechanism supports empty history, configure it explicitly rather than assuming a new agent has no inherited turns. Independent analysis may inspect the same source; describe the isolation accurately as no inherited conversation history.

## Reconcile once

Check the returned proposal against the actual task and repository. Record the evidence for adopting or rejecting a material suggestion, and surface requirement conflicts. Do not average incompatible designs or restart completed work solely because another answer is newer.

Missing runtime access or omitted source evidence limits what the independent pass establishes. Its design is a proposal until exercised. If it returns an assumption as fact, verify it before relying on it.

Retrieve maintained project facts only when relevant, and check their source version, conditions, and invalidation triggers. An earlier design preference is not a verified fact. Do not append accumulated conclusions to the brief in the name of memory. End the consultation after this reconciliation; it is not an iterative agent-judging loop.

The existing `non-context-thinking` command offers a fresh framing inside the same conversation. That is useful but does not satisfy this protocol's history-free execution requirement. This Skill remains self-contained and does not require that command to be installed.
