"""Project comparison and analysis delegated to a connected MCP agent."""
from __future__ import annotations

import json
from pathlib import Path
import shlex
import sqlite3
import streamlit as st

from ..project_analysis import ProjectAnalysis, row
from ..project_store import ProjectStore
from ..review_store import ACTION_STATES, ReviewStore
from .presentation import page_header, remember, saved_notice

STATES = {"pending": "에이전트 인수 대기", "running": "에이전트 분석 중", "completed": "분석 완료", "failed": "분석 실패"}


def _project_settings(service, snapshot):
    with st.expander("프로젝트 연결 관리"):
        registered, assignments = service.store.projects()
        by_id = {project["project_id"]: project for project in registered}
        selected = st.selectbox("등록한 프로젝트", [None, *by_id], format_func=lambda value: "새로 등록" if value is None else by_id[value]["name"])
        project = by_id.get(selected, {})
        sessions = {(row(item)["agent"], row(item)["session_id"]): row(item).get("title") for item in snapshot.get("sessions", [])}
        default = [(item["agent"], item["session_id"]) for item in assignments if item["project_id"] == selected]
        for key in default:
            sessions.setdefault(key, "현재 로그 미확인")
        with st.form(f"project-settings:{selected}"):
            name = st.text_input("프로젝트 이름", value=project.get("name", ""), max_chars=200)
            root = st.text_input("프로젝트 폴더 절대 경로", value=project.get("root", ""))
            members = st.multiselect("수동으로 연결할 세션", list(sessions), default=default,
                                     format_func=lambda key: f"{key[0]} · {sessions[key] or key[1]} · {key[1]}",
                                     help="로그에 프로젝트가 없을 때 사용할 수 있습니다. 다른 프로젝트의 수동 연결도 선택한 프로젝트로 이동합니다.")
            if st.form_submit_button("프로젝트 연결 저장"):
                service.register(name, root, members)
                st.rerun()


def project_improvements(store=None):
    store = store or ProjectStore()
    items = store.improvements()
    if not items:
        return
    st.header("에이전트 분석에서 채택한 개선 항목")
    for item in items:
        identity = f"{item['job_id']}:{item['item_index']}"
        with st.expander(f"{ACTION_STATES[item['status']]} · {item['title']}"):
            job = store.get_job(item["job_id"])
            recommendation = job["report"]["recommendations"][item["item_index"]]
            st.write(recommendation["rationale"])
            st.caption("대상 프로젝트: " + ", ".join(recommendation["project_ids"]))
            if item["applied_at"]:
                st.caption(f"적용 기록: {item['applied_at']}")
            with st.form(f"project-improvement:{identity}"):
                status = st.selectbox("프로젝트 개선 상태", list(ACTION_STATES), index=list(ACTION_STATES).index(item["status"]), format_func=ACTION_STATES.get)
                if st.form_submit_button("프로젝트 개선 상태 저장"):
                    store.update_improvement(item["job_id"], item["item_index"], status)
                    saved_notice("프로젝트 개선 상태를 저장했습니다.")
                    st.rerun()


def _report(store, job):
    report = job["report"]
    st.header("에이전트 분석 결과")
    st.write(report["summary"])
    refs = {item["id"]: item for item in job["context"]["evidence_catalog"]}
    for finding in report["findings"]:
        with st.expander(finding["title"]):
            st.write(finding["detail"])
            st.json([refs[key] for key in finding["evidence_ids"]])
    accepted = {(item["job_id"], item["item_index"]) for item in store.improvements()}
    for index, recommendation in enumerate(report["recommendations"]):
        with st.expander("개선 제안: " + recommendation["title"]):
            st.write(recommendation["rationale"])
            st.json([refs[key] for key in recommendation["evidence_ids"]])
            if st.button("실천할 개선 항목으로 채택", key=f"accept:{job['job_id']}:{index}", disabled=(job["job_id"], index) in accepted):
                store.accept(job["job_id"], index)
                saved_notice("실천할 개선 항목으로 채택했습니다.")
                st.rerun()
    st.download_button("분석 보고서 JSON", json.dumps(job, ensure_ascii=False, indent=2, default=str), f"analysis-{job['job_id']}.json", "application/json")


def agent_analysis_page(snapshot, state):
    page_header("프로젝트·에이전트 분석", "프로젝트 통계와 지침을 비교하고 연결한 에이전트의 분석을 검토합니다. 공통 필터 중 기간만 적용하며 분석할 프로젝트는 아래에서 선택합니다.")
    service = ProjectAnalysis(lambda: snapshot)
    try:
        catalog = service.catalog()
        projects = {item["project_id"]: item for item in catalog["projects"]}
        st.caption(f"프로젝트 {len(projects)}개 · 프로젝트 미연결 세션 {len(catalog['unassigned_sessions'])}개")
        st.header("분석할 범위")
        scope = remember(st.radio,"분석 범위",options=["프로젝트", "프로젝트 간 비교", "작업 세션"],horizontal=True,key="agent-analysis-scope")
        selected, session_keys = [], None
        if scope == "작업 세션":
            tasks = {item["task_id"]: item for item in ReviewStore().list_tasks()}
            if tasks:
                task_id = remember(st.selectbox,"분석할 작업",options=list(tasks),key="analysis-task", format_func=lambda value: tasks[value]["title"])
                session_keys = [(member["agent"], member["session_id"]) for member in tasks[task_id]["sessions"]]
                owners = {tuple(key): pid for pid, project in projects.items() for key in project["session_keys"]}
                if all(key in owners for key in session_keys):
                    selected = list(dict.fromkeys(owners[key] for key in session_keys))
                else:
                    st.info("작업의 모든 세션을 프로젝트에 연결해야 분석할 수 있습니다.")
            else:
                st.info("작업 이력의 회고에서 먼저 작업을 만드세요.")
        elif projects:
            if scope == "프로젝트":
                selected = [remember(st.selectbox,"분석할 프로젝트",options=list(projects),key="analysis-project", format_func=lambda value: projects[value]["name"])]
            else:
                selected = remember(st.multiselect,"비교할 프로젝트 (첫 항목이 지침 비교 기준)",options=list(projects),key="analysis-projects", max_selections=8, format_func=lambda value: projects[value]["name"])
        if selected and (scope != "프로젝트 간 비교" or len(selected) >= 2):
            statistics = service.statistics(selected, state.get("start"), state.get("end"), session_keys)
            st.dataframe([{"프로젝트": item["name"], "세션": item["session_count"], "요청": item["request_count"], "전체 토큰": item["usage"]["total_tokens"],
                           "토큰 확인 기록": f"{item['coverage']['known_totals']}/{item['coverage']['usage_events']}", "문제 신호": len(item["signals"])} for item in statistics["projects"]], hide_index=True, width="stretch")
            st.download_button("프로젝트 통계 JSON", json.dumps(statistics, ensure_ascii=False, indent=2, default=str), "project-statistics.json", "application/json")
            if st.button("프로젝트 지침 비교" if len(selected) > 1 else "프로젝트 지침 보기"):
                st.json(service.compare_instructions(selected) if len(selected) > 1 else service.instructions(selected))
            st.header("에이전트에게 분석 요청")
            st.caption("요청을 저장한 뒤 MCP로 연결한 에이전트에게 전달하세요. 요청 생성만으로 분석이 시작되지는 않습니다.")
            with st.form("request-agent-analysis"):
                objective = st.text_area("에이전트에게 요청할 분석", value="작업 이력과 통계에서 반복되는 문제를 찾고, 프로젝트 지침을 비교해 근거가 있는 작업 방식·지침 개선안을 제안해 주세요.", max_chars=4000)
                if st.form_submit_button("에이전트 분석 요청 만들기", type="primary"):
                    created = service.create_job(selected, objective, state.get("start"), state.get("end"), session_keys)
                    st.session_state["selected-analysis-job"] = created["job_id"]
                    st.session_state.pop("_ui:selected-analysis-job", None)
                    saved_notice("분석 요청을 저장했습니다. 연결한 에이전트에 요청을 전달하세요.")
                    st.rerun()
        elif not projects:
            st.info("로그에서 프로젝트를 찾지 못했습니다. 프로젝트 연결 관리에서 폴더와 세션을 등록하세요.")
        _project_settings(service, snapshot)
        with st.expander("MCP 연결 안내"):
            root = Path(__file__).resolve().parents[3]
            st.markdown("**로컬 분석 에이전트 · 전체 도구**")
            command = ["codex", "mcp", "add", "agent-session-monitor", "--", "uv", "--directory", str(root), "run", "--locked", "python", str(root / "mcp_server.py")]
            st.code(shlex.join(command), language="bash")
            st.caption("연결 후 사용 중인 에이전트 세션에 아래 분석 요청을 전달하세요. 대기 요청을 만드는 것만으로 에이전트가 자동 실행되지는 않습니다. 사용 중인 에이전트의 데이터 전송·과금 설정이 적용됩니다.")
            st.markdown("**ChatGPT Web · 완료 보고서 읽기 전용**")
            results_command = ["uv", "--directory", str(root), "run", "--locked", "python", str(root / "mcp_server.py"), "--scope", "results"]
            st.code(shlex.join(results_command), language="bash")
            st.caption("이 명령을 OpenAI Secure MCP Tunnel의 stdio 대상으로 연결하면 완료된 보고서와 사용한 근거만 조회할 수 있습니다. 원본 로그와 로컬 파일 위치는 제공하지 않습니다.")
        st.header("분석 요청과 결과")
        if st.button("분석 결과 새로고침"):
            st.rerun()
        jobs = {item["job_id"]: item for item in service.store.jobs()}
        if jobs:
            if st.session_state.get("selected-analysis-job") not in jobs:
                st.session_state.pop("selected-analysis-job", None)
            identity = remember(st.selectbox,"분석 요청",options=list(jobs), format_func=lambda value: f"{STATES[jobs[value]['status']]} · {jobs[value]['context']['objective'][:60]}", key="selected-analysis-job")
            job = jobs[identity]
            st.write(f"**{STATES[job['status']]}**")
            st.caption(f"담당: {job['agent_name'] or '미지정'} · 요청: {job['created_at']}")
            with st.expander("에이전트에 전달할 요청"):
                st.code(service.agent_prompt(identity), language=None, wrap_lines=True)
            if job["status"] in {"running", "failed"}:
                if job["error"]:
                    st.error(job["error"])
                if st.button("분석 요청 다시 대기시키기"):
                    service.store.retry(identity)
                    saved_notice("분석 요청을 다시 대기 상태로 변경했습니다.")
                    st.rerun()
            if job["report"]:
                _report(service.store, job)
        else:
            st.info("아직 만든 분석 요청이 없습니다.")
        project_improvements(service.store)
    except (sqlite3.Error, OSError, ValueError) as error:
        st.error(f"프로젝트 분석을 처리하지 못했습니다: {error}")
