from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from agent_monitor.insights import tool_observations
from agent_monitor.parsers import parse_codex, parse_claude, parse_antigravity
from agent_monitor.request_tools import request_tool_history
from test_core import source
from test_app_integration import _snapshot, go_page


def call(cid="c", name="exec_command"):
    return {"type": "function_call", "call_id": cid, "name": name, "arguments": '{"cmd":"pytest"}'}


def output(cid="c", code=0):
    return {"type": "function_call_output", "call_id": cid, "output": {"exit_code": code, "text": "test output"}}


def event(eid, tid, node, agent="codex", sid="same"):
    return {"agent": agent, "session_id": sid, "turn_id": tid, "event_id": eid,
            "occurred_at": datetime(2026, 9, 7, 14, tzinfo=timezone.utc),
            "source_path": "synthetic.jsonl", "record_key": eid,
            "tool_observations": tool_observations(node)}


def test_codex_tool_events_keep_request_identity_even_with_same_timestamps(tmp_path):
    records = [{"type": "session_meta", "payload": {"id": "same"}},
               {"type": "response_item", "payload": call("before")},
               {"type": "turn_context", "payload": {"turn_id": "first"}},
               {"type": "response_item", "payload": call("a")},
               {"type": "turn_context", "payload": {"turn_id": "second"}},
               {"type": "response_item", "payload": output("a")},
               {"type": "response_item", "payload": call("b")}]
    for row in records:
        row["timestamp"] = "2026-09-07T14:00:00Z"
    parsed = parse_codex(source(tmp_path, "codex", '\n'.join(json.dumps(row) for row in records)))
    assert [e.turn_id for e in parsed.events] == [None, None, "first", "first", "second", "second", "second"]
    history = request_tool_history(parsed.events, "codex", "same", "first")
    assert len(history["items"]) == 1
    assert history["items"][0]["status"] == "성공"
    assert history["items"][0]["results"][0]["turn_id"] == "second"
    assert history["unassigned_calls"] == 1


def test_claude_tool_results_do_not_create_phantom_requests(tmp_path):
    records = [
        {"uuid": "u1", "message": {"role": "user", "content": "Run checks"}},
        {"uuid": "a1", "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "c", "name": "Bash", "input": {"command": "pytest"}}]}},
        {"uuid": "r1", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c", "content": "passed", "is_error": False}]}},
        {"uuid": "a2", "message": {"role": "assistant", "id": "response", "content": "Done", "usage": {"input_tokens": 10, "output_tokens": 2}}},
        {"uuid": "u2", "message": {"role": "user", "content": "Next"}},
    ]
    for index, row in enumerate(records):
        row["timestamp"] = f"2026-09-07T14:00:0{index}Z"
    parsed = parse_claude(source(tmp_path, "claude", '\n'.join(json.dumps(row) for row in records)))
    assert [turn.turn_id for turn in parsed.turns] == ["u1", "u2"]
    assert [e.turn_id for e in parsed.events] == ["u1", "u1", "u1", "u1", "u2"]
    assert parsed.turns[0].usage[0].turn_id == "u1"
    assert parsed.turns[0].ended_at.isoformat() == "2026-09-07T14:00:03+00:00"
    history = request_tool_history(parsed.events, "claude", "claude", "u1")
    assert len(history["items"]) == 1 and history["items"][0]["status"] == "성공"


def test_antigravity_request_zero_and_inline_result_are_linked(tmp_path):
    records = [{"type": "USER_INPUT", "step_index": 0, "content": "Test"},
               {"type": "RUN_COMMAND", "step_index": 1, "command": "pytest", "exit_code": 1},
               {"type": "USER_INPUT", "step_index": 2, "content": "Next"}]
    for index, row in enumerate(records):
        row["created_at"] = f"2026-09-07T14:00:0{index}Z"
    parsed = parse_antigravity(source(tmp_path, "antigravity", '\n'.join(json.dumps(row) for row in records)))
    assert [e.turn_id for e in parsed.events] == ["0", "0", "2"]
    items = request_tool_history(parsed.events, "antigravity", parsed.sessions[0].session_id, "0")["items"]
    assert len(items) == 1 and items[0]["status"] == "실패 포함"


def test_tool_pairing_isolated_by_session_request_and_call_id():
    events = [event("a", "first", call()), event("b", "first", output(code=1)),
              event("c", "second", call()), event("d", "second", output()),
              event("e", "first", output(), agent="claude"), event("f", "first", output(), sid="other")]
    first = request_tool_history(events + events, "codex", "same", "first")["items"]
    second = request_tool_history(events, "codex", "same", "second")["items"]
    assert len(first) == len(second) == 1
    assert first[0]["status"] == "실패 포함" and second[0]["status"] == "성공"
    assert len(first[0]["results"]) == 1
    assert "pytest" in first[0]["calls"][0]["preview"]
    assert "test output" in first[0]["results"][0]["preview"]


def test_missing_ambiguous_and_unknown_results_are_not_reported_as_success():
    events = [event("a", "first", call("same")), event("b", "first", call("same", "other_tool")),
              event("c", "first", output("same")), event("d", "first", output("orphan")),
              event("e", "first", call("unknown")), event("f", "first", {"type": "function_call_output", "call_id": "unknown", "output": "error mentioned in documentation"}),
              event("g", "first", call(None)), event("h", "first", output(None)), event("i", None, call("unassigned"))]
    before = deepcopy(events)
    result = request_tool_history(events, "codex", "same", "first")
    statuses = [item["status"] for item in result["items"]]
    assert "호출 연결 모호" in statuses and "호출 미확인" in statuses
    assert "성공 여부 미확인" in statuses and "결과 미확인" in statuses
    assert "성공" not in statuses and result["unassigned_calls"] == 1
    assert events == before


def test_tool_previews_are_bounded_without_changing_failure_metadata():
    values = tool_observations({"type": "function_call_output", "call_id": "x", "output": {"is_error": True, "content": "x" * 10000}})
    assert values[0]["failed"] is True
    assert len(values[0]["preview"]) <= 1001


def test_history_request_selection_and_lazy_raw_retry(monkeypatch):
    from agent_monitor import service
    from agent_monitor.ui import app as ui
    snapshot = _snapshot()
    second = {**snapshot["requests"][0], "turn_id": "second", "user_preview": "Second request"}
    snapshot["requests"].append(second)
    snapshot["events"] = [event("1", "turn", call(), sid="root"), event("2", "turn", output(), sid="root"),
                          event("3", "second", call("later"), sid="root")]
    monkeypatch.setattr(ui, "_snapshot", lambda force=False: snapshot)
    reads = []

    def raw(*args):
        reads.append(args)
        if len(reads) == 1:
            raise OSError("synthetic unavailable file")
        return {"type": "function_call", "arguments": "pytest"}

    monkeypatch.setattr(service, "raw_event", raw)
    monkeypatch.setattr(service, "poll_session", lambda *args, **kwargs: pytest.fail("Request detail must not start polling"))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run(timeout=20)
    go_page(app, "작업 이력")
    assert not app.exception and not reads
    assert next(m.value for m in app.metric if m.label == "세션 입력 토큰") == "10"
    assert any("요청당 평균 토큰" in c.value and "확인 1/2건" in c.value for c in app.caption)
    table = next(t.value for t in app.dataframe if "호출 ID" in t.value)
    assert table["호출 ID"].tolist() == ["c"]
    next(b for b in app.button if b.label == "도구 원문 불러오기").click().run(timeout=20)
    assert not app.exception and any("synthetic unavailable" in e.value for e in app.error)
    next(b for b in app.button if b.label == "도구 원문 불러오기").click().run(timeout=20)
    assert len(reads) == 2 and reads[-1] == ("codex", "root", "synthetic.jsonl", "1")
    next(s for s in app.selectbox if s.label == "추적할 요청").set_value("second").run(timeout=20)
    table = next(t.value for t in app.dataframe if "호출 ID" in t.value)
    assert table["호출 ID"].tolist() == ["later"]
    assert table["상태"].tolist() == ["결과 미확인"]
    go_page(app, "개요")
    go_page(app, "작업 이력")
    assert next(s for s in app.selectbox if s.label == "추적할 요청").value == "second"
    assert len(reads) == 2


def test_codex_task_start_before_context_preserves_tool_only_request(tmp_path):
    from agent_monitor.service import AgentMonitor
    records = [
        {"type": "session_meta", "payload": {"id": "session"}},
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "request"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "Run tools"}},
        {"type": "turn_context", "payload": {"turn_id": "request"}},
        {"type": "response_item", "payload": call("tool-only")},
        {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": "request"}},
    ]
    for index, row in enumerate(records):
        row["timestamp"] = f"2026-09-07T14:00:0{index}Z"
    source(tmp_path, "codex", '\n'.join(json.dumps(row) for row in records))
    snapshot = AgentMonitor({"paths": {"codex": [str(tmp_path)], "claude": [], "antigravity": []}}).get_snapshot()
    assert len(snapshot["requests"]) == 1
    assert snapshot["requests"][0].user_preview == "Run tools"
    assert not snapshot["usage"]
    history = request_tool_history(snapshot["events"], "codex", "session", "request")
    assert len(history["items"]) == 1 and history["items"][0]["call_id"] == "tool-only"


def test_explicit_tool_call_without_input_remains_visible_and_unfingerprinted():
    observation = tool_observations({"type": "tool_call", "name": "list_resources", "call_id": "no-args"})[0]
    assert observation["kind"] == "call" and observation["signature"] is None
    assert observation["preview"] == "" and observation["target"] == ""
    history = request_tool_history([event("1", "request", {"type": "tool_call", "name": "list_resources", "call_id": "no-args"})], "codex", "same", "request")
    assert len(history["items"]) == 1
