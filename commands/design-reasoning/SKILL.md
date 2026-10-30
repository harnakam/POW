---
name: design-reasoning
description: Design or improve a real UI through an explicit product direction, preserved behavior, browser captures and interactions, and an evidence-bound independent visual critique with a finite revision budget.
---

# Design reasoning

Build a coherent product surface for its actual users, then examine the running result. Preserve valuable existing identity and behavior while improving hierarchy, usability, accessibility, and visual character. More CSS, screenshots, or critique rounds do not themselves establish better design.

## Establish a concrete direction

Identify the user's task, audience, primary action, important content, and the interface's setting. Inspect the existing tokens, typography, layouts, components, states, routes, and navigation. Name what must remain intact and the actual weakness to improve. For a new surface, derive the direction from the product rather than defaulting to a familiar dashboard template.

Describe a short visual direction with reasons: hierarchy, density, typography, color roles, spacing, imagery, and interaction behavior. Consider a meaningful alternative when it changes the product experience. Avoid a universal aesthetic blacklist: a card, gradient, dark theme, or editorial layout is justified by its function and context, not by fashion. Do not import reference visuals or assets without checking provenance and permission.

Plan loading, empty, error, success, disabled and long-content states as relevant; primary and keyboard actions; small-screen behavior; readable contrast; labels and focus. Reuse the project's design system when it supports that direction. Do not broaden an improvement into an unrelated rebrand.

## Record the brief and baseline

Use the bundled standalone `scripts/design-reasoning.mjs` CLI; read [the execution contract](references/runtime.md) for input formats. State lives in the target repository's `.pow/design-reasoning/`. No model, server package, or browser is downloaded by this command.

Write a task-local brief and initialize once. It records the goal, audience, primary action, design direction, implementer identity, exact source files in scope, preservation requirements, viewports, interaction steps and maximum revision rounds. Use the project's real files and URL. Initializing does not overwrite an existing session. A changed task needs a separate working directory or deliberate archival of its existing evidence.

For an existing UI, capture a baseline before editing. `capture` launches an existing Chrome/Edge/Chromium in an isolated headless profile and uses CDP to navigate, execute the brief's concrete user actions, collect bounded DOM facts and record PNGs. Default viewports are desktop and mobile. Browser collection requires Node 22+; the state/review commands require Node 20+. If these capabilities are unavailable, state the missing coverage rather than install dependencies or fabricate screenshots.

## Implement, view, and criticize

Implement the chosen direction through the real components, state, data and navigation. Build/compile only as needed to run the surface. Do not add test files, snapshot suites, fixtures, or a new harness to verify styling.

Capture `candidate-1` against the running implementation. Observe the actual screenshots and interaction results. Ask a distinct available reviewer to inspect the brief, preservation requirements, browser observations and baseline/candidate images. Use a history-free agent when available and authorized, sending primary evidence without the implementer's desired conclusion. One independent reviewer is enough; do not create a judging committee. A human visual review can fill this role when no independent agent is available.

The reviewer records `pass`, `needs-work`, or `blocked`, with image-specific evidence, for hierarchy, identity, consistency, usability and accessibility, plus every preservation requirement. They name concrete issues and bind the review to the captured image hashes. No objective beauty score is invented. The CLI enforces the evidence shape and rejects a reviewer ID identical to the implementer; it cannot authenticate a human/model identity or prove that a reviewer looked at an image. Report that trust boundary honestly.

Fix only observed material issues. Capture a new numbered candidate only after a relevant source change. Maximum candidate rounds default to three and can be set to one through five at initialization. Unchanged recapture is refused. At the limit, report the unresolved issue rather than resetting the session to keep cycling. A successful round ends verification.

## Finish with actual evidence

`finish` requires current screenshots for every declared viewport, successful declared interactions (unless the brief explicitly describes a static surface), no observed page overflow or unnamed visible controls, and a matching passing independent review with no blocking preservation issue. Evidence becomes stale when a named source file changes. `report` writes a local HTML comparison of real captures and findings.

The DOM checks are limited observations, not full WCAG conformance; screenshots are not proof of every state or route. The review must call out missing coverage. Do not report complete if a required behavior, responsive view, or independent visual review is unavailable. For a design-only request, deliver the direction and proposal without claiming an implementation or capture occurred.

Report the result, files changed, actual build/browser commands, review findings, improvements visible in the evidence, and remaining limitations. Do not auto-publish screenshots, commit credentials, send feedback, or invoke paid model APIs.
