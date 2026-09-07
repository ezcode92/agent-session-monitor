from datetime import datetime, timedelta, timezone
import pandas as pd
from streamlit.testing.v1 import AppTest
from agent_monitor.models import Session, Usage
from agent_monitor.ui.app import _agent_status, _history_events, _scalar_table
from agent_monitor.ui.adapter import append_bounded, append_unique, clipped_duration_seconds, event_rows, export_csv, filter_events, filtered_requests, filtered_sessions, filtered_usage, frame, hierarchy_rows, lazy_preview, monitor_cursor, monitor_view, period_bounds, recent_records, source_label, subtree_keys, usage_label, usage_total, weighted_cache_ratio
from agent_monitor.ui.view_data import build_view_data

def test_missing_usage_is_never_shown_as_zero(): assert usage_total({}) is None and usage_label(None)=="—"
def test_record_is_shallow_for_nested_dataclass_fields():
    session=Session('s','codex',None,'p',None,None,None,None,own_usage=[Usage(total_tokens=1)])
    assert frame([session]).iloc[0].own_usage[0].total_tokens == 1
def test_scalar_table_hides_nested_usage_columns():
    assert "own_usage" not in _scalar_table([{"session_id":"s","own_usage":[1],"child_usage":[2]}]).columns

def test_agent_status_keeps_configured_empty_antigravity_root():
    rows=dict((agent,(roots,files,sessions)) for agent,roots,files,sessions in _agent_status(
        {"paths":{"antigravity":["C:/a/.gemini/antigravity"]}}, pd.DataFrame([{"agent":"codex","session_id":"s","source_path":"C:/codex/s"}]), {"antigravity"}))
    assert rows["antigravity"] == (1,0,0) and rows["codex"] == (0,1,1)

def test_scalar_session_table_has_usage_counts_without_nested_lists():
    result=_scalar_table([{"session_id":"s","own_usage":[1,2],"child_usage":[3]}])
    assert result.loc[0,"own_usage_count"] == 2 and result.loc[0,"child_usage_count"] == 1

def test_sidebar_shows_configured_antigravity_and_diagnostics():
    source='''import streamlit as st
import agent_monitor.ui.app as ui
from datetime import datetime, timezone
at=datetime(2026,9,7,tzinfo=timezone.utc)
s={"timezone":"UTC","config":{"timezone":"UTC","paths":{"antigravity":["C:/a/.gemini/antigravity"]}},"sessions":[{"agent":"codex","session_id":"s","started_at":at,"last_activity":at}],"requests":[],"usage":[],"events":[],"diagnostics":["unreadable"],"config_diagnostics":[],"paths":{"antigravity":["C:/a/.gemini/antigravity"]},"scanned_at":at,"generation":1,"orchestration":{}}
ui._snapshot=lambda force=False:s
ui.run()'''
    app=AppTest.from_string(source).run()
    assert "agy (Antigravity)" in app.multiselect[0].options
    assert any("진단 1건" in item.value for item in app.warning)

def test_manual_refresh_uses_cached_source_refresh_and_rerenders_snapshot():
    source='''import agent_monitor.service as service
import agent_monitor.ui.app as ui
from datetime import datetime, timezone
at=datetime(2026,9,7,tzinfo=timezone.utc)
def snap(total, generation):
 return {"timezone":"UTC","config":{"paths":{}},"sessions":[{"agent":"codex","session_id":"s","started_at":at,"last_activity":at}],"requests":[],"usage":[{"agent":"codex","session_id":"s","event_id":str(generation),"total_tokens":total,"occurred_at":at}],"events":[],"diagnostics":[],"config_diagnostics":[],"paths":{},"scanned_at":at,"generation":generation,"orchestration":{}}
ui._snapshot=lambda force=False:snap(1,1)
service.refresh_sources=lambda:snap(2,2)
ui.run()'''
    app=AppTest.from_string(source).run()
    next(button for button in app.button if button.label == "지금 새로고침").click().run(timeout=10)
    assert next(metric.value for metric in app.metric if metric.label == "전체 토큰") == "2"

def test_orchestration_does_not_poll_live_log_until_enabled():
    source='''import pandas as pd
import agent_monitor.ui.app as ui
from datetime import datetime, timezone
at=datetime(2026,9,7,tzinfo=timezone.utc)
original_live_monitor=ui._live_monitor
ui._live_monitor=lambda agent,sid: (_ for _ in ()).throw(AssertionError("unexpected poll"))
snapshot={"sessions":[{"agent":"a","session_id":"r","started_at":at,"last_activity":at}],"orchestration":{"roots":[("a","r")],"children":{("a","r"):[]},"depths":{("a","r"):0},"edges":[]}}
view={"graph_view":{"context":snapshot["orchestration"],"rollups":{("a","r"):{"total_tokens":1}}}}
ui.orchestration(snapshot,pd.DataFrame(snapshot["sessions"]),{},view)
ui._live_monitor=original_live_monitor'''
    app=AppTest.from_string(source).run()
    assert not app.exception

def test_orchestration_selected_subtree_uses_indented_titles_and_numeric_token_columns():
    source='''import pandas as pd
import agent_monitor.ui.app as ui
from datetime import datetime, timezone
at=datetime(2026,9,7,tzinfo=timezone.utc)
snapshot={"sessions":[{"agent":"a","session_id":"root","title":"root","started_at":at,"last_activity":at},{"agent":"a","session_id":"child","title":"child","started_at":at,"last_activity":at}],"orchestration":{"roots":[("a","root")],"children":{("a","root"):[("a","child")],("a","child"):[]},"depths":{("a","root"):0,("a","child"):1},"edges":[]}}
view={"graph_view":{"context":snapshot["orchestration"],"rollups":{("a","child"):{"own_total":None,"descendant_total":None,"total_tokens":None},("a","root"):{"own_total":10,"descendant_total":None,"total_tokens":30}}}}
ui.orchestration(snapshot,pd.DataFrame(snapshot["sessions"]),{},view)'''
    app=AppTest.from_string(source).run()
    table=next(item.value for item in app.dataframe if {"제목","직접 토큰","하위 토큰","전체 토큰"} <= set(item.value.columns))
    assert table["제목"].tolist()==["root","  child"]
    assert table[["직접 토큰","하위 토큰","전체 토큰"]].apply(pd.api.types.is_numeric_dtype).all()
    assert table["전체 토큰"].iloc[0] == 30 and pd.isna(table["전체 토큰"].iloc[1])

def test_live_monitor_passes_composite_session_identity_to_polling_service():
    source='''import agent_monitor.service as service
import agent_monitor.ui.app as ui
calls=[]
original_poll_session=service.poll_session
try:
 service.poll_session=lambda session_id,agent=None: calls.append((session_id,agent)) or {"events":[],"generation":1}
 ui._live_monitor("codex","same")
finally:
 service.poll_session=original_poll_session
assert calls == [("same","codex")]'''
    app=AppTest.from_string(source).run()
    assert not app.exception

def test_total_fallback_does_not_double_count_cache_read(): assert usage_total({"input_tokens":10,"cache_read_tokens":8,"output_tokens":2})==12
def test_usage_total_requires_both_fallback_parts(): assert usage_total({"input_tokens":10}) is None

def test_session_and_request_intervals_overlap_period():
    start=datetime(2026,9,7,tzinfo=timezone.utc); end=start+timedelta(days=1)
    sessions=[{"session_id":"agy","started_at":"2026-09-06T23:00:00Z","last_activity":"2026-09-07T01:00:00Z"}]
    requests=[{"session_id":"agy","started_at":"2026-09-06T23:00:00Z","ended_at":"2026-09-07T01:00:00Z"}]
    assert filtered_sessions(sessions,start,end).session_id.tolist()==["agy"]
    assert filtered_requests(requests,start,end,sessions=sessions).session_id.tolist()==["agy"]

def test_qualified_session_membership_is_vectorized_and_keeps_legacy_agentless_rows():
    selected=[{"agent":"a","session_id":"same"}]
    requests=[{"agent":"a","session_id":"same"},{"agent":"b","session_id":"same"}]
    usage=[{"agent":"a","session_id":"same"},{"agent":"b","session_id":"same"}]
    assert filtered_requests(requests, sessions=selected).agent.tolist()==["a"]
    assert filtered_usage(usage, sessions=selected).agent.tolist()==["a"]
    assert filtered_requests([{"session_id":"same"}], sessions=selected).session_id.tolist()==["same"]
    assert filtered_usage(usage, sessions=[]).empty

def test_history_log_filter_is_narrow_and_base_view_has_no_events():
    start=datetime(2026,9,7,tzinfo=timezone.utc); end=start+timedelta(days=1)
    snapshot={"events":[{"agent":"a","session_id":"same","event_id":"keep","occurred_at":start},{"agent":"b","session_id":"same","event_id":"drop","occurred_at":start}]}
    state={"start":start,"end":end,"models":[]}
    assert _history_events(snapshot,"a","same",state).event_id.tolist()==["keep"]
    base=build_view_data({"sessions":[{"agent":"a","session_id":"same","started_at":start,"last_activity":end}],"usage":[],"requests":[],"events":snapshot["events"],"orchestration":{}},{**state,"agents":[],"projects":[],"include_events":False})
    assert base["events_df"].empty

def test_history_panes_are_lazy_and_realtime_polls_composite_identity():
    source='''import pandas as pd
import agent_monitor.service as service
import agent_monitor.ui.app as ui
from datetime import datetime, timezone, timedelta
at=datetime(2026,9,7,tzinfo=timezone.utc)
calls=[]
def poll_session(session_id, agent=None):
 calls.append((agent, session_id))
 return {"events":[],"generation":1}
original_poll_session=service.poll_session
snapshot={"events":[{"agent":"a","session_id":"same","event_id":"keep","display":"keep","occurred_at":at},{"agent":"b","session_id":"same","event_id":"drop","display":"drop","occurred_at":at}]}
sessions=pd.DataFrame([{"agent":"a","session_id":"same","started_at":at,"last_activity":at,"title":"one"}])
view={"requests_df":pd.DataFrame([{"agent":"a","session_id":"same","turn_id":"t","total_tokens":3}])}
state={"start":at-timedelta(hours=1),"end":at+timedelta(hours=1),"models":[]}
try:
 service.poll_session=poll_session
 ui.history(snapshot,sessions,state,view)
finally:
 service.poll_session=original_poll_session
import streamlit as st
st.session_state["poll-calls"]=calls'''
    app=AppTest.from_string(source).run()
    assert app.radio[0].options == ["요청","로그","실시간"]
    assert app.session_state["poll-calls"] == []
    assert not app.button
    app.radio[0].set_value("로그").run(timeout=10)
    assert not app.exception
    assert app.session_state["poll-calls"] == []
    log_frame = next(element.value for element in app.dataframe if "event_id" in element.value.columns)
    assert log_frame.event_id.tolist() == ["keep"]
    app.radio[0].set_value("실시간").run(timeout=10)
    assert not app.exception
    assert app.session_state["poll-calls"] == [("a", "same")]

def test_view_cache_reuses_same_snapshot_and_state():
    source='''import agent_monitor.ui.app as ui
calls=[]
original_build_view_data=ui.build_view_data
ui.build_view_data=lambda snapshot,state: calls.append((snapshot,state)) or {"calls":len(calls)}
snapshot={"generation":1,"timezone":"UTC"}
state={"start":"start","end":"end","agents":[],"projects":[],"models":[]}
first=ui._view(snapshot,state)
second=ui._view(snapshot,state)
assert first is second and len(calls)==1
ui.build_view_data=original_build_view_data'''
    app=AppTest.from_string(source).run()
    assert not app.exception
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


def test_duration_labels_preserve_unknown_and_do_not_wrap_at_one_day():
    from agent_monitor.ui.adapter import duration_label
    assert [duration_label(value) for value in (0, 59, 60, 3599.6, 3661, 90061)] == ["00:00:00", "00:00:59", "00:01:00", "01:00:00", "01:01:01", "25:01:01"]
    assert all(duration_label(value) == "—" for value in (None, pd.NA, float("nan"), float("inf"), -1))
