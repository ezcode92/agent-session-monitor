# Validation

## Current checks (2026-09-08)

```bash
UV_CACHE_DIR=/tmp/agent-monitor-uv-cache uv lock --offline
UV_CACHE_DIR=/tmp/agent-monitor-uv-cache uv run pytest -q
```

Result: **112 passed in 9.74s**, without warnings. The Streamlit minimum is
1.63 for the tested cell-selection and programmatic selection-reset behavior;
lock resolution changed only the application's minimum requirement.
After the final timeline lane-order and diagnostic-tooltip corrections,
`uv run pytest -q tests/test_app_integration.py` passed **11 tests in 5.91s**.
`uv sync --locked --group dev` and `git diff --check` also passed.

Focused checks before the full run covered:

- Actual entrypoint rendering, numeric cache-component bars (including unknown
  components), separate total/input/output and per-request averages, and HH:MM:SS.
- Session/parent cell selection with colliding agent IDs, absent parents,
  parents outside current filters, pagination/search selection reset, compact
  visible columns, and deduplicated provenance.
- Initial and newly completed Codex sessions do not stat or parse on live polls;
  manual refresh can observe a resumed session and enable polling again.
- Antigravity created_at/step_index records, USER_INPUT turns, stable event
  merging, unknown usage, malformed records, brain defaults and legacy roots.
- Local date, Monday week and calendar-month boundaries with multiple agents.
- Per-request timeline clipping, gaps, overlaps, missing/reversed/zero spans,
  composite identity filtering and no input mutation.
- Metric/table-header tooltips and removal of previous-period comparison and
  Graph exports. The base view no longer computes either removed dataset.

The existing same-snapshot cache tests still confirm that `_view` reuses its
lightweight base view and does not materialize transcript events.

## Historical same-snapshot view benchmark (before this UI revision)

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

A separate Streamlit server and Chromium 153 used synthetic data only (three
Codex sessions with fifteen requests). The endpoint returned HTTP 200.

- All five pages and History request/log/live panes were exercised.
- Real mouse clicks on session and parent cells changed the detail panel.
- Completed-session live notice and daily/weekly/monthly selection worked.
- Analysis CSV contained the selected period buckets and grouping.
- The orchestration plot rendered fifteen request spans across three lanes,
  with idle gaps, local timestamps and formatted duration hovers. No Graph
  download buttons remained.
- Compact History and analysis tables, chart labels and captions were visually
  inspected. No Streamlit exceptions or JavaScript errors were observed.

Browser scripts/screenshots live only in a temporary QA directory and contain
synthetic content; no raw private logs or browser artifacts are committed.

## Selected live-poll contract

For a changed selected file, `poll_session` returns the selected live view and
does not rebuild the orchestration graph.  A stable poll may reuse the dashboard
snapshot.  Dashboard aggregates update on the next normal or manual refresh;
missing files are cleared on the next discovery pass.

## Actual-data checks and limits

Codex actual-log behavior was validated earlier. No Claude sample was available.
The Antigravity CLI brain tree was inspected read-only: **356 transcripts,
868 requests, 70,953 events**; four malformed lines were skipped with diagnostics.
Scanning the installation root and its brain child returned identical source
files and provenance. The antigravity and antigravity-ide brain roots were absent
in this environment; synthetic fixtures cover those installation labels.

These AGY transcripts have created_at, step_index, type, status, content and
optional tool-call metadata. They contain no token/model/parent/project fields,
so usage stays unknown and parent links are not invented. Individual step DONE
is not conversation completion. A per-source usage_unavailable diagnostic
replaces the unused per-session/request quality columns.

The official [Hooks documentation](https://www.antigravity.google/docs/hooks)
confirms `<app_data_dir>/brain/<conversationId>/.system_generated/logs/transcript.jsonl`
for Antigravity and CLI; [IDE Hooks](https://antigravity.google/docs/ide/hooks)
documents the IDE installation root. Existing saved roots are preserved; defaults
now explicitly point to brain. Full/chunk transcript copies are not ingested.

## Historical monitor benchmark

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
