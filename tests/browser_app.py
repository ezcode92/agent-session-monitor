"""Synthetic browser audit fixture. No real collector, config or user databases.

Run through tools/verify_ui.mjs or expose temporarily for external browser QA.
This is not the real-data application entrypoint.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st
from test_app_integration import _snapshot
from agent_monitor import config, service
from agent_monitor.project_analysis import ProjectAnalysis
from agent_monitor.review_store import ReviewStore
from agent_monitor.insights import tool_observations
from agent_monitor.ui import app as ui

os.environ["AGENT_MONITOR_AUDIT_MODE"] = "synthetic"


@st.cache_resource
def fixture():
    directory = tempfile.TemporaryDirectory(prefix="asm-browser-data-")
    root = Path(directory.name)
    project = root / "synthetic-project"
    project.mkdir()
    (project / "AGENTS.md").write_text("# Synthetic project\nVerify changes with tests.\n")
    os.environ["AGENT_MONITOR_REVIEW_DB"] = str(root / "reviews.sqlite3")
    os.environ["AGENT_MONITOR_ANALYSIS_DB"] = str(root / "analysis.sqlite3")
    snapshot = _snapshot()
    delta = datetime.now(timezone.utc) - timedelta(days=1) - snapshot["scanned_at"]

    def recent(value):
        if isinstance(value, datetime):
            return value + delta
        if isinstance(value, dict):
            return {key: recent(item) for key, item in value.items()}
        if isinstance(value, list):
            return [recent(item) for item in value]
        return value

    snapshot = recent(snapshot)
    titles = ["에이전트 세션 모니터의 화면 개선과 회귀 테스트", "긴 한글 제목과 데이터 필터를 함께 확인하는 작업", "사용량이 확인되지 않은 로그의 처리"]
    for index, session in enumerate(snapshot["sessions"]):
        session.update(project=str(project), title=titles[index], source_path="synthetic.jsonl", parent_session_id=None if index == 0 else snapshot["sessions"][index-1]["session_id"])
    snapshot["sessions"][0]["status"] = "active_inferred"
    for index, event in enumerate(snapshot["events"]):
        event.update(source_path="synthetic.jsonl", record_key=str(index + 1))
    for usage in snapshot["usage"]:
        usage["model"] = "synthetic-model"
    for request in snapshot["requests"]:
        request["title"] = "선택 기간의 토큰·작업 시간 확인"
    if os.environ.get("VERIFY_REQUEST_TOOLS"):
        snapshot["requests"].append({**snapshot["requests"][0], "turn_id": "followup", "title": "후속 요청의 도구 호출 확인"})
        for index, (tid, raw) in enumerate([
            ("turn", {"type": "function_call", "call_id": "check", "name": "exec_command", "arguments": {"cmd": "pytest -q", "reason": "선택한 요청의 입력·출력과 도구 호출 근거를 확인합니다."}}),
            ("turn", {"type": "function_call_output", "call_id": "check", "output": {"exit_code": 0, "text": "검증 통과"}}),
            ("turn", {"type": "function_call", "call_id": "failed", "name": "read_file", "arguments": {"path": "/synthetic/missing.py"}}),
            ("turn", {"type": "function_call_output", "call_id": "failed", "output": {"is_error": True, "text": "파일 없음"}}),
            ("followup", {"type": "function_call", "call_id": "later", "name": "read_file", "arguments": {"path": "/synthetic/app.py"}}),
        ]):
            snapshot["events"].append({"agent": "codex", "session_id": "root", "turn_id": tid,
                                       "event_id": f"browser-tool-{index}", "occurred_at": snapshot["scanned_at"] + timedelta(seconds=index),
                                       "source_path": "synthetic.jsonl", "record_key": str(index+100),
                                       "display": raw["type"], "tool_observations": tool_observations(raw)})
    snapshot["config"]["paths"] = {"codex": [str(project / "synthetic-logs")]}
    snapshot["paths"] = snapshot["config"]["paths"]
    reviews = ReviewStore()
    task = reviews.save_task(title="대시보드 사용성 개선", sessions=[snapshot["sessions"][0]], task_type="feature", outcome="partial",
                             went_well="핵심 지표와 작업 상세를 연결했습니다.", blocked_by="좁은 창에서 긴 선택값을 확인해야 합니다.", next_change="변경한 상태를 저장하고 다시 확인합니다.")
    reviews.add_action(task, "작업을 마치기 전에 핵심 흐름을 확인하기")
    analysis = ProjectAnalysis(lambda: snapshot)
    pid = analysis.catalog()["projects"][0]["project_id"]
    job = analysis.create_job([pid], "프로젝트의 작업 기록을 검토하고 다음 행동을 제안해 주세요.")
    job = analysis.store.get_job(job["job_id"])
    claim = analysis.store.claim(job["job_id"], "검증용 에이전트")
    evidence = job["context"]["evidence_catalog"][0]["id"]
    analysis.complete(job["job_id"], claim["claim_token"], {
        "summary": "선택한 프로젝트의 작업 기록을 검토했습니다.",
        "findings": [{"title": "사용량 확인", "detail": "확인된 기록으로만 통계를 계산합니다.", "evidence_ids": [evidence]}],
        "recommendations": [{"title": "화면 검증 결과 기록", "rationale": "변경한 화면과 확인 범위를 함께 기록합니다.", "project_ids": [pid], "evidence_ids": [evidence]}],
    })
    analysis.store.accept(job["job_id"], 0)
    return directory, snapshot


_directory, snapshot = fixture()


def save_config(value, *args, **kwargs):
    snapshot["config"] = deepcopy(value)
    snapshot["paths"] = deepcopy(value["paths"])
    snapshot["timezone"] = config.normalized_timezone(value)[0]
    snapshot["generation"] += 1


config.load_config = lambda *args, **kwargs: deepcopy(snapshot["config"])
config.save_config = save_config
config.default_config = lambda: {"timezone": "Asia/Seoul", "paths": {"codex": []}}
service.update_config = lambda *args, **kwargs: None
service.reload_config = lambda *args, **kwargs: None
service.refresh_sources = lambda: snapshot
service.poll_session = lambda *args, **kwargs: snapshot
service.raw_event = lambda *args, **kwargs: {"synthetic": True}
ui._snapshot = lambda force=False: snapshot
ui.run()
