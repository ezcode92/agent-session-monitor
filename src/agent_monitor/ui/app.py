from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any
import os
import pandas as pd
import plotly.express as px
import streamlit as st
from .adapter import append_bounded, clipped_duration_seconds, duration_label, event_rows, export_csv, filter_events, filtered_requests, filtered_sessions, filtered_usage, frame, get, hierarchy_rows, lazy_preview, monitor_cursor, monitor_view, period_bounds, record, request_timeline, subtree_keys, usage_label, usage_total, weighted_cache_ratio
from .core import CoreContractError, load_snapshot
from .view_data import build_view_data
from .help_text import COLUMN_HELP
from .review import review_page, session_review
from .agent_analysis import agent_analysis_page
from .navigation import navigation
from .presentation import apply_styles, metrics, page_header, remember, saved_notice, show_notice
from .request_detail import session_tokens, request_tools

_NESTED_COLUMNS={"own_usage","child_usage","usage"}
def _scalar_table(value):
    data=frame(value)
    for name in ("own_usage", "child_usage"):
        if name in data:
            data[f"{name}_count"] = data[name].map(lambda rows: len(rows) if isinstance(rows, (list, tuple)) else 0)
    return data.drop(columns=[name for name in _NESTED_COLUMNS if name in data],errors="ignore")

def _table(data, *, column_config=None, **kwargs):
    config = {name: {"help": COLUMN_HELP[name]} for name in getattr(data, "columns", []) if name in COLUMN_HELP}
    for name, options in (column_config or {}).items():
        if isinstance(options, dict):
            config[name] = {**config.get(name, {}), **options}
            if not config[name].get("help") and name in COLUMN_HELP:
                config[name]["help"] = COLUMN_HELP[name]
        else:
            config[name] = options
    return st.dataframe(data, column_config=config, **kwargs)


def _duration_table(value):
    data = _scalar_table(value).copy()
    for name, label in (("clipped_duration_seconds", "기간 내 작업 시간 (시:분:초)"), ("duration_seconds", "작업 시간 (시:분:초)")):
        if name in data:
            data[name] = data[name].map(duration_label)
            data = data.rename(columns={name: label})
    return data


def _chart(figure, title, description, *, data=None):
    st.header(title)
    st.caption(description)
    figure.update_layout(title={"text": ""})
    # All line charts here use calendar-day buckets. Sub-day automatic ticks
    # would repeat the same label when formatted without a time component.
    dates = []
    for trace in figure.data:
        if trace.type == "scatter" and trace.mode == "lines":
            trace.mode = "lines+markers"
            dates.extend(trace.x)
    if dates:
        days = pd.DatetimeIndex(dates).dropna().normalize().sort_values()
        if len(days):
            step = max(1, ((days[-1] - days[0]).days + 5) // 6)
            figure.update_xaxes(type="date", tickmode="linear", tick0=days[0].isoformat(),
                                dtick=step * 86_400_000,
                                tickformat="%Y-%m-%d" if days[0].year != days[-1].year else "%m-%d")
    st.plotly_chart(figure, width="stretch", theme="streamlit")
    if data is not None:
        with st.expander(f"{title} 데이터"):
            _table(_duration_table(data), width="stretch", hide_index=True)


def _duration_axis(figure, seconds, axis="y"):
    known = pd.to_numeric(pd.Series(seconds), errors="coerce").dropna()
    if not known.empty:
        maximum = max(float(known.max()), 0)
        ticks = sorted({int(maximum * index / 4 + 0.5) for index in range(5)})
        figure.update_layout(**{f"{axis}axis": {"title": "작업 시간 (시:분:초)", "tickmode": "array", "tickvals": ticks, "ticktext": [duration_label(value) for value in ticks]}})
    return figure


def _duration_line(data):
    display = data.assign(작업시간=data.duration_seconds.map(duration_label))
    figure = px.line(display, x="date", y="duration_seconds", custom_data=["작업시간"], labels={"date": "날짜"})
    figure.update_traces(hovertemplate="날짜: %{x}<br>작업 시간: %{customdata[0]}<extra></extra>")
    return _duration_axis(figure, data.duration_seconds)


def _event_table(data, timezone_name):
    _table(data, width="stretch", hide_index=True,
                 column_order=[name for name in ("occurred_at", "role", "message") if name in data],
                 column_config={"occurred_at": st.column_config.DatetimeColumn("시각", format="MM-DD HH:mm:ss", timezone=timezone_name, width="medium"),
                                "role": st.column_config.TextColumn("역할", width="small"),
                                "message": st.column_config.TextColumn("메시지", width="large")})


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

def _filters(snapshot, page="개요"):
    sessions=_scalar_table(snapshot["sessions"])
    # The snapshot and its data were produced from this configuration.  Do not
    # independently reload config here, which can put date boundaries out of sync.
    timezone_name = snapshot.get("timezone") or snapshot.get("config", {}).get("timezone") or "Asia/Seoul"
    with st.sidebar:
        st.markdown("**Agent Session Monitor**")
        st.caption("Codex 전용 · 로컬 세션 기록 · 작업 회고")
        period_disabled = page in {"회고·개선", "설정"}
        scope_disabled = period_disabled or page == "에이전트 분석"
        choice=remember(st.selectbox,"기간",options=["최근 7일","오늘","최근 30일","직접 선택"],key="filter-period", disabled=period_disabled)
        dates=remember(st.date_input,"분석 기간",value=(datetime.now().date()-timedelta(days=6),datetime.now().date()),key="filter-dates", disabled=period_disabled) if choice=="직접 선택" else None
        start,end=period_bounds(choice,*(dates if isinstance(dates,tuple) and len(dates)==2 else (None,None)),tz_name=timezone_name)
        configured=set(snapshot.get("paths",{})) | set(snapshot.get("config",{}).get("paths",{})); discovered=set(sessions.get("agent",pd.Series(dtype=str)).dropna().astype(str)); agent_options=sorted(configured|discovered)
        agents=remember(st.multiselect,"에이전트",options=agent_options,key="filter-agents",format_func=lambda value: "agy (Antigravity)" if value in {"antigravity","agy"} else value, disabled=scope_disabled)
        projects=remember(st.multiselect,"프로젝트",options=sorted(sessions.get("project",pd.Series(dtype=str)).dropna().astype(str).unique()),key="filter-projects", disabled=scope_disabled)
        models=remember(st.multiselect,"모델",options=sorted(frame(snapshot["usage"]).get("model",pd.Series(dtype=str)).dropna().astype(str).unique()),key="filter-models", disabled=scope_disabled)
        if scope_disabled:
            st.caption("이 화면은 저장한 전체 기록·설정을 표시합니다." if period_disabled else "기간만 적용합니다. 분석할 프로젝트는 본문에서 선택하세요.")
        refresh = st.toggle("고급: 전체 화면 5초 자동 새로고침", value=False)
        if st.button("지금 새로고침", width="stretch"):
            from agent_monitor.service import refresh_sources
            try:
                with st.spinner("변경된 로그 경로를 확인하는 중…"):
                    refreshed = refresh_sources()
                st.session_state["dashboard_snapshot"] = refreshed
                st.session_state.pop("view-cache", None)
                st.session_state.pop("refresh-error", None)
                st.rerun()
            except (CoreContractError, OSError, ValueError) as error:
                st.session_state["refresh-error"] = f"새로고침에 실패해 이전 데이터를 표시합니다. 다시 시도하세요: {error}"
        if st.session_state.get("refresh-error"):
            st.warning(st.session_state["refresh-error"])
        st.caption(f"기간: {choice} · 시간대: {timezone_name}")
        st.caption(f"마지막 스캔: {snapshot['scanned_at']}")
        with st.expander("에이전트별 수집 현황"):
            for agent, roots, files, count in _agent_status(snapshot, sessions, configured):
                label="agy (Antigravity)" if agent in {"antigravity","agy"} else agent
                st.caption(f"{label}: 구성 루트 {roots} · 읽은 로그 파일 {files} · 세션 {count}")
        diagnostics=list(snapshot.get("diagnostics", []))+list(snapshot.get("config_diagnostics", []))
        if diagnostics:
            st.warning(f"진단 {len(diagnostics)}건: 설정에서 수집 상태와 형식 안내를 확인하세요.")
            st.page_link(str(Path(__file__).with_name("pages") / "settings.py"), label="수집 진단 확인")
    if refresh: _dashboard_refresh()
    selected=filtered_sessions(sessions,start,end,agents,projects)
    return selected,{"page":page,"start":start,"end":end,"agents":agents,"projects":projects,"models":models,"timezone":timezone_name}

@st.fragment(run_every="5s")
def _dashboard_refresh():
    """Independent five-second collector refresh; no custom JS is used."""
    try:
        current = _snapshot(force=False)
    except (CoreContractError, OSError, ValueError) as error:
        st.warning(f"자동 갱신에 실패해 이전 데이터를 표시합니다: {error}")
        return
    previous = st.session_state.get("dashboard_snapshot")
    if previous is not None and current.get("generation") != previous.get("generation"):
        st.session_state["dashboard_snapshot"] = current
        st.rerun()
    st.caption(f"자동 갱신 확인: {current['scanned_at']}")

def overview(snapshot,sessions,state,view=None):
    zone=snapshot.get("timezone") or snapshot.get("config", {}).get("timezone") or "UTC"
    view=view or {}; page_header("개요", "선택한 기간과 필터에 해당하는 세션·요청·사용량을 요약합니다. 알 수 없는 값은 —로 표시합니다."); usage=view.get("usage_df",pd.DataFrame()); requests=view.get("requests_df",pd.DataFrame())
    summary=(view or {}).get("summary",{}); total=summary.get("total_tokens",usage.total_tokens.sum(min_count=1) if "total_tokens" in usage else None); input_total=summary.get("input_tokens",usage.input_tokens.sum(min_count=1) if "input_tokens" in usage else None); output_total=summary.get("output_tokens",usage.output_tokens.sum(min_count=1) if "output_tokens" in usage else None); cache=usage.cache_read_tokens.sum(min_count=1) if "cache_read_tokens" in usage else None
    known=requests.get("clipped_duration_seconds",pd.Series(dtype=float)).dropna(); average=(summary.get("request_duration_seconds") / len(known)) if len(known) and summary.get("request_duration_seconds") is not None else None; ratio=summary.get("cache_read_ratio",weighted_cache_ratio(usage)); ratio=(ratio*100) if ratio is not None else None
    metrics([
        ("세션", len(sessions), "선택 기간에 활동한 대화 수"),
        ("요청", len(requests), "선택 세션의 개별 요청 수"),
        ("전체 토큰", usage_label(total), "확인된 사용량 이벤트의 토큰 합계"),
        ("평균 작업 시간", duration_label(average), "시:분:초 · 기간 내 요청 시간의 평균"),
    ], "overview")
    if sessions.empty:
        st.info("아직 수집한 세션이 없습니다. 설정에서 수집 경로와 진단을 확인하세요." if not snapshot.get("sessions") else "현재 조건에 맞는 세션이 없습니다. 기간·에이전트·프로젝트 필터를 조정하세요.")
    average_input = pd.to_numeric(requests.get("input_tokens", pd.Series(dtype=float)), errors="coerce").mean()
    average_output = pd.to_numeric(requests.get("output_tokens", pd.Series(dtype=float)), errors="coerce").mean()
    with st.expander("사용량 지표 상세"):
        metrics([
            ("입력 토큰", usage_label(input_total), "요청에 사용한 입력 토큰 합계"),
            ("출력 토큰", usage_label(output_total), "응답으로 생성한 출력 토큰 합계"),
            ("평균 입력 토큰", f"{average_input:,.1f}" if pd.notna(average_input) else "—", "입력이 확인된 요청당 평균 · 미확인 요청 제외"),
            ("평균 출력 토큰", f"{average_output:,.1f}" if pd.notna(average_output) else "—", "출력이 확인된 요청당 평균 · 미확인 요청 제외"),
            ("캐시 읽기 비율", f"{ratio:.1f}%" if ratio is not None else "—", "입력·캐시가 함께 확인된 기록 기준"),
        ], "usage-detail")
    if not usage.empty and "occurred_at" in usage and usage.occurred_at.notna().any():
        daily=usage.dropna(subset=["occurred_at"]).assign(날짜=lambda d:d.occurred_at.dt.tz_convert(zone).dt.date)
        _chart(px.line(daily.groupby("날짜").total_tokens.sum(min_count=1).reset_index(),x="날짜",y="total_tokens",labels={"total_tokens":"토큰"}), "일별 전체 토큰", "설정한 시간대의 날짜별 토큰 합계입니다. 사용량이 확인된 기록만 합산합니다.", data=daily.groupby("날짜").total_tokens.sum(min_count=1).reset_index())
        with st.expander("입력·출력·캐시 상세"):
            composition=daily.groupby("날짜")[[name for name in ("input_tokens","output_tokens","cache_read_tokens","cache_creation_tokens") if name in daily]].sum(min_count=1).reset_index()
            if "input_tokens" in composition and "cache_read_tokens" in composition:
                creation=composition.get("cache_creation_tokens",0)
                composition["입력(캐시 제외)"]=(composition.input_tokens-composition.cache_read_tokens-creation).clip(lower=0)
                composition=composition.drop(columns=["input_tokens"])
            components = [name for name in composition if name != "날짜"]
            if components:
                composition[components] = composition[components].apply(pd.to_numeric, errors="coerce").astype("Float64")
                composition = composition.rename(columns={"output_tokens": "출력", "cache_read_tokens": "캐시 읽기", "cache_creation_tokens": "캐시 생성", "input_tokens": "입력"})
                _chart(px.bar(composition,x="날짜",y=[name for name in composition if name != "날짜"],barmode="stack",labels={"value":"토큰","variable":"구성"}), "입력·출력·캐시 구성", "날짜별 토큰을 입력·출력·캐시 항목으로 나눠 표시합니다. 입력에서 확인된 캐시를 빼 중복을 줄이며, 미확인 값은 표시하지 않습니다.", data=composition)
            paired=daily.dropna(subset=[name for name in ("input_tokens","cache_read_tokens") if name in daily])
            if not paired.empty and {"input_tokens","cache_read_tokens"} <= set(paired):
                ratios=paired.groupby("날짜")[["input_tokens","cache_read_tokens"]].sum().reset_index(); ratios["cache_ratio"]=ratios.cache_read_tokens/ratios.input_tokens.replace(0,pd.NA)*100
                _chart(px.line(ratios,x="날짜",y="cache_ratio",labels={"cache_ratio":"캐시 읽기 비율 (%)"}), "일별 가중 캐시 읽기 비율 (%)", "입력과 캐시 읽기가 모두 확인된 기록에서 캐시 읽기 합계를 입력 합계로 나눈 비율입니다.", data=ratios)
    daily_request=(view or {}).get("daily_request_duration")
    if daily_request is not None and not daily_request.empty:
        _chart(_duration_line(daily_request), "기간 내 작업 시간", "요청 시간 중 선택 기간에 포함된 부분을 날짜별로 합산합니다. 시:분:초로 표시하며 동시에 진행된 요청 시간은 각각 더합니다.", data=daily_request)
    elif not sessions.empty and {"started_at","last_activity"} <= set(sessions):
        timeline=sessions.dropna(subset=["started_at","last_activity"]).copy()
        if not timeline.empty:
            timeline["clip_start"]=timeline.started_at.clip(lower=state["start"]); timeline["clip_end"]=timeline.last_activity.clip(upper=state["end"])
            timeline=timeline[timeline.clip_end>timeline.clip_start]
            if not timeline.empty:
                timeline["date"]=timeline.clip_start.dt.tz_convert(snapshot["timezone"]).dt.date
                daily_duration=timeline.assign(duration_seconds=(timeline.clip_end-timeline.clip_start).dt.total_seconds()).groupby("date").duration_seconds.sum().reset_index()
                _chart(_duration_line(daily_duration), "기간 내 작업 시간", "요청 시간 정보가 없어 세션의 관측 구간으로 계산합니다. 선택 기간과 겹치는 시간을 시작 날짜별로 합산해 시:분:초로 표시합니다.", data=daily_duration)
    if not requests.empty:
        recent=(requests.sort_values("total_tokens",ascending=False,na_position="last",kind="stable") if "total_tokens" in requests else requests).head(10).copy()
        recent=pd.DataFrame({
            "제목": recent.get("title", recent.get("turn_id", pd.Series(index=recent.index, dtype=str))),
            "에이전트": recent.get("agent", pd.Series(index=recent.index, dtype=str)),
            "상태": recent.get("status", pd.Series(index=recent.index, dtype=str)),
            "작업 시간 (시:분:초)": recent.get("clipped_duration_seconds", pd.Series(index=recent.index, dtype=float)).map(duration_label),
            "토큰": recent.get("total_tokens", pd.Series(index=recent.index, dtype="Int64")).map(usage_label),
            "출처": recent.get("source_label", pd.Series(index=recent.index, dtype=str)),
        })
        st.header("요청 상위 10건")
        st.caption("선택 기간의 토큰 사용량이 큰 요청 10건입니다. 작업 시간은 기간에 포함된 구간만 시:분:초로 표시합니다.")
        _table(recent,width="stretch",hide_index=True)
    with st.expander("세션 목록·내보내기"):
        st.header("세션 목록"); st.caption("선택 기간에 활동한 세션의 제목·상태·출처를 확인하고 CSV로 내려받을 수 있습니다.")
        _table(_scalar_table(sessions),width="stretch",hide_index=True); st.download_button("세션 CSV",export_csv(_scalar_table(sessions)),"sessions.csv","text/csv")

@st.fragment(run_every="1s")
def _live_monitor(agent: str, sid: str):
    from agent_monitor.service import poll_session
    monitor_id=f"{agent}:{sid}"; final_key=f"completed-live:{monitor_id}"
    final_snapshot = st.session_state.get(final_key)
    dashboard = st.session_state.get("dashboard_snapshot", {})
    if final_snapshot is not None and dashboard.get("generation", 0) > final_snapshot.get("generation", 0):
        st.session_state.pop(final_key, None)
        final_snapshot = None
    snapshot=final_snapshot if final_snapshot is not None else poll_session(sid,agent=agent)
    if agent == "codex" and any(get(record(session), "agent") == agent and get(record(session), "session_id") == sid and str(get(record(session), "status", default="")).lower() in {"complete", "completed"} for session in snapshot.get("sessions", [])):
        st.session_state[final_key] = snapshot
        st.info("Codex 작업이 완료되어 실시간 추적을 중지했습니다. 마지막 수집 로그를 표시합니다.")
    key=f"events:{monitor_id}"; generation_key=f"generation:{monitor_id}"
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
    st.caption(f"수집 버퍼 {len(buffer)}/2,000건 · 화면 {len(display)}건"); _event_table(display, snapshot.get("timezone") or "UTC")

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
    page_header("작업 이력", "세션을 선택해 요청별 사용량, 메시지 기록, 실시간 이벤트를 확인합니다.")
    if sessions.empty: st.info("아직 수집한 세션이 없습니다. 설정에서 수집 경로를 확인하세요." if not snapshot.get("sessions") else "현재 조건에 맞는 세션이 없습니다. 기간·필터를 조정하세요."); return
    query=remember(st.text_input,"세션 검색 (제목·ID·프로젝트)",key="history-search"); visible=sessions if not query else sessions[sessions.astype(str).apply(lambda row: row.str.contains(query,case=False,regex=False).any(),axis=1)]
    search_context = (query, tuple(zip(visible.agent.astype(str), visible.session_id.astype(str))))
    if st.session_state.get("history-search-context") != search_context:
        st.session_state.pop("history-page", None)
        st.session_state.pop("_ui:history-page", None)
        st.session_state["history-search-context"] = search_context
    if visible.empty:
        st.info("검색 결과가 없습니다. 제목·ID·프로젝트 검색어를 바꿔 보세요.")
        return
    page=remember(st.number_input,"페이지",min_value=1,max_value=max(1,(len(visible)+49)//50),value=1,step=1,key="history-page"); start=(page-1)*50; st.caption(f"검색 결과 {len(visible)}건 · 페이지당 50건")
    zone = snapshot.get("timezone") or "UTC"
    page_rows = visible.iloc[start:start+50].reset_index(drop=True)
    if page_rows.empty:
        st.info("이 페이지에 표시할 세션이 없습니다.")
        return
    table_key = "history-session-table"
    table_context = tuple((str(row.get("agent")), str(row.get("session_id")), str(row.get("parent_session_id"))) for row in page_rows.to_dict("records"))
    if st.session_state.get("history-table-context") != table_context:
        st.session_state[table_key] = {"selection": {"cells": []}}
        st.session_state["history-table-context"] = table_context
        st.session_state["history-saved-cells"] = []
    st.caption("세션 ID를 선택하면 해당 세션, 부모 ID를 선택하면 부모 세션의 상세를 아래에서 확인할 수 있습니다.")
    def remember_cells():
        st.session_state["history-saved-cells"] = st.session_state[table_key]["selection"]["cells"]
    selection = _table(page_rows,width="stretch",hide_index=True,
                 key=table_key, on_select=remember_cells, selection_mode="single-cell",
                 column_order=[name for name in ("session_id", "parent_session_id", "title", "agent", "status", "last_activity") if name in page_rows],
                 column_config={"session_id":st.column_config.TextColumn("세션 ID", width="small", help="선택하면 해당 세션 상세로 이동합니다."),
                                "parent_session_id":st.column_config.TextColumn("부모 ID", width="small", help="선택하면 같은 에이전트의 부모 세션 상세로 이동합니다."),
                                "title":st.column_config.TextColumn("제목", width="medium"), "agent":st.column_config.TextColumn("에이전트", width="small"), "status":st.column_config.TextColumn("상태", width="small"),
                                "last_activity":st.column_config.DatetimeColumn("최근 활동", format="MM-DD HH:mm", timezone=zone, width="medium")})
    item = page_rows.iloc[0].to_dict()
    choice = (str(item["agent"]), str(item["session_id"]))
    cells = selection.selection.cells or st.session_state.get("history-saved-cells", [])
    st.session_state["history-saved-cells"] = cells
    if cells:
        position, column = cells[-1]
        if 0 <= position < len(page_rows):
            row = page_rows.iloc[position]
            target = row.get("parent_session_id") if column == "parent_session_id" else row.get("session_id")
            if target is None or pd.isna(target) or not str(target):
                st.info("이 세션에는 확인된 부모 세션이 없습니다.")
                return
            choice = (str(row.agent), str(target))
            selected = sessions[(sessions.agent.astype(str)==choice[0]) & (sessions.session_id.astype(str)==choice[1])]
            if selected.empty:
                all_sessions = _scalar_table(snapshot.get("sessions", []))
                if {"agent", "session_id"} <= set(all_sessions):
                    selected = all_sessions[(all_sessions.agent.astype(str)==choice[0]) & (all_sessions.session_id.astype(str)==choice[1])]
                if selected.empty:
                    st.info("선택한 부모 세션의 로그를 찾을 수 없습니다.")
                    return
                st.info("부모 세션이 현재 필터 밖에 있습니다. 요청과 로그에는 현재 기간·필터가 적용됩니다.")
            item = selected.iloc[0].to_dict()
    agent, sid = choice
    st.header("선택 세션 상세")
    st.caption(f"{agent} · {item.get('title') or sid}")
    with st.expander("세션 ID·출처 상세"):
        st.caption(f"에이전트: {agent} · 출처: {item.get('source_label') or '—'} · 형식: {item.get('source_kind') or '—'}")
        st.text("세션 ID"); st.code(sid, language=None, wrap_lines=True)
        primary = item.get("source_path")
        if primary:
            st.text("대표 로그 파일"); st.code(str(primary), language=None, wrap_lines=True)
        sources = item.get("sources")
        additional = list(dict.fromkeys(str(path) for path in sources if path and str(path) != str(primary))) if isinstance(sources, (list, tuple)) else []
        if additional:
            st.text("함께 병합한 추가 로그 파일")
            for path in additional:
                st.code(path, language=None, wrap_lines=True)
        st.caption("대표 파일과 추가 파일이 같은 세션의 기록으로 병합됩니다. 동일한 경로는 한 번만 표시합니다.")
    st.caption(f"직접 사용량 이벤트 {item.get('own_usage_count', 0)}건 · 하위 세션 사용량 이벤트 {item.get('child_usage_count', 0)}건")
    reqs=(view or {}).get("requests_df",pd.DataFrame()); reqs=reqs[(reqs.session_id.astype(str)==sid) & (reqs.agent.astype(str)==agent)] if {"session_id","agent"} <= set(reqs) else reqs
    monitor_id=f"{agent}:{sid}"; pane=remember(st.radio,"세션 보기",options=["요청","로그","실시간","회고"],horizontal=True,key=f"history-pane:{monitor_id}")
    if pane == "요청":
        session_tokens((view or {}).get("usage_df", pd.DataFrame()), reqs, agent, sid)
        st.header("요청 사용량·시간·상태"); st.caption("선택한 세션의 요청별 토큰·상태와 기간 내 작업 시간(시:분:초)입니다. CSV에서 추가 토큰 항목과 초 단위 원본 시간을 확인할 수 있습니다.")
        request_table = _duration_table(reqs)
        _table(request_table,width="stretch",hide_index=True,
                     column_order=[name for name in ("title", "status", "기간 내 작업 시간 (시:분:초)", "input_tokens", "output_tokens", "total_tokens") if name in request_table],
                     column_config={"title":st.column_config.TextColumn("요청", width="medium"), "status":st.column_config.TextColumn("상태", width="small"),
                                    "기간 내 작업 시간 (시:분:초)":st.column_config.TextColumn("작업 시간 (시:분:초)", width="medium"),
                                    "input_tokens":st.column_config.NumberColumn("입력", width="small"), "output_tokens":st.column_config.NumberColumn("출력", width="small"), "total_tokens":st.column_config.NumberColumn("전체", width="small")})
        st.download_button("요청 CSV",export_csv(_scalar_table(reqs)),f"{sid}-requests.csv","text/csv")
        request_tools(snapshot, reqs, agent, sid, zone)
    elif pane == "회고":
        session_review(snapshot, agent, sid)
    elif pane == "로그":
        raw_events=_history_events(snapshot,agent,sid,state)
        hide_noise=st.toggle("노이즈 이벤트 숨기기",value=True,key=f"history-noise:{monitor_id}")
        normalized=frame(event_rows(raw_events.to_dict("records"),hide_noise))
        st.header("정규화된 메시지 이벤트"); st.caption("선택 기간에 기록된 사용자·응답·도구 메시지입니다. 아래 최근 20건을 펼치면 미리보기·출처와 원시 JSON 조회 버튼이 나타납니다."); _event_table(normalized, zone)
        for event in normalized.tail(20).to_dict("records"):
            with st.expander(f"{event.get('occurred_at','')} · {event.get('source_label','')} · {event.get('record_key','')}"):
                st.text(lazy_preview(event)); st.caption(f"출처: {event.get('source_label') or '—'} · 기록: {event.get('record_key') or '—'}")
                if event.get("source_path"):
                    st.code(str(event["source_path"]), language=None, wrap_lines=True)
                st.caption("원시 JSON은 자동으로 읽지 않습니다.")
                if st.button("원시 JSON 불러오기", key=f"raw:{choice}:{event.get('event_id') or event.get('record_key')}"):
                    from agent_monitor.service import raw_event
                    st.json(raw_event(agent, sid, str(event.get("source_path")), str(event.get("record_key"))) or {})
    else:
        if agent == "codex" and str(item.get("status", "")).lower() in {"complete", "completed"}:
            st.info("완료된 Codex 세션은 실시간 추적하지 않습니다. 로그 보기에서 수집된 기록을 확인하세요.")
            return
        st.header("실시간 이벤트"); st.caption("선택 로그를 1초마다 확인합니다. 일시정지는 화면만 멈추며, 수집된 새 이벤트는 재개할 때 표시합니다.")
        a,b,c,d=st.columns(4); remember(a.toggle,"일시정지",key=f"pause:{monitor_id}"); remember(b.toggle,"최신 이벤트 따라가기",value=True,key=f"follow:{monitor_id}"); remember(c.toggle,"노이즈 숨기기",value=True,key=f"noise:{monitor_id}"); remember(d.selectbox,"표시 건수",options=[50,100,200,500],index=2,key=f"limit:{monitor_id}")
        _live_monitor(agent, sid)

def analysis(snapshot,sessions,state,view=None):
    view=view or {}; page_header("기간 분석", "선택 기간의 토큰 사용량과 요청 시간을 비교합니다. 모든 작업 시간 표시는 시:분:초 형식입니다."); usage=view.get("usage_df",pd.DataFrame())
    if usage.empty: st.info("현재 조건에 사용량 기록이 없습니다. 기간·필터와 설정의 수집 진단을 확인하세요. 기록이 없는 값은 0으로 추정하지 않습니다."); return
    left, right = st.columns(2)
    labels = {"agent":"에이전트", "model":"모델", "source_label":"출처", "bucket":"기간 시작", "total_tokens":"토큰"}
    group=remember(left.selectbox,"비교 기준",key="analysis-group",options=[x for x in ("agent","model","source_label") if x in usage], format_func=lambda value: labels[value],help="각 기간 안에서 에이전트·모델·출처별 사용량을 나란히 비교합니다.")
    granularity=remember(right.selectbox,"집계 단위",key="analysis-granularity",options=["일별","주별","월별"],help="설정 시간대 기준입니다. 주는 월요일부터 일요일, 월은 1일부터 묶습니다.")
    time_usage=usage.dropna(subset=["occurred_at"]).copy()
    frequency={"일별":"D", "주별":"W-SUN", "월별":"M"}[granularity]
    local_time=time_usage.occurred_at.dt.tz_convert(snapshot["timezone"]).dt.tz_localize(None)
    time_usage["bucket"]=local_time.dt.to_period(frequency).dt.start_time
    time_usage[group]=time_usage[group].fillna("미확인").astype(str)
    grouped=time_usage.groupby(["bucket",group],dropna=False).total_tokens.sum(min_count=1).reset_index()
    category_chart = px.bar(grouped,x="bucket",y="total_tokens",color=group,barmode="group",labels=labels)
    category_chart.update_xaxes(tickmode="array",tickvals=grouped.bucket.drop_duplicates(),tickformat="%Y-%m" if granularity=="월별" else "%Y-%m-%d")
    _chart(category_chart, "기준별 토큰 사용량", f"{granularity}로 {labels[group]}별 사용량을 비교합니다. 주는 월요일, 월은 1일 기준이며 선택 기간 안의 기록만 합산합니다.", data=grouped)
    duration=(view or {}).get("requests_df",pd.DataFrame()).get("clipped_duration_seconds",pd.Series(dtype=float)).dropna()
    cache_ratio=weighted_cache_ratio(usage); errors=frame(snapshot["diagnostics"])
    coverage=f"{usage.total_tokens.notna().sum()}/{len(usage)}" if "total_tokens" in usage else "0/0"; stats=pd.DataFrame({"항목":["평균 작업 시간 (시:분:초)","P90 작업 시간 (시:분:초)","캐시 읽기 비율","진단/오류","사용량 적용 범위"],"값":[duration_label(duration.mean()),duration_label(duration.quantile(.9)),f"{cache_ratio*100:.1f}%" if cache_ratio is not None else "—",str(len(errors)),coverage]}); st.header("작업 시간·데이터 품질"); st.caption("P90은 요청 90%가 이 시간 이내에 끝났다는 뜻입니다. 적용 범위는 전체 사용량 기록 중 토큰이 확인된 기록 수이며, 진단 수는 전체 수집 기준입니다."); _table(stats.set_index("항목").T,hide_index=True,width="stretch")
    total_chart = px.bar(time_usage.groupby("bucket").total_tokens.sum(min_count=1).reset_index(),x="bucket",y="total_tokens",labels=labels)
    total_chart.update_xaxes(tickmode="array",tickvals=grouped.bucket.drop_duplicates(),tickformat="%Y-%m" if granularity=="월별" else "%Y-%m-%d")
    _chart(total_chart, f"{granularity} 전체 토큰", "위에서 선택한 집계 단위로 전체 토큰의 추이를 표시합니다. CSV에도 같은 집계 단위와 비교 기준이 적용됩니다.", data=time_usage.groupby("bucket").total_tokens.sum(min_count=1).reset_index())
    if not duration.empty:
        distribution = _duration_axis(px.histogram(x=duration, labels={"y":"요청 수"}), duration, axis="x")
        distribution.update_traces(hovertemplate="요청 수: %{y}건<extra></extra>")
        _chart(distribution, "작업 시간 분포", "선택 기간에 포함된 요청 시간을 구간별로 묶은 분포입니다. 가로축은 시:분:초, 세로축은 각 구간의 요청 수입니다.", data=pd.DataFrame({"duration_seconds":duration}))
    markdown="# Agent Session Monitor 기간 분석\n\n" + f"기간: {state['start'].isoformat()} ~ {state['end'].isoformat()}\n집계: {granularity} · {labels[group]}\n\n" + "\n\n## 기준별 토큰 사용량\n\n```csv\n" + grouped.to_csv(index=False) + "```\n\n## 품질 및 작업 시간\n\n```csv\n" + stats.to_csv(index=False) + "```"
    st.download_button("분석 CSV",export_csv(grouped),"analysis.csv","text/csv"); st.download_button("분석 Markdown",markdown,"analysis.md","text/markdown")

def settings(snapshot, sessions, state):
    from agent_monitor.config import default_config, load_config, normalized_timezone, save_config
    from agent_monitor.service import reload_config, update_config
    page_header("설정 · 출처 · 진단", "로그 수집 경로와 표시 시간대를 관리합니다. 오른쪽 위 메뉴에서 시스템·라이트·다크 테마를 선택할 수 있습니다.")
    if st.session_state.pop("settings-reset", False):
        st.session_state.pop("paths-editor", None)
        st.session_state.pop("settings-timezone", None)
        st.session_state.pop("settings-paths-draft", None)
        st.session_state.pop("settings-recover-paths", None)
    recovery = st.session_state.pop("settings-recover-paths", None)
    if recovery is not None:
        # Rebase once after a failed save: the user's full edited rows survive
        # independently of the editor's transient row-index delta state.
        st.session_state["settings-paths-draft"] = recovery
        st.session_state.pop("paths-editor", None)
    try:
        config = load_config()
        paths = pd.DataFrame([{"agent": agent, "path": path} for agent, roots in config["paths"].items() for path in roots], columns=["agent", "path"])
        with st.container(key="asm-settings-fields"):
            st.header("수집 설정")
            st.caption("Codex만 수집합니다. Claude·AGY 수집은 지원 종료되었으며 기존 원본 로그와 저장된 회고는 삭제하지 않습니다.")
            timezone_name = st.text_input("IANA timezone", value=snapshot.get("timezone") or config.get("timezone") or "UTC", key="settings-timezone")
            normalized_tz, timezone_error = normalized_timezone({"timezone": timezone_name})
            if timezone_error:
                st.error(timezone_error["message"])
            editor_paths = st.session_state.get("settings-paths-draft", paths)
            edited = st.data_editor(editor_paths, width="stretch", hide_index=True, num_rows="dynamic", key="paths-editor",
                                    column_config={"agent": st.column_config.SelectboxColumn("에이전트", options=["codex"], required=True, default="codex"), "path": {"help": COLUMN_HELP["path"]}})
            left, middle, right = st.columns(3)
            if left.button("설정 저장", type="primary", width="stretch"):
                if timezone_error:
                    st.error("유효한 IANA 시간대를 입력하세요.")
                else:
                    new_paths = {agent: [] for agent in config.get("paths", {})}
                    for row in edited.to_dict("records"):
                        if row.get("agent") and row.get("path"):
                            if row["agent"] != "codex":
                                raise ValueError("Codex 수집 경로만 설정할 수 있습니다.")
                            new_paths["codex"].append(str(row["path"]))
                    updated = {**config, "timezone": normalized_tz, "paths": new_paths}
                    with st.spinner("설정을 저장하고 수집 상태를 확인하는 중…"):
                        save_config(updated)
                        update_config(updated)
                        refreshed = _snapshot(force=False)
                    st.session_state["dashboard_snapshot"] = refreshed
                    st.session_state["settings-reset"] = True
                    st.session_state.pop("view-cache", None)
                    saved_notice("설정을 저장했습니다.")
                    st.rerun()
            if middle.button("기본 경로 복원", width="stretch"):
                st.session_state["settings-restore-pending"] = True
            if right.button("전체 재스캔", width="stretch"):
                with st.spinner("저장한 경로에서 로그를 다시 읽는 중…"):
                    reload_config(config)
                    refreshed = _snapshot(force=True)
                st.session_state["dashboard_snapshot"] = refreshed
                st.session_state.pop("view-cache", None)
                saved_notice("저장한 경로의 로그를 다시 읽었습니다.")
                st.rerun()
            if st.session_state.get("settings-restore-pending"):
                with st.container(border=True):
                    st.warning("현재 수집 경로와 시간대를 기본 설정으로 교체합니다. 입력 중인 변경도 초기화됩니다. 원본 로그와 저장된 회고는 유지됩니다.")
                    confirm, cancel = st.columns(2)
                    if confirm.button("기본 설정으로 복원", type="primary"):
                        with st.spinner("기본 설정을 복원하는 중…"):
                            restored = default_config()
                            save_config(restored)
                            reload_config(restored)
                            refreshed = _snapshot(force=False)
                        st.session_state["dashboard_snapshot"] = refreshed
                        st.session_state["settings-reset"] = True
                        st.session_state.pop("settings-restore-pending", None)
                        st.session_state.pop("view-cache", None)
                        saved_notice("기본 경로와 시간대를 복원했습니다.")
                        st.rerun()
                    if cancel.button("복원 취소"):
                        st.session_state.pop("settings-restore-pending", None)
                        st.rerun()
        with st.expander("현재 수집 경로"):
            st.caption("Codex의 sessions·archived_sessions 아래 JSONL을 읽습니다. 비활성화된 수집기의 경로는 검사하지 않습니다.")
            _table(paths, width="stretch", hide_index=True)
    except (OSError, ValueError, CoreContractError) as error:
        if "edited" in locals():
            st.session_state["settings-recover-paths"] = edited.copy()
        st.error(f"설정 저장 또는 수집 갱신을 완료하지 못했습니다. 입력을 확인하고 다시 시도하세요: {error}")
    st.header("수집 진단")
    st.caption("파일 접근·로그 형식·경로·시간대 문제를 표시합니다. 진단 없음은 사용량 0을 의미하지 않습니다.")
    for label, items in (("로그 읽기·해석", snapshot.get("diagnostics", [])), ("설정·경로", snapshot.get("config_diagnostics", []))):
        st.subheader(label)
        if items:
            data = frame(items)
            if "kind" in data:
                counts = data.groupby("kind", dropna=False).size().reset_index(name="건수")
                _table(counts, width="stretch", hide_index=True)
                kinds = st.multiselect("진단 유형", sorted(data["kind"].dropna().unique()), key=f"diagnostic-kinds:{label}")
                if kinds:
                    data = data[data["kind"].isin(kinds)]
            _table(data, width="stretch", hide_index=True, column_config={"message": {"help": "진단 원인과 수집에 미치는 영향입니다."}})
        else:
            st.info(f"{label} 진단이 없습니다.")

def orchestration_legacy(snapshot,sessions,state):
    st.header("오케스트레이션")
    rows=frame(hierarchy_rows(sessions))
    if rows.empty: st.info("선택 기간에 세션 계층이 없습니다."); return
    roots=int((rows.relationship=="root").sum()); children=int((rows.relationship=="child").sum())
    a,b,c=st.columns(3); a.metric("루트 세션",roots); b.metric("하위 세션",children); c.metric("평균 하위 세션",f"{children / roots:.1f}" if roots else "—")
    cols=[x for x in ("relationship","depth","session_id","parent_session_id","agent","title","status","source_label","source_path","last_activity") if x in rows]
    _table(rows[cols].sort_values(["depth","last_activity"] if "last_activity" in rows else ["depth"]),width="stretch",hide_index=True)
    if "last_activity" in rows and rows.last_activity.notna().any(): st.plotly_chart(px.scatter(rows.dropna(subset=["last_activity"]),x="last_activity",y="depth",color="relationship",hover_data=[x for x in ("session_id","parent_session_id","title") if x in rows],title="세션 계층 타임라인"),width="stretch")
    selected=st.selectbox("드릴다운 세션",rows.session_id.astype(str)); detail=rows[rows.session_id.astype(str)==selected].iloc[0].to_dict(); descendants=rows[rows.parent_session_id.astype(str)==selected] if "parent_session_id" in rows else pd.DataFrame()
    st.json(detail); st.header("직접 하위 세션"); _table(descendants,width="stretch",hide_index=True)

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
    page_header("오케스트레이션", "로그에 명시된 부모·자식 관계로 세션 계층을 표시합니다. 토큰과 작업 시간 집계에는 현재 기간·필터가 적용됩니다.")
    metrics([
        ("루트 세션", len(graph.get("roots", [])), "부모가 없는 최상위 세션 수"),
        ("관계", graph.get("relation_count", 0), "근거가 확인된 부모·자식 연결 수"),
        ("부모 미확인", graph.get("missing_parent_count", 0), "참조한 부모 기록을 찾지 못한 세션 수"),
        ("순환 관계", graph.get("cycle_count", 0), "부모·자식 관계가 순환하는 오류 수"),
    ], "orchestration")
    if graph.get("missing_parent_count") or graph.get("cycle_count"):
        st.warning("부모 미확인 또는 순환 관계가 있습니다. 아래 관계 근거에서 확인하세요. 근거가 없는 관계는 추정하지 않습니다.")
    roots = [(agent, sid) for agent, sid in graph.get("roots", [])]
    subtree=data; keys=[]
    if roots:
        selected = remember(st.selectbox,"루트 세션 선택",key="graph-root",options=roots, format_func=lambda value: f"{value[0]} · {value[1]}")
        selected_key = tuple(selected)
        keys = subtree_keys(graph, selected_key)
        subtree = data[data.apply(lambda row: (row.get("agent"), row.get("session_id")) in keys, axis=1)]
        st.header("선택한 루트의 전체 하위 트리"); st.caption("들여쓰기는 세션 깊이입니다. 직접 토큰은 해당 세션, 하위 토큰은 자손, 전체 토큰은 둘의 합이며 작업 시간은 겹친 구간을 한 번만 셉니다.")
        tree_rows = subtree.copy()
        order = {key: index for index, key in enumerate(keys)}
        tree_rows["_tree_order"] = tree_rows.apply(lambda row: order[(row.get("agent"), row.get("session_id"))], axis=1)
        tree_rows = tree_rows.sort_values("_tree_order")
        root_depth = graph.get("depths", {}).get(selected_key, 0)
        titles = tree_rows.get("title", tree_rows["session_id"]).fillna("").astype(str)
        depths = tree_rows["depth"].fillna(root_depth).astype(int)
        tree_rows["제목"] = ["  " * max(depth - root_depth, 0) + (title or str(session_id))
                           for depth, title, session_id in zip(depths, titles, tree_rows["session_id"])]
        for source, label in (("own_total", "직접 토큰"), ("descendant_total", "하위 토큰"), ("total_tokens", "전체 토큰")):
            tree_rows[label] = pd.to_numeric(tree_rows[source], errors="coerce").astype("Int64") if source in tree_rows else pd.Series(pd.NA, index=tree_rows.index, dtype="Int64")
        if "duration_seconds" in tree_rows:
            tree_rows["작업 시간 (시:분:초)"] = tree_rows.duration_seconds.map(duration_label)
        columns = [name for name in ("제목", "직접 토큰", "하위 토큰", "전체 토큰", "작업 시간 (시:분:초)", "agent", "session_id", "status", "source_label", "source_path") if name in tree_rows]
        _table(tree_rows[columns], width="stretch", hide_index=True)
        node=remember(st.selectbox,"세션 드릴다운",key="graph-node",options=keys, format_func=lambda value: f"{value[0]} · {value[1]}")
        st.caption("선택 세션의 상세 집계입니다. 시간은 시:분:초로 표시하며, 알 수 없는 사용량은 비워 둡니다."); st.json(_duration_table(subtree[(subtree.agent==node[0]) & (subtree.session_id==node[1])]).iloc[0].to_dict())
        selected_status = subtree[(subtree.agent==node[0]) & (subtree.session_id==node[1])].iloc[0].get("status")
        completed = node[0] == "codex" and str(selected_status).lower() in {"complete", "completed"}
        if completed:
            st.caption("완료된 Codex 세션은 실시간 추적하지 않습니다.")
        if st.toggle("실시간 로그 보기", value=False, disabled=completed, key=f"graph-live:{node[0]}:{node[1]}") and not completed:
            _live_monitor(node[0], node[1])
    else: _table(_duration_table(data), width="stretch", hide_index=True)
    timeline = request_timeline((view or {}).get("requests_df", pd.DataFrame()), keys, state.get("start"), state.get("end"))
    if not timeline.empty:
        zone = snapshot.get("timezone", "UTC")
        timeline["lane"] = timeline.agent.astype(str) + ":" + timeline.session_id.astype(str)
        timeline["작업 시간"] = timeline.clipped_duration_seconds.map(duration_label)
        timeline["요청"] = timeline.get("title", timeline["turn_id"]).fillna(timeline["turn_id"]).astype(str)
        timeline["status"] = timeline.get("status", pd.Series("미확인", index=timeline.index)).fillna("미확인")
        # Plotly dates have no configurable display timezone: convert once for both axis and hover.
        for name in ("clip_start", "clip_end"):
            timeline[name] = timeline[name].dt.tz_convert(zone).dt.tz_localize(None)
        figure = px.timeline(timeline, x_start="clip_start", x_end="clip_end", y="lane", color="status",
                             custom_data=["요청", "작업 시간", "clip_start", "clip_end"],
                             category_orders={"lane":[f"{agent}:{sid}" for agent,sid in keys]}, labels={"lane":"세션", "status":"상태"})
        figure.update_traces(marker_line_width=1, marker_line_color="white",
                             hovertemplate="세션: %{y}<br>요청: %{customdata[0]}<br>작업 시간: %{customdata[1]}<br>시작: %{customdata[2]}<br>종료: %{customdata[3]}<extra>%{fullData.name}</extra>")
        figure.update_layout(barmode="overlay", xaxis_title=f"시각 ({zone})")
        figure.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=[f"{agent}:{sid}" for agent,sid in keys])
        _chart(figure, "세션 실행 타임라인", "요청마다 막대를 나눠 요청 사이 공백과 세션 간 겹침을 표시합니다. 선택 기간 안의 관측 구간이며, 막대에 마우스를 올리면 요청·시작·종료·작업 시간을 볼 수 있습니다.", data=timeline[["lane","요청","clip_start","clip_end","작업 시간","status"]])
    else:
        st.header("세션 실행 타임라인")
        st.info("선택 기간에 시작·종료 시각이 확인된 요청 구간이 없습니다.")
    with st.expander("관계 근거 상세"):
        st.header("부모·자식 관계"); st.caption("명시적 로그 근거로 확인된 부모·자식 연결입니다. 같은 세션 ID라도 에이전트가 다르면 별도로 취급합니다.")
        edges=pd.DataFrame(graph.get("edges", []))
        if keys and not edges.empty and {"child","parent"} <= set(edges): edges=edges[edges.child.apply(tuple).isin(keys) & edges.parent.apply(tuple).isin(keys)]
        _table(edges, width="stretch", hide_index=True)
        st.write({"부모 미확인 참조": graph.get("missing_placeholders", [])})

def run():
    st.set_page_config(page_title="Agent Session Monitor",layout="wide")
    apply_styles()
    page = navigation()
    try:
          snapshot=st.session_state.get("dashboard_snapshot")
          if snapshot is None:
              with st.spinner("로그 인덱스를 확인하는 중…"):
                  snapshot=_snapshot()
              st.session_state["dashboard_snapshot"]=snapshot
    except CoreContractError as error: st.error(f"코어 서비스 계약 오류: {error}"); st.stop()
    sessions,state=_filters(snapshot, page.title)
    st.session_state["ui-context"] = (snapshot, sessions, state)
    with st.container(key="asm-content"):
        show_notice()
        if os.environ.get("AGENT_MONITOR_AUDIT_MODE") == "synthetic":
            st.info("외부 브라우저 점검용 합성 데이터입니다. 실제 세션 로그와 사용자 데이터베이스는 사용하지 않습니다.")
        page.run()


def render_page(page):
    snapshot, sessions, state = st.session_state["ui-context"]
    if page == "설정": settings(snapshot,sessions,state)
    elif page == "회고·개선": review_page(snapshot)
    elif page == "에이전트 분석": agent_analysis_page(snapshot, state)
    else: {"개요":overview,"작업 이력":history,"기간 분석":analysis,"오케스트레이션":orchestration}[page](snapshot,sessions,state,_view(snapshot,state))
