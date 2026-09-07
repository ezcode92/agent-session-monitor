import json
from datetime import datetime, timezone
from pathlib import Path

from agent_monitor.config import default_config, load_config
from agent_monitor.discovery import scan_sources
from agent_monitor.parsers import parse_source, parse_sources


def write_transcript(root, rows, sid='conversation', name='transcript.jsonl'):
    path = root / 'brain' / sid / '.system_generated' / 'logs' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    return path


def step(index, kind, seconds, **extra):
    return {'step_index': index, 'source': 'synthetic', 'type': kind, 'status': 'DONE',
            'created_at': f'2026-01-01T00:00:{seconds:02d}Z', **extra}


def test_brain_steps_produce_sessions_turns_events_and_unknown_usage(tmp_path):
    root = tmp_path / 'antigravity-cli'
    rows = [step(0, 'USER_INPUT', 0, content='Synthetic first request'),
            step(1, 'PLANNER_RESPONSE', 2, tool_calls=[{'name': 'read_file', 'args': {'path': 'example'}}]),
            step(2, 'RUN_COMMAND', 5, content='synthetic output', exit_code=0),
            step(3, 'USER_INPUT', 10, content='Synthetic second request'),
            step(4, 'ERROR_MESSAGE', 15, error='synthetic failure', error_code=1)]
    path = write_transcript(root, rows)
    result = parse_sources(scan_sources({'antigravity': [str(root)]}))
    assert [item.kind for item in result.diagnostics] == ['usage_unavailable']
    assert len(result.sessions) == 1 and len(result.turns) == 2 and len(result.events) == 5
    session = result.sessions[0]
    assert session.session_id == 'conversation' and session.title == 'Synthetic first request'
    assert session.parent_session_id is None and session.project is None and session.own_usage == []
    assert session.started_at == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert session.last_activity_at.second == 15
    assert session.status == 'unfinished'
    assert [(turn.turn_id, (turn.ended_at - turn.started_at).total_seconds()) for turn in result.turns] == [('0', 5), ('3', 5)]
    assert all(turn.duration_kind == 'observed' and not turn.usage for turn in result.turns)
    assert [event.role for event in result.events] == ['user', 'assistant', 'tool', 'user', 'error']
    assert 'read_file' in result.events[1].display and 'DONE' in result.events[1].display
    assert 'exit_code=0' in result.events[2].display and 'synthetic failure' in result.events[4].display
    for item in [session, *result.events]:
        assert item.source_label == 'antigravity-cli' and item.source_kind == 'antigravity'
        assert item.source_path == str(path) and item.sources == [str(path)]
    assert result.events[0].event_id.endswith(':step:0') and result.events[0].record_key == '1'


def test_brain_mirrors_merge_stable_steps_even_when_display_changes(tmp_path):
    roots = [tmp_path / name for name in ('antigravity', 'antigravity-cli')]
    for index, root in enumerate(roots):
        write_transcript(root, [step(0, 'USER_INPUT', 0, content='Synthetic request'),
                                step(1, 'PLANNER_RESPONSE', 2, content=f'Synthetic snapshot {index}')])
    result = parse_sources(scan_sources({'antigravity': [str(root / 'brain') for root in roots]}))
    assert len(result.sessions) == 1 and len(result.turns) == 1 and len(result.events) == 2
    assert result.sessions[0].source_label in ('antigravity', 'antigravity-cli')
    assert all(len(event.sources) == 2 for event in result.events)


def test_discovery_ignores_full_and_chunk_transcripts(tmp_path):
    root = tmp_path / 'antigravity-cli'
    rows = [step(0, 'USER_INPUT', 0, content='Synthetic request')]
    expected = write_transcript(root, rows)
    write_transcript(root, rows, name='transcript_full.jsonl')
    write_transcript(root, rows, name='chunks/transcript/00000000.jsonl')
    write_transcript(root, rows, name='chunks/transcript_full/00000000.jsonl')
    sources = scan_sources({'antigravity': [str(tmp_path / 'missing'), str(root)]})
    assert [source.path for source in sources] == [expected]


def test_brain_user_step_without_content_remains_a_turn(tmp_path):
    root = tmp_path / 'antigravity-cli'
    write_transcript(root, [step(0, 'USER_INPUT', 0), step(1, 'PLANNER_RESPONSE', 3, content='Synthetic reply')])
    result = parse_sources(scan_sources({'antigravity': [str(root)]}))
    assert len(result.turns) == 1 and result.turns[0].user_preview is None
    assert result.turns[0].ended_at.second == 3


def test_unrecognized_brain_schema_keeps_diagnostic(tmp_path):
    root = tmp_path / 'antigravity-cli'
    write_transcript(root, [{'content': 'Synthetic unknown record'}])
    result = parse_source(scan_sources({'antigravity': [str(root)]})[0])
    assert not result.sessions and result.diagnostics[0].kind == 'unsupported_format'


def test_default_roots_target_brain_directories(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    assert default_config()['paths']['antigravity'] == [
        str(tmp_path / '.gemini' / name / 'brain')
        for name in ('antigravity', 'antigravity-cli', 'antigravity-ide')
    ]


def test_saved_installation_roots_remain_unchanged_and_scan_same_logs(tmp_path):
    root = tmp_path / 'antigravity-cli'
    write_transcript(root, [step(0, 'USER_INPUT', 0, content='Synthetic request')])
    config_path = tmp_path / 'config.json'
    content = json.dumps({'paths': {'antigravity': [str(root)]}})
    config_path.write_text(content, encoding='utf-8')
    loaded = load_config(config_path)
    assert loaded['paths']['antigravity'] == [str(root)]
    assert config_path.read_text(encoding='utf-8') == content
    installation_sources = scan_sources({'antigravity': [str(root)]})
    brain_sources = scan_sources({'antigravity': [str(root / 'brain')]})
    assert len(installation_sources) == 1 and installation_sources == brain_sources
    assert brain_sources[0].source_label == 'antigravity-cli'
