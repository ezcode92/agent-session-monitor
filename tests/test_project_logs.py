from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from agent_monitor.config import codex_only_config, default_config, load_config, path_diagnostics, save_config
from agent_monitor.insights import tool_observations
from agent_monitor.project_analysis import ProjectAnalysis, project_id
from agent_monitor.project_store import ProjectStore
from agent_monitor.service import AgentMonitor

AT = datetime(2026, 9, 9, tzinfo=timezone.utc)


def event(sid, number, observation=None, agent="codex"):
    return {"agent": agent, "session_id": sid, "event_id": f"{sid}:{number}",
            "occurred_at": AT + timedelta(seconds=number), "source_path": f"/synthetic/{sid}.jsonl",
            "record_key": str(number + 1), "display": "synthetic error text is NOT a failure signal",
            "tool_observations": [observation] if observation else []}


def pair(sid, number, command="build", failed=True):
    identity = str(number)
    call = {"kind": "call", "call_id": identity, "tool_name": "exec_command", "target": command,
            "signature": command, "preview": command, "is_read": False}
    output = {"kind": "result", "call_id": identity, "failed": failed, "preview": "synthetic result"}
    return [event(sid, number, call), event(sid, number + 1, output)]


@pytest.fixture
def project(tmp_path):
    roots = [tmp_path / name for name in ("one", "two")]
    for root in roots:
        root.mkdir()
    sessions = [{"agent": "codex", "session_id": sid, "project": str(root), "title": sid,
                 "started_at": AT, "last_activity_at": AT+timedelta(hours=2), "status": "unfinished"}
                for sid, root in (("a", roots[0]), ("b", roots[0]), ("other", roots[1]))]
    snapshot = {"sessions": sessions, "requests": [], "usage": [], "events": [], "generation": 1}
    service = ProjectAnalysis(lambda: snapshot, ProjectStore(tmp_path / "analysis.sqlite3"))
    return service, snapshot, project_id(roots[0]), project_id(roots[1])


def test_legacy_configuration_is_archived_not_scanned_or_mutated(tmp_path, monkeypatch):
    legacy = {"timezone": "UTC", "paths": {"codex": [], "claude": ["/legacy/claude"], "antigravity": ["/legacy/agy"]}}
    original = deepcopy(legacy)
    assert set(default_config()["paths"]) == {"codex"}
    assert codex_only_config(legacy)["deprecated_paths"]["claude"] == ["/legacy/claude"]
    path = tmp_path / "config.json"
    path.write_text(json.dumps(legacy))
    saved = path.read_bytes()
    loaded = load_config(path)
    assert path.read_bytes() == saved
    assert loaded["paths"] == {"codex": []}
    assert path_diagnostics(legacy) == []
    save_config(loaded, path)
    assert load_config(path) == loaded
    seen = []
    monkeypatch.setattr("agent_monitor.service.scan_sources", lambda paths: seen.append(paths) or [])
    monitor = AgentMonitor(legacy)
    monitor.get_snapshot(force=True)
    monitor.update_config(legacy)
    monitor.get_snapshot(force=True)
    assert seen == [{"codex": []}, {"codex": []}]
    assert legacy == original
    assert path_diagnostics({"paths": {"codex": [str(tmp_path / "absent")]}})[0]["kind"] == "missing"


def test_failures_aggregate_across_sessions_but_not_projects_or_agents(project):
    service, snapshot, pid, other = project
    snapshot["events"] = pair("a", 0) + pair("a", 2) + pair("b", 4) + pair("other", 6)
    snapshot["events"] += [{**item, "agent": "claude"} for item in pair("a", 8)]
    result = service.analyze_logs(pid)
    assert len(result["report"]["recommendations"]) == 1
    item = result["report"]["recommendations"][0]
    assert item["priority"] == "P1" and item["observed_count"] == 3 and item["project_ids"] == [pid]
    assert {ref["session_id"] for ref in result["evidence_catalog"]} == {"a", "b"}
    assert {ref["agent"] for ref in result["evidence_catalog"]} == {"codex"}
    assert not service.analyze_logs(other)["report"]["findings"]
    assert not service.store.path.exists()  # Pure analysis never writes.


def test_period_end_exclusive_and_request_scope(project):
    service, snapshot, pid, _ = project
    snapshot["events"] = pair("a", 0) + pair("a", 2) + pair("a", 4)
    # Last failure occurs at the exclusive boundary and must not be counted.
    result = service.analyze_logs(pid, AT, AT+timedelta(seconds=5))
    assert result["coverage"]["explicit_failed_calls"] == 2
    assert not result["report"]["findings"]
    with pytest.raises(ValueError):
        service.analyze_logs(pid, AT, AT)
    with pytest.raises(ValueError):
        service.analyze_logs(pid, session_keys=[("codex", "other")])
    missing = event("a", 10)
    missing["occurred_at"] = None
    snapshot["events"].append(missing)
    assert service.analyze_logs(pid, AT, AT+timedelta(hours=1))["coverage"]["events_excluded_missing_time"] == 1


def test_free_text_unfinished_and_unknown_results_are_not_failures(project):
    service, snapshot, pid, _ = project
    snapshot["events"] = [event("a", 0)] + pair("a", 2, failed=None) + pair("a", 4, failed=False)
    snapshot["usage"] = [{"agent": "codex", "session_id": "a", "event_id": "u", "total_tokens": None}]
    result = service.analyze_logs(pid)
    assert not result["report"]["findings"]
    assert result["coverage"]["explicit_failed_calls"] == 0
    assert result["coverage"]["unknown_total_usage"] == 1
    assert any("unfinished" in text for text in result["limitations"])


def test_explicit_test_failure_and_read_repetition(project):
    service, snapshot, pid, _ = project
    snapshot["events"] = pair("a", 0, "uv run pytest tests/test_example.py")
    snapshot["events"] += sum((pair("a", i, "cat example.py", False) for i in (2, 4, 6)), [])
    result = service.analyze_logs(pid)
    assert {item["kind"] for item in result["report"]["findings"]} == {"test_failure", "repeated_read"}
    assert all(item["validation"] for item in result["report"]["recommendations"])


def test_raw_codex_exit_code_not_output_word_drives_failure():
    observed = tool_observations({"type": "response_item", "payload": {
        "type": "function_call_output", "call_id": "c",
        "output": "Process exited with code 0\nFinal output:\nerror: synthetic text"}})
    assert observed[0]["failed"] is False


def test_same_call_success_and_duplicate_events_do_not_inflate(project):
    service, snapshot, pid, _ = project
    one = pair("a", 0)
    snapshot["events"] = one * 5
    result = service.analyze_logs(pid)
    assert result["coverage"]["explicit_failed_calls"] == 1
    assert result["coverage"]["events_analyzed"] == 2
    snapshot["events"].append(event("a", 10, {"kind": "result", "call_id": "0", "failed": False}))
    assert service.analyze_logs(pid)["coverage"]["explicit_failed_calls"] == 0


def test_usage_growth_preserves_distinct_usage_in_same_turn_and_cache_caveat(project):
    service, snapshot, pid, _ = project
    snapshot["usage"] = [{"agent": "codex", "session_id": "a", "turn_id": "same",
        "occurred_at": AT+timedelta(seconds=i), "model": "synthetic", "input_tokens": count,
        "cache_read_tokens": count-100, "record_key": str(i), "source_path": "/synthetic/a.jsonl"}
        for i, count in enumerate((1000, 7000))]
    result = service.analyze_logs(pid)
    assert result["coverage"]["usage_analyzed"] == 2
    assert result["report"]["findings"][0]["kind"] == "input_growth"
    assert "캐시" in result["report"]["findings"][0]["detail"]
    assert len(result["evidence_catalog"]) == 2


def test_long_request_clipped_to_selected_period(project):
    service, snapshot, pid, _ = project
    snapshot["requests"] = [{"agent": "codex", "session_id": "a", "turn_id": "r", "started_at": AT,
        "ended_at": AT+timedelta(hours=1), "status": "completed"}]
    assert service.analyze_logs(pid)["report"]["findings"][0]["kind"] == "long_observed_request"
    result = service.analyze_logs(pid, AT, AT+timedelta(minutes=5))
    assert not result["report"]["findings"]


def test_save_is_atomic_idempotent_and_acceptance_survives_reanalysis(project):
    service, snapshot, pid, _ = project
    snapshot["events"] = pair("a", 0, "pytest")
    first = service.save_log_analysis(pid)
    second = service.save_log_analysis(pid)
    assert first["job_id"] == second["job_id"] and first["status"] == "completed"
    assert len(service.store.jobs()) == 1
    service.store.accept(first["job_id"], 0)
    service.store.update_improvement(first["job_id"], 0, "applied")
    assert service.save_log_analysis(pid)["job_id"] == first["job_id"]
    assert service.store.improvements()[0]["status"] == "applied"
    snapshot["events"] += pair("a", 2, "pytest")
    assert service.save_log_analysis(pid)["job_id"] != first["job_id"]
    assert len(service.store.jobs()) == 2
    queued = service.create_job([pid], "검토")
    context = service.store.get_job(queued["job_id"])["context"]
    assert context["log_analysis"]["report"]["findings"]
    assert all(ref in {item["id"] for item in context["evidence_catalog"]}
               for finding in context["log_analysis"]["report"]["findings"] for ref in finding["evidence_ids"])


def test_empty_and_bounded_analysis_report_coverage(project, monkeypatch):
    service, snapshot, pid, _ = project
    assert service.analyze_logs(pid)["status"] == "insufficient_evidence"
    monkeypatch.setattr("agent_monitor.project_logs.MAX_EVENTS", 3)
    snapshot["events"] = pair("a", 0, "pytest") + pair("a", 2, "pytest")
    result = service.analyze_logs(pid)
    assert result["coverage"]["events_analyzed"] == 3
    assert result["coverage"]["events_available"] == 4
    assert result["coverage"]["truncated"]


@pytest.mark.parametrize("command", ["sed -i s/x/y/ file.py", "cat file.py && pytest", "sed 'w output' input", "cat " + "x"*240])
def test_mutating_or_truncated_shell_commands_are_not_file_read_signals(project, command):
    service, snapshot, pid, _ = project
    snapshot["events"] = sum((pair("a", i, command, False) for i in (0, 2, 4)), [])
    assert not service.analyze_logs(pid)["report"]["findings"]


def test_safe_sed_read_and_reordered_input_are_deterministic(project):
    service, snapshot, pid, _ = project
    snapshot["events"] = sum((pair("a", i, "sed -n '1,30p' file.py", False) for i in (0, 2, 4)), [])
    first = service.save_log_analysis(pid)
    assert first["report"]["findings"][0]["kind"] == "repeated_read"
    snapshot["events"].reverse()
    assert service.save_log_analysis(pid)["job_id"] == first["job_id"]
