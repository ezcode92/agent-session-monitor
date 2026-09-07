from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any
import pandas as pd
import plotly.express as px
import streamlit as st
from .adapter import append_bounded, clipped_duration_seconds, comparison_summary, event_rows, export_csv, filter_events, filtered_requests, filtered_sessions, filtered_usage, frame, get, hierarchy_rows, lazy_preview, monitor_cursor, monitor_view, period_bounds, prior_period, record, subtree_keys, usage_label, usage_total, weighted_cache_ratio
from .core import CoreContractError, load_snapshot
from .view_data import build_view_data

_NESTED_COLUMNS={"own_usage","child_usage","usage"}
def _scalar_table(value):
    data=frame(value)
    for name in ("own_usage", "child_usage"):
        if name in data:
            data[f"{name}_count"] = data[name].map(lambda rows: len(rows) if isinstance(rows, (list, tuple)) else 0)
    return data.drop(columns=[name for name in _NESTED_COLUMNS if name in data],errors="ignore")

def _view(snapshot, state):
    # Transcript records are fetched only by the selected history log pane.
    # The shared dashboard view is always the lightweight base view.
    include_events = False
    key=(id(snapshot), snapshot.get("generation"), snapshot.get("timezone"), state["start"], state["end"], tuple(state["agents"]), tuple(state["projects"]), tuple(state["models"]), include_events)
    cached=st.session_state.get("view-cache")
    if cached and cached[0] == key: return cached[1]
    value=build_view_data(snapshot,{**state,"start":state["start"],"end":state["end"],"include_events":include_events})
    st.session_state["view-cache"]=(key,value)
    return value

def _snapshot(force=False):
    value = load_snapshot(force=force); required={"sessions","requests","usage","events","diagnostics","paths","scanned_at"}; missing=required-set(value)
    if missing: raise CoreContractError("서비스 스냅샷 필수 필드 누락: " + ", ".join(sorted(missing)))
    return value

def _usage(snapshot, ids, restrict=True):
    data=frame(snapshot["usage"])
    if restrict and "session_id" in data: data=data[data.session_id.isin(ids)].copy()
    if not data.empty: data["total_tokens"]=data.apply(lambda row: usage_total(row.to_dict()),axis=1)
    return data

def _agent_status(snapshot, sessions, configured):
    """Small sidebar inventory that also represents configured empty roots."""
    rows=[]
    for agent in sorted(set(configured) | set(sessions.get("agent", pd.Series(dtype=str)).dropna().astype(str))):
        subset=sessions[sessions.get("agent", pd.Series(dtype=str)).astype(str)==agent] if "agent" in sessions else pd.DataFrame()
        source_values=[]
        if "source_path" in subset:
            source_values.extend(str(value) for value in subset["source_path"].dropna() if str(value))
        if "sources" in subset:
            for values in subset["sources"].dropna():
                if isinstance(values, (list, tuple, set)):
                    source_values.extend(str(value) for value in values if str(value))
        # A configured root is still a source worth reporting when discovery
        # found no readable session beneath it.
        roots=(snapshot.get("paths", {}).get(agent) or snapshot.get("config", {}).get("paths", {}).get(agent) or [])
        rows.append((agent, len(roots), len(set(source_values)), len(subset)))
    return rows

def _filters(snapshot):
    sessions=_scalar_table(snapshot["sessions"])
    # The snapshot and its data were produced from this configuration.  Do not
    # independently reload config here, which can put date boundaries out of sync.
    timezone_name = snapshot.get("timezone") or snapshot.get("config", {}).get("timezone") or "Asia/Seoul"
    with st.sidebar:
        st.title("Agent Session Monitor"); page=st.radio("메뉴",["개요","작업 이력","기간 분석","오케스트레이션","설정"])
        choice=st.selectbox("기간",["최근 7일","오늘","최근 30일","직접 선택"])
        dates=st.date_input("분석 기간",value=(datetime.now().date()-timedelta(days=6),datetime.now().date())) if choice=="직접 선택" else None
        start,end=period_bounds(choice,*(dates if isinstance(dates,tuple) and len(dates)==2 else (None,None)),tz_name=timezone_name)
        configured=set(snapshot.get("paths",{})) | set(snapshot.get("config",{}).get("paths",{})); discovered=set(sessions.get("agent",pd.Series(dtype=str)).dropna().astype(str)); agent_options=sorted(configured|discovered)
        agents=st.multiselect("에이전트",agent_options,format_func=lambda value: "agy (Antigravity)" if value in {"antigravity","agy"} else value)
        projects=st.multiselect("프로젝트",sorted(sessions.get("project",pd.Series(dtype=str)).dropna().astype(str).unique()))
        models=st.multiselect("모델",sorted(frame(snapshot["usage"]).get("model",pd.Series(dtype=str)).dropna().astype(str).unique()))
        refresh = st.toggle("고급: 전체 화면 5초 자동 새로고침", value=False)
        if st.button("지금 새로고침", use_container_width=True):
            from agent_monitor.service import refresh_sources
            with st.spinner("변경된 로그 경로를 확인하는 중…"):
                st.session_state["dashboard_snapshot"] = refresh_sources()
            st.session_state.pop("view-cache", None)
            st.rerun()
        st.caption(f"기간: {choice} · 시간대: {timezone_name}")
        st.caption(f"마지막 스캔: {snapshot['scanned_at']}")
        for agent, roots, files, count in _agent_status(snapshot, sessions, configured):
            label="agy (Antigravity)" if agent in {"antigravity","agy"} else agent
            st.caption(f"{label}: 구성 루트 {roots} · 읽은 로그 파일 {files} · 세션 {count}")
        diagnostics=list(snapshot.get("diagnostics", []))+list(snapshot.get("config_diagnostics", []))
        if diagnostics:
            st.warning(f"진단 {len(diagnostics)}건: 일부 로그 경로를 읽지 못했을 수 있습니다.")
    if refresh: _dashboard_refresh()
    selected=filtered_sessions(sessions,start,end,agents,projects)
    return selected,{"page":page,"start":start,"end":end,"agents":agents,"projects":projects,"models":models}

@st.fragment(run_every="5s")
def _dashboard_refresh():
    """Independent five-second collector refresh; no custom JS is used."""
    current = _snapshot(force=False)
    previous = st.session_state.get("dashboard_snapshot")
    if previous is not None and current.get("generation") != previous.get("generation"):
        st.session_state["dashboard_snapshot"] = current
        st.rerun()
    st.caption(f"자동 갱신 확인: {current['scanned_at']}")

def overview(snapshot,sessions,state,view=None):
    zone=snapshot.get("timezone") or snapshot.get("config", {}).get("timezone") or "UTC"
    view=view or {}; st.header("개요"); usage=view.get("usage_df",pd.DataFrame()); requests=view.get("requests_df",pd.DataFrame())
    summary=(view or {}).get("summary",{}); total=summary.get("total_tokens",usage.total_tokens.sum(min_count=1) if "total_tokens" in usage else None); input_total=summary.get("input_tokens",usage.input_tokens.sum(min_count=1) if "input_tokens" in usage else None); output_total=summary.get("output_tokens",usage.output_tokens.sum(min_count=1) if "output_tokens" in usage else None); cache=usage.cache_read_tokens.sum(min_count=1) if "cache_read_tokens" in usage else None
    known=requests.get("clipped_duration_seconds",pd.Series(dtype=float)).dropna(); average=(summary.get("request_duration_seconds") / len(known)) if len(known) and summary.get("request_duration_seconds") is not None else None; ratio=summary.get("cache_read_ratio",weighted_cache_ratio(usage)); ratio=(ratio*100) if ratio is not None else None
    cols=st.columns(6); cols[0].metric("세션",len(sessions)); cols[1].metric("요청",len(requests)); cols[2].metric("전체 토큰",usage_label(total)); cols[3].metric("입력 / 출력",f"{usage_label(input_total)} / {usage_label(output_total)}"); cols[4].metric("평균 작업 시간",f"{average:.0f}초" if average is not None else "—"); cols[5].metric("캐시 읽기 비율",f"{ratio:.1f}%" if ratio is not None else "—")
    if not usage.empty and "occurred_at" in usage and usage.occurred_at.notna().any():
        daily=usage.dropna(subset=["occurred_at"]).assign(날짜=lambda d:d.occurred_at.dt.tz_convert(zone).dt.date)
        st.plotly_chart(px.line(daily.groupby("날짜").total_tokens.sum(min_count=1).reset_index(),x="날짜",y="total_tokens",title="일별 전체 토큰"),use_container_width=True)
        composition=daily.groupby("날짜")[[name for name in ("input_tokens","output_tokens","cache_read_tokens","cache_creation_tokens") if name in daily]].sum(min_count=1).reset_index()
        if "input_tokens" in composition and "cache_read_tokens" in composition:
            creation=composition.get("cache_creation_tokens",0)
            composition["입력(캐시 제외)"]=(composition.input_tokens-composition.cache_read_tokens-creation).clip(lower=0)
            composition=composition.drop(columns=["input_tokens"])
        st.plotly_chart(px.bar(composition,x="날짜",title="입력·출력·캐시 구성"),use_container_width=True)
        paired=daily.dropna(subset=[name for name in ("input_tokens","cache_read_tokens") if name in daily])
        if not paired.empty and {"input_tokens","cache_read_tokens"} <= set(paired):
            ratios=paired.groupby("날짜")[["input_tokens","cache_read_tokens"]].sum().reset_index(); ratios["cache_ratio"]=ratios.cache_read_tokens/ratios.input_tokens.replace(0,pd.NA)*100
            st.plotly_chart(px.line(ratios,x="날짜",y="cache_ratio",title="일별 가중 캐시 읽기 비율 (%)"),use_container_width=True)
    daily_request=(view or {}).get("daily_request_duration")
    if daily_request is not None and not daily_request.empty:
        st.plotly_chart(px.line(daily_request,x="date",y="duration_seconds",title="기간 내 작업 시간"),use_container_width=True)
    elif not sessions.empty and {"started_at","last_activity"} <= set(sessions):
        timeline=sessions.dropna(subset=["started_at","last_activity"]).copy()
        if not timeline.empty:
            timeline["clip_start"]=timeline.started_at.clip(lower=state["start"]); timeline["clip_end"]=timeline.last_activity.clip(upper=state["end"])
            timeline=timeline[timeline.clip_end>timeline.clip_start]
            if not timeline.empty:
                timeline["date"]=timeline.clip_start.dt.tz_convert(snapshot["timezone"]).dt.date
                daily_duration=timeline.assign(duration_seconds=(timeline.clip_end-timeline.clip_start).dt.total_seconds()).groupby("date").duration_seconds.sum().reset_index()
                st.plotly_chart(px.line(daily_duration,x="date",y="duration_seconds",title="기간 내 작업 시간"),use_container_width=True)
    st.dataframe(_scalar_table(sessions),use_container_width=True,hide_index=True); st.download_button("세션 CSV",export_csv(_scalar_table(sessions)),"sessions.csv","text/csv")

@st.fragment(run_every="1s")
def _live_monitor(agent: str, sid: str):
    from agent_monitor.service import poll_session
    monitor_id=f"{agent}:{sid}"; snapshot=poll_session(sid); key=f"events:{monitor_id}"; generation_key=f"generation:{monitor_id}"
    generation_changed=st.session_state.get(generation_key) not in (None,snapshot.get("generation"))
    if generation_changed:
        # Preserve the paused frozen display and baseline across replacement;
        # only the live collection state belongs to the old generation.
        for prefix in ("events:","cursor:"):
            st.session_state.pop(f"{prefix}{monitor_id}",None)
    st.session_state[generation_key]=snapshot.get("generation"); buffer=st.session_state.setdefault(key,[])
    # Filter dataclass events before DataFrame/asdict conversion: a live
    # session should not materialize every other session's transcript.
    selected_events=[event for event in snapshot["events"] if (event.get("session_id") if isinstance(event,dict) else getattr(event,"session_id",None))==sid and (event.get("agent") if isinstance(event,dict) else getattr(event,"agent",None))==agent]
    full_rows=frame(selected_events).to_dict("records")
    ids_key=f"event-ids:{monitor_id}"; current_ids={str(row.get("event_id")) for row in full_rows}; previous_ids=st.session_state.get(ids_key,set()); added=len(current_ids-previous_ids); st.session_state[ids_key]=current_ids
    cursor_key=f"cursor:{monitor_id}"; incoming, cursor=monitor_cursor(full_rows,st.session_state.get(cursor_key),snapshot.get("generation")); st.session_state[cursor_key]=cursor
    if generation_changed:
        buffer[:]=incoming[-2000:]
    else: append_bounded(buffer,incoming,maximum=2000)
    received_key=f"received:{monitor_id}"; received=st.session_state.get(received_key,0)+added; st.session_state[received_key]=received
    paused=st.session_state.get(f"pause:{monitor_id}",False); basekey=f"pause-base:{monitor_id}"
    if paused:
        baseline=st.session_state.setdefault(basekey,received); frozen=st.session_state.setdefault(f"frozen:{monitor_id}",list(buffer)); display=frame(event_rows(monitor_view(buffer,frozen,st.session_state.get(f"limit:{monitor_id}",200),st.session_state.get(f"follow:{monitor_id}",True)),st.session_state.get(f"noise:{monitor_id}",True))); st.info(f"일시정지 — 새 이벤트 {received-baseline}건 수집됨")
    else:
        st.session_state.pop(basekey,None); st.session_state.pop(f"frozen:{monitor_id}",None); display=frame(event_rows(monitor_view(buffer,None,st.session_state.get(f"limit:{monitor_id}",200),st.session_state.get(f"follow:{monitor_id}",True)),st.session_state.get(f"noise:{monitor_id}",True)))
    st.caption(f"수집 버퍼 {len(buffer)}/2,000건 · 화면 {len(display)}건"); st.dataframe(display,use_container_width=True,hide_index=True)

def _history_events(snapshot, agent, sid, state):
    """Narrow transcript materialization to the selected composite session."""
    rows=[]
    for event in snapshot.get("events", []):
        value=record(event)
        if str(value.get("agent")) != str(agent) or str(value.get("session_id")) != str(sid):
            continue
        rows.append(value)
    data=frame(rows)
    if data.empty: return data
    if "occurred_at" in data:
        data=data[data.occurred_at.notna() & (data.occurred_at >= state["start"]) & (data.occurred_at < state["end"])]
    if state.get("models") and "model" in data: data=data[data.model.isin(state["models"])]
    return data


def history(snapshot,sessions,state,view=None):
    st.header("작업 이력")
    if sessions.empty: st.info("표시할 세션이 없습니다."); return
    query=st.text_input("세션 검색 (제목·ID·프로젝트)"); visible=sessions if not query else sessions[sessions.astype(str).apply(lambda row: row.str.contains(query,case=False,regex=False).any(),axis=1)]
    page=st.number_input("페이지",min_value=1,value=1,step=1); start=(page-1)*50; st.caption(f"검색 결과 {len(visible)}건 · 페이지당 50건"); st.dataframe(visible.iloc[start:start+50],use_container_width=True,hide_index=True)
    if visible.empty: return
    choices=[(str(row.agent),str(row.session_id)) for row in visible.itertuples()]
    choice=st.selectbox("세션",choices,format_func=lambda key: f"{key[0]} · {str(visible[(visible.agent.astype(str)==key[0]) & (visible.session_id.astype(str)==key[1])].iloc[0].get('title') or key[1])} · {key[1]}")
    agent, sid=choice; item=sessions[(sessions.agent.astype(str)==agent) & (sessions.session_id.astype(str)==sid)].iloc[0].to_dict(); st.json({k:item.get(k) for k in ("agent","status","source_label","source_kind","source_path","sources","data_status")})
    st.caption(f"직접 사용량 이벤트 {item.get('own_usage_count', 0)}건 · 하위 세션 사용량 이벤트 {item.get('child_usage_count', 0)}건")
    reqs=(view or {}).get("requests_df",pd.DataFrame()); reqs=reqs[(reqs.session_id.astype(str)==sid) & (reqs.agent.astype(str)==agent)] if {"session_id","agent"} <= set(reqs) else reqs
    monitor_id=f"{agent}:{sid}"; pane=st.radio("세션 보기",["요청","로그","실시간"],horizontal=True,key=f"history-pane:{monitor_id}")
    if pane == "요청":
        st.subheader("요청 사용량·시간·상태"); st.dataframe(_scalar_table(reqs),use_container_width=True,hide_index=True); st.download_button("요청 CSV",export_csv(_scalar_table(reqs)),f"{sid}-requests.csv","text/csv")
    elif pane == "로그":
        raw_events=_history_events(snapshot,agent,sid,state)
        hide_noise=st.toggle("노이즈 이벤트 숨기기",value=True,key=f"history-noise:{monitor_id}")
        normalized=frame(event_rows(raw_events.to_dict("records"),hide_noise))
        st.subheader("정규화된 메시지 이벤트"); st.dataframe(normalized,use_container_width=True,hide_index=True)
        for event in normalized.tail(20).to_dict("records"):
            with st.expander(f"{event.get('occurred_at','')} · {event.get('source_label','')} · {event.get('record_key','')}"):
                st.text(lazy_preview(event)); st.caption("원시 JSON은 자동으로 읽지 않습니다.")
                if st.button("원시 JSON 불러오기", key=f"raw:{choice}:{event.get('event_id') or event.get('record_key')}"):
                    from agent_monitor.service import raw_event
                    st.json(raw_event(agent, sid, str(event.get("source_path")), str(event.get("record_key"))) or {})
    else:
        st.subheader("실시간 이벤트")
        a,b,c,d=st.columns(4); a.toggle("일시정지",key=f"pause:{monitor_id}"); b.toggle("최신 이벤트 따라가기",value=True,key=f"follow:{monitor_id}"); c.toggle("노이즈 숨기기",value=True,key=f"noise:{monitor_id}"); d.selectbox("표시 건수",[50,100,200,500],index=2,key=f"limit:{monitor_id}")
        _live_monitor(agent, sid)

def analysis(snapshot,sessions,state,view=None):
    view=view or {}; st.header("기간 분석"); usage=view.get("usage_df",pd.DataFrame())
    if usage.empty: st.info("분석할 사용량이 없습니다."); return
    group=st.selectbox("비교 기준",[x for x in ("agent","model","source_label") if x in usage]); grouped=usage.groupby(group,dropna=False).total_tokens.sum(min_count=1).reset_index(); st.plotly_chart(px.bar(grouped,x=group,y="total_tokens"),use_container_width=True)
    comparison=view.get("comparison")
    if comparison is None:
        previous_start, previous_end = prior_period(state["start"], state["end"])
        all_sessions=frame(snapshot["sessions"]); previous_sessions=filtered_sessions(all_sessions,previous_start,previous_end,state["agents"],state["projects"])
        previous_usage=filtered_usage(snapshot["usage"],previous_start,previous_end,state["agents"],state["projects"],state["models"],previous_sessions)
        comparison, sentence=comparison_summary(usage,previous_usage)
    else:
        sentence="현재 보기 데이터와 직전 동일 기간을 비교합니다."
    st.subheader("직전 동일 기간 비교"); st.dataframe(comparison,hide_index=True); st.caption(sentence)
    duration=(view or {}).get("requests_df",pd.DataFrame()).get("clipped_duration_seconds",pd.Series(dtype=float)).dropna()
    cache_ratio=weighted_cache_ratio(usage); errors=frame(snapshot["diagnostics"])
    coverage=f"{usage.total_tokens.notna().sum()}/{len(usage)}" if "total_tokens" in usage else "0/0"; stats=pd.DataFrame({"항목":["평균 작업 시간(초)","P90 작업 시간(초)","캐시 읽기 비율","진단/오류","사용량 적용 범위"],"값":[duration.mean() if not duration.empty else None,duration.quantile(.9) if not duration.empty else None,(cache_ratio*100) if cache_ratio is not None else None,len(errors),coverage]}); st.dataframe(stats,hide_index=True)
    granularity=st.selectbox("시간 단위",["시간","일","주","월"]); time_usage=usage.dropna(subset=["occurred_at"]).copy(); freq={"시간":"h","일":"D","주":"W-SUN","월":"M"}[granularity]; time_usage["bucket"]=time_usage.occurred_at.dt.tz_convert(snapshot["timezone"]).dt.to_period(freq).dt.start_time; st.plotly_chart(px.bar(time_usage.groupby("bucket").total_tokens.sum(min_count=1).reset_index(),x="bucket",y="total_tokens",title=f"{granularity}별 토큰"),use_container_width=True)
    if not duration.empty: st.plotly_chart(px.histogram(duration,x=duration,title="작업 시간 분포"),use_container_width=True)
    markdown="# Agent Session Monitor 기간 분석\n\n" + f"기간: {state['start'].isoformat()} ~ {state['end'].isoformat()}\n\n" + sentence + "\n\n## 비교\n\n```csv\n" + comparison.to_csv(index=False) + "```\n\n## 품질 및 작업 시간\n\n```csv\n" + stats.to_csv(index=False) + "```"
    st.download_button("분석 CSV",export_csv(grouped),"analysis.csv","text/csv"); st.download_button("분석 Markdown",markdown,"analysis.md","text/markdown")

def settings(snapshot,sessions,state):
    from agent_monitor.config import default_config, load_config, normalized_timezone, save_config
    from agent_monitor.service import reload_config, update_config
    st.header("설정 · 출처 · 진단")
    config=load_config(); paths=pd.DataFrame([{"agent":a,"path":p} for a, ps in config["paths"].items() for p in ps],columns=["agent","path"])
    timezone_name=st.text_input("IANA timezone", value=snapshot.get("timezone") or config.get("timezone") or "UTC")
    normalized_tz, timezone_error=normalized_timezone({"timezone":timezone_name})
    if timezone_error: st.error(timezone_error["message"])
    edited=st.data_editor(paths,use_container_width=True,hide_index=True,num_rows="dynamic",key="paths-editor")
    left,middle,right=st.columns(3)
    if left.button("설정 저장"):
        if timezone_error:
            st.error("유효한 IANA 시간대를 입력하세요."); return
        new_paths={agent: [] for agent in config.get("paths", {})}
        for row in edited.to_dict("records"):
            if row.get("agent") and row.get("path"): new_paths.setdefault(str(row["agent"]),[]).append(str(row["path"]))
        config.update({"timezone":normalized_tz,"paths":new_paths}); save_config(config); update_config(config); refreshed=_snapshot(force=False); st.session_state["dashboard_snapshot"]=refreshed; st.success("설정을 저장했습니다.")
    if middle.button("기본 경로 복원"):
        restored=default_config(); save_config(restored); reload_config(restored); st.success("기본 경로를 복원했습니다.")
    if right.button("전체 재스캔"):
        reload_config(config); _snapshot(force=True); st.rerun()
    st.subheader("현재 수집 경로"); st.dataframe(frame([{**row,"source_path":row["path"]} for row in paths.to_dict("records")]),use_container_width=True,hide_index=True)
    st.subheader("진단"); st.dataframe(frame(snapshot["diagnostics"]),use_container_width=True,hide_index=True)
    st.subheader("설정 진단"); st.dataframe(frame(snapshot.get("config_diagnostics",[])),use_container_width=True,hide_index=True)

def orchestration_legacy(snapshot,sessions,state):
    st.header("오케스트레이션")
    rows=frame(hierarchy_rows(sessions))
    if rows.empty: st.info("선택 기간에 세션 계층이 없습니다."); return
    roots=int((rows.relationship=="root").sum()); children=int((rows.relationship=="child").sum())
    a,b,c=st.columns(3); a.metric("루트 세션",roots); b.metric("하위 세션",children); c.metric("평균 하위 세션",f"{children / roots:.1f}" if roots else "—")
    cols=[x for x in ("relationship","depth","session_id","parent_session_id","agent","title","status","source_label","source_path","last_activity") if x in rows]
    st.dataframe(rows[cols].sort_values(["depth","last_activity"] if "last_activity" in rows else ["depth"]),use_container_width=True,hide_index=True)
    if "last_activity" in rows and rows.last_activity.notna().any(): st.plotly_chart(px.scatter(rows.dropna(subset=["last_activity"]),x="last_activity",y="depth",color="relationship",hover_data=[x for x in ("session_id","parent_session_id","title") if x in rows],title="세션 계층 타임라인"),use_container_width=True)
    selected=st.selectbox("드릴다운 세션",rows.session_id.astype(str)); detail=rows[rows.session_id.astype(str)==selected].iloc[0].to_dict(); descendants=rows[rows.parent_session_id.astype(str)==selected] if "parent_session_id" in rows else pd.DataFrame()
    st.json(detail); st.subheader("직접 하위 세션"); st.dataframe(descendants,use_container_width=True,hide_index=True)
    st.download_button("계층 CSV",export_csv(rows),"orchestration.csv","text/csv")

def orchestration(snapshot, sessions, state, view=None):
    """Render only the collector's evidence-qualified graph contract."""
    graph_view=(view or {}).get("graph_view", {}); graph = graph_view.get("context") or snapshot.get("orchestration")
    if not isinstance(graph, dict):
        st.error("Orchestration graph is unavailable from the collector service.")
        return
    rows = []
    for key, rollup in (graph_view.get("rollups") or graph.get("rollups", {})).items():
        agent, session_id = key
        rows.append({"agent": agent, "session_id": session_id,
                     "depth": graph.get("depths", {}).get(key), **rollup})
    data = pd.DataFrame(rows)
    session_times = frame(snapshot["sessions"])
    if not data.empty and {"agent", "session_id"} <= set(session_times):
        data = data.merge(session_times[[name for name in ("agent", "session_id", "started_at", "last_activity", "title", "status") if name in session_times]], on=["agent", "session_id"], how="left")
    st.header("Orchestration")
    a, b, c, d = st.columns(4)
    a.metric("Roots", len(graph.get("roots", [])))
    b.metric("Relations", graph.get("relation_count", 0))
    c.metric("Missing parents", graph.get("missing_parent_count", 0))
    d.metric("Cycles", graph.get("cycle_count", 0))
    roots = [(agent, sid) for agent, sid in graph.get("roots", [])]
    subtree=data; keys=[]
    if roots:
        selected = st.selectbox("Root drilldown", roots, format_func=lambda value: f"{value[0]} · {value[1]}")
        selected_key = tuple(selected)
        keys = subtree_keys(graph, selected_key)
        subtree = data[data.apply(lambda row: (row.get("agent"), row.get("session_id")) in keys, axis=1)]
        st.subheader("선택한 루트의 전체 하위 트리")
        st.dataframe(subtree, use_container_width=True, hide_index=True)
        node=st.selectbox("세션 드릴다운", keys, format_func=lambda value: f"{value[0]} · {value[1]}")
        st.json(subtree[(subtree.agent==node[0]) & (subtree.session_id==node[1])].iloc[0].to_dict())
        if st.toggle("실시간 로그 보기", value=False, key=f"graph-live:{node[0]}:{node[1]}"):
            _live_monitor(node[0], node[1])
    else: st.dataframe(data, use_container_width=True, hide_index=True)
    if {"started_at", "last_activity"} <= set(subtree) and subtree.started_at.notna().any():
        timeline = subtree.dropna(subset=["started_at", "last_activity"]).copy()
        if not timeline.empty:
            timeline["lane"] = timeline.agent.astype(str) + ":" + timeline.session_id.astype(str)
            st.plotly_chart(px.timeline(timeline, x_start="started_at", x_end="last_activity", y="lane", color="depth", hover_data=[name for name in ("session_count", "usage_event_count", "total_tokens", "cache_read_tokens", "duration_seconds") if name in timeline]), use_container_width=True)
    st.subheader("Evidence-qualified edges")
    edges=pd.DataFrame(graph.get("edges", []))
    if keys and not edges.empty and {"child","parent"} <= set(edges): edges=edges[edges.child.apply(tuple).isin(keys) & edges.parent.apply(tuple).isin(keys)]
    st.dataframe(edges, use_container_width=True, hide_index=True)
    st.caption(f"Missing placeholders: {graph.get('missing_placeholders', [])}")
    markdown="# 오케스트레이션\n\n```csv\n" + subtree.to_csv(index=False) + "```"
    st.download_button("Graph CSV", export_csv(subtree), "orchestration.csv", "text/csv")
    st.download_button("Graph Markdown", markdown, "orchestration.md", "text/markdown")

def run():
    st.set_page_config(page_title="Agent Session Monitor",layout="wide")
    try:
          snapshot=st.session_state.get("dashboard_snapshot")
          if snapshot is None:
              with st.spinner("로그 인덱스를 확인하는 중…"):
                  snapshot=_snapshot()
              st.session_state["dashboard_snapshot"]=snapshot
    except CoreContractError as error: st.error(f"코어 서비스 계약 오류: {error}"); st.stop()
    sessions,state=_filters(snapshot)
    if state["page"]=="설정": settings(snapshot,sessions,state)
    else: {"개요":overview,"작업 이력":history,"기간 분석":analysis,"오케스트레이션":orchestration}[state["page"]](snapshot,sessions,state,_view(snapshot,state))
