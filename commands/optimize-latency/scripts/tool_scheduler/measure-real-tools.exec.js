// @exec: {"yield_time_ms": 1000, "max_output_tokens": 1500}
// functions.exec only. Run bootstrap.exec.js first. This reruns every test.
const bundle = load("tool-scheduler-runtime");
const definitions = load("tool-scheduler-real-tasks");
if (!bundle || !definitions) throw new Error("Run bootstrap.exec.js first");
const { runToolTasks } = Function(bundle.source)();
const samples = [];
text({started: true, tasks: definitions.map(t => t.id)});
await yield_control();
for (const mode of ["serial", "parallel", "parallel", "serial", "serial", "parallel"]) {
  const begin = Date.now();
  const result = await runToolTasks(definitions.map(d => ({
    id: d.id, reads: d.reads, writes: d.writes, estimated_s: d.estimated_s,
    run: async t => {
      let reply = await t.exec_command(d.arguments);
      let output = reply.output || "";
      while (reply.session_id !== undefined) {
        reply = await t.write_stdin({session_id: reply.session_id, chars: "",
          yield_time_ms: 1000, max_output_tokens: 3000});
        output += reply.output || "";
      }
      const count = output.match(/Ran (\d+) tests?/);
      if (reply.exit_code !== 0 || !count || Number(count[1]) !== d.expected_tests)
        throw new Error(`${d.id} failed: ${output.slice(-1000)}`);
      return {exit_code: reply.exit_code, tests: Number(count[1]), output};
    },
  })), {tools, taskConcurrency: mode === "serial" ? 1 : 3, toolConcurrency: 3});
  const sample = {mode, elapsed_s: (Date.now() - begin) / 1000, result};
  samples.push(sample);
  notify({sample: samples.length, mode, elapsed_s: sample.elapsed_s,
    tasks: result.tasks.map(t => ({id: t.id, status: t.status}))});
}
const median = values => [...values].sort((a, b) => a - b)[1];
const median_s = Object.fromEntries(["serial", "parallel"].map(mode =>
  [mode, median(samples.filter(s => s.mode === mode).map(s => s.elapsed_s))]));
const report = {samples_per_mode: 3, median_s, samples,
  observed_reduction_percent: 100 * (1 - median_s.parallel / median_s.serial),
  all_tasks_passed: samples.every(s => s.result.tasks.every(t => t.status === "completed")),
  scope: "Actual tool transport/hooks/process/tests; excludes model generation and bootstrap"};
const path = `work/scheduler-measurements/real-tool-rerun-${Date.now()}.json`;
await tools.apply_patch("*** Begin Patch\n*** Add File: " + path + "\n" +
  JSON.stringify(report, null, 2).split("\n").map(line => "+" + line).join("\n") + "\n*** End Patch");
store("tool-scheduler-last-rerun", report);
text({saved: path, median_s, all_tasks_passed: report.all_tasks_passed});
