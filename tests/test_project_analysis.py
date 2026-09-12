from datetime import datetime, timedelta, timezone
import json

import pytest
from streamlit.testing.v1 import AppTest

from agent_monitor.project_analysis import ProjectAnalysis, project_id, read_instructions
from agent_monitor.project_store import ProjectStore


@pytest.fixture
def project_fixture(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    first.mkdir()
    second.mkdir()
    (first / "AGENTS.md").write_text("Run targeted tests.\n", encoding="utf-8")
    (second / "AGENTS.md").write_text("Run all tests.\n", encoding="utf-8")
    at = datetime(2026, 9, 9, tzinfo=timezone.utc)
    sessions = [{"agent": agent, "session_id": "same", "project": str(root), "title": root.name,
                 "started_at": at, "last_activity_at": at+timedelta(hours=2), "status": "completed"}
                for agent, root in (("codex", first), ("claude", second))]
    usage = [{"agent": item["agent"], "session_id": "same", "event_id": item["agent"], "occurred_at": at,
              "model": "example", "input_tokens": 100 if item["agent"] == "codex" else None,
              "output_tokens": 20 if item["agent"] == "codex" else None, "total_tokens": 120 if item["agent"] == "codex" else None}
             for item in sessions]
    requests = [{"agent": "codex", "session_id": "same", "turn_id": str(i), "started_at": at+timedelta(minutes=i*30), "ended_at": at+timedelta(hours=1, minutes=i*30)} for i in range(2)]
    snapshot = {"sessions": sessions, "usage": usage, "requests": requests, "events": [], "generation": 1}
    service = ProjectAnalysis(lambda: snapshot, ProjectStore(tmp_path / "analysis.sqlite3"))
    return service, snapshot, first, second


def test_cross_project_statistics_preserve_unknowns_and_union_time(project_fixture):
    service, snapshot, first, second = project_fixture
    result = service.statistics([project_id(first), project_id(second)])
    a, b = result["projects"]
    assert a["usage"]["total_tokens"] == 120 and b["usage"]["total_tokens"] is None
    assert a["observed_request_seconds"] == 7200 and a["observed_wall_seconds"] == 5400
    assert b["observed_wall_seconds"] is None
    assert a["session_count"] == b["session_count"] == 1
    at = snapshot["sessions"][0]["started_at"]
    clipped = service.statistics([project_id(first)], at+timedelta(minutes=45), at+timedelta(hours=1))["projects"][0]
    assert clipped["usage"]["total_tokens"] is None
    assert clipped["observed_wall_seconds"] == 900
    with pytest.raises(ValueError):
        service.statistics([project_id(first)], at, at)
    with pytest.raises(ValueError):
        service.events(project_id(first), "claude", "same")


def test_manual_project_assignment_survives_and_does_not_conflate_ids(project_fixture):
    service, snapshot, first, second = project_fixture
    snapshot["sessions"][1]["project"] = None
    assert len(service.catalog()["unassigned_sessions"]) == 1
    service.register("Two", str(second), [("claude", "same")])
    restored = ProjectAnalysis(lambda: snapshot, ProjectStore(service.store.path))
    assert not restored.catalog()["unassigned_sessions"]
    assert restored.statistics([project_id(first)])["projects"][0]["usage"]["total_tokens"] == 120


def test_instruction_comparison_scope_limits_and_symlink_exclusion(project_fixture, tmp_path):
    service, _, first, second = project_fixture
    nested = first / "src"
    nested.mkdir()
    (nested / "AGENTS.md").write_text("Scoped guidance", encoding="utf-8")
    secret = tmp_path / "outside.md"
    secret.write_text("Do not expose", encoding="utf-8")
    (first / "CLAUDE.md").symlink_to(secret)
    ignored = first / "node_modules"
    ignored.mkdir()
    (ignored / "AGENTS.md").write_text("Excluded dependency", encoding="utf-8")
    docs = service.instructions([project_id(first)])[0]
    assert {item["path"] for item in docs["files"]} == {"AGENTS.md", "src/AGENTS.md"}
    assert docs["diagnostics"] and "Do not expose" not in json.dumps(docs)
    comparison = service.compare_instructions([project_id(first), project_id(second)])
    assert comparison["baseline_project_id"] == project_id(first)
    assert comparison["comparisons"][0]["differences"][0]["change"] == "changed"


def valid_report(context):
    evidence = context["evidence_catalog"][0]["id"]
    return {"summary": "Synthetic grounded analysis", "findings": [{"title": "Observation", "detail": "Known metric", "evidence_ids": [evidence]}],
            "recommendations": [{"title": "Review test guidance", "rationale": "Align scope with the task", "evidence_ids": [evidence], "project_ids": context["project_ids"]}]}


def test_job_claims_reject_stale_tokens_and_ungrounded_reports(project_fixture):
    service, _, first, second = project_fixture
    identity = service.create_job([project_id(first), project_id(second)], "Compare workflows")["job_id"]
    claim = service.store.claim(identity, "Synthetic agent")
    with pytest.raises(ValueError):
        service.store.claim(identity, "Another agent")
    report = valid_report(claim["job"]["context"])
    wrong = {**report, "findings": [{"title": "Invented", "detail": "Unsupported", "evidence_ids": ["not-real"]}]}
    with pytest.raises(ValueError, match="근거"):
        service.complete(identity, claim["claim_token"], wrong)
    with pytest.raises(ValueError, match="토큰"):
        service.complete(identity, "wrong-token", report)
    assert service.store.get_job(identity)["status"] == "running"
    service.store.retry(identity)
    with pytest.raises(ValueError):
        service.complete(identity, claim["claim_token"], report)
    fresh = service.store.claim(identity, "Agent retry")
    assert "claim_token" not in json.dumps(service.store.jobs())
    assert "Run targeted tests." not in json.dumps(fresh["job"]["context"])
    finished = service.complete(identity, fresh["claim_token"], report)
    assert finished["status"] == "completed"
    service.store.accept(identity, 0)
    service.store.accept(identity, 0)
    assert len(service.store.improvements()) == 1
    service.store.update_improvement(identity, 0, "applied")
    assert ProjectStore(service.store.path).improvements()[0]["applied_at"]


def test_original_event_tool_checks_scope_and_returns_actual_record(project_fixture, tmp_path):
    from agent_monitor.discovery import SourceFile
    from agent_monitor.parsers import parse_source
    service, snapshot, first, _ = project_fixture
    path = tmp_path / "synthetic.jsonl"
    payload = [{"type": "session_meta", "payload": {"id": "same", "cwd": str(first)}},
               {"type": "response_item", "timestamp": "2026-09-09T00:00:00Z", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "A full original request"}]}}]
    path.write_text("\n".join(json.dumps(value) for value in payload), encoding="utf-8")
    stat = path.stat()
    parsed = parse_source(SourceFile("codex", path, stat.st_size, stat.st_mtime_ns))
    snapshot["events"] = parsed.events
    event = parsed.events[-1]
    response = service.event_source(project_id(first), "codex", "same", event.event_id)
    assert "A full original request" in response["raw_json"] and not response["truncated"]
    payload[-1]["payload"]["content"][0]["text"] = "Changed request"
    path.write_text("\n".join(json.dumps(value) for value in payload), encoding="utf-8")
    with pytest.raises(ValueError, match="변경"):
        service.event_source(project_id(first), "codex", "same", event.event_id)


def test_project_analysis_ui_creates_mcp_work_and_shows_results(project_fixture, monkeypatch, tmp_path):
    service, snapshot, _, _ = project_fixture
    monkeypatch.setenv("AGENT_MONITOR_ANALYSIS_DB", str(service.store.path))
    monkeypatch.setenv("AGENT_MONITOR_REVIEW_DB", str(tmp_path / "reviews.sqlite3"))
    app = AppTest.from_string('''import streamlit as st
from agent_monitor.ui.agent_analysis import agent_analysis_page
agent_analysis_page(st.session_state["fixture"], {"start": None, "end": None})
''')
    app.session_state["fixture"] = snapshot
    app.run(timeout=20)
    assert not app.exception
    assert any("--scope results" in item.value for item in app.code)
    next(item for item in app.radio if item.label == "분석 범위").set_value("프로젝트 간 비교").run(timeout=20)
    select = next(item for item in app.multiselect if item.label.startswith("비교할 프로젝트"))
    select.set_value([item["project_id"] for item in service.catalog()["projects"]]).run(timeout=20)
    next(button for button in app.button if button.label == "에이전트 분석 요청 만들기").click().run(timeout=20)
    assert not app.exception and len(service.store.jobs()) == 1
    job = service.store.jobs()[0]
    claim = service.store.claim(job["job_id"], "Synthetic agent")
    service.complete(job["job_id"], claim["claim_token"], valid_report(job["context"]))
    app.run(timeout=20)
    assert not app.exception
    next(button for button in app.button if button.label == "실천할 개선 항목으로 채택").click().run(timeout=20)
    assert not app.exception and service.store.improvements()
