# Standalone design evidence runtime

Use the absolute path to this installed Skill's `scripts/design-reasoning.mjs`. Below `<cli>` denotes that path. Arguments are separate shell-quoted values. The CLI has no third-party dependencies. Capturing requires an already installed Chromium-family browser and Node 22+; it never adds `--no-sandbox` or reuses your personal browser profile.

## Brief

Supply a UTF-8 JSON file outside production source if convenient:

```json
{
  "goal": "Let a person add and complete a task without ambiguity",
  "audience": "People managing today's work on desktop and phone",
  "primaryAction": "Add a task",
  "direction": "Quiet, legible task list; strong action hierarchy and clear completion feedback",
  "implementer": "implementation-agent",
  "sourcePaths": ["index.html"],
  "preserve": ["Adding a task still works"],
  "maxRounds": 3,
  "interactions": [
    {"action": "fill", "selector": "#task", "value": "Send invoice", "expect": {"selector": "#hint", "textIncludes": "Enter a task"}},
    {"action": "click", "selector": "#add", "expect": {"selector": "#tasks", "textIncludes": "Send invoice"}}
  ]
}
```

Every interaction must have an observed expected text. Supported actions: native mouse click, text insertion into a focused field, and Enter/Escape/Tab/Space key dispatch. These do not cover every widget or device. Set `staticSurface:true` only for a genuinely noninteractive surface; it allows an empty interaction list. Set `newSurface:true` when there is no pre-existing UI to preserve; otherwise baseline capture is required.

`sourcePaths` lists 1..64 exact regular files inside the target. Hashes cover these files only, not remote data or omitted dependencies. Include the relevant CSS, scripts and components. Symlink paths, .git and .pow are refused. `viewports` can override the defaults with up to four `{id,width,height}` objects; width is 320..2560, height 240..2160, scale one.

## Commands

```text
node <cli> init --root <repository> --brief <brief.json>
node <cli> capture --root <repository> --round baseline --url http://127.0.0.1:5173 --browser <browser-executable>
node <cli> capture --root <repository> --round candidate-1 --url http://127.0.0.1:5173 --browser <browser-executable>
node <cli> status --root <repository>
node <cli> review --root <repository> --round candidate-1 --review <review.json>
node <cli> report --root <repository>
node <cli> finish --root <repository>
```

Start the real application using its normal command before capture. The CLI does not invent its dev-server command, start arbitrary npm hooks, or publish. Each capture creates a fresh headless profile and closes its own process tree afterward. Browser interactions can change application data: use an authorized disposable local account/data set rather than a live production account. The profile is not an isolation sandbox for the visited application.

All views are captured in one bounded invocation. Capture may observe a failure and still save the screenshots; `finish` then refuses completion. Exit codes: 0 successful operation, 1 invalid input/runtime failure, 2 incomplete `finish`. An exit-zero capture is not a passing quality judgment. The CLI observes horizontal overflow and visible unnamed controls, not arbitrary contrast/focus/state issues.

## Independent review

Read the actual images. Use the hashes returned by `capture` or stored in `state.json`, never made-up hashes. Review JSON contains:

- `reviewer`: a nonempty identity different from `brief.implementer`.
- `round`: the candidate ID.
- `screenshots`: map from every viewport ID to its captured SHA-256.
- `criteria`: exactly five `{id,status,evidence,viewport}` entries; IDs are `hierarchy`, `identity`, `consistency`, `usability`, `accessibility`.
- `preserved`: exactly one `{requirement,status,evidence,viewport}` for each string in `brief.preserve`.
- `issues`: a bounded list of `{message,blocking}` observations, including unexamined behavior or missing evidence when material.

Each status is `pass`, `needs-work`, or `blocked`. Evidence should identify the element, relationship or interaction actually observed in that viewport; generic praise is not useful. Hash binding establishes consistency of artifacts, not an authenticated reviewer or a scientifically objective taste judgment. A reviewer may disagree even when deterministic checks pass; retain that disagreement and improve only within the remaining round budget.

Keep four evidence types distinct within these existing fields:

- **Structural:** the bounded DOM observations, such as overflow or unnamed controls, tied to the captured viewport. These cover only what the collector inspected.
- **Visual:** an image-specific judgment about hierarchy, identity or consistency. Read the current image before judging it; DOM checks and a remembered screenshot are insufficient.
- **Interaction:** the recorded action and observed effect. A visible control or dispatched click alone is not a successful operation.
- **Preservation:** each original requirement, its baseline/candidate evidence and whether the behavior or identity survived. Improvements elsewhere cannot cancel a preservation failure.

Use a short type prefix in an `issues[].message` when it clarifies the source of a finding; no new JSON fields or criteria IDs are required. Retain the five criteria and exact preservation entries. Report required, observed, failed and unobserved counts for declared views, interactions and preservation requirements in the evidence or report. Counts describe coverage, not a score. Keep a failed observation distinct from unavailable or unread evidence; use `blocked` and a concrete missing-evidence issue for required coverage that was not observed. Do not create more captures or repeat successful interactions to fill a denominator.

## State and recovery

The directory contains `state.json`, screenshots and `report.html`; a writer lock serializes mutations. Source hashes invalidate a candidate after relevant edits, and screenshot hashes detect changed image evidence. On compaction or handoff, carry the brief and a bounded neutral round/image locator and hash index, then re-read current state and images before judging them. Do not carry the previous reviewer's verdict as a substitute for this inspection. Do not commit private captures or browser data. Never remove a lock while its PID is still writing. An interrupted capture may leave PNGs without a committed round: retain and inspect those artifacts before deliberate recovery; never report them as complete evidence.

The session is deliberately bounded. It does not silently reset a spent budget, start model calls, estimate saved tokens, or promise full-route coverage from one screenshot. Report the actually captured URL, files, viewports, interaction steps and remaining gaps.
