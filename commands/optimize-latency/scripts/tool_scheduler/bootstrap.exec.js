// @exec: {"yield_time_ms": 1000, "max_output_tokens": 700}
// functions.exec only. Load the fixed, locally reviewed modules once per chat.
const exported = await tools.exec_command({
  cmd: "python -S commands/optimize-latency/scripts/tool_scheduler/build_runtime.py --export",
  max_output_tokens: 15000,
});
if (exported.exit_code !== 0) throw new Error(exported.output);
const data = JSON.parse(exported.output);
// Revision audit, not a replacement for sandboxing or hook trust.
if (data.bundle.sha256 !== "08461c48d4bada3a27f58768510a8916f452f2a00a102583db3c252c4a6de346")
  throw new Error("Review the changed scheduler revision before loading it");
const runtime = Function(data.bundle.source)();
if (typeof runtime.runToolTasks !== "function") throw new Error("Missing router");
store("tool-scheduler-runtime", data.bundle);
store("tool-scheduler-real-tasks", data.tasks);
text({loaded: true, sha256: data.bundle.sha256, tasks: data.tasks.map(t => t.id)});
