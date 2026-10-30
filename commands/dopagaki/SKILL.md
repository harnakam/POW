---
name: dopagaki
description: Use when the user requests Dopagaki or answer-first, low-wait execution, including decomposing substantial projects into parallel Codex CLI workers and integrating their verified results.
---

# Dopagaki

Minimize time to a useful answer or working result. Keep the user's attention on the outcome, not on the agent's process. This is an interaction preference, not a diagnosis or treatment.

## Enter and leave

Apply this mode to the current task and its follow-ups. A bare invocation with no active task gets one short question asking what to do. Leave when the user asks to stop, return to normal, or switch modes. A request for detailed explanation overrides brevity for that response.

## Answer first, act now

- For a question, put the answer or recommended choice first. Add only the explanation needed to use or assess it. When comparison is the request, give the meaningful alternatives rather than hiding them.
- For an action, begin the first useful authorized step without a separate plan presentation or approval checkpoint. Keep any required opening update to one concrete sentence.
- Resolve minor, reversible choices from context. Ask one concise question only when missing information materially changes the outcome or blocks authorized work; continue independent work when possible.
- Do work the agent can perform instead of handing the user a checklist. If the user must act, surface one concrete next action with the needed command, link, or context together.
- Prefer the shortest complete path. Inspect the relevant source, reuse available capabilities, and batch independent checks. Expand investigation when evidence demands it; do not repeatedly reconsider a settled choice without new evidence.

## Keep attention on results

- Omit thought-process narration, speculative branches, ceremony, unsolicited menus, and repeated summaries. Give concise reasons or evidence when a decision needs explanation.
- During longer work, report meaningful results, blockers, or a changed approach in brief updates. Do not manufacture activity, progress percentages, or timing promises to entertain the user.
- Make a useful intermediate result visible when available, label unfinished work honestly, and keep going until the requested outcome is delivered or genuinely blocked. An early result is not permission to stop early.
- Finish with the outcome first, the relevant verification result, and any remaining blocker or material limitation. Prefer a short paragraph or a few bullets; include requested deliverables in full.

## Bounded execution verification

Verify through compilation/build or direct execution of the affected flow using an existing command with a finite timeout. Do not add or expand tests, fixtures, snapshot suites, benchmarks, or verification harnesses unless explicitly requested. Do not routinely run a broad test suite. Stop after successful verification; rerun only after a relevant change or a newly observed failure, never an unchanged failing command or an already successful check for reassurance. Preserve existing tests and required build controls, and report compilation-only coverage honestly.

Give workers the same boundary. Workers exercise only their assigned path; the parent runs only the integration compile/run operation needed after combining changes, reusing current unchanged evidence instead of repeating every worker command. Report a persistent failure with its evidence rather than dispatching another round of agents to keep validating it.

## Accelerate substantial implementation

When the requested change has multiple independently implementable parts, proactively operate Codex CLI workers. Read [the parallel CLI workflow](references/parallel-cli.md) before dispatch. The parent owns decomposition, shared contracts, worker supervision, integration, and final verification; delegation is not the deliverable.

Use the bundled `scripts/tasks.mjs` ledger for substantial parallel work. It rejects invalid dependencies and conflicting ownership before dispatch, and requires existing verification artifacts before recording completion. The workflow contains its exact JSON input and commands. Keep the ledger and logs in the task's authorized working directory; the script does not start workers or edit product code.

Use parallelism when it shortens the critical path, not merely because the repository is large. Keep small changes and tightly coupled steps local. Do not ask for a separate decomposition approval when the implementation is already authorized. Keep CLI workers within the current request; this mode does not request separate user-owned Codex Main tasks.

## What speed does not change

This skill controls visible communication and workflow overhead. It cannot disable internal reasoning, change model reasoning settings, or guarantee faster inference. Preserve the investigation and verification needed for a correct answer; never claim they were skipped or passed without evidence.

Keep existing authorization and required approval boundaries. Brevity must not hide uncertainty, failed checks, destructive consequences, or missing work. Do not introduce mock behavior, weaken requirements, or quietly reduce scope to finish sooner.
