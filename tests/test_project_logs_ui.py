"""Actual Streamlit interaction tests for local project work-log analysis."""
from streamlit.testing.v1 import AppTest

from agent_monitor.project_analysis import ProjectAnalysis
from test_project_logs import project, pair
from test_design_ui import dashboard
from test_app_integration import go_page


def log_app(project, monkeypatch, tmp_path):
    service, snapshot, pid, _ = project
    monkeypatch.setenv("AGENT_MONITOR_ANALYSIS_DB", str(service.store.path))
    monkeypatch.setenv("AGENT_MONITOR_REVIEW_DB", str(tmp_path / "reviews.sqlite3"))
    app = AppTest.from_string('''import streamlit as st
from agent_monitor.ui.presentation import show_notice
from agent_monitor.ui.agent_analysis import agent_analysis_page
show_notice()
agent_analysis_page(st.session_state["fixture"], {"start": None, "end": None})
''')
    app.session_state["fixture"] = snapshot
    app.run(timeout=20)
    next(item for item in app.selectbox if item.label == "분석할 프로젝트").set_value(pid).run(timeout=20)
    assert not app.exception
    return app


def test_log_analysis_run_save_adopt_apply_and_reload(project, monkeypatch, tmp_path):
    service, snapshot, pid, _ = project
    snapshot["events"] = pair("a", 0, "pytest")
    app = log_app(project, monkeypatch, tmp_path)
    execute = lambda: next(button for button in app.button if button.label == "작업 로그 분석 실행·저장").click().run(timeout=20)
    execute()
    assert not app.exception and len(service.store.jobs()) == 1
    job = service.store.jobs()[0]
    assert job["context"]["project_ids"] == [pid]
    assert job["status"] == "completed" and job["context"]["analysis_kind"] == "project_logs"
    assert any(item.value == "프로젝트 작업 로그 개선 분석 결과" for item in app.header)
    assert not any("claim_analysis_job" in item.value for item in app.code)
    assert any("테스트" in item.label for item in app.expander)
    next(button for button in app.button if button.label == "실천할 개선 항목으로 채택").click().run(timeout=20)
    assert not app.exception and len(service.store.improvements()) == 1
    next(item for item in app.selectbox if item.label == "프로젝트 개선 상태").set_value("applied")
    next(button for button in app.button if button.label == "프로젝트 개선 상태 저장").click().run(timeout=20)
    assert not app.exception and service.store.improvements()[0]["status"] == "applied"
    execute()
    assert len(service.store.jobs()) == 1 and len(service.store.improvements()) == 1
    fresh = log_app(project, monkeypatch, tmp_path)
    assert not fresh.exception
    assert next(item for item in fresh.selectbox if item.label == "프로젝트 개선 상태").value == "applied"


def test_log_analysis_failure_is_retryable_and_does_not_create_job(project, monkeypatch, tmp_path):
    service, snapshot, pid, _ = project
    snapshot["events"] = pair("a", 0, "pytest")
    original = ProjectAnalysis.save_log_analysis
    def fail(*args, **kwargs):
        raise OSError("synthetic disk full")
    app = log_app(project, monkeypatch, tmp_path)
    monkeypatch.setattr(ProjectAnalysis, "save_log_analysis", fail)
    next(button for button in app.button if button.label == "작업 로그 분석 실행·저장").click().run(timeout=20)
    assert not app.exception and any("synthetic disk full" in item.value for item in app.error)
    assert not service.store.jobs()
    assert next(item for item in app.selectbox if item.label == "분석할 프로젝트").value == pid
    monkeypatch.setattr(ProjectAnalysis, "save_log_analysis", original)
    next(button for button in app.button if button.label == "작업 로그 분석 실행·저장").click().run(timeout=20)
    assert not app.exception and len(service.store.jobs()) == 1


def test_empty_project_logs_report_explicit_insufficient_evidence(project, monkeypatch, tmp_path):
    service, _, _, _ = project
    app = log_app(project, monkeypatch, tmp_path)
    next(button for button in app.button if button.label == "작업 로그 분석 실행·저장").click().run(timeout=20)
    assert not app.exception
    assert service.store.jobs()[0]["context"]["analysis_status"] == "insufficient_evidence"
    assert any("근거가 부족" in item.value for item in app.info)
    assert not any(button.label == "실천할 개선 항목으로 채택" for button in app.button)


def test_irrelevant_global_filters_are_disabled_and_recover_on_navigation(dashboard):
    _, app = dashboard
    for page in ("회고·개선", "설정", "에이전트 분석"):
        go_page(app, page)
        assert not app.exception
        assert next(item for item in app.selectbox if item.label == "기간").disabled == (page != "에이전트 분석")
        assert all(next(item for item in app.multiselect if item.label == label).disabled
                   for label in ("에이전트", "프로젝트", "모델"))
    go_page(app, "개요")
    assert not next(item for item in app.multiselect if item.label == "모델").disabled


def test_legacy_boolean_filter_state_is_normalized():
    app = AppTest.from_string('''import streamlit as st
from agent_monitor.ui.presentation import remember
remember(st.multiselect, "에이전트", options=["codex"], key="filter-agents")
remember(st.selectbox, "기간", options=["최근 7일", "오늘"], key="filter-period")
''')
    app.session_state["filter-agents"] = True
    app.session_state["filter-period"] = True
    app.run(timeout=20)
    assert not app.exception
    assert app.multiselect[0].value == [] and app.selectbox[0].value == "최근 7일"
