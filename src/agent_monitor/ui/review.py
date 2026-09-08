"""Personal task retrospectives and evidence-backed improvement actions."""
from __future__ import annotations

import sqlite3
import streamlit as st

from ..insights import analyze_task
from ..review_store import ACTION_STATES, OUTCOMES, TASK_TYPES, ReviewStore
from .adapter import record


def _members(snapshot):
    result = {}
    for item in snapshot.get("sessions", []):
        row = record(item)
        key = (str(row["agent"]), str(row["session_id"]))
        result[key] = {"agent": key[0], "session_id": key[1], "title": row.get("title") or key[1], "project": row.get("project") or ""}
    return result


def _evidence(snapshot, refs, key):
    if not refs:
        return
    position = st.selectbox("근거 로그", range(len(refs)),
                            format_func=lambda index: f"{refs[index].get('agent')} · {refs[index].get('session_id')} · 기록 {refs[index].get('record_key') or '미확인'}",
                            key=f"evidence:{key}")
    ref = refs[position]
    rows = snapshot.get("usage" if ref.get("kind") == "usage" else "events", [])
    current = next((record(row) for row in rows if all(str(record(row).get(field) or "") == str(ref.get(field) or "")
                                                    for field in ("agent", "session_id", "event_id", "source_path", "record_key"))), None)
    st.caption(f"출처: {ref.get('source_path') or '미확인'} · 기록: {ref.get('record_key') or '미확인'}")
    if current is None:
        st.info("이 근거는 현재 수집된 로그에서 찾을 수 없습니다. 저장된 회고와 개선 항목은 유지됩니다.")
        return
    st.text(current.get("display") or f"입력 토큰: {current.get('input_tokens', '미확인')}")
    if ref.get("source_path") and ref.get("record_key") and st.button("근거 원문 보기", key=f"raw-evidence:{key}:{position}"):
        from ..service import raw_event
        raw = raw_event(ref["agent"], ref["session_id"], ref["source_path"], ref["record_key"])
        if raw is None:
            st.info("원본을 읽을 수 없습니다. 로그 이동·삭제 또는 변경 여부를 확인하세요.")
        else:
            st.json(raw)


def _actions(store, snapshot, actions, prefix):
    if not actions:
        st.info("기록한 개선 항목이 없습니다.")
    for action in actions:
        key = f"{prefix}:{action['action_id']}"
        with st.expander(f"{ACTION_STATES[action['status']]} · {action['title']}"):
            st.caption(f"작업: {action['task_title']} · 기록: {action['created_at']}")
            if action["applied_at"]:
                st.caption(f"적용 기록: {action['applied_at']}")
            with st.form(f"action:{key}"):
                title = st.text_input("개선 내용", value=action["title"], max_chars=1000, key=f"action-title:{key}")
                status = st.selectbox("실천 상태", list(ACTION_STATES), index=list(ACTION_STATES).index(action["status"]),
                                      format_func=ACTION_STATES.get, key=f"action-status:{key}")
                if st.form_submit_button("개선 항목 저장"):
                    store.update_action(action["action_id"], title=title, status=status)
                    st.rerun()
            _evidence(snapshot, action["evidence"], key)


def _task(store, snapshot, task):
    task_id = task["task_id"]
    current = _members(snapshot)
    saved = {(member["agent"], member["session_id"]): member for member in task["sessions"]}
    occupied = {(member["agent"], member["session_id"]) for other in store.list_tasks()
                if other["task_id"] != task_id for member in other["sessions"]}
    available = {**saved, **{key: member for key, member in current.items() if key not in occupied}}
    st.subheader("작업 회고")
    st.caption("작업 결과는 직접 평가합니다. 세션 완료 상태나 토큰 수로 성공 여부를 정하지 않습니다.")
    missing = len(set(saved) - set(current))
    st.caption(f"연결 세션 {len(saved)}개 · 현재 로그 미확인 {missing}개. 회고와 문제 신호는 연결된 세션의 전체 이력을 기준으로 합니다.")
    with st.form(f"task:{task_id}"):
        title = st.text_input("작업 이름", value=task["title"], max_chars=200, key=f"title:{task_id}")
        kind = st.selectbox("작업 유형", list(TASK_TYPES), index=list(TASK_TYPES).index(task["task_type"]), format_func=TASK_TYPES.get, key=f"type:{task_id}")
        outcome = st.selectbox("작업 결과", list(OUTCOMES), index=list(OUTCOMES).index(task["outcome"]), format_func=OUTCOMES.get, key=f"outcome:{task_id}")
        members = st.multiselect("연결할 세션", list(available), default=list(saved),
                                 format_func=lambda key: f"{key[0]} · {available[key]['title']} · {key[1]}", key=f"members:{task_id}",
                                 help="한 세션은 한 작업에 연결됩니다. 다른 작업의 세션은 그 작업에서 연결을 해제한 뒤 선택할 수 있습니다.")
        went_well = st.text_area("잘된 점", value=task["went_well"], max_chars=4000, key=f"well:{task_id}")
        blocked_by = st.text_area("막힌 점", value=task["blocked_by"], max_chars=4000, key=f"blocked:{task_id}")
        next_change = st.text_area("다음에 바꿀 행동", value=task["next_change"], max_chars=4000, key=f"next:{task_id}")
        if st.form_submit_button("회고 저장"):
            store.save_task(task_id=task_id, title=title, task_type=kind, outcome=outcome,
                            sessions=[available[key] for key in members], went_well=went_well, blocked_by=blocked_by, next_change=next_change)
            st.rerun()
    st.subheader("확인할 문제 신호")
    result = analyze_task(snapshot, task["sessions"])
    coverage = result["coverage"]
    st.caption(f"도구 호출 {coverage['tool_calls']}건 · 결과 연결 {coverage['paired_results']}건 · 입력 토큰 확인 {coverage['known_inputs']}/{coverage['usage_events']}건")
    st.caption("반복 실패·같은 파일 조회는 동일 요청 3회 이상, 입력 증가는 같은 세션·모델에서 3배 이상이면서 4,096토큰 이상 증가할 때 표시합니다. 반복이나 증가 자체가 낭비를 뜻하지는 않습니다.")
    if not result["signals"]:
        st.info("확인 가능한 기록에서 기준에 해당하는 신호가 없습니다. 메타데이터가 없거나 적으면 판단할 수 없습니다.")
    recorded = {action["signal_id"] for action in store.list_actions(task_id)}
    for signal in result["signals"]:
        key = f"{task_id}:{signal['signal_id']}"
        with st.expander(f"{signal['title']} · {signal['count']}건"):
            st.write(signal["detail"])
            st.write(f"검토할 행동: {signal['suggestion']}")
            _evidence(snapshot, signal["evidence"], key)
            if st.button("개선 항목으로 기록", key=f"capture:{key}", disabled=signal["signal_id"] in recorded):
                store.add_action(task_id, signal["suggestion"], signal["evidence"], signal["signal_id"])
                st.rerun()
            if signal["signal_id"] in recorded:
                st.caption("이미 개선 항목으로 기록했습니다.")
    st.subheader("이 작업의 개선 항목")
    with st.form(f"new-action:{task_id}", clear_on_submit=True):
        action_title = st.text_input("실천할 행동", max_chars=1000, key=f"new-action-title:{task_id}")
        if st.form_submit_button("개선 항목 추가"):
            store.add_action(task_id, action_title)
            st.rerun()
    _actions(store, snapshot, store.list_actions(task_id), f"task-actions:{task_id}")


def session_review(snapshot, agent, session_id):
    try:
        store = ReviewStore()
        task = store.task_for_session(agent, session_id)
        if task:
            _task(store, snapshot, task)
            return
        member = _members(snapshot)[(agent, session_id)]
        st.subheader("이 세션의 작업 기록")
        st.caption("세션을 작업에 연결하면 결과·회고·개선 항목을 재시작 후에도 보관할 수 있습니다.")
        with st.form(f"create-task:{agent}:{session_id}"):
            title = st.text_input("새 작업 이름", value=str(member["title"])[:200], max_chars=200)
            if st.form_submit_button("이 세션으로 작업 만들기"):
                store.save_task(title=title, sessions=[member])
                st.rerun()
        tasks = store.list_tasks()
        if tasks:
            by_id = {task["task_id"]: task for task in tasks}
            target = st.selectbox("기존 작업에 연결", list(by_id), format_func=lambda value: by_id[value]["title"])
            if st.button("선택 작업에 이 세션 연결"):
                task = by_id[target]
                store.save_task(**{field: task[field] for field in ("task_id", "title", "task_type", "outcome", "went_well", "blocked_by", "next_change")},
                                sessions=[*task["sessions"], member])
                st.rerun()
    except (sqlite3.Error, OSError, ValueError) as error:
        st.error(f"회고를 저장하거나 불러오지 못했습니다: {error}")


def review_page(snapshot):
    st.header("회고·개선")
    st.caption("저장한 작업과 개선 항목 전체를 표시합니다. 이 화면에는 사이드바 기간·에이전트·모델 필터를 적용하지 않습니다.")
    try:
        store = ReviewStore()
        mode = st.radio("회고 보기", ["작업 회고", "개선 항목"], horizontal=True)
        if mode == "개선 항목":
            status = st.selectbox("개선 항목 필터", ["open", "applied", "dismissed", "all"],
                                  format_func=lambda value: ACTION_STATES.get(value, "전체"))
            actions = store.list_actions()
            _actions(store, snapshot, [action for action in actions if status == "all" or action["status"] == status], "all-actions")
            from .agent_analysis import project_improvements
            project_improvements()
        else:
            tasks = store.list_tasks()
            if not tasks:
                st.info("작업 이력에서 세션을 선택하고, 세션 보기의 회고에서 첫 작업을 만드세요.")
            else:
                by_id = {task["task_id"]: task for task in tasks}
                chosen = st.selectbox("회고할 작업", list(by_id), format_func=lambda value: f"{by_id[value]['title']} · {OUTCOMES[by_id[value]['outcome']]}")
                _task(store, snapshot, by_id[chosen])
        if store.list_tasks():
            st.download_button("회고·개선 JSON 내보내기", store.export_json(), "agent-monitor-reviews.json", "application/json")
    except (sqlite3.Error, OSError, ValueError) as error:
        st.error(f"회고를 저장하거나 불러오지 못했습니다: {error}")
