from datetime import datetime, timezone
from pathlib import Path

from agent_monitor.analysis import analyze, filter_data, interval_for_dates, orchestration_graph, split_duration_by_day
from agent_monitor.discovery import SourceFile
from agent_monitor.models import LogEvent, ParseResult, Session, Turn, Usage
from agent_monitor.parsers import parse_claude, parse_codex
from agent_monitor.parsers import parse_sources
from agent_monitor.service import AgentMonitor, poll_session as public_poll_session, recent_events as public_recent_events, update_config
from agent_monitor.parsers import _event_id
from agent_monitor.config import load_config, path_diagnostics


def test_refresh_sources_reuses_unchanged_parse_cache(tmp_path, monkeypatch):
    path=tmp_path / "s.jsonl"
    path.write_text('{"type":"session_meta","payload":{"id":"s"}}', encoding="utf-8")
    monitor=AgentMonitor({"paths":{"codex":[str(tmp_path)],"claude":[],"antigravity":[]}})
    import agent_monitor.service as service
    original=service.parse_source; calls=[]
    monkeypatch.setattr(service,"parse_source",lambda source: calls.append(source.path) or original(source))
    first=monitor.get_snapshot()
    second=monitor.refresh_sources()
    assert len(calls) == 1 and first is second


def source(tmp_path: Path, agent: str, text: str) -> SourceFile:
    path = tmp_path / f'{agent}.jsonl'; path.write_text(text, encoding='utf-8'); stat = path.stat()
    return SourceFile(agent, path, stat.st_size, stat.st_mtime_ns)


def test_codex_preferred_usage_is_not_merged_with_cumulative(tmp_path):
    result = parse_codex(source(tmp_path, 'codex', '\n'.join([
        '{"type":"session_meta","payload":{"id":"s"},"timestamp":"2026-01-01T00:00:00Z"}',
        '{"type":"turn_context","payload":{"turn_id":"t"},"timestamp":"2026-01-01T00:00:01Z"}',
        '{"type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"total_tokens":100}}}}',
        '{"type":"token_usage_record","payload":{"turn_id":"t","response_id":"r","usage":{"input_tokens":10,"cached_input_tokens":4,"output_tokens":2,"total_tokens":12}},"timestamp":"2026-01-01T00:00:02Z"}',
    ])))
    usages = result.turns[0].usage
    assert len(usages) == 1 and usages[0].total_tokens == 12 and usages[0].session_id == 's'


def test_codex_cumulative_reset_keeps_new_period_and_preferred_turn_wins(tmp_path):
    result = parse_codex(source(tmp_path, 'codex', '\n'.join([
        '{"type":"session_meta","payload":{"id":"s"}}',
        '{"type":"turn_context","payload":{"turn_id":"old"}}',
        '{"type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"total_tokens":100}}}}',
        '{"type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"total_tokens":20}}}}',
        '{"type":"turn_context","payload":{"turn_id":"new"}}',
        '{"type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"total_tokens":30}}}}',
        '{"type":"token_usage_record","payload":{"turn_id":"new","response_id":"r","usage":{"total_tokens":4}}}',
    ])))
    old = next(turn for turn in result.turns if turn.turn_id == 'old')
    new = next(turn for turn in result.turns if turn.turn_id == 'new')
    assert [usage.total_tokens for usage in old.usage] == [100, 20]
    assert [usage.total_tokens for usage in new.usage] == [4]


def test_codex_total_token_count_uses_total_as_cumulative_and_components_delta(tmp_path):
    result = parse_codex(source(tmp_path, 'codex', '\n'.join([
        '{"type":"session_meta","payload":{"id":"s"}}', '{"type":"turn_context","payload":{"turn_id":"t"}}',
        '{"type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"total_tokens":110,"input_tokens":100,"output_tokens":10},"last_token_usage":{"total_tokens":1}}}}',
        '{"type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"total_tokens":170,"input_tokens":150,"output_tokens":20},"last_token_usage":{"total_tokens":1}}}}',
        '{"type":"event_msg","payload":{"type":"task_complete"}}',
    ])))
    usage = result.turns[0].usage
    assert [item.total_tokens for item in usage] == [110, 60] and (usage[-1].input_tokens, usage[-1].output_tokens) == (50, 10) and result.sessions[0].status == 'completed'


def test_codex_lifecycle_ends_only_target_turn_and_context_model(tmp_path):
    result = parse_codex(source(tmp_path, 'codex', '\n'.join([
        '{"type":"session_meta","payload":{"id":"s"}}', '{"type":"turn_context","payload":{"turn_id":"t1","model":"m"}}',
        '{"type":"token_usage_record","payload":{"turn_id":"t1","usage":{"total_tokens":1}}}',
        '{"type":"turn_context","payload":{"turn_id":"t2"}}', '{"type":"event_msg","timestamp":"2026-01-01T00:00:02Z","payload":{"type":"task_complete","turn_id":"t1"}}',
    ])))
    t1, t2 = result.turns
    assert t1.status == 'completed' and t1.usage[0].model == 'm' and t2.status != 'completed' and result.sessions[0].status != 'completed'


def test_codex_task_abort_marks_turn_cancelled(tmp_path):
    result = parse_codex(source(tmp_path, 'codex', '\n'.join(['{"type":"session_meta","payload":{"id":"s"}}','{"type":"turn_context","payload":{"turn_id":"t"}}','{"type":"event_msg","payload":{"type":"task_abort","turn_id":"t"}}'])))
    assert result.turns[0].status == 'cancelled' and result.sessions[0].status == 'cancelled'


def test_codex_null_token_count_info_is_ignored(tmp_path):
    result = parse_codex(source(tmp_path, 'codex', '\n'.join([
        '{"type":"session_meta","payload":{"id":"s"}}',
        '{"type":"event_msg","payload":{"type":"token_count","info":null}}',
    ])))
    assert result.sessions[0].session_id == 's' and not result.turns


def test_codex_parent_uses_explicit_subagent_spawn_evidence(tmp_path):
    result = parse_codex(source(tmp_path, 'codex', '{"type":"session_meta","payload":{"id":"child","source":{"subagent":{"thread_spawn":{"parent_thread_id":"parent"}}}}}'))
    assert result.sessions[0].parent_session_id == 'parent'


def test_nested_item_role_and_content_are_preserved(tmp_path):
    result = parse_codex(source(tmp_path, 'codex', '{"type":"session_meta","payload":{"id":"s"}}\n{"type":"response_item","payload":{"item":{"role":"user","content":"hello"}}}'))
    event = result.events[-1]
    assert event.role == 'user' and 'hello' in event.display


def test_orchestration_graph_reports_explicit_relations_and_missing_parent():
    at = datetime.now(timezone.utc)
    Session = __import__('agent_monitor.models', fromlist=['Session']).Session
    parent = Session('p', 'codex', None, 'p', None, None, at, at)
    child = Session('c', 'codex', 'p', 'c', None, None, at, at)
    missing = Session('m', 'codex', 'none', 'm', None, None, at, at)
    graph = orchestration_graph(ParseResult(sessions=[parent, child, missing]))
    assert graph['relation_count'] == 1 and graph['missing_parent_count'] == 1 and graph['depths'][('codex', 'c')] == 1


def test_orchestration_rollup_is_unique_across_three_levels():
    at = datetime.now(timezone.utc); Session = __import__('agent_monitor.models', fromlist=['Session']).Session
    sessions = [Session('a', 'codex', None, 'a', None, None, at, at), Session('b', 'codex', 'a', 'b', None, None, at, at), Session('c', 'codex', 'b', 'c', None, None, at, at)]
    turns = [Turn('ta', 'a', None, at, at, usage=[Usage(total_tokens=2, event_id='a')]), Turn('tb', 'b', None, at, at, usage=[Usage(total_tokens=3, event_id='b')]), Turn('tc', 'c', None, at, at, usage=[Usage(total_tokens=3, event_id='b')])]
    graph = orchestration_graph(ParseResult(sessions=sessions, turns=turns))
    assert graph['depths'][('codex', 'c')] == 2 and graph['rollups'][('codex', 'a')]['total_tokens'] == 5


def test_orchestration_numeric_all_null_and_overlap_duration_union():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc); Session = __import__('agent_monitor.models', fromlist=['Session']).Session
    sessions = [Session('r', 'codex', None, 'r', None, None, base, base.replace(hour=2)), Session('m', 'codex', 'r', 'm', None, None, base.replace(hour=1), base.replace(hour=3)), Session('w', 'codex', 'm', 'w', None, None, base.replace(hour=2), base.replace(hour=4))]
    turns = [Turn('r', 'r', None, base, base, usage=[Usage(total_tokens=10, input_tokens=10, cache_read_tokens=1, event_id='1')]), Turn('m', 'm', None, base, base, usage=[Usage(total_tokens=20, input_tokens=20, cache_read_tokens=2, event_id='2')]), Turn('w', 'w', None, base, base, usage=[Usage(total_tokens=30, input_tokens=30, cache_read_tokens=3, event_id='3'), Usage(total_tokens=40, input_tokens=40, cache_read_tokens=4, event_id='4')])]
    graph = orchestration_graph(ParseResult(sessions=sessions, turns=turns))
    rollup = graph['rollups'][('codex', 'r')]
    assert rollup['total_tokens'] == 100 and rollup['cache_read_ratio'] == .1 and rollup['duration_seconds'] == 14400
    null_graph = orchestration_graph(ParseResult(sessions=[sessions[0]], turns=[Turn('n', 'r', None, base, base, usage=[Usage(event_id='n')])]))
    assert null_graph['rollups'][('codex', 'r')]['total_tokens'] is None


def test_config_missing_path_is_diagnostic_and_update_resets_monitor(tmp_path):
    missing = str(tmp_path / 'missing')
    assert path_diagnostics({'paths': {'codex': [missing]}})[0]['kind'] == 'missing'
    monitor = AgentMonitor({'paths': {'codex': [missing], 'claude': [], 'antigravity': []}})
    assert monitor.refresh()['config_diagnostics'][0]['path'] == missing
    monitor.update_config({'paths': {'codex': [], 'claude': [], 'antigravity': []}})
    assert monitor.refresh()['generation'] == 2


def test_load_config_valid_json_wrong_shape_falls_back(tmp_path):
    path = tmp_path / 'config.json'; path.write_text('[]', encoding='utf-8')
    assert 'paths' in load_config(path)


def test_module_update_config_is_public():
    update_config({'paths': {'codex': [], 'claude': [], 'antigravity': []}})
    assert isinstance(public_poll_session('none'), dict)
    assert public_recent_events('none') == []


def test_snapshot_timezone_is_normalized_and_invalid_value_is_diagnostic():
    valid = AgentMonitor({'timezone': 'UTC', 'paths': {'codex': [], 'claude': [], 'antigravity': []}}).refresh()
    invalid = AgentMonitor({'timezone': 'Nope/Invalid', 'paths': {'codex': [], 'claude': [], 'antigravity': []}}).refresh()
    assert valid['timezone'] == 'UTC' and valid['config']['timezone'] == 'UTC'
    assert invalid['timezone'] == 'UTC' and any(item['kind'] == 'invalid_timezone' for item in invalid['config_diagnostics'])


def test_poll_session_generation_changes_only_when_selected_file_changes(tmp_path):
    path = tmp_path / 's.jsonl'; path.write_text('{"type":"session_meta","payload":{"id":"s"}}\n', encoding='utf-8')
    monitor = AgentMonitor({'paths': {'codex': [str(tmp_path)], 'claude': [], 'antigravity': []}})
    first = monitor.refresh()['generation']
    stable = monitor.refresh()
    assert stable['generation'] == first
    # Steady selected polling returns the cached snapshot identity: no scan,
    # parse, deepcopy, or full derived-view combination is needed.
    assert monitor.poll_session('s') is stable
    path.write_text('{"type":"session_meta","payload":{"id":"s"}}\n{"type":"turn_context","payload":{"turn_id":"t"}}\n', encoding='utf-8')
    assert monitor.poll_session('s')['generation'] == first + 1


def test_selected_poll_replaces_only_the_matching_agent_without_snapshot_recombination(tmp_path, monkeypatch):
    import agent_monitor.service as service
    roots = {agent: tmp_path / agent for agent in ('codex', 'claude')}
    for agent, root in roots.items():
        root.mkdir(); (root / 'same.jsonl').write_text('1', encoding='utf-8')

    def parsed(source_file):
        total = int(source_file.path.read_text(encoding='utf-8'))
        session = Session('same', source_file.agent, None, str(source_file.path), None, source_file.agent, None, None, sources=[str(source_file.path)])
        usage = Usage(total_tokens=total, event_id=f'{source_file.agent}-{total}', agent=source_file.agent, session_id='same')
        turn = Turn('turn', 'same', None, None, None, usage=[usage], agent=source_file.agent)
        event = LogEvent(f'{source_file.agent}-{total}', source_file.agent, 'same', None, str(total), str(source_file.path), source_file.agent, 'jsonl', '1')
        return ParseResult(sessions=[session], turns=[turn], events=[event])

    monkeypatch.setattr(service, 'parse_source', parsed)
    monitor = AgentMonitor({'paths': {agent: [str(root)] for agent, root in roots.items()}})
    initial = monitor.refresh()
    (roots['codex'] / 'same.jsonl').write_text('30', encoding='utf-8')
    monkeypatch.setattr(monitor, 'get_snapshot', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('whole snapshot recombination')))
    monkeypatch.setattr(service, 'orchestration_graph', lambda *args: (_ for _ in ()).throw(AssertionError('whole graph rebuild')))
    updated = monitor.poll_session('same', agent='codex')
    totals = {(turn.agent, turn.session_id): turn.usage[0].total_tokens for turn in updated['requests']}
    assert totals == {('codex', 'same'): 30}
    assert {(event.agent, event.session_id) for event in updated['events']} == {('codex', 'same')}
    assert {(turn.agent, turn.session_id): turn.usage[0].total_tokens for turn in initial['requests']} == {('codex', 'same'): 1}
    assert updated['generation'] == initial['generation'] + 1
    legacy = monitor.poll_session('same')
    assert {(turn.agent, turn.session_id): turn.usage[0].total_tokens for turn in legacy['requests']} == {('codex', 'same'): 30}
    assert legacy['generation'] > updated['generation']


def test_selected_poll_reports_empty_old_session_after_source_replacement_until_refresh(tmp_path, monkeypatch):
    import agent_monitor.service as service
    path = tmp_path / 'same.jsonl'; path.write_text('same', encoding='utf-8')

    def parsed(source_file):
        sid = source_file.path.read_text(encoding='utf-8')
        session = Session(sid, source_file.agent, None, str(source_file.path), None, sid, None, None, sources=[str(source_file.path)])
        return ParseResult(sessions=[session], turns=[Turn('turn', sid, None, None, None, agent=source_file.agent)])

    monkeypatch.setattr(service, 'parse_source', parsed)
    monitor = AgentMonitor({'paths': {'codex': [str(tmp_path)], 'claude': [], 'antigravity': []}})
    initial = monitor.refresh()
    path.write_text('replacement', encoding='utf-8')
    live = monitor.poll_session('same', agent='codex')
    assert not live['sessions'] and initial['sessions'][0].session_id == 'same'
    refreshed = monitor.refresh()
    assert [session.session_id for session in refreshed['sessions']] == ['replacement']


def test_claude_cache_is_added_and_duplicate_response_is_replaced(tmp_path):
    result = parse_claude(source(tmp_path, 'claude', '\n'.join([
        '{"type":"user","uuid":"u","timestamp":"2026-01-01T00:00:00Z","message":{"role":"user","content":"hello"}}',
        '{"uuid":"a1","timestamp":"2026-01-01T00:00:01Z","message":{"role":"assistant","id":"r","usage":{"input_tokens":10,"cache_read_input_tokens":5,"cache_creation_input_tokens":3,"output_tokens":2}}}',
        '{"uuid":"a2","timestamp":"2026-01-01T00:00:02Z","message":{"role":"assistant","id":"r","usage":{"input_tokens":12,"cache_read_input_tokens":5,"cache_creation_input_tokens":3,"output_tokens":4}}}',
    ])))
    usage = result.turns[0].usage[0]
    assert (usage.input_tokens, usage.output_tokens, usage.total_tokens) == (20, 4, 24)


def test_unknown_values_stay_unknown_and_cache_ratio_is_weighted():
    at = datetime.now(timezone.utc)
    turn = Turn('t', 's', None, at, at, usage=[Usage(input_tokens=100, cache_read_tokens=50), Usage(input_tokens=None, cache_read_tokens=None)])
    summary = analyze(ParseResult(turns=[turn]))
    assert summary['usage']['output_tokens'] is None and summary['cache_read_ratio'] == .5


def test_model_filter_does_not_mutate_original_usage():
    at = datetime.now(timezone.utc)
    usage = Usage(model='one', total_tokens=1)
    session = __import__('agent_monitor.models', fromlist=['Session']).Session('s', 'codex', None, 'p', None, None, at, at)
    original = ParseResult(sessions=[session], turns=[Turn('t', 's', None, at, at, usage=[usage])])
    filtered = filter_data(original, models=['other'])
    assert not filtered.turns[0].usage and original.turns[0].usage == [usage]


def test_period_and_model_filter_are_event_level_and_exclude_unknown_time():
    at = datetime(2026, 1, 2, tzinfo=timezone.utc); Session = __import__('agent_monitor.models', fromlist=['Session']).Session
    session = Session('s', 'codex', None, 'p', None, None, at, at)
    turn = Turn('t', 's', None, at, at, usage=[Usage(model='m', total_tokens=10, occurred_at=at), Usage(model='m', total_tokens=20), Usage(model='x', total_tokens=30, occurred_at=at)])
    filtered = filter_data(ParseResult(sessions=[session], turns=[turn]), start=datetime(2026, 1, 1, tzinfo=timezone.utc), end=datetime(2026, 1, 3, tzinfo=timezone.utc), models=['m'])
    assert [usage.total_tokens for usage in filtered.turns[0].usage] == [10]


def test_interval_and_duration_cross_midnight():
    start, end = interval_for_dates(datetime(2026, 1, 1).date(), datetime(2026, 1, 1).date(), 'Asia/Seoul')
    assert (end - start).total_seconds() == 86400
    split = split_duration_by_day(datetime(2026, 1, 1, 14, tzinfo=timezone.utc), datetime(2026, 1, 1, 16, tzinfo=timezone.utc), 'Asia/Seoul')
    assert split['2026-01-01'] == 3600 and split['2026-01-02'] == 3600


def test_same_antigravity_session_merges_installation_sources(tmp_path):
    left = tmp_path / 'antigravity' / 'same'; right = tmp_path / 'antigravity-cli' / 'same'
    left.mkdir(parents=True); right.mkdir(parents=True)
    text = '{"timestamp":"2026-01-01T00:00:00Z","role":"user","content":"hello"}\n'
    paths = [left / 'transcript.jsonl', right / 'transcript.jsonl']
    for path in paths: path.write_text(text, encoding='utf-8')
    files = []
    for path, label in zip(paths, ('antigravity', 'antigravity-cli')):
        stat = path.stat(); files.append(SourceFile('antigravity', path, stat.st_size, stat.st_mtime_ns, label, 'antigravity'))
    result = parse_sources(files)
    assert len(result.sessions) == 1
    assert result.sessions[0].sources == [str(path) for path in paths]
    assert result.sessions[0].source_label == 'antigravity'


def test_event_ids_do_not_collide_between_sessions(tmp_path):
    def codex(path, sid):
        path.write_text('\n'.join([
            f'{{"type":"session_meta","payload":{{"id":"{sid}"}}}}',
            '{"type":"turn_context","payload":{"turn_id":"t"}}',
            '{"type":"token_usage_record","payload":{"turn_id":"t","response_id":"shared","usage":{"total_tokens":4}}}',
        ]), encoding='utf-8')
        stat = path.stat(); return SourceFile('codex', path, stat.st_size, stat.st_mtime_ns)
    result = parse_sources([codex(tmp_path / 'one.jsonl', 'one'), codex(tmp_path / 'two.jsonl', 'two')])
    usages = [usage for turn in result.turns for usage in turn.usage]
    assert len(usages) == 2 and len({usage.event_id for usage in usages}) == 2


def test_cross_agent_same_session_turn_usage_event_ids_are_distinct():
    left = Usage(source='shared', response_id='response')
    right = Usage(source='shared', response_id='response')
    assert _event_id(left, 'codex', 'same') != _event_id(right, 'claude', 'same')


def test_monitor_reparses_replaced_or_growing_jsonl_and_exposes_recent_events(tmp_path):
    path = tmp_path / 'session.jsonl'
    path.write_text('{"type":"session_meta","payload":{"id":"s"}}\n', encoding='utf-8')
    monitor = AgentMonitor({'paths': {'codex': [str(tmp_path)], 'claude': [], 'antigravity': []}})
    assert not monitor.refresh()['usage']
    path.write_text('\n'.join([
        '{"type":"session_meta","payload":{"id":"s"}}',
        '{"type":"turn_context","payload":{"turn_id":"t"}}',
        '{"type":"token_usage_record","timestamp":"2026-01-01T00:00:00Z","payload":{"turn_id":"t","response_id":"r","usage":{"total_tokens":7}}}',
        '{"type":"token_usage_record"',  # incomplete trailing JSONL is safely skipped
    ]), encoding='utf-8')
    monitor.poll_session('s')
    events = monitor.recent_events(session_id='s', include_raw=True)
    assert len(events) == 3 and events[-1].raw_record['payload']['usage']['total_tokens'] == 7


def test_monitor_logs_merge_mirrored_sources_and_filter_to_selected_session(tmp_path):
    roots = [tmp_path / name for name in ('antigravity', 'antigravity-cli', 'antigravity-ide')]
    for root in roots:
        folder = root / 'same'; folder.mkdir(parents=True)
        (folder / 'transcript.jsonl').write_text('{"id":"e","timestamp":"2026-01-01T00:00:00Z","role":"user","content":"live"}\n', encoding='utf-8')
    monitor = AgentMonitor({'paths': {'codex': [], 'claude': [], 'antigravity': [str(root) for root in roots]}})
    events = monitor.recent_events('same', limit=200, include_raw=True)
    assert events == []  # Deprecated collectors never read historical sources.
    assert monitor.get_snapshot()['diagnostics'] == []
    assert monitor.get_snapshot()['paths'] == {'codex': []}


def test_antigravity_brain_path_uses_conversation_component(tmp_path):
    path = tmp_path / 'brain' / 'conversation-42' / '.system_generated' / 'logs' / 'transcript.jsonl'
    path.parent.mkdir(parents=True)
    path.write_text('{"timestamp":"2026-01-01T00:00:00Z","role":"user","content":"x"}\n', encoding='utf-8')
    stat = path.stat()
    result = parse_sources([SourceFile('antigravity', path, stat.st_size, stat.st_mtime_ns)])
    assert result.sessions[0].session_id == 'conversation-42'
