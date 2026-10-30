"""Exercise the packaged native tool dispatcher against a loopback SSE fixture.

No model service, credentials, global
configuration, existing chat, or Desktop process is used.
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time


ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-6.1-sol"
MARKER = "native-proof"


def offered_tools(definitions, namespace=None):
    for definition in definitions:
        if definition.get("type") == "namespace":
            yield from offered_tools(definition.get("tools", []), definition["name"])
        else:
            yield namespace, definition


class Fixture(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        self.connection.settimeout(5)
        request = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        state = self.server.proof_state
        state["requests"].append(request)
        index = len(state["requests"])
        response_id = f"resp_native_{state['mode']}_{index}"
        if index == 1:
            expected_name = "exec" if state["mode"] == "code_mode" else "exec_command"
            definitions = request.get("tools", []) + [tool for item in request.get("input", []) if item.get("type") == "additional_tools" for tool in item.get("tools", [])]
            matches = [(namespace, tool) for namespace, tool in offered_tools(definitions) if tool.get("name") == expected_name]
            if not matches:
                state["fixture_error"] = f"required tool {expected_name} was not advertised"
                item = self.message(state["fixture_error"])
            else:
                namespace, definition = matches[0]
                item = {"id": "native_call_item", "call_id": "native_proof_call", "name": definition["name"], "status": "completed"}
                if namespace:
                    item["namespace"] = namespace
                if state["mode"] == "code_mode":
                    item.update(type="custom_tool_call", input="text(await tools.exec_command(" + json.dumps(state["arguments"]) + "));")
                else:
                    item.update(type="function_call", arguments=json.dumps(state["arguments"]))
                state["issued_call"] = item
        else:
            item = self.message("Local native dispatcher fixture finished.")
        frames = [
            {"type": "response.created", "response": {"id": response_id}},
            {"type": "response.output_item.done", "output_index": 0, "item": item},
            {"type": "response.completed", "response": {"id": response_id, "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}},
        ]
        payload = "".join(f"event: {frame['type']}\ndata: {json.dumps(frame)}\n\n" for frame in frames).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    @staticmethod
    def message(text):
        return {"id": "native_fixture_message", "type": "message", "role": "assistant", "status": "completed", "content": [{"type": "output_text", "text": text, "annotations": []}]}


def prove(binary: Path, mode: str, output: Path, windows_sandbox: str = "unelevated") -> dict:
    case = output / mode
    home = case / "codex-home"
    workspace = case / "workspace"
    home.mkdir(parents=True, exist_ok=False)
    workspace.mkdir()
    command = "Write-Output 'native-proof'" if os.name == "nt" else "printf 'native-proof\\n'"
    state = {"mode": mode, "requests": [], "arguments": {"cmd": command, "login": False, "max_output_tokens": 1000, "yield_time_ms": 10000}}
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    server.daemon_threads = True
    server.proof_state = state
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
    provider = '{name="Native local fixture",base_url="http://127.0.0.1:' + str(server.server_port) + '/v1",wire_api="responses",requires_openai_auth=false,supports_websockets=false}'
    overrides = ["model_provider=native_fixture", "model_providers.native_fixture=" + provider, f'model="{MODEL}"', "features.apps=false", "features.plugins=false", "analytics.enabled=false", 'chatgpt_base_url="http://127.0.0.1:' + str(server.server_port) + '"', "features.unified_exec=true", "features.code_mode=" + str(mode == "code_mode").lower(), "features.code_mode_only=" + str(mode == "code_mode").lower()]
    if os.name == "nt":
        overrides.append(f'windows.sandbox="{windows_sandbox}"')
        if windows_sandbox == "mxc":
            overrides.append("features.prefer_mxc=true")
    arguments = [str(binary)]
    for override in overrides:
        arguments.extend(["-c", override])
    arguments.extend(["app-server", "--listen", "stdio://"])
    environment = {key: value for key, value in os.environ.items() if not key.startswith(("OPENAI_", "AZURE_OPENAI_")) and key not in {"CHATGPT_API_KEY", "CODEX_API_KEY"}}
    environment.update(CODEX_HOME=str(home), CODEX_NATIVE_TOOL_CONCURRENCY="1", RUST_LOG="warn,codex_core::tools::native_scheduler=info,codex_core::tools::registry=debug", LOG_FORMAT="json")
    process = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=environment, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    pending = queue.Queue()
    events = []
    errors = []

    def stdout_reader():
        with (case / "app-server.jsonl").open("a", encoding="utf-8") as stream:
            for line in process.stdout:
                stream.write(line)
                stream.flush()
                try:
                    message = json.loads(line)
                    events.append(message)
                    pending.put(message)
                except json.JSONDecodeError:
                    errors.append("non-JSON app-server stdout")
        pending.put({"proof_eof": True})

    def stderr_reader():
        with (case / "native-trace.jsonl").open("w", encoding="utf-8") as stream:
            for line in process.stderr:
                stream.write(line)
                stream.flush()
                errors.append(line.rstrip())

    output_thread = threading.Thread(target=stdout_reader, daemon=True)
    output_thread.start()
    error_thread = threading.Thread(target=stderr_reader, daemon=True)
    error_thread.start()

    def send(message):
        process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
        process.stdin.flush()

    deadline = time.monotonic() + 60

    def receive(identity=None, completion=False):
        while time.monotonic() < deadline:
            try:
                message = pending.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty as error:
                raise TimeoutError("native local fixture exceeded 60 seconds") from error
            if message.get("proof_eof"):
                raise RuntimeError("app-server exited before completing the fixture")
            if "id" in message and "method" in message:
                raise RuntimeError("fixture requested a client action; no approval was granted")
            if identity is not None and message.get("id") == identity:
                if "error" in message:
                    raise RuntimeError(str(message["error"]))
                return message["result"]
            if completion and message.get("method") == "turn/completed":
                return message
        raise TimeoutError("native local fixture exceeded 60 seconds")

    result = {"mode": mode, "windows_sandbox": windows_sandbox if os.name == "nt" else None, "api_requests": 0, "paid_model_requests": 0, "network_target": "loopback fixture only", "global_configuration_changed": False}
    try:
        send({"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "native-scheduler-proof", "version": "1"}, "capabilities": {"experimentalApi": True}}})
        receive(1)
        send({"method": "initialized"})
        send({"id": 2, "method": "thread/start", "params": {"ephemeral": True, "cwd": str(workspace), "approvalPolicy": "never", "sandbox": "read-only", "modelProvider": "native_fixture", "model": MODEL, "baseInstructions": "Use only the local fixture response. This is an isolated native dispatcher test."}})
        thread_id = receive(2)["thread"]["id"]
        send({"id": 3, "method": "turn/start", "params": {"threadId": thread_id, "input": [{"type": "text", "text": "Execute the fixture tool call."}]}})
        receive(3)
        result["completion"] = receive(completion=True)
    except Exception as error:
        result["error"] = str(error)
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)
        output_thread.join(timeout=2)
        error_thread.join(timeout=2)
        server.shutdown()
        server.server_close()
    (case / "provider-requests.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    result["api_requests"] = len(state["requests"])
    result["process_exit_code"] = process.returncode
    commands = [event.get("params", {}).get("item", {}) for event in events if event.get("method") == "item/completed" and event.get("params", {}).get("item", {}).get("type") == "commandExecution"]
    result["command_items"] = commands
    result["native_admission_trace"] = [line for line in errors if "native tool scheduler admitted invocation" in line]
    result["native_enabled_trace"] = [line for line in errors if "native tool scheduler enabled" in line]
    sandbox_selections = []
    for sandbox_log in sorted((home / ".sandbox").glob("sandbox.*.log")):
        sandbox_selections.extend(line for line in sandbox_log.read_text(encoding="utf-8", errors="replace").splitlines() if "Windows sandbox selection:" in line)
    result["sandbox_selection_trace"] = sandbox_selections
    result["selected_windows_sandbox"] = sandbox_selections[-1].rsplit(": ", 1)[-1] if sandbox_selections else None
    result["success"] = bool("error" not in result and result.get("completion", {}).get("params", {}).get("turn", {}).get("status") == "completed" and not state.get("fixture_error") and len(state["requests"]) >= 2 and result["native_admission_trace"] and any(item.get("exitCode") == 0 and item.get("aggregatedOutput", "").strip() == MARKER for item in commands))
    if os.name == "nt" and windows_sandbox == "mxc":
        result["success"] = result["success"] and result["selected_windows_sandbox"] == "mxc"
    (case / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "package/bin/codex.exe")
    parser.add_argument("--receipt", type=Path, default=ROOT / "build-receipt.json")
    parser.add_argument("--output", type=Path, required=True, help="New local output directory outside installed skill resources")
    parser.add_argument("--mode", choices=("direct", "code_mode", "both"), default="both")
    parser.add_argument("--windows-sandbox", choices=("unelevated", "mxc"), default="unelevated", help="Windows backend for the isolated child; mxc requires the existing service and never falls back")
    args = parser.parse_args()
    if args.windows_sandbox == "mxc" and os.name != "nt":
        parser.error("mxc requires Windows")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8-sig"))
    digest = hashlib.sha256()
    with args.binary.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != receipt["binary"]["sha256"]:
        parser.error("binary does not match the native build receipt")
    args.output.mkdir(parents=True, exist_ok=False)
    modes = ("direct", "code_mode") if args.mode == "both" else (args.mode,)
    results = [prove(args.binary.resolve(), mode, args.output, args.windows_sandbox) for mode in modes]
    print(json.dumps({"output": str(args.output), "cases": [{"mode": result["mode"], "success": result["success"], "error": result.get("error"), "api_requests": result["api_requests"]} for result in results]}))
    return 0 if all(result["success"] for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
