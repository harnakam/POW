---
name: optimize-latency
description: Use when diagnosing slow Codex tasks, reducing generated tool arguments or model round trips, or tuning measured command and agent orchestration.
---

# Optimize Codex task latency

Reduce the measured cost of a task while preserving its requested behavior, verification, permissions, and model quality. This is an optimization workflow, not mandatory instrumentation for every feature request.

## Workflow

1. Define the actual target: implementation plus verification, a fixed command workflow, or the complete user turn. Record the boundary before comparing times. Never substitute a fast test duration for task duration.
2. Inspect existing scripts, package commands, dispatcher presets, and saved traces. Reuse or minimally extend them before generating inline programs or new monitors. Respect requests for a new implementation; reuse of measurement infrastructure does not authorize reuse of the requested product code.
3. Measure the suspected bottleneck with existing instrumentation. Separate model request latency, argument delivery, tool execution, startup, and answer delivery where observable. Mark unavailable attribution as unknown; a UI Thinking label is not a CPU profile.
4. Make one targeted change: shorten repeated arguments with a registered entry point, batch independent commands, cache unchanged read-only indexes, or eliminate unnecessary model round trips. Keep commands, logs, failures, and verification real.
5. Use a bounded command scheduler for commands. For substantial independent model work, use the smallest useful sub-agent team with clear ownership. The parent continues independent work and waits only at dependency boundaries. Keep short, tightly coupled work in the parent.
6. Compare the same workload and outputs, including failures. Report sample counts, cache state, measurement overhead, and the exact verified result. Do not claim a universal speedup from a small experiment or unrelated examples.

## Routing

- Read [the file and installation inventory](references/inventory.md) for required Python/Node entry points, Skills, external tools, and excluded private artifacts.

- Read [the optimization procedure](references/workflow.md) for measurement boundaries, reuse, concurrency, and stopping conditions.
- Read [the measured examples](references/measurements-2026-10-19.md) only when an evidence example or comparison is useful. Their values are historical observations, not performance promises.
- Read [the bundled cxd guide](references/cxd.md) when a reusable dispatcher is needed. It includes a Python-standard-library Windows/Linux runtime and an explicit, ownership-preserving installer; do not install or start it merely because this skill was loaded.
- Read [the scheduler guide](references/scheduler.md) for command DAGs, attached start/wait/result, shared Tool slots, resource leases, and proxy boundaries.
- Read [the investigation method](references/investigation.md) for timeline attribution, concurrency settings, reproducible experiments, and the native integration boundary.
- Read [the 2026-10-27 measurements](references/measurements-2026-10-27.md) for real Tool verification versus synthetic scheduling experiments.
- Read [the RTK and Headroom guide](references/headroom.md) for context compression. Keep compression before model ingestion, preserve retrieval, and distinguish optional stdio MCP from automatic proxy routing.

- Read [the native integration guide](native/README.md) when process-wide native Tool admission or a version-matched Desktop override is explicitly needed. Keep build, isolated verification, registry configuration, and live engine verification distinct.

## Constraints

- Do not create an LLM agent merely to execute a command, wait for a session, or compress output.
- Do not reuse cached test success. Read-only caches must invalidate when their inputs change.
- Do not claim that asynchronous tools parallelize a single parent model request.
- Do not change model quality, plugins, security settings, API endpoints, or global configuration without a demonstrated relevant bottleneck and authorization.
- Do not install a new dispatcher, proxy, compressor, or always-on daemon merely to follow this skill. Use capabilities actually available in the current workspace.
- Keep raw sensitive logs local. Export the minimum timing and count metadata needed for the comparison.

## Output

State what changed, which boundary was measured, validation outcomes, comparable before/after samples, and remaining unknowns. If only a provisional checkpoint is available, label it explicitly and distinguish it from a recorded completion event.
