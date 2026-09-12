"""Exercise the actual stdio transport with isolated logs and storage."""
import json
from pathlib import Path
from queue import Queue
import subprocess
import sys
from threading import Thread

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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
        logs_tool = next(item for item in tools if item["name"] == "analyze_project_work_logs")
        assert logs_tool["annotations"]["readOnlyHint"]
        before = database.read_bytes()
        logs = call("analyze_project_work_logs", {"project_id": pid})
        assert logs["project_id"] == pid and logs["status"] == "insufficient_evidence"
        assert logs["report"]["recommendations"] == []
        assert database.read_bytes() == before
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


def test_results_scope_lists_completed_reports_without_local_source_locations(tmp_path):
    database = tmp_path / "analysis.sqlite3"
    store = ProjectStore(database)
    context = {
        "objective": "Review the completed analysis",
        "project_ids": ["project:synthetic"],
        "evidence_catalog": [
            {"id": "stat:requests", "kind": "statistic", "project_id": "project:synthetic", "metric": "request_count", "value": 3},
            {"id": "event:failure", "kind": "event", "project_id": "project:synthetic", "agent": "codex",
             "session_id": "session-1", "event_id": "event-1", "source_path": "/private/session.jsonl", "record_key": "7", "preview": "private command must not be exported"},
        ],
    }
    job_id = store.create_job(context)
    claim = store.claim(job_id, "Synthetic MCP agent")
    report = {
        "summary": "Three requests included one recorded failure.",
        "findings": [{"title": "Recorded failure", "detail": "The captured event is the evidence.",
                      "evidence_ids": ["event:failure"]}],
        "recommendations": [{"title": "Review failures", "rationale": "Use the captured request count.",
                             "evidence_ids": ["stat:requests"], "project_ids": ["project:synthetic"]}],
    }
    store.finish(job_id, claim["claim_token"], report=report)
    server = Path(__file__).resolve().parents[1] / "mcp_server.py"

    async def exercise():
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[str(server), "--scope", "results", "--analysis-db", str(database)],
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert {tool.name for tool in tools.tools} == {"list_analysis_reports", "get_analysis_report"}
                assert all(tool.annotations.model_dump(by_alias=True)["readOnlyHint"] for tool in tools.tools)
                listed = await session.call_tool("list_analysis_reports", {"limit": 10})
                assert not listed.is_error
                summaries = listed.structured_content["result"]
                assert summaries == [{
                    "job_id": job_id,
                    "agent_name": "Synthetic MCP agent",
                    "created_at": summaries[0]["created_at"],
                    "updated_at": summaries[0]["updated_at"],
                    "objective": context["objective"],
                    "project_ids": context["project_ids"],
                    "summary": report["summary"],
                    "finding_count": 1,
                    "recommendation_count": 1,
                }]
                fetched = await session.call_tool("get_analysis_report", {"job_id": job_id})
                assert not fetched.is_error
                result = json.loads(fetched.content[0].text)
                assert result["report"] == report
                assert {item["id"] for item in result["evidence"]} == {"event:failure", "stat:requests"}
                assert all("source_path" not in item and "record_key" not in item and "preview" not in item for item in result["evidence"])

    anyio.run(exercise)
