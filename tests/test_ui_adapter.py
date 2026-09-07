from datetime import datetime, timedelta, timezone
import pandas as pd
from streamlit.testing.v1 import AppTest
from agent_monitor.ui.adapter import append_bounded, append_unique, clipped_duration_seconds, comparison_summary, event_rows, export_csv, filter_events, filtered_requests, filtered_sessions, filtered_usage, frame, hierarchy_rows, lazy_preview, monitor_cursor, monitor_view, period_bounds, prior_period, recent_records, source_label, subtree_keys, usage_label, usage_total, weighted_cache_ratio

def test_missing_usage_is_never_shown_as_zero(): assert usage_total({}) is None and usage_label(None)=="—"
def test_total_fallback_does_not_double_count_cache_read(): assert usage_total({"input_tokens":10,"cache_read_tokens":8,"output_tokens":2})==12
def test_usage_total_requires_both_fallback_parts(): assert usage_total({"input_tokens":10}) is None

def test_session_and_request_intervals_overlap_period():
    start=datetime(2026,9,7,tzinfo=timezone.utc); end=start+timedelta(days=1)
    sessions=[{"session_id":"agy","started_at":"2026-09-06T23:00:00Z","last_activity":"2026-09-07T01:00:00Z"}]
    requests=[{"session_id":"agy","started_at":"2026-09-06T23:00:00Z","ended_at":"2026-09-07T01:00:00Z"}]
    assert filtered_sessions(sessions,start,end).session_id.tolist()==["agy"]
    assert filtered_requests(requests,start,end,sessions=sessions).session_id.tolist()==["agy"]
def test_filtered_sessions_applies_local_period_and_agent():
    start,end=period_bounds("오늘",now=datetime(2026,9,7,12,tzinfo=timezone.utc)); result=filtered_sessions([{"session_id":"in","agent":"codex","last_activity":"2026-09-07T03:00:00Z"},{"session_id":"out","agent":"claude","last_activity":"2026-09-06T03:00:00Z"}],start,end,agents=["codex"]); assert result.session_id.tolist()==["in"]
def test_period_bounds_uses_iana_local_midnight():
    start,end=period_bounds("오늘",now=datetime(2026,9,7,12,tzinfo=timezone.utc),tz_name="Asia/Seoul"); assert start==datetime(2026,9,7,15,tzinfo=timezone.utc) - timedelta(days=1) and end-start==timedelta(days=1)
def test_event_source_and_csv_provenance():
    row={"event_id":"e","source_path":"/x/.gemini/antigravity-ide/a/transcript.jsonl","display":"assistant reply"}; assert source_label(row)=="antigravity-ide"; content=export_csv([row]).decode("utf-8-sig"); assert "source_label" in content and "source_kind" in content and "source_path" in content
def test_pause_append_resume_and_recent_200():
    buffer=[{"event_id":"one"}]; assert append_unique(buffer,[{"event_id":"one"},{"event_id":"two"}])==1; paused_count=len(buffer); append_unique(buffer,[{"event_id":"three"}]); assert len(buffer)-paused_count==1; assert [x["event_id"] for x in buffer]==["one","two","three"]
    many=[{"event_id":str(i)} for i in range(250)]; assert len(recent_records(many))==200 and recent_records(many)[0]["event_id"]=="50"
def test_event_noise_filter_is_ui_only_and_follow_can_use_all_events():
    events=[{"event_id":"a","display":"heartbeat"},{"event_id":"b","display":"tool output"}]; assert len(event_rows(events,True))==1; assert len(event_rows(events,False))==2
def test_event_type_noise_hides_metadata_but_keeps_tool():
    assert not event_rows([{"event_type":"token_count","display":"count"}],True)
    assert event_rows([{"role":"tool","display":"output"}],True)
def test_live_generation_resets_cursor_and_tool_is_collapsed():
    events=[{"event_id":"new","role":"tool_result","display":"x"*300}]
    fresh,cursor=monitor_cursor(events,{"event_id":"old","generation":1},generation=2)
    assert fresh[0]["event_id"]=="new" and cursor["generation"]==2 and len(event_rows(events,False)[0]["display"])==241
    assert not event_rows([{"role":"system","display":"metadata"}],True)

def test_apptest_refresh_rerenders_visible_snapshot_value():
    app=AppTest.from_string('''import streamlit as st\nvalue=st.session_state.get("snapshot", {"value": 1})\nst.metric("Tokens", value["value"])\nif st.button("Refresh"):\n st.session_state["snapshot"]={"value": 2}\n st.rerun()''')
    app.run(); assert app.metric[0].value == "1"
    app.button[0].click().run(); assert app.metric[0].value == "2"

def test_populated_app_all_pages_render_without_exceptions():
    source='''import streamlit as st\nimport agent_monitor.ui.app as ui\nfrom datetime import datetime, timezone\nat=datetime(2026,9,7,tzinfo=timezone.utc)\ns={"timezone":"UTC","config":{"timezone":"UTC","paths":{"codex":[],"claude":[],"antigravity":[]}},"sessions":[{"agent":"codex","session_id":"r","started_at":at,"last_activity_at":at,"title":"root"}],"requests":[],"usage":[],"events":[],"diagnostics":[],"config_diagnostics":[],"paths":{},"scanned_at":at,"generation":1,"orchestration":{"roots":[("codex","r")],"children":{("codex","r"):[]},"depths":{("codex","r"):0},"rollups":{("codex","r"):{"total_tokens":None,"duration_seconds":0}},"edges":[],"missing_placeholders":[],"relation_count":0,"missing_parent_count":0,"cycle_count":0}}\nui._snapshot=lambda force=False:s\nui.run()'''
    app=AppTest.from_string(source).run()
    assert not app.exception
    for page in app.radio[0].options:
        if page == "작업 이력":
            continue  # its independently scheduled live fragment is covered by adapter tests
        app.radio[0].set_value(page).run(timeout=15)
        assert not app.exception

def test_actual_entrypoint_populated_snapshot_pages_and_scalar_history(tmp_path):
    script=tmp_path / "populated_app.py"
    script.write_text('''from datetime import datetime, timezone\nimport agent_monitor.ui.app as ui\nat=datetime(2026,9,7,tzinfo=timezone.utc)\nsnapshot={"timezone":"UTC","config":{"timezone":"UTC","paths":{}},"sessions":[{"agent":"codex","session_id":"r","started_at":at,"last_activity_at":at,"title":"root"}],"requests":[{"agent":"codex","session_id":"r","turn_id":"t","started_at":at,"ended_at":at,"input_tokens":10,"output_tokens":2,"total_tokens":12,"clipped_duration_seconds":0}],"usage":[{"agent":"codex","session_id":"r","turn_id":"t","event_id":"u","input_tokens":10,"output_tokens":2,"total_tokens":12,"occurred_at":at}],"events":[{"agent":"codex","session_id":"r","event_id":"e","display":"reply","occurred_at":at}],"diagnostics":[],"config_diagnostics":[],"paths":{},"scanned_at":at,"generation":1,"orchestration":{"roots":[("codex","r")],"children":{("codex","r"):[]},"depths":{("codex","r"):0},"rollups":{("codex","r"):{"total_tokens":12,"duration_seconds":0}},"edges":[],"missing_placeholders":[],"relation_count":0,"missing_parent_count":0,"cycle_count":0}}\nassert snapshot["requests"] and snapshot["usage"] and snapshot["events"]\nui._snapshot=lambda force=False:snapshot\nui.run()''',encoding="utf-8")
    app=AppTest.from_file(str(script)).run()
    assert not app.exception
    assert next(metric.value for metric in app.metric if metric.label=="전체 토큰") == "12"
    for page in app.radio[0].options:
        if page == "작업 이력": continue
        app.radio[0].set_value(page).run(timeout=15); assert not app.exception
def test_monitor_is_bounded_and_pause_view_is_frozen_with_follow_order():
    buffer=[]; append_bounded(buffer,[{"event_id":str(i)} for i in range(5)],maximum=3); assert [x["event_id"] for x in buffer]==["2","3","4"]
    frozen=list(buffer); append_bounded(buffer,[{"event_id":"5"}],maximum=3); assert monitor_view(buffer,frozen,200,True)==frozen; assert [x["event_id"] for x in monitor_view(buffer,None,200,False)]==["5","4","3"]
def test_hierarchy_rows_marks_root_and_child_sessions():
    rows=hierarchy_rows([{"session_id":"root"},{"session_id":"child","parent_session_id":"root"},{"session_id":"orphan","parent_session_id":"gone"}]); assert [(r["session_id"],r["relationship"],r["depth"]) for r in rows]==[("root","root",0),("child","child",1),("orphan","root",0)]
def test_event_filter_and_cursor_respect_time_agent_model_and_generation():
    events=[{"event_id":"1","agent":"a","model":"m","occurred_at":"2026-09-07T01:00:00Z"},{"event_id":"2","agent":"b","model":"n","occurred_at":"2026-09-08T01:00:00Z"}]
    start=datetime(2026,9,7,tzinfo=timezone.utc); end=datetime(2026,9,8,tzinfo=timezone.utc); assert filter_events(events,start,end,["a"],["m"]).event_id.tolist()==["1"]
    fresh,cursor=monitor_cursor(events,"1"); assert [x["event_id"] for x in fresh]==["2"] and cursor=="2"
def test_lazy_preview_never_requires_raw_and_caps_display(): assert lazy_preview({"display":"x"*5},3)=="xxx…"
def test_equal_previous_period_and_rules_based_summary():
    start,end=period_bounds("오늘",now=datetime(2026,9,7,12,tzinfo=timezone.utc)); assert prior_period(start,end)==(datetime(2026,9,6,tzinfo=timezone.utc),start)
    table,text=comparison_summary(pd.DataFrame({"total_tokens":[20]}),pd.DataFrame({"total_tokens":[5]})); assert table.iloc[-1]["값"]==15 and "증가" in text

def test_usage_filters_apply_time_and_model_without_hiding_empty_usage_sessions():
    start=datetime(2026,9,7,tzinfo=timezone.utc); end=start+timedelta(days=1)
    sessions=[{"session_id":"used","agent":"a"},{"session_id":"empty","agent":"a"}]
    usage=[{"session_id":"used","agent":"a","model":"m","occurred_at":"2026-09-07T02:00:00Z"},{"session_id":"used","agent":"a","model":"x","occurred_at":"2026-09-06T02:00:00Z"}]
    assert filtered_sessions(sessions,start,end,agents=["a"],models=["m"]).session_id.tolist()==["used","empty"]
    assert filtered_usage(usage,start,end,agents=["a"],models=["m"],sessions=sessions).model.tolist()==["m"]

def test_clipped_duration_weighted_ratio_and_arbitrary_subtree():
    start=datetime(2026,9,7,tzinfo=timezone.utc); end=start+timedelta(hours=4)
    sessions=[{"started_at":"2026-09-06T23:00:00Z","last_activity":"2026-09-07T05:00:00Z"}]
    assert clipped_duration_seconds(sessions,start,end).tolist()==[14400]
    assert weighted_cache_ratio([{"input_tokens":100,"cache_read_tokens":50},{"input_tokens":10,"cache_read_tokens":0}]) == 50/110
    graph={"children":{("a","r"):[("a","c")],("a","c"):[("a","g")]}}
    assert subtree_keys(graph,("a","r"))==[("a","r"),("a","c"),("a","g")]
