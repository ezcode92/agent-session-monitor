import json
from pathlib import Path

import pytest

from agent_monitor.service import AgentMonitor


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')


def codex_rows(status='task_started'):
    return [
        {'type': 'session_meta', 'payload': {'id': 'same'}},
        {'type': 'turn_context', 'timestamp': '2026-01-01T00:00:00Z', 'payload': {'turn_id': 'turn'}},
        {'type': 'response_item', 'timestamp': '2026-01-01T00:00:01Z', 'payload': {'role': 'user', 'content': 'Synthetic request'}},
        {'type': 'event_msg', 'timestamp': '2026-01-01T00:00:02Z', 'payload': {'type': status, 'turn_id': 'turn'}},
    ]


def make_monitor(tmp_path, status='task_started'):
    path = tmp_path / 'codex' / 'same.jsonl'
    write_rows(path, codex_rows(status))
    monitor = AgentMonitor({'timezone': 'UTC', 'paths': {'codex': [str(path.parent)], 'claude': [], 'antigravity': []}})
    monitor.get_snapshot()
    return monitor, path


def test_live_completion_stops_stat_after_returning_final_event(tmp_path, monkeypatch):
    monitor, path = make_monitor(tmp_path)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'type': 'event_msg', 'timestamp': '2026-01-01T00:00:03Z', 'payload': {'type': 'task_complete', 'turn_id': 'turn'}}) + '\n')
    completed = monitor.poll_session('same', 'codex')
    assert completed['sessions'][0].status == 'completed'
    assert completed['events'][-1].role == 'task_complete'
    assert monitor._snapshot['sessions'][0].status == 'unfinished'
    monkeypatch.setattr(Path, 'stat', lambda *args, **kwargs: pytest.fail('Completed session was stat-ed'))
    assert monitor.poll_session('same', 'codex') is completed
    # Switching to the legacy API must also honor the latest completion.
    assert monitor.poll_session('same')['sessions'][0].status == 'completed'


@pytest.mark.parametrize('status', ['complete', 'completed'])
def test_initial_complete_codex_does_not_stat(tmp_path, monkeypatch, status):
    monitor, _ = make_monitor(tmp_path, 'task_complete')
    monitor._snapshot['sessions'][0].status = status
    monkeypatch.setattr(Path, 'stat', lambda *args, **kwargs: pytest.fail('Completed session was stat-ed'))
    assert monitor.poll_session('same', 'codex')['sessions'][0].status == status


def test_manual_refresh_can_resume_completed_codex_tracking(tmp_path, monkeypatch):
    monitor, path = make_monitor(tmp_path, 'task_complete')
    write_rows(path, codex_rows())
    assert monitor.poll_session('same', 'codex')['sessions'][0].status == 'completed'
    assert monitor.refresh_sources()['sessions'][0].status == 'unfinished'
    original_stat = Path.stat
    calls = []

    def traced_stat(self, *args, **kwargs):
        calls.append(self)
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'stat', traced_stat)
    monitor.poll_session('same', 'codex')
    assert calls == [path]


@pytest.mark.parametrize('status', ['task_abort', 'task_error'])
def test_cancelled_and_failed_codex_continue_tracking(tmp_path, monkeypatch, status):
    monitor, path = make_monitor(tmp_path, status)
    original_stat = Path.stat
    calls = []

    def traced_stat(self, *args, **kwargs):
        calls.append(self)
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'stat', traced_stat)
    monitor.poll_session('same', 'codex')
    assert calls == [path]


def test_legacy_poll_keeps_other_agent_with_same_id_running(tmp_path, monkeypatch):
    monitor, codex_path = make_monitor(tmp_path, 'task_complete')
    claude_path = tmp_path / 'claude' / 'same.jsonl'
    write_rows(claude_path, [{'type': 'user', 'timestamp': '2026-01-01T00:00:00Z', 'uuid': 'u', 'message': {'role': 'user', 'content': 'Synthetic request'}}])
    monitor.config['paths']['claude'] = [str(claude_path.parent)]
    monitor.refresh_sources()
    original_stat = Path.stat
    calls = []

    def traced_stat(self, *args, **kwargs):
        calls.append(self)
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'stat', traced_stat)
    snapshot = monitor.poll_session('same')
    assert calls == [claude_path] and codex_path not in calls
    assert {session.agent for session in snapshot['sessions']} == {'codex', 'claude'}


def test_deprecated_agy_is_not_read_by_dashboard_or_live_poll(tmp_path):
    path = tmp_path / 'antigravity-cli' / 'brain' / 'same' / '.system_generated' / 'logs' / 'transcript.jsonl'
    rows = [{'step_index': 0, 'type': 'USER_INPUT', 'status': 'DONE', 'created_at': '2026-01-01T00:00:00Z'}]
    write_rows(path, rows)
    monitor = AgentMonitor({'timezone': 'UTC', 'paths': {'codex': [], 'claude': [], 'antigravity': [str(tmp_path / 'antigravity-cli')]}})
    snapshot = monitor.get_snapshot()
    assert snapshot['requests'] == []
    rows.append({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'status': 'DONE', 'created_at': '2026-01-01T00:00:05Z', 'content': 'Synthetic reply'})
    write_rows(path, rows)
    live = monitor.poll_session('same', 'antigravity')
    assert live['requests'] == []
    assert path.exists()  # Deprecation never deletes original logs.
