from datetime import datetime, timedelta, timezone
import json

import pytest
from streamlit.testing.v1 import AppTest

from agent_monitor.insights import analyze_task, tool_observations
from agent_monitor.review_store import ReviewStore


def member(agent="codex", sid="same"):
    return {"agent": agent, "session_id": sid, "title": "Synthetic task", "project": ""}


def test_review_reads_do_not_create_storage_and_writes_survive_restart(tmp_path):
    path = tmp_path / "notes" / "reviews.sqlite3"
    store = ReviewStore(path)
    assert store.list_tasks() == [] and not path.exists()
    task = store.save_task(title="Fix tests", sessions=[member(), member("claude")])
    assert ReviewStore(path).get_task(task)["outcome"] == "unreviewed"
    store.save_task(task_id=task, title="Fix tests", sessions=[member(), member("claude")], outcome="partial", blocked_by="Missing fixture", next_change="Explain the fixture first")
    saved = ReviewStore(path).get_task(task)
    assert saved["outcome"] == "partial" and saved["next_change"] == "Explain the fixture first"
    assert len(saved["sessions"]) == 2


def test_membership_conflict_preserves_existing_task_and_other_agent(tmp_path):
    store = ReviewStore(tmp_path / "reviews.sqlite3")
    first = store.save_task(title="One", sessions=[member()])
    second = store.save_task(title="Two", sessions=[member("claude")])
    with pytest.raises(ValueError, match="다른 작업"):
        store.save_task(task_id=first, title="Changed", sessions=[member(), member("claude")])
    assert store.get_task(first)["title"] == "One"
    assert store.task_for_session("claude", "same")["task_id"] == second


def test_actions_keep_only_evidence_locations_and_deduplicate_signals(tmp_path):
    store = ReviewStore(tmp_path / "reviews.sqlite3")
    task = store.save_task(title="One", sessions=[member()])
    ref = {"agent": "codex", "session_id": "same", "event_id": "e1", "source_path": "gone.jsonl", "record_key": "2", "raw_record": "SECRET"}
    action = store.add_action(task, "Check the environment", [ref], "signal-1")
    assert store.add_action(task, "Again", [ref], "signal-1") == action
    assert "SECRET" not in store.export_json()
    store.update_action(action, title="Check first", status="applied")
    applied = store.list_actions()[0]["applied_at"]
    assert applied
    store.update_action(action, title="Check first", status="applied")
    assert store.list_actions()[0]["applied_at"] == applied
    store.update_action(action, title="Check first", status="open")
    assert store.list_actions()[0]["applied_at"] is None


def tool_events(failed=True):
    result = []
    for index in range(3):
        call = {"type": "response_item", "payload": {"type": "function_call", "name": "exec_command", "call_id": str(index), "arguments": '{"cmd":"pytest"}'}}
        output = {"type": "response_item", "payload": {"type": "function_call_output", "call_id": str(index), "output": {"exit_code": 1 if failed else 0}}}
        for suffix, raw in (("call", call), ("result", output)):
            result.append({**member(), "event_id": f"{index}-{suffix}", "source_path": "synthetic.jsonl", "record_key": str(len(result)+1), "display": suffix, "tool_observations": tool_observations(raw)})
    return result


def test_repeat_failures_pair_calls_preserve_evidence_and_deduplicate():
    events = tool_events()
    report = analyze_task({"events": [*events, *events], "usage": []}, [member()])
    assert report["coverage"]["tool_calls"] == 3
    assert report["signals"][0]["kind"] == "repeated_failure"
    assert report["signals"][0]["count"] == 3
    assert len(report["signals"][0]["evidence"]) == 6
    assert analyze_task({"events": tool_events(False)}, [member()])["signals"] == []
    assert analyze_task({"events": events}, [member("claude")])["signals"] == []


def test_provider_blocks_unknown_results_and_exact_read_requests():
    assert tool_observations({"payload": {"type": ["unsupported"]}}) == []
    blocks = tool_observations({"message": {"content": [{"type": "tool_use", "id": "a", "name": "Read", "input": {"file_path": "app.py"}}, {"type": "tool_result", "tool_use_id": "a", "is_error": False}]}})
    assert blocks[0]["is_read"] and blocks[1]["failed"] is False
    unknown = tool_observations({"payload": {"type": "function_call_output", "call_id": "a", "output": "error: mentioned in documentation"}})
    assert unknown[0]["failed"] is None
    exited = tool_observations({"payload": {"type": "function_call_output", "call_id": "a", "output": "Process exited with code 1\nFinal output:\nfailed"}})
    assert exited[0]["failed"] is True
    events = [{**member(), "event_id": str(i), "tool_observations": [{**blocks[0], "call_id": str(i)}]} for i in range(3)]
    assert analyze_task({"events": events}, [member()])["signals"][0]["kind"] == "repeated_read"
    agy = tool_observations({"created_at": "2026-09-09T00:00:00Z", "type": "RUN_COMMAND", "step_index": 0, "command": "pytest", "exit_code": 1})
    assert len(agy) == 2 and agy[0]["call_id"] == agy[1]["call_id"] == "step:0"


def test_input_growth_requires_known_time_model_and_sufficient_difference():
    at = datetime(2026, 9, 9, tzinfo=timezone.utc)
    usage = [{**member(), "event_id": str(i), "occurred_at": at+timedelta(seconds=i), "model": "example", "input_tokens": tokens} for i, tokens in enumerate((1000, 6000))]
    assert analyze_task({"usage": usage}, [member()])["signals"][0]["kind"] == "input_growth"
    usage[1]["model"] = "another"
    assert not analyze_task({"usage": usage}, [member()])["signals"]
    usage[1].update(model="example", input_tokens=None)
    result = analyze_task({"usage": usage}, [member()])
    assert result["coverage"]["known_inputs"] == 1 and not result["signals"]


def test_session_review_ui_persists_notes_and_tracks_action(tmp_path, monkeypatch):
    path = tmp_path / "reviews.sqlite3"
    monkeypatch.setenv("AGENT_MONITOR_REVIEW_DB", str(path))
    snapshot = {"sessions": [{**member(), "status": "completed"}], "usage": [], "events": tool_events()}
    source = '''import streamlit as st
from agent_monitor.ui.review import session_review
session_review(st.session_state["fixture"], "codex", "same")
'''
    app = AppTest.from_string(source)
    app.session_state["fixture"] = snapshot
    app.run(timeout=20)
    next(button for button in app.button if button.label == "이 세션으로 작업 만들기").click().run(timeout=20)
    assert not app.exception
    next(item for item in app.text_area if item.label == "막힌 점").set_value("Environment was missing")
    next(item for item in app.selectbox if item.label == "작업 결과").set_value("partial")
    next(button for button in app.button if button.label == "회고 저장").click().run(timeout=20)
    assert not app.exception
    assert ReviewStore(path).list_tasks()[0]["blocked_by"] == "Environment was missing"
    next(button for button in app.button if button.label == "개선 항목으로 기록").click().run(timeout=20)
    assert not app.exception and len(ReviewStore(path).list_actions()) == 1
    next(item for item in app.selectbox if item.label == "실천 상태").set_value("applied")
    next(button for button in app.button if button.label == "개선 항목 저장").click().run(timeout=20)
    assert not app.exception and ReviewStore(path).list_actions()[0]["applied_at"]
    restored = AppTest.from_string(source)
    restored.session_state["fixture"] = {**snapshot, "events": []}
    restored.run(timeout=20)
    assert not restored.exception
    assert next(item for item in restored.text_area if item.label == "막힌 점").value == "Environment was missing"
    assert any("현재 수집된 로그" in item.value for item in restored.info)
