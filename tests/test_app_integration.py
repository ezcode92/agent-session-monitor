"""End-to-end Streamlit checks with representative, nonempty monitor data."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from copy import deepcopy
import pytest

from streamlit.testing.v1 import AppTest
from agent_monitor.ui.view_data import build_view_data
from agent_monitor.ui.navigation import PAGES


def go_page(app, label):
    name = next(name for name, title, _ in PAGES if title == label)
    page = Path(__file__).resolve().parents[1] / "src/agent_monitor/ui/pages" / f"{name}.py"
    return app.switch_page(str(page)).run(timeout=20)


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
    monkeypatch.setattr(service, "poll_session", lambda session_id, agent=None: snapshot)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run(timeout=20)
    assert not app.exception
    assert next(metric for metric in app.metric if metric.label == "전체 토큰").value == "63"
    for _, label, _ in PAGES:
        go_page(app, label)
        assert not app.exception
        assert len(app.title) == 1
    go_page(app, "작업 이력")
    request_frames = [element.value for element in app.dataframe if "total_tokens" in element.value.columns]
    assert request_frames and request_frames[-1].iloc[0]["total_tokens"] == 11


def test_overview_renders_compact_top_ten_request_scalars():
    source = '''import pandas as pd
import streamlit as st
import agent_monitor.ui.app as ui
requests = pd.DataFrame([{"title": "unknown-first", "agent": "codex", "status": "completed", "clipped_duration_seconds": 0, "total_tokens": pd.NA, "source_label": "codex"}, *[{"title": f"request-{index}", "agent": "codex", "status": "completed", "clipped_duration_seconds": index, "total_tokens": index, "source_label": "codex"} for index in range(2, 11)], {"title": "unknown-last", "agent": "codex", "status": "completed", "clipped_duration_seconds": 1, "total_tokens": pd.NA, "source_label": "codex"}])
ui.overview({"timezone": "UTC"}, pd.DataFrame(), {"start": None, "end": None}, {"requests_df": requests, "usage_df": pd.DataFrame(), "summary": {}})'''
    app = AppTest.from_string(source).run(timeout=20)
    assert not app.exception
    table = next(element.value for element in app.dataframe if list(element.value.columns) == ["제목", "에이전트", "상태", "작업 시간 (시:분:초)", "토큰", "출처"])
    assert table.shape == (10, 6)
    assert table.iloc[0].to_dict() == {"제목": "request-10", "에이전트": "codex", "상태": "completed", "작업 시간 (시:분:초)": "00:00:10", "토큰": "10", "출처": "codex"}
    assert table["제목"].tolist() == [f"request-{index}" for index in range(10, 1, -1)] + ["unknown-first"]
    assert table.iloc[-1]["토큰"] == "—"


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
    assert "comparison" not in view
    assert view["summary"]["total_tokens"] == 60
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
    for session in initial["sessions"]:
        session["status"] = "active_inferred"
    for index, event in enumerate(initial["events"], 1):
        event.update({"source_path": "synthetic.jsonl", "record_key": str(index)})
    current = {"value": initial}
    raw_calls = []

    def raw_event(agent, session_id, source_path, record_key):
        raw_calls.append((agent, session_id, source_path, record_key))
        return {"selected": record_key}

    monkeypatch.setattr(ui, "_snapshot", lambda force=False: current["value"])
    monkeypatch.setattr(service, "poll_session", lambda session_id, agent=None: current["value"])
    monkeypatch.setattr(service, "raw_event", raw_event)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run(timeout=20)
    go_page(app, "작업 이력")
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
    go_page(app, "개요")
    refresh = next(toggle for toggle in app.toggle if toggle.label == "고급: 전체 화면 5초 자동 새로고침")
    refresh.set_value(True).run(timeout=20)
    assert next(metric for metric in app.metric if metric.label == "전체 토큰").value == "162"


def test_duration_labels_and_composition_chart_use_values_and_explanations(monkeypatch):
    import agent_monitor.ui.app as ui

    captured = {}
    original_chart = ui._chart

    def chart(figure, title, description, **kwargs):
        captured[title] = figure
        original_chart(figure, title, description, **kwargs)

    monkeypatch.setattr(ui, "_chart", chart)
    monkeypatch.setattr(ui, "_snapshot", lambda force=False: _snapshot())
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run(timeout=20)
    assert not app.exception
    assert next(metric for metric in app.metric if metric.label == "평균 작업 시간").value == "02:00:00"
    metrics = {metric.label: metric.value for metric in app.metric}
    assert {label: metrics[label] for label in ("전체 토큰", "입력 토큰", "출력 토큰", "평균 입력 토큰", "평균 출력 토큰")} == {"전체 토큰": "63", "입력 토큰": "60", "출력 토큰": "3", "평균 입력 토큰": "20.0", "평균 출력 토큰": "1.0"}
    assert "입력 / 출력" not in metrics
    composition = captured["입력·출력·캐시 구성"]
    assert composition.layout.yaxis.title.text == "토큰"
    assert {trace.name: sum(trace.y) for trace in composition.data} == {"입력(캐시 제외)": 30, "출력": 3, "캐시 읽기": 30}
    assert composition.layout.barmode == "stack"
    duration = captured["기간 내 작업 시간"]
    for title in ("일별 전체 토큰", "기간 내 작업 시간"):
        assert captured[title].layout.xaxis.tickmode == "linear"
        assert captured[title].layout.xaxis.dtick >= 86_400_000
    assert "시:분:초" in duration.layout.yaxis.title.text
    assert all(label.count(":") == 2 for label in duration.layout.yaxis.ticktext)
    assert all(value[0].count(":") == 2 for value in duration.data[0].customdata)
    assert any("날짜별 토큰을 입력·출력·캐시" in caption.value for caption in app.caption)
    go_page(app, "작업 이력")
    assert not app.exception
    requests = next(element.value for element in app.dataframe if "기간 내 작업 시간 (시:분:초)" in element.value)
    assert requests["기간 내 작업 시간 (시:분:초)"].tolist() == ["02:00:00"]
    go_page(app, "기간 분석")
    assert not app.exception
    stats = next(element.value for element in app.dataframe if "평균 작업 시간 (시:분:초)" in element.value).T
    assert stats.loc["평균 작업 시간 (시:분:초)", "값"] == "02:00:00"
    assert stats.loc["P90 작업 시간 (시:분:초)", "값"] == "02:00:00"
    distribution = captured["작업 시간 분포"]
    assert distribution.layout.xaxis.title.text == "작업 시간 (시:분:초)"


def test_overview_token_averages_exclude_unknown_requests_and_include_zero():
    source = """import pandas as pd
import agent_monitor.ui.app as ui
requests=pd.DataFrame({"input_tokens":[10, None, 0],"output_tokens":[None, None, None]})
ui.overview({"timezone":"UTC"}, pd.DataFrame(), {}, {"requests_df":requests,"summary":{},"usage_df":pd.DataFrame()})
"""
    app = AppTest.from_string(source).run(timeout=20)
    assert not app.exception
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["평균 입력 토큰"] == "5.0"
    assert metrics["평균 출력 토큰"] == "—"


def test_analysis_groups_categories_by_local_day_week_month(monkeypatch):
    import pandas as pd
    import agent_monitor.ui.app as ui
    from agent_monitor.ui.adapter import frame

    start=datetime(2026, 8, 1, tzinfo=timezone.utc)
    end=datetime(2026, 10, 1, tzinfo=timezone.utc)
    snapshot={"timezone":"Asia/Seoul", "sessions":[], "requests":[], "events":[], "diagnostics":[], "paths":{}, "scanned_at":start,
              "usage":[{"agent":agent,"session_id":agent,"turn_id":"t","event_id":str(index),"occurred_at":at,"total_tokens":total}
                       for index,(agent,at,total) in enumerate([
                           ("codex", datetime(2026,8,30,16,tzinfo=timezone.utc),10),
                           ("claude",datetime(2026,8,30,17,tzinfo=timezone.utc),20),
                           ("codex",datetime(2026,8,31,16,tzinfo=timezone.utc),30),
                           ("codex",datetime(2026,9,7,16,tzinfo=timezone.utc),40)])]}
    view={"usage_df":frame(snapshot["usage"]),"requests_df":pd.DataFrame()}
    monkeypatch.setattr(ui,"_snapshot",lambda force=False:snapshot)
    monkeypatch.setattr(ui,"_filters",lambda snapshot, page="개요":(pd.DataFrame(),{"timezone":"Asia/Seoul","page":page,"start":start,"end":end,"agents":[],"projects":[],"models":[]}))
    monkeypatch.setattr(ui,"_view",lambda snapshot,state:view)
    charts={}
    original=ui._chart
    def chart(figure, title, description, **kwargs):
        charts[title]=figure
        original(figure,title,description, **kwargs)
    monkeypatch.setattr(ui,"_chart",chart)
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py").run(timeout=20)
    go_page(app, "기간 분석")
    def points():
        return {(trace.name,pd.Timestamp(date).strftime("%Y-%m-%d")):int(value) for trace in charts["기준별 토큰 사용량"].data for date,value in zip(trace.x,trace.y)}
    assert not app.exception
    assert points()=={("codex","2026-08-31"):10,("claude","2026-08-31"):20,("codex","2026-09-01"):30,("codex","2026-09-08"):40}
    next(select for select in app.selectbox if select.label=="집계 단위").set_value("주별").run(timeout=20)
    assert not app.exception
    assert points()=={("codex","2026-08-31"):40,("claude","2026-08-31"):20,("codex","2026-09-07"):40}
    next(select for select in app.selectbox if select.label=="집계 단위").set_value("월별").run(timeout=20)
    assert not app.exception
    assert points()=={("codex","2026-08-01"):10,("claude","2026-08-01"):20,("codex","2026-09-01"):70}


def test_composition_chart_keeps_missing_cache_components_unknown(monkeypatch):
    import pandas as pd
    import agent_monitor.ui.app as ui

    snapshot = _snapshot()
    for usage in snapshot['usage']:
        usage['cache_creation_tokens'] = None
    captured = {}
    original = ui._chart
    def chart(figure, title, description, **kwargs):
        captured[title] = figure
        original(figure, title, description, **kwargs)
    monkeypatch.setattr(ui, '_chart', chart)
    monkeypatch.setattr(ui, '_snapshot', lambda force=False: snapshot)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py').run(timeout=20)
    assert not app.exception
    traces = {trace.name: trace for trace in captured['입력·출력·캐시 구성'].data}
    assert sum(traces['출력'].y) == 3 and sum(traces['캐시 읽기'].y) == 30
    assert all(pd.isna(value) for value in traces['캐시 생성'].y)
    assert all(pd.isna(value) for value in traces['입력(캐시 제외)'].y)
    assert captured['일별 전체 토큰'].layout.title.text == ''


def test_request_timeline_preserves_gaps_and_removed_exports(monkeypatch):
    import pandas as pd
    import agent_monitor.ui.app as ui

    snapshot = _snapshot()
    start = snapshot["requests"][0]["started_at"]
    snapshot["requests"] = [
        {"agent":"codex", "session_id":"root", "turn_id":str(index), "title":f"request {index}",
         "started_at":start+timedelta(minutes=minute), "ended_at":start+timedelta(minutes=minute+5), "status":"completed"}
        for index,minute in enumerate((0,30))]
    captured = {}
    original = ui._chart
    def chart(figure, title, description, **kwargs):
        captured[title] = figure
        original(figure,title,description, **kwargs)
    monkeypatch.setattr(ui,"_chart",chart)
    monkeypatch.setattr(ui,"_snapshot",lambda force=False:snapshot)
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py").run(timeout=20)
    go_page(app, "오케스트레이션")
    assert not app.exception
    assert captured["세션 실행 타임라인"].layout.yaxis.categoryarray == ("codex:root", "codex:middle", "codex:leaf")
    trace=captured["세션 실행 타임라인"].data[0]
    assert list(trace.x)==[300000,300000]
    assert pd.Timestamp(trace.base[1])-pd.Timestamp(trace.base[0])==timedelta(minutes=30)
    assert [row[1] for row in trace.customdata]==["00:05:00","00:05:00"]
    assert not app.get("download_button")
    go_page(app, "기간 분석")
    assert not app.exception
    assert not any("직전" in item.value for item in app.header)
    assert all("previous_total" not in element.value for element in app.dataframe)


def test_visible_table_headers_and_metrics_have_tooltips(monkeypatch):
    import json
    import agent_monitor.ui.app as ui

    monkeypatch.setattr(ui,"_snapshot",lambda force=False:_snapshot())
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py").run(timeout=20)
    assert all(metric.proto.help for metric in app.metric)
    go_page(app, "작업 이력")
    assert not app.exception
    for table in app.dataframe:
        config=json.loads(table.proto.columns)
        for name in table.proto.column_order:
            assert config[name]["help"], name
    go_page(app, "기간 분석")
    assert not app.exception
    table=next(item for item in app.dataframe if "P90 작업 시간 (시:분:초)" in item.value)
    assert all(json.loads(table.proto.columns)[name]["help"] for name in table.value.columns)


@pytest.mark.parametrize("offsets", [(0,), (0, 1), (0, 3, 6), (0, 30, 400)])
def test_date_line_ticks_are_unique_without_compressing_missing_days(monkeypatch, offsets):
    import pandas as pd
    import plotly.express as px
    import agent_monitor.ui.app as ui

    for name in ("header", "caption", "plotly_chart"):
        monkeypatch.setattr(ui.st, name, lambda *args, **kwargs: None)
    dates = [datetime(2026, 9, 7) + timedelta(days=offset) for offset in offsets]
    figure = px.line(x=dates, y=list(range(len(dates))))
    ui._chart(figure, "Daily", "Daily totals")
    axis = figure.layout.xaxis
    ticks = pd.date_range(dates[0], dates[-1], freq=pd.Timedelta(milliseconds=axis.dtick))
    labels = ticks.strftime(axis.tickformat).tolist()
    assert 1 <= len(labels) <= 7
    assert len(labels) == len(set(labels))
    assert axis.dtick >= 86_400_000 and axis.dtick % 86_400_000 == 0
    assert pd.Timestamp(axis.tick0) == dates[0]
    assert list(pd.to_datetime(figure.data[0].x)) == dates
    assert figure.data[0].mode == "lines+markers"
    if dates[-1].year != dates[0].year:
        assert labels[0].startswith("2026-")
