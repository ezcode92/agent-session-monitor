"""Behavioral regression checks for navigation, recovery and accessible themes."""
from copy import deepcopy
from pathlib import Path
import tomllib

import pytest
from streamlit.testing.v1 import AppTest

from test_app_integration import _snapshot, go_page
from agent_monitor.review_store import ReviewStore
from agent_monitor.project_analysis import ProjectAnalysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def dashboard(monkeypatch, tmp_path):
    from agent_monitor.ui import app as ui
    from agent_monitor import service
    snapshot = _snapshot()
    for usage in snapshot["usage"]:
        usage["model"] = "test-model"
    monkeypatch.setattr(ui, "_snapshot", lambda force=False: snapshot)
    monkeypatch.setattr(service, "poll_session", lambda *args, **kwargs: pytest.fail("Unselected live view was polled"))
    monkeypatch.setenv("AGENT_MONITOR_REVIEW_DB", str(tmp_path / "reviews.sqlite3"))
    monkeypatch.setenv("AGENT_MONITOR_ANALYSIS_DB", str(tmp_path / "analysis.sqlite3"))
    return snapshot, AppTest.from_file(ROOT / "app.py").run(timeout=20)


def test_page_roundtrip_preserves_filters_search_selected_session_and_pane(dashboard):
    _, app = dashboard
    next(item for item in app.multiselect if item.label == "모델").set_value(["test-model"]).run(timeout=20)
    go_page(app, "작업 이력")
    app.session_state["history-session-table"] = {"selection": {"cells": [[2, "session_id"]]}}
    app.run(timeout=20)
    assert app.code[0].value == "leaf"
    next(item for item in app.radio if item.label == "세션 보기").set_value("로그").run(timeout=20)
    go_page(app, "회고·개선")
    go_page(app, "작업 이력")
    assert not app.exception
    assert app.code[0].value == "leaf"
    assert next(item for item in app.radio if item.label == "세션 보기").value == "로그"
    assert next(item for item in app.multiselect if item.label == "모델").value == ["test-model"]
    next(item for item in app.text_input if item.label.startswith("세션 검색")).set_value("middle").run(timeout=20)
    go_page(app, "개요")
    go_page(app, "작업 이력")
    assert not app.exception
    assert next(item for item in app.text_input if item.label.startswith("세션 검색")).value == "middle"
    assert app.code[0].value == "middle"
    next(item for item in app.text_input if item.label.startswith("세션 검색")).set_value("not-present").run(timeout=20)
    assert any("검색 결과가 없습니다" in item.value for item in app.info)


def test_refresh_failure_retains_metrics_and_snapshot_then_retry_replaces_them(dashboard, monkeypatch):
    from agent_monitor import service
    snapshot, app = dashboard

    def unavailable():
        raise OSError("synthetic read failure")

    monkeypatch.setattr(service, "refresh_sources", unavailable)
    next(button for button in app.button if button.label == "지금 새로고침").click().run(timeout=20)
    assert not app.exception
    assert any("이전 데이터를 표시" in item.value for item in app.warning)
    assert next(item for item in app.metric if item.label == "전체 토큰").value == "63"
    assert app.session_state["dashboard_snapshot"]["generation"] == 1
    updated = deepcopy(snapshot)
    updated["generation"] = 2
    updated["usage"][0]["total_tokens"] += 100
    monkeypatch.setattr(service, "refresh_sources", lambda: updated)
    next(button for button in app.button if button.label == "지금 새로고침").click().run(timeout=20)
    assert not app.exception
    assert next(item for item in app.metric if item.label == "전체 토큰").value == "163"
    assert not any("이전 데이터를 표시" in item.value for item in app.warning)


def test_automatic_refresh_failure_leaves_existing_dashboard_usable(dashboard, monkeypatch):
    from agent_monitor.ui import app as ui
    _, app = dashboard

    def unavailable(force=False):
        raise OSError("synthetic read failure")

    monkeypatch.setattr(ui, "_snapshot", unavailable)
    next(item for item in app.toggle if item.label.startswith("고급:")).set_value(True).run(timeout=20)
    assert not app.exception
    assert any("자동 갱신에 실패" in item.value for item in app.warning)
    assert next(item for item in app.metric if item.label == "전체 토큰").value == "63"


def test_settings_failure_preserves_draft_and_retry_saves_once(dashboard, monkeypatch):
    from agent_monitor import config, service
    snapshot, app = dashboard
    current = {"timezone": "Asia/Seoul", "paths": {"codex": ["/synthetic/original"]}}
    calls = []
    fail = [True]

    def save(value):
        calls.append(deepcopy(value))
        if fail[0]:
            raise OSError("synthetic disk full")
        current.update(value)
        snapshot["config"] = deepcopy(value)
        snapshot["timezone"] = value["timezone"]

    monkeypatch.setattr(config, "load_config", lambda: deepcopy(current))
    monkeypatch.setattr(config, "save_config", save)
    monkeypatch.setattr(service, "update_config", lambda value: None)
    go_page(app, "설정")
    next(item for item in app.text_input if item.label == "IANA timezone").set_value("UTC").run(timeout=20)
    app.session_state["paths-editor"] = {"edited_rows": {0: {"path": "/synthetic/changed"}}, "added_rows": [], "deleted_rows": []}
    next(button for button in app.button if button.label == "설정 저장").click().run(timeout=20)
    assert not app.exception and app.error
    assert next(item for item in app.text_input if item.label == "IANA timezone").value == "UTC"
    assert calls[0]["paths"]["codex"] == ["/synthetic/changed"]
    assert current["paths"]["codex"] == ["/synthetic/original"]
    fail[0] = False
    next(button for button in app.button if button.label == "설정 저장").click().run(timeout=20)
    app.run(timeout=20)
    assert not app.exception
    assert len(calls) == 2 and calls[0] == calls[1]
    assert current["timezone"] == "UTC" and current["paths"]["codex"] == ["/synthetic/changed"]


def test_settings_restore_requires_confirmation_and_cancel_keeps_settings(dashboard, monkeypatch):
    from agent_monitor import config, service
    _, app = dashboard
    original = {"timezone": "UTC", "paths": {"codex": ["/synthetic/original"]}}
    defaults = {"timezone": None, "paths": {"codex": ["/synthetic/default"]}}
    saves = []
    monkeypatch.setattr(config, "load_config", lambda: deepcopy(original))
    monkeypatch.setattr(config, "default_config", lambda: deepcopy(defaults))
    monkeypatch.setattr(config, "save_config", lambda value: saves.append(value))
    monkeypatch.setattr(service, "reload_config", lambda value: None)
    go_page(app, "설정")
    next(button for button in app.button if button.label == "기본 경로 복원").click().run(timeout=20)
    assert not saves
    next(button for button in app.button if button.label == "복원 취소").click().run(timeout=20)
    assert not saves
    next(button for button in app.button if button.label == "기본 경로 복원").click().run(timeout=20)
    next(button for button in app.button if button.label == "기본 설정으로 복원").click().run(timeout=20)
    assert not app.exception and saves == [defaults]


def test_failed_improvement_creation_keeps_text_and_success_clears_it(dashboard, monkeypatch):
    snapshot, app = dashboard
    store = ReviewStore()
    store.save_task(title="Test task", sessions=[snapshot["sessions"][0]])
    original = ReviewStore.add_action
    fail = [True]

    def add(self, *args, **kwargs):
        if fail[0]:
            raise OSError("synthetic disk full")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(ReviewStore, "add_action", add)
    go_page(app, "회고·개선")
    next(item for item in app.text_input if item.label == "실천할 행동").set_value("검증 근거를 기록하기")
    next(button for button in app.button if button.label == "개선 항목 추가").click().run(timeout=20)
    assert not app.exception and app.error
    assert next(item for item in app.text_input if item.label == "실천할 행동").value == "검증 근거를 기록하기"
    assert store.list_actions() == []
    fail[0] = False
    next(button for button in app.button if button.label == "개선 항목 추가").click().run(timeout=20)
    assert not app.exception
    assert next(item for item in app.text_input if item.label == "실천할 행동").value == ""
    app.run(timeout=20)
    assert len(store.list_actions()) == 1


def test_failed_analysis_request_keeps_objective_for_retry(dashboard, monkeypatch, tmp_path):
    snapshot, app = dashboard
    project = tmp_path / "project"
    project.mkdir()
    for session in snapshot["sessions"]:
        session["project"] = str(project)
    original = ProjectAnalysis.create_job

    def unavailable(*args, **kwargs):
        raise OSError("synthetic disk full")

    monkeypatch.setattr(ProjectAnalysis, "create_job", unavailable)
    go_page(app, "에이전트 분석")
    next(item for item in app.text_area if item.label == "에이전트에게 요청할 분석").set_value("작업 기록의 근거를 확인해 주세요.")
    next(button for button in app.button if button.label == "에이전트 분석 요청 만들기").click().run(timeout=20)
    assert not app.exception and app.error
    assert next(item for item in app.text_area if item.label == "에이전트에게 요청할 분석").value == "작업 기록의 근거를 확인해 주세요."
    monkeypatch.setattr(ProjectAnalysis, "create_job", original)
    next(button for button in app.button if button.label == "에이전트 분석 요청 만들기").click().run(timeout=20)
    assert not app.exception
    jobs = ProjectAnalysis(lambda: snapshot).store.jobs()
    assert len(jobs) == 1 and jobs[0]["context"]["objective"] == "작업 기록의 근거를 확인해 주세요."


def luminance(color):
    rgb = [int(color[index:index+2], 16) / 255 for index in (1, 3, 5)]
    channels = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in rgb]
    return sum(value * weight for value, weight in zip(channels, (.2126, .7152, .0722)))


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_theme_contrast_on_actual_adjacent_surfaces(mode):
    theme = tomllib.loads((ROOT / ".streamlit/config.toml").read_text())["theme"][mode]

    def check(foreground, background, minimum):
        low, high = sorted((luminance(foreground), luminance(background)))
        ratio = (high + .05) / (low + .05)
        assert ratio >= minimum, f"{mode}: {foreground} on {background}: {ratio:.2f} < {minimum}"

    for background in {theme["backgroundColor"], theme["secondaryBackgroundColor"], theme["codeBackgroundColor"],
                       theme["sidebar"]["backgroundColor"], theme["sidebar"]["secondaryBackgroundColor"]}:
        check(theme["textColor"], background, 4.5)
        check(theme["linkColor"], background, 4.5)
        check(theme["borderColor"], background, 3)
    check("#ffffff", theme["primaryColor"], 4.5)
    for state in ("blue", "green", "orange", "red"):
        check(theme[f"{state}TextColor"], theme[f"{state}BackgroundColor"], 4.5)
