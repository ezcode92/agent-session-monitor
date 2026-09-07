# Validation

## Current focused checks

The following commands ran against the current working tree:

```bash
uv run pytest tests/test_app_integration.py::test_overview_renders_compact_top_ten_request_scalars -q
```

Result: **1 passed in 1.26s**.

```bash
uv run pytest tests/test_ui_adapter.py -k 'live_monitor_passes_composite or history_panes_are_lazy or view_cache_reuses' -q
```

Result: **3 passed, 31 deselected in 1.40s**.

```bash
uv run pytest tests/test_app_integration.py -q
```

Result: **5 passed in 3.59s**, with **1 pandas Period timezone conversion warning**.

```bash
uv run pytest tests/test_ui_adapter.py -q
```

Result: **34 passed in 3.47s**, with **1 pandas Period timezone conversion warning**.

```bash
UV_CACHE_DIR=/tmp/agent-monitor-uv-cache uv run pytest -q
```

Result: **76 passed in 6.26s**, with **2 existing pandas Period timezone
conversion warnings**.  The earlier `70 passed` result is historical WIP
evidence only.

The focused cache check proves that calling `_view` twice with the same snapshot
object and filter state invokes `build_view_data` once and returns the cached
object on the second call.

## Same-snapshot view benchmark

An in-memory synthetic snapshot was reused for every sample: 20 sessions,
1,000 usage rows, 1,000 requests, and 10,000 events.  Reproduce it with:

```bash
uv run python benchmark_monitor.py --view
```

The benchmark calls `build_view_data` seven times per mode with identical
filters and reports the median of `perf_counter()` durations.  It does not read
local agent logs or write benchmark files.

| Mode | Median | Samples (seconds) |
| --- | ---: | --- |
| `include_events=False` | 0.460635 s | 0.468004, 0.489991, 0.453654, 0.438680, 0.460635, 0.465539, 0.440448 |
| `include_events=True` | 0.711450 s | 0.711450, 0.749218, 0.761766, 0.669662, 0.662025, 0.702650, 0.747419 |

This is a synthetic construction-time comparison, not a browser rendering,
collector, or real-log performance claim.

## Runtime and browser checks

- `uv sync --locked --group dev` completed successfully.
- `python app.py` completed without a traceback or `ImportError`.
- The Streamlit endpoint returned HTTP 200.
- Chromium 153 exercised all five pages, the History request/log/live panes,
  and manual refresh without Streamlit exceptions or JavaScript errors.  The
  toolbar was hidden.

## Selected live-poll contract

For a changed selected file, `poll_session` returns the selected live view and
does not rebuild the orchestration graph.  A stable poll may reuse the dashboard
snapshot.  Dashboard aggregates update on the next normal or manual refresh;
missing files are cleared on the next discovery pass.

## Actual-data limits

Codex actual-log behavior was validated.  No Claude sample was available.  The
readable AGY sample currently produced `unsupported_format` and zero sessions,
so its real schema remains unverified.

## Monitor benchmark

On the same 10,486,027-byte synthetic dataset, the changed selected-file poll
improved from a **1.315s** baseline to **0.856s**.  The final run parsed the
selected file twice and the unrelated file once.  Reproduce the collector
measurement with `uv run python benchmark_monitor.py`; it creates only
temporary local JSONL files and writes an ignored local report.

## Historical benchmark evidence

The synthetic 10 MB monitor benchmark recorded cold refresh 4.008s, warm
refresh 2.025s before the unchanged-snapshot fast path, unchanged selected
poll below 0.001s, and changed selected poll 2.849s.  These figures predate
the current continuation; rerun `benchmark_monitor.py` before making a current
collector-performance claim.
