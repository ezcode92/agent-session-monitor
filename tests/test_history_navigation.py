from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from streamlit.testing.v1 import AppTest


def snapshot_fixture():
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    sessions = [
        {'agent': 'codex', 'session_id': 'child', 'parent_session_id': 'parent', 'title': 'Synthetic child'},
        {'agent': 'claude', 'session_id': 'parent', 'parent_session_id': None, 'title': 'Other agent parent'},
        {'agent': 'codex', 'session_id': 'parent', 'parent_session_id': None, 'title': 'Same agent parent'},
        {'agent': 'codex', 'session_id': 'orphan', 'parent_session_id': 'missing', 'title': 'Synthetic orphan'},
    ]
    for session in sessions:
        session.update({'started_at': at, 'last_activity_at': at + timedelta(seconds=5), 'status': 'completed',
                        'source_path': 'synthetic-primary.jsonl',
                        'sources': ['synthetic-primary.jsonl', 'synthetic-primary.jsonl', 'synthetic-extra.jsonl', 'synthetic-extra.jsonl']})
    return {'sessions': sessions, 'requests': [], 'events': [], 'usage': [], 'timezone': 'UTC', 'generation': 1}


def history_app(snapshot=None, visible=None):
    source = '''import streamlit as st
import agent_monitor.ui.app as ui
from datetime import timedelta
snapshot = st.session_state["fixture"]
rows = snapshot["sessions"]
visible = st.session_state.get("visible")
sessions = ui.frame([rows[index] for index in visible] if visible is not None else rows)
at = rows[0]["started_at"]
ui.history(snapshot, sessions, {"start": at, "end": at + timedelta(days=1), "models": []})
'''
    app = AppTest.from_string(source)
    app.session_state['fixture'] = snapshot or snapshot_fixture()
    app.session_state['visible'] = visible
    app.run(timeout=20)
    assert not app.exception
    return app


def select_cell(app, row, column):
    app.session_state['history-session-table'] = {'selection': {'cells': [[row, column]]}}
    app.run(timeout=20)
    assert not app.exception


def test_session_id_cell_selects_details_without_dropdown_and_deduplicates_paths():
    app = history_app()
    select_cell(app, 3, 'session_id')
    assert any(element.value == '선택 세션 상세' for element in app.header)
    assert app.code[0].value == 'orphan'
    assert [element.value for element in app.code].count('synthetic-primary.jsonl') == 1
    assert [element.value for element in app.code].count('synthetic-extra.jsonl') == 1
    assert not any(element.label == '세션' for element in app.selectbox)
    table = next(element for element in app.dataframe if element.key == 'history-session-table')
    assert {'session_id', 'parent_session_id'} <= set(table.proto.column_order)
    assert not {'source_path', 'sources', 'data_quality', 'data_status'} & set(table.proto.column_order)


def test_parent_cell_uses_same_agent_identity():
    app = history_app()
    select_cell(app, 0, 'parent_session_id')
    assert app.code[0].value == 'parent'
    assert any(element.value == 'codex · Same agent parent' for element in app.caption)
    assert not any(element.value == 'claude · Other agent parent' for element in app.caption)


def test_parent_outside_filter_comes_from_full_snapshot():
    app = history_app(visible=[0])
    select_cell(app, 0, 'parent_session_id')
    assert app.code[0].value == 'parent'
    assert any('현재 필터 밖' in element.value for element in app.info)
    assert any(element.value == 'codex · Same agent parent' for element in app.caption)


def test_parent_existing_only_for_other_agent_is_not_used_as_fallback():
    snapshot = snapshot_fixture()
    snapshot['sessions'] = snapshot['sessions'][:2]
    app = history_app(snapshot)
    select_cell(app, 0, 'parent_session_id')
    assert any('로그를 찾을 수 없습니다' in element.value for element in app.info)
    assert not app.code


@pytest.mark.parametrize(('row', 'notice'), [(3, '로그를 찾을 수 없습니다'), (2, '확인된 부모 세션이 없습니다')])
def test_unavailable_parent_shows_notice_without_unrelated_details(row, notice):
    app = history_app()
    select_cell(app, row, 'parent_session_id')
    assert any(notice in element.value for element in app.info)
    assert not app.code and not any(element.value == '선택 세션 상세' for element in app.header)


def test_changed_visible_rows_clear_old_cell_selection():
    app = history_app()
    select_cell(app, 3, 'session_id')
    assert app.code[0].value == 'orphan'
    app.session_state['visible'] = [0]
    app.run(timeout=20)
    assert not app.exception
    assert app.code[0].value == 'child'


def test_completed_codex_history_never_calls_live_service(monkeypatch):
    import agent_monitor.service as service

    monkeypatch.setattr(service, 'poll_session', lambda *args, **kwargs: pytest.fail('Completed session was polled'))
    app = history_app()
    next(element for element in app.radio if element.label == '세션 보기').set_value('실시간').run(timeout=20)
    assert not app.exception
    assert any('완료된 Codex 세션' in element.value for element in app.info)


def test_completed_codex_graph_disables_live_control(monkeypatch):
    import agent_monitor.service as service

    monkeypatch.setattr(service, 'poll_session', lambda *args, **kwargs: pytest.fail('Completed session was polled'))
    snapshot = snapshot_fixture()
    snapshot['sessions'] = [snapshot['sessions'][2]]
    key = ('codex', 'parent')
    snapshot['orchestration'] = {'roots': [key], 'children': {key: []}, 'depths': {key: 0},
                                 'rollups': {key: {'total_tokens': None, 'duration_seconds': 5}}, 'edges': []}
    app = AppTest.from_string('''import streamlit as st
import agent_monitor.ui.app as ui
snapshot = st.session_state["fixture"]
ui.orchestration(snapshot, ui.frame(snapshot["sessions"]), {})
''')
    app.session_state['fixture'] = snapshot
    app.run(timeout=20)
    assert not app.exception
    assert next(element for element in app.toggle if element.label == '실시간 로그 보기').disabled


def test_live_completion_keeps_final_events_and_stops_next_service_call(monkeypatch):
    import agent_monitor.service as service

    snapshot = snapshot_fixture()
    snapshot['sessions'] = [snapshot['sessions'][0]]
    snapshot['sessions'][0]['status'] = 'active_inferred'
    completed = deepcopy(snapshot)
    completed['generation'] = 2
    completed['sessions'][0]['status'] = 'completed'
    completed['events'] = [{'agent': 'codex', 'session_id': 'child', 'event_id': 'final',
                            'occurred_at': snapshot['sessions'][0]['started_at'], 'role': 'assistant', 'display': 'Synthetic final answer'}]
    calls = []

    def poll(session_id, agent=None):
        calls.append((agent, session_id))
        return completed

    monkeypatch.setattr(service, 'poll_session', poll)
    app = history_app(snapshot)
    next(element for element in app.radio if element.label == '세션 보기').set_value('실시간').run(timeout=20)
    assert not app.exception and calls == [('codex', 'child')]
    assert any('추적을 중지' in element.value for element in app.info)
    app.run(timeout=20)
    assert not app.exception and calls == [('codex', 'child')]
    tables = [element.value for element in app.dataframe if 'event_id' in element.value]
    assert tables[-1]['event_id'].tolist() == ['final']
