import pandas as pd

from agent_monitor.ui.adapter import request_timeline


def request(turn, left, right, agent='codex', sid='same', **extra):
    return {'agent': agent, 'session_id': sid, 'turn_id': turn, 'started_at': left, 'ended_at': right,
            'status': 'completed', 'title': f'Synthetic {turn}', 'total_tokens': 7, **extra}


def test_request_intervals_keep_gaps_and_metadata_without_mutating_source():
    data = pd.DataFrame([
        request('one', '2026-01-01T00:00:00Z', '2026-01-01T00:00:10Z'),
        request('two', '2026-01-01T00:01:00Z', '2026-01-01T00:01:20Z'),
    ])
    original = data.copy(deep=True)
    result = request_timeline(data, [('codex', 'same')], '2026-01-01T00:00:00Z', '2026-01-02T00:00:00Z')
    assert len(result) == 2 and result.turn_id.tolist() == ['one', 'two']
    assert result.clipped_duration_seconds.tolist() == [10, 20]
    assert (result.iloc[1].clip_start - result.iloc[0].clip_end).total_seconds() == 50
    assert result.title.tolist() == ['Synthetic one', 'Synthetic two']
    assert result.status.tolist() == ['completed', 'completed'] and result.total_tokens.tolist() == [7, 7]
    pd.testing.assert_frame_equal(data, original)


def test_selected_period_clips_partial_intervals_and_omits_outside_rows():
    data = pd.DataFrame([
        request('left', '2025-12-31T23:59:00Z', '2026-01-01T00:00:10Z'),
        request('right', '2026-01-01T00:00:50Z', '2026-01-01T00:01:10Z'),
        request('before', '2025-12-31T23:58:00Z', '2026-01-01T00:00:00Z'),
        request('after', '2026-01-01T00:01:00Z', '2026-01-01T00:02:00Z'),
    ])
    result = request_timeline(data, [('codex', 'same')], '2026-01-01T00:00:00Z', '2026-01-01T00:01:00Z')
    assert result.turn_id.tolist() == ['left', 'right']
    assert result.clipped_duration_seconds.tolist() == [10, 10]
    assert result.iloc[0].clip_start == pd.Timestamp('2026-01-01T00:00:00Z')
    assert result.iloc[1].clip_end == pd.Timestamp('2026-01-01T00:01:00Z')
    assert result.iloc[0].started_at == pd.Timestamp('2025-12-31T23:59:00Z')


def test_composite_session_filter_does_not_include_other_agents():
    data = pd.DataFrame([
        request('one', '2026-01-01T00:00:00Z', '2026-01-01T00:00:10Z'),
        request('two', '2026-01-01T00:00:00Z', '2026-01-01T00:00:10Z', agent='claude'),
        request('three', '2026-01-01T00:00:00Z', '2026-01-01T00:00:10Z', sid='other'),
    ])
    result = request_timeline(data, [('codex', 'same')], None, None)
    assert result.turn_id.tolist() == ['one']
    assert request_timeline(data, [], None, None).empty


def test_unknown_invalid_zero_and_reversed_intervals_are_omitted():
    data = pd.DataFrame([
        request('unknown-start', None, '2026-01-01T00:00:10Z'),
        request('unknown-end', '2026-01-01T00:00:00Z', None),
        request('invalid', 'invalid timestamp', '2026-01-01T00:00:10Z'),
        request('zero', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'),
        request('reversed', '2026-01-01T00:00:10Z', '2026-01-01T00:00:00Z'),
    ])
    assert request_timeline(data, [('codex', 'same')], None, None).empty
    assert request_timeline(pd.DataFrame(), [('codex', 'same')], None, None).empty


def test_offset_times_are_converted_to_utc_and_missing_columns_are_empty():
    data = pd.DataFrame([request('one', '2026-01-01T09:00:00+09:00', '2026-01-01T09:00:10+09:00')])
    result = request_timeline(data, [('codex', 'same')], '2026-01-01T00:00:00Z', '2026-01-01T00:01:00Z')
    assert result.iloc[0].clip_start == pd.Timestamp('2026-01-01T00:00:00Z')
    assert str(result.started_at.dt.tz) == 'UTC'
    assert request_timeline(data.drop(columns='ended_at'), [('codex', 'same')], None, None).empty
    assert request_timeline(data.drop(columns='agent'), [('codex', 'same')], None, None).empty
