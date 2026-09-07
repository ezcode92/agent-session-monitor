"""End-to-end Streamlit checks with representative, nonempty monitor data."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from copy import deepcopy

from streamlit.testing.v1 import AppTest
from agent_monitor.ui.view_data import build_view_data


def _snapshot():
    start = datetime(2026, 9, 7, 14, tzinfo=timezone.utc)
    sessions = [
        {"agent": "codex", "session_id": sid, "title": sid, "started_at": start,
         "last_activity_at": start + timedelta(hours=3), "status": "completed"}
        for sid in ("root", "middle", "leaf")
    ]
    usage = [
        {"agent": "codex", "session_id": sid, "turn_id": "turn", "event_id": sid,
         "occurred_at": start + timedelta(minutes=30), "input_tokens": value,
         "output_tokens": 1, "cache_read_tokens": value // 2,
         "total_tokens": value + 1}
        for sid, value in (("root", 10), ("middle", 20), ("leaf", 30))
    ]
    requests = [
        {"agent": "codex", "session_id": sid, "turn_id": "turn", "started_at": start,
         "ended_at": start + timedelta(hours=2), "status": "completed"}
        for sid in ("root", "middle", "leaf")
    ]
    return {
        "timezone": "Asia/Seoul", "config": {"timezone": "Asia/Seoul", "paths": {"codex": [], "claude": [], "antigravity": []}},
        "sessions": sessions, "requests": requests, "usage": usage,
        "events": [
            {"agent": "codex", "session_id": "root", "event_id": "user", "occurred_at": start, "role": "user", "display": "question"},
            {"agent": "codex", "session_id": "root", "event_id": "assistant", "occurred_at": start, "role": "assistant", "display": "answer"},
            {"agent": "codex", "session_id": "root", "event_id": "tool", "occurred_at": start, "role": "tool", "display": "tool result"},
        ],
        "diagnostics": [], "config_diagnostics": [], "paths": {}, "scanned_at": start,
        "generation": 1,
        "orchestration": {
            "roots": [("codex", "root")],
            "children": {("codex", "root"): [("codex", "middle")], ("codex", "middle"): [("codex", "leaf")], ("codex", "leaf"): []},
            "depths": {("codex", "root"): 0, ("codex", "middle"): 1, ("codex", "leaf"): 2},
            "edges": [], "missing_placeholders": [], "relation_count": 2,
            "missing_parent_count": 0, "cycle_count": 0,
        },
    }


def test_actual_entrypoint_renders_all_pages_with_scalar_request_values(monkeypatch):
    """Run the real app.py entrypoint, rather than a hand-written page stub."""
    import agent_monitor.ui.app as ui
    import agent_monitor.service as service

    snapshot = _snapshot()
    assert snapshot["requests"] and snapshot["usage"] and snapshot["events"]
    monkeypatch.setattr(ui, "_snapshot", lambda force=False: snapshot)
    monkeypatch.setattr(service, "poll_session", lambda session_id: snapshot)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run(timeout=20)
    assert not app.exception
    assert next(metric for metric in app.metric if metric.label == "전체 토큰").value == "63"
    menu = next(radio for radio in app.radio if radio.label == "메뉴")
    for page in menu.options:
        menu.set_value(page).run(timeout=20)
        assert not app.exception
    menu = next(radio for radio in app.radio if radio.label == "메뉴")
    menu.set_value("작업 이력").run(timeout=20)
    request_frames = [element.value for element in app.dataframe if "total_tokens" in element.value.columns]
    assert request_frames and request_frames[-1].iloc[0]["total_tokens"] == 11


def test_populated_rollup_period_and_day_split_contract():
    start = datetime(2026, 9, 7, 14, tzinfo=timezone.utc)
    end = start + timedelta(hours=12)
    ids = ("root", "middle", "leaf", "outside")
    sessions = [{"agent": "codex", "session_id": sid, "started_at": start, "last_activity_at": end} for sid in ids]
    sessions.append({"agent": "codex", "session_id": "prior", "started_at": start - timedelta(days=1), "last_activity_at": start - timedelta(hours=1)})
    usage = [{"agent": "codex", "session_id": sid, "turn_id": sid, "event_id": sid,
              "occurred_at": when, "input_tokens": tokens, "output_tokens": 0,
              "cache_read_tokens": cache, "total_tokens": tokens}
             for sid, tokens, cache, when in (("root", 10, 5, start), ("middle", 20, 10, start),
                                               ("leaf", 30, 15, start), ("outside", 40, 20, end), ("prior", 40, 20, start - timedelta(hours=6)))]
    requests = [{"agent": "codex", "session_id": "root", "turn_id": "root", "started_at": start, "ended_at": start + timedelta(hours=2)}]
    graph = {"children": {("codex", "root"): [("codex", "middle")], ("codex", "middle"): [("codex", "leaf")], ("codex", "leaf"): [("codex", "outside")]},
             "depths": {("codex", sid): depth for depth, sid in enumerate(ids)}}
    view = build_view_data({"timezone": "Asia/Seoul", "sessions": sessions, "requests": requests, "usage": usage,
                            "events": [{"agent": "codex", "session_id": "root", "occurred_at": start, "display": "x"}], "orchestration": graph},
                           {"start": start, "end": end, "agents": [], "projects": [], "models": []})
    rollup = view["graph_view"]["rollups"][("codex", "root")]
    assert (rollup["own_total"], rollup["descendant_total"], rollup["total_tokens"]) == (10, 50, 60)
    assert rollup["cache_read_ratio"] == 0.5
    assert rollup["coverage"] == {"known_total_events": 3, "usage_events": 3}
    assert view["comparison"].iloc[0].to_dict() == {"current_total": 60, "previous_total": 40}
    assert view["daily_request_duration"].duration_seconds.tolist() == [3600.0, 3600.0]


def test_view_day_split_handles_new_york_dst_fall_back():
    start = datetime(2026, 11, 1, 4, tzinfo=timezone.utc)  # local midnight EDT
    end = datetime(2026, 11, 2, 5, tzinfo=timezone.utc)    # local midnight EST
    view = build_view_data({"timezone": "America/New_York", "sessions": [{"agent": "a", "session_id": "s", "started_at": start, "last_activity_at": end}],
                            "requests": [{"agent": "a", "session_id": "s", "turn_id": "t", "started_at": start, "ended_at": end}],
                            "usage": [], "events": [], "orchestration": {"depths": {("a", "s"): 0}}},
                           {"start": start, "end": end, "agents": [], "projects": [], "models": []})
    assert view["summary"]["request_duration_seconds"] == 90000.0
    assert view["daily_request_duration"].duration_seconds.tolist() == [90000.0]


def test_actual_pause_raw_and_generation_refresh_actions(monkeypatch):
    """Exercise the real history controls against a changing synthetic collector."""
    import agent_monitor.service as service
    import agent_monitor.ui.app as ui

    initial = _snapshot()
    for index, event in enumerate(initial["events"], 1):
        event.update({"source_path": "synthetic.jsonl", "record_key": str(index)})
    current = {"value": initial}
    raw_calls = []

    def raw_event(agent, session_id, source_path, record_key):
        raw_calls.append((agent, session_id, source_path, record_key))
        return {"selected": record_key}

    monkeypatch.setattr(ui, "_snapshot", lambda force=False: current["value"])
    monkeypatch.setattr(service, "poll_session", lambda session_id: current["value"])
    monkeypatch.setattr(service, "raw_event", raw_event)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run(timeout=20)
    next(radio for radio in app.radio if radio.label == "메뉴").set_value("작업 이력").run(timeout=20)
    next(radio for radio in app.radio if radio.label == "세션 보기").set_value("실시간").run(timeout=20)
    pause = next(toggle for toggle in app.toggle if toggle.label == "일시정지")
    pause.set_value(True).run(timeout=20)
    changed = deepcopy(initial)
    changed["generation"] = 2
    changed["events"].append({"agent": "codex", "session_id": "root", "event_id": "four", "occurred_at": initial["scanned_at"], "role": "assistant", "display": "four", "source_path": "synthetic.jsonl", "record_key": "4"})
    current["value"] = changed
    app.run(timeout=20)
    assert any("새 이벤트 1건" in element.value for element in app.info)
    event_frames = [element.value for element in app.dataframe if "event_id" in element.value.columns]
    assert event_frames[-1].event_id.tolist() == ["user", "assistant", "tool"]
    app.run(timeout=20)
    assert any("새 이벤트 1건" in element.value for element in app.info)
    changed["events"].append({"agent": "codex", "session_id": "root", "event_id": "five", "occurred_at": initial["scanned_at"], "role": "assistant", "display": "five", "source_path": "synthetic.jsonl", "record_key": "5"})
    current["value"] = changed
    app.run(timeout=20)
    assert any("새 이벤트 2건" in element.value for element in app.info)
    replacement = deepcopy(changed)
    replacement["generation"] = 3
    replacement["events"] = [{"agent": "codex", "session_id": "root", "event_id": "replacement", "occurred_at": initial["scanned_at"], "role": "assistant", "display": "replacement", "source_path": "synthetic.jsonl", "record_key": "6"}]
    current["value"] = replacement
    app.run(timeout=20)
    assert any("새 이벤트 3건" in element.value for element in app.info)
    next(radio for radio in app.radio if radio.label == "세션 보기").set_value("로그").run(timeout=20)
    next(button for button in app.button if button.label == "원시 JSON 불러오기").click().run(timeout=20)
    assert raw_calls == [("codex", "root", "synthetic.jsonl", "1")]
    assert any("selected" in element.value for element in app.json)
    next(radio for radio in app.radio if radio.label == "세션 보기").set_value("실시간").run(timeout=20)
    pause = next(toggle for toggle in app.toggle if toggle.label == "일시정지")
    pause.set_value(False).run(timeout=20)
    event_frames = [element.value for element in app.dataframe if "event_id" in element.value.columns]
    assert event_frames[-1].event_id.tolist() == ["replacement"]
    refreshed = deepcopy(replacement)
    refreshed["generation"] = 4
    refreshed["usage"][0]["total_tokens"] = 110
    current["value"] = refreshed
    next(radio for radio in app.radio if radio.label == "메뉴").set_value("개요").run(timeout=20)
    refresh = next(toggle for toggle in app.toggle if toggle.label == "고급: 전체 화면 5초 자동 새로고침")
    refresh.set_value(True).run(timeout=20)
    assert next(metric for metric in app.metric if metric.label == "전체 토큰").value == "162"
