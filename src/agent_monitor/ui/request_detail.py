"""Selected-session token summary and lazy request tool-call inspection."""
import hashlib
import json

import pandas as pd
import streamlit as st

from ..request_tools import request_tool_history
from .adapter import usage_label
from .presentation import metrics, remember


def session_tokens(usage, requests, agent, session_id):
    selected = usage
    if {"agent", "session_id"} <= set(usage):
        selected = usage[(usage.agent.astype(str) == agent) & (usage.session_id.astype(str) == session_id)]
    else:
        selected = pd.DataFrame()
    st.header("선택 세션 토큰")
    st.caption("현재 기간·필터에 해당하는 이 세션의 직접 사용량입니다. 하위 세션은 제외하며, 미확인 값은 —로 표시합니다.")
    values = [("세션 요청 수", len(requests), "현재 기간과 겹치는 이 세션의 요청 수")]
    averages = []
    for name, label in (("input_tokens", "입력"), ("output_tokens", "출력"), ("total_tokens", "전체")):
        column = pd.to_numeric(selected.get(name, pd.Series(dtype=float)), errors="coerce")
        values.append((f"세션 {label} 토큰", usage_label(column.sum(min_count=1)), f"확인된 {label} 토큰만 합산"))
        per_request = pd.to_numeric(requests.get(name, pd.Series(dtype=float)), errors="coerce").dropna()
        average = f"{per_request.mean():,.1f}" if len(per_request) else "—"
        averages.append(f"{label} {average} (확인 {len(per_request)}/{len(requests)}건)")
    metrics(values, "selected-session")
    st.caption("요청당 평균 토큰: " + " · ".join(averages))


def request_tools(snapshot, requests, agent, session_id, timezone_name):
    st.header("요청별 도구 호출 이력")
    st.caption("요청을 선택하면 수집된 해당 요청의 전체 도구 이력을 표시합니다. 토큰 표의 기간·모델 필터로 호출 결과를 잘라내지 않습니다. 성공 여부는 명시된 오류·종료 코드로만 판단합니다.")
    if requests.empty or "turn_id" not in requests:
        st.info("선택할 요청이 없습니다. 기간·필터와 수집 기록을 확인하세요.")
        return
    choices = {str(row["turn_id"]): row for row in requests.to_dict("records") if pd.notna(row.get("turn_id"))}
    if not choices:
        st.info("요청 ID를 확인할 수 없습니다.")
        return
    owner = hashlib.sha256(f"{agent}\0{session_id}".encode()).hexdigest()[:20]
    selected = remember(st.selectbox, "추적할 요청", options=list(choices), key=f"request-tools:{owner}",
                        format_func=lambda key: f"{choices[key].get('title') or '제목 없음'} · {key}")
    request = choices[selected]
    st.caption("선택 요청 토큰: " + " · ".join(f"{label} {usage_label(request.get(name))}" for name, label in
                                             (("input_tokens", "입력"), ("output_tokens", "출력"), ("total_tokens", "전체"))))
    history = request_tool_history(snapshot.get("events", []), agent, session_id, selected)
    items = history["items"]
    if history["unassigned_calls"]:
        st.warning(f"이 세션의 도구 호출 {history['unassigned_calls']}건은 요청 ID가 없어 요청에 연결하지 않았습니다. 로그 보기에서 확인하세요.")
    if not items:
        st.info("이 요청에 연결된 도구 호출 기록이 없습니다. 도구를 사용하지 않았거나 로그 형식·요청 연결 정보가 부족할 수 있습니다.")
        return
    rows = []
    for index, item in enumerate(items):
        ref = (item["calls"] or item["results"])[0]
        rows.append({"순서": index + 1, "호출 시각": ref["occurred_at"] if item["calls"] else None,
                     "결과 시각": item["results"][-1]["occurred_at"] if item["results"] else None, "도구": item["tool_name"],
                     "상태": item["status"], "호출 ID": item["call_id"],
                     "입력 미리보기": item["calls"][0]["preview"] if item["calls"] else "",
                     "결과 미리보기": "\n".join(result["preview"] for result in item["results"])[:1000]})
    table = pd.DataFrame(rows)
    table["호출 시각"] = pd.to_datetime(table["호출 시각"], errors="coerce", utc=True)
    table["결과 시각"] = pd.to_datetime(table["결과 시각"], errors="coerce", utc=True)
    st.dataframe(table, hide_index=True, width="stretch", column_config={
        "호출 시각": st.column_config.DatetimeColumn("호출 시각", format="MM-DD HH:mm:ss", timezone=timezone_name),
        "결과 시각": st.column_config.DatetimeColumn("결과 시각", format="MM-DD HH:mm:ss", timezone=timezone_name),
        "입력 미리보기": st.column_config.TextColumn(width="large"), "결과 미리보기": st.column_config.TextColumn(width="large"),
    })
    st.caption(f"호출 {sum(bool(item['calls']) for item in items)}건 · 호출 미연결 결과 {sum(not item['calls'] for item in items)}건 · 상세에서 입력·결과와 출처를 확인할 수 있습니다.")
    details = {hashlib.sha256(json.dumps([item['call_id'], (item['calls'] or item['results'])[0]], default=str, sort_keys=True).encode()).hexdigest()[:24]: (index, item)
               for index, item in enumerate(items)}
    picked = remember(st.selectbox, "도구 호출 상세", options=list(details), key=f"tool-detail:{owner}:{selected}",
                      format_func=lambda key: f"{details[key][0] + 1}. {details[key][1]['tool_name']} · {details[key][1]['status']}")
    item = details[picked][1]
    st.caption("입력·결과 미리보기는 각각 최대 1,000자입니다. 전체 원문은 버튼을 누를 때만 읽습니다.")
    for kind, refs in (("호출 입력", item["calls"]), ("호출 결과", item["results"])):
        for index, ref in enumerate(refs):
            with st.expander(f"{kind} {index + 1} · {ref['record_key'] or '기록 번호 미확인'}", expanded=True):
                st.code(ref["preview"] or "미리보기 없음", language=None, wrap_lines=True)
                st.caption(f"출처: {ref['source_path'] or '미확인'} · 기록: {ref['record_key'] or '미확인'}")
                identity = hashlib.sha256(json.dumps([owner, selected, picked, kind, index, ref['event_id']], ensure_ascii=False).encode()).hexdigest()[:24]
                if st.button("도구 원문 불러오기", key=f"tool-raw:{identity}", disabled=not(ref["source_path"] and ref["record_key"])):
                    from ..service import raw_event
                    try:
                        raw = raw_event(agent, session_id, ref["source_path"], str(ref["record_key"]))
                        if raw is None:
                            st.warning("원본을 읽을 수 없습니다. 파일 이동·삭제 또는 기록 변경 여부를 확인하세요.")
                        else:
                            st.json(raw)
                    except (OSError, ValueError) as error:
                        st.error(f"도구 원문을 읽지 못했습니다. 다시 시도하세요: {error}")
