"""Exercise the actual stdio transport with isolated logs and storage."""
import json
from pathlib import Path
from queue import Queue
import subprocess
import sys
from threading import Thread

from agent_monitor.project_analysis import project_id
from agent_monitor.project_store import ProjectStore


def test_stdio_handshake_statistics_and_agent_report_round_trip(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENTS.md").write_text("Run focused tests.\n", encoding="utf-8")
    database = tmp_path / "analysis.sqlite3"
    store = ProjectStore(database)
    pid = project_id(project)
    store.save_project(pid, "Synthetic project", str(project), [])
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"timezone": "UTC", "paths": {"codex": [], "claude": [], "antigravity": []}}), encoding="utf-8")
    server = Path(__file__).resolve().parents[1] / "mcp_server.py"
    process = subprocess.Popen([sys.executable, str(server), "--config", str(config), "--analysis-db", str(database)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    received, errors = Queue(), []
    def read_stdout():
        for line in process.stdout:
            received.put(json.loads(line))
    def read_stderr():
        errors.extend(process.stderr)
    Thread(target=read_stdout, daemon=True).start()
    Thread(target=read_stderr, daemon=True).start()
    request_id = 0
    def send(method, params, notification=False):
        nonlocal request_id
        request_id += 1
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            message["id"] = request_id
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()
        if notification:
            return
        while True:
            try:
                response = received.get(timeout=15)
            except Exception as error:
                raise AssertionError("MCP response missing: " + "".join(errors)) from error
            if response.get("id") == request_id:
                assert "error" not in response, response
                return response["result"]
    def call(name, arguments):
        result = send("tools/call", {"name": name, "arguments": arguments})
        assert not result.get("isError"), result
        return json.loads(next(item["text"] for item in result["content"] if item["type"] == "text"))
    try:
        hello = send("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "monitor-test", "version": "1"}})
        assert hello["serverInfo"]["name"] == "agent-session-monitor"
        send("notifications/initialized", {}, notification=True)
        tools = send("tools/list", {})["tools"]
        assert {"get_project_statistics", "compare_project_instructions", "get_event_source", "complete_analysis_job"} <= {item["name"] for item in tools}
        assert next(item for item in tools if item["name"] == "get_project_statistics")["annotations"]["readOnlyHint"]
        statistics = call("get_project_statistics", {"project_ids": [pid]})
        assert statistics["projects"][0]["usage"]["total_tokens"] is None
        created = call("create_analysis_job", {"project_ids": [pid], "objective": "Review the project"})
        claim = call("claim_analysis_job", {"job_id": created["job_id"], "agent_name": "Synthetic MCP agent"})
        context = claim["job"]["context"]
        report = {"summary": "No observed usage; inspect guidelines.", "findings": [], "recommendations": [
            {"title": "Clarify the test command", "rationale": "Make the instruction actionable", "project_ids": [pid],
             "evidence_ids": [next(item["id"] for item in context["evidence_catalog"] if item["kind"] == "instruction")]}]}
        completed = call("complete_analysis_job", {"job_id": created["job_id"], "claim_token": claim["claim_token"], "report": report})
        assert completed["status"] == "completed"
        assert ProjectStore(database).get_job(created["job_id"])["report"]["summary"] == report["summary"]
    finally:
        process.terminate()
        process.wait(timeout=10)
