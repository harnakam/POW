// @exec: {"yield_time_ms": 1000, "max_output_tokens": 1000}
// Paste into functions.exec; keep this cell alive until its completion event.
const workspace = "."; // The task workspace containing .codex-dispatch.json.
const preset = "check";
if (!/^[a-z][a-z0-9-]{0,63}$/.test(preset))
  throw new Error("Invalid cxd preset name");
const key = `cxd:${Date.now()}`;
const pending = tools.exec_command({
  cmd: `cxd start ${preset} --workspace . --attached --compact`,
  workdir: workspace,
  login: false, yield_time_ms: 10000, max_output_tokens: 3000,
});
text({submission_pending: true, resultKey: key});
await yield_control();
try {
  let reply = await pending;
  let remainder = "";
  let latest;
  function accept(chunk) {
    const lines = (remainder + (chunk || "")).split(/\r?\n/);
    remainder = lines.pop();
    for (const line of lines) {
      try {
        const value = JSON.parse(line);
        if (typeof value.run_id === "string") latest = value;
      } catch { /* Diagnostic text is not a completion event. */ }
    }
  }
  accept(reply.output);
  while (reply.session_id !== undefined) {
    reply = await tools.write_stdin({session_id: reply.session_id,
      chars: "", yield_time_ms: 5000, max_output_tokens: 3000});
    accept(reply.output);
  }
  accept("\n");
  if (!latest || !["completed", "failed", "interrupted"].includes(latest.status))
    throw new Error(`No terminal state; tool exit ${reply.exit_code}`);
  store(key, {...latest, exit_code: reply.exit_code});
  notify({type: "cxd_completed", resultKey: key, ...latest, exit_code: reply.exit_code});
} catch (error) {
  store(key, {error: String(error)});
  notify({type: "cxd_bridge_failed", resultKey: key, error: String(error)});
  throw error;
}
