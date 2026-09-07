from datetime import datetime, timedelta, timezone
from agent_monitor.ui.view_data import build_view_data
from agent_monitor.service import AgentMonitor


def test_graph_filtered_rollup_keeps_parent_context_and_unknowns_none():
    start=datetime(2026,1,2,tzinfo=timezone.utc); end=start+timedelta(days=1)
    snap={"sessions":[{"agent":"a","session_id":"r","started_at":"2026-01-01T00:00:00Z","last_activity":"2026-01-01T01:00:00Z"},{"agent":"a","session_id":"m","started_at":"2026-01-02T00:00:00Z","last_activity":"2026-01-02T01:00:00Z"}],"usage":[{"agent":"a","session_id":"m","event_id":"1","total_tokens":20,"occurred_at":"2026-01-02T01:00:00Z"},{"agent":"a","session_id":"m","event_id":"2","total_tokens":40,"occurred_at":"2026-01-03T01:00:00Z"}],"orchestration":{"children":{("a","r"):[("a","m")]},"depths":{("a","r"):0,("a","m"):1}},"requests":[],"events":[]}
    view=build_view_data(snap,{"start":start,"end":end,"agents":[],"projects":[],"models":[]})
    assert view["graph_view"]["rollups"][("a","r")]["total_tokens"] == 20
    assert ("a","r") in view["graph_view"]["context"]["depths"]


def test_four_level_rollup_exact_period_and_unknown_contract():
    start=datetime(2026,1,2,tzinfo=timezone.utc); end=start+timedelta(days=1)
    sessions=[{"agent":"a","session_id":sid,"started_at":"2026-01-02T00:00:00Z","last_activity":"2026-01-02T02:00:00Z"} for sid in ("r","m","l","x")]
    usage=[{"agent":"a","session_id":sid,"event_id":sid,"total_tokens":value,"occurred_at":when} for sid,value,when in [("r",10,"2026-01-02T01:00:00Z"),("m",20,"2026-01-02T01:00:00Z"),("l",30,"2026-01-02T01:00:00Z"),("x",40,"2026-01-03T01:00:00Z")]]
    graph={"children":{("a","r"):[("a","m")],("a","m"):[("a","l")],("a","l"):[("a","x")]},"depths":{("a",sid):i for i,sid in enumerate(("r","m","l","x"))}}
    view=build_view_data({"sessions":sessions,"usage":usage,"requests":[],"events":[],"orchestration":graph},{"start":start,"end":end,"agents":[],"projects":[],"models":[]})
    assert view["graph_view"]["rollups"][("a","r")]["total_tokens"] == 60
    unknown=build_view_data({"sessions":sessions[:1],"usage":[{"agent":"a","session_id":"r","event_id":"u","occurred_at":"2026-01-02T01:00:00Z"}],"requests":[],"events":[],"orchestration":{"depths":{("a","r"):0}}},{"start":start,"end":end,"agents":[],"projects":[],"models":[]})
    assert unknown["graph_view"]["rollups"][("a","r")]["total_tokens"] is None


def test_actual_monitor_snapshot_builds_view_and_request_duration(tmp_path):
    path=tmp_path / "s.jsonl"
    path.write_text('\n'.join(['{"type":"session_meta","payload":{"id":"s"},"timestamp":"2026-01-02T00:00:00Z"}','{"type":"turn_context","payload":{"turn_id":"t"},"timestamp":"2026-01-02T00:00:00Z"}','{"type":"token_usage_record","timestamp":"2026-01-02T01:00:00Z","payload":{"turn_id":"t","usage":{"input_tokens":10,"output_tokens":2}}}']),encoding="utf-8")
    snap=AgentMonitor({"timezone":"UTC","paths":{"codex":[str(tmp_path)],"claude":[],"antigravity":[]}}).refresh()
    start=datetime(2026,1,2,tzinfo=timezone.utc); view=build_view_data(snap,{"start":start,"end":start+timedelta(days=1),"agents":[],"projects":[],"models":[]})
    assert view["summary"]["total_tokens"] == 12 and "requests_df" in view


def test_populated_request_contract_midnight_ambiguity_and_coverage():
    start=datetime(2026,1,1,14,tzinfo=timezone.utc); end=start+timedelta(hours=12)
    sessions=[{"agent":"a","session_id":sid,"started_at":start,"last_activity":end} for sid in ("r","m","l","x")]+[{"agent":"b","session_id":"r","started_at":start,"last_activity":end}]
    usage=[{"agent":"a","session_id":sid,"turn_id":"t","event_id":sid,"total_tokens":n,"input_tokens":n,"output_tokens":0,"cache_read_tokens":n//2,"occurred_at":when} for sid,n,when in [("r",10,start),("m",20,start),("l",30,start),("x",40,end)]]+[{"session_id":"r","turn_id":"amb","event_id":"amb","input_tokens":9,"output_tokens":1,"occurred_at":start}]
    requests=[{"agent":"a","session_id":"r","turn_id":"t","started_at":start,"ended_at":start+timedelta(hours=2)},{"agent":"a","session_id":"l","turn_id":"none","started_at":start,"ended_at":start+timedelta(hours=1)},{"agent":"a","session_id":"r","turn_id":"amb","started_at":start,"ended_at":start+timedelta(hours=1)},{"agent":"b","session_id":"r","turn_id":"amb","started_at":start,"ended_at":start+timedelta(hours=1)}]
    graph={"children":{("a","r"):[("a","m")],("a","m"):[("a","l")],("a","l"):[("a","x")]},"depths":{("a",sid):i for i,sid in enumerate(("r","m","l","x"))}}
    view=build_view_data({"timezone":"Asia/Seoul","sessions":sessions,"usage":usage,"requests":requests,"events":[],"orchestration":graph},{"start":start,"end":end,"agents":[],"projects":[],"models":[]})
    root=view["graph_view"]["rollups"][("a","r")]
    scalar=view["requests_df"].query("agent == 'a' and session_id == 'r' and turn_id == 't'").iloc[0]
    assert root["total_tokens"]==60 and scalar.total_tokens==10 and scalar.cache_read_ratio==.5
    assert view["daily_request_duration"].duration_seconds.sum()==18000 and len(view["daily_request_duration"])==2
    ambiguous=view["requests_df"].query("turn_id == 'amb'"); assert ambiguous.input_tokens.isna().all()
    assert view["requests_df"].query("turn_id == 'none'").total_tokens.isna().all()


def test_request_cache_ratio_uses_only_known_pairs():
    start=datetime(2026,1,1,tzinfo=timezone.utc); end=start+timedelta(days=1)
    sessions=[{"agent":"a","session_id":"s","started_at":start,"last_activity":end}]
    usage=[{"agent":"a","session_id":"s","turn_id":"t","event_id":"one","input_tokens":100,"cache_read_tokens":50,"occurred_at":start},{"agent":"a","session_id":"s","turn_id":"t","event_id":"two","input_tokens":100,"occurred_at":start}]
    requests=[{"agent":"a","session_id":"s","turn_id":"t","started_at":start,"ended_at":start+timedelta(hours=1)}]
    view=build_view_data({"sessions":sessions,"usage":usage,"requests":requests,"events":[],"orchestration":{}},{"start":start,"end":end,"agents":[],"projects":[],"models":[]})
    assert view["requests_df"].iloc[0].cache_read_ratio == .5
