# Agent Monitor continuation handoff

Use this document as the working prompt for the next maintainer.  It describes
the repository state without exposing local log contents, private paths, or
machine-specific configuration.  Keep this file in the authorized WIP
checkpoint; do not delete it until every required checklist item below has been
verified in the current checkout.

Repository: `https://github.com/ezcode92/agent-session-monitor.git`

## Objective and constraints

The application monitors Codex, Claude, and Antigravity/AGY local agent logs.
AGY is one logical agent assembled from the three configured roots for the
base Antigravity data, CLI data, and IDE data.  Every session, usage record,
and display event must retain source provenance (`source_label`, `source_kind`,
and `source_path`); same session IDs from different agents are distinct.

The three portable AGY roots are `~/.gemini/antigravity`,
`~/.gemini/antigravity-cli`, and `~/.gemini/antigravity-ide`.  They remain one
AGY agent in aggregate while each retained record identifies its source.
The physical working folder remains `agent-monitor` because a Windows
open-handle rename was unfinished.  A fresh `git clone` defaults to
`agent-session-monitor`; no rename is required in a new environment.

Keep the collector in-process and file based: no database, no separate
collector daemon, and no raw-log loading during ordinary dashboard rendering.  Selected
session monitoring is intended for one-second polling; full discovery is
throttled.  Preserve nullable unknown token values instead of replacing them
with zero.  Use composite `(agent, session_id)` identities in joins, filters,
event IDs, hierarchy ownership, and monitor views.

Do not add private paths, raw log payloads, user configuration, credentials, or
tool staging output to source control.  Spark work was cancelled; do not resume
it.  Checkpoint commits/pushes are now authorized for completed changes.  The
remote/main checkpoint `35ae0af` is a historical baseline; the commit that
includes this handoff is the restart base for future work.  Delete this handoff
only after the final checklist is complete, then use `git rm`, commit, and push.

Roles: the main agent owns orchestration and final review but does not directly
change source or run unit checks; it gives staged instructions to the Terra
medium sub-orchestrator.  Terra medium gives detailed bounded tasks to Terra
low, owns independent parallel work and integration, and reports evidence back
to main.  Terra low owns bounded source changes and unit tests.  Spark is
cancelled.

## Current feature map

### Collector/core

- `models.py` defines sessions, turns, usage, provenance, and display-event
  fields.  Usage/event agent identity is explicit.
- `discovery.py` finds configured sources independently so an unreadable root
  is isolated.  Configuration defaults include the three AGY roots.
- `parsers.py` normalizes Codex, Claude, and AGY JSON/JSONL records.  Codex
  handles nullable nested payloads, cumulative token deltas/reset behavior,
  lifecycle records, per-turn status/model context, and nested role/content.
  Claude supports streamed/cache records and parent/child data.  AGY session
  identity uses explicit conversation identity or the brain component rather
  than the `logs` directory name.
- `service.py` combines sources without sid-only collisions, merges same-agent
  sessions while preserving source lists and turns, exposes snapshots, selected
  polling, recent events, raw single-record lookup, configuration wrappers, and
  orchestration output.  `refresh_sources()` is the manual discovery/stat path:
  it makes discovery due but calls `get_snapshot(force=False)`, reusing cached
  parsed files when revisions do not change.
- `analysis.py` provides event-level filtering, local-time day splitting, and
  evidence-qualified orchestration graph/rollups.

### View data and UI

- `ui/adapter.py` contains shallow record/frame conversion, source labels,
  scalar usage helpers, filtering, monitor helpers, CSV export, and UI-only
  noise filtering.  Request/usage selected-session membership is vectorized
  with composite MultiIndex membership, with a sid-only fallback only for
  legacy agentless records.
- `ui/view_data.py` builds filtered scalar data frames, request token/cache
  aggregates, period-clipped request duration/daily duration, comparisons,
  graph rollups, and exports.  Its event prefilter accepts `include_events`;
  typed datetimes avoid string timestamp parsing and bounds are normalized once
  before the raw-event loop.
- `ui/app.py` caches the base view by snapshot object identity, generation,
  timezone, filters, and event inclusion.  The shared base view requests
  `include_events=False`.  History creates event rows only for the selected
  `(agent, sid)` in its Logs pane; real-time polling only runs in its Real-time
  pane.  Raw JSON is fetched only on explicit drawer action.
- Sidebar agent options are the union of configured and discovered agents;
  AGY is rendered as `agy (Antigravity)`.  It reports configured roots, unique
  read log files, and sessions, including an explicit zero for configured AGY
  roots with no sessions.  It shows compact diagnostic count, a manual refresh
  button, and an opt-in advanced five-second refresh.  Cold/manual retrieval
  uses a spinner.  Streamlit config enables minimal toolbar and hides the top
  bar.
- Overview retains six scalar KPIs and current charts.  History uses Request,
  Logs, and Real-time native horizontal radio panes.  Analysis consumes view
  data and request clipped durations.  Orchestration uses evidence-qualified
  graph data; its live-log toggle is default off.

## Completed and verified in this WIP

Focused tests most recently run successfully:

- `tests/test_view_data.py -q`: 7 passed after typed event timestamp/bounds
  work.
- History lazy-pane target: 2 passed, 26 deselected.
- Refresh/status/orchestration target: 5 passed, 54 deselected.
- Composite membership target: 2 passed, 24 deselected.

The current full-suite result is
`.venv\Scripts\python.exe -m pytest -q`: **70 passed**, with **2 pandas Period
timezone conversion warnings**, in **14.85 s**.  An older scheduled-fragment
AppTest timeout was historical WIP evidence and is not the current full-suite
result.  Browser visual QA and latest real-data startup/cache validation remain
TODO before release claims.

`docs/validation.md` records prior synthetic 10 MB timing observations:
cold 4.008 s, warm 2.025 s (both pre-fastpath), unchanged under 0.001 s, and
changed 2.849 s.  Those numbers are historical/synthetic and are not a current
benchmark of the latest WIP.  Re-run a controlled benchmark before making any
performance claim.

The most recent same-snapshot timing evidence was 26.949 s before versus
21.987 s after (18.4% improvement); `include_events=False` measured 5.712 s.
The cProfile run measured 62.511 s and carries profiler overhead, so it is not
directly comparable to wall-clock timings.  These WIP measurements must be
remeasured with the final code and identical snapshot/filter conditions.

AGY diagnostic evidence is limited: readable transcript count was zero and
the CLI returned Unauthorized.  That is an access/readability finding, not
evidence of malformed raw usage or parser failure.

## Work in progress / remaining checklist

1. The last requested UI polish batch was interrupted before product edits:
   add a compact Overview top-10 request scalar table using existing
   `view['requests_df']` only (title, agent, status, clipped time, tokens,
   source).  Do not introduce new filtering or aggregation work.
2. In Orchestration, present selected-subtree rows with depth-indented title
   and native numeric columns labelled directly/descendant/total tokens in
   Korean.  Leave timeline/export behavior unchanged.  Add a focused AppTest.
3. Re-run all relevant focused tests after any continuation edit, then execute
   the complete pytest suite.  Preserve the current warning count/result as a
   baseline and investigate any new scheduled-fragment/AppTest regression.
4. Validate a clean Streamlit startup and a normal page request.  `python
   app.py` has a local `src` bootstrap for imports; normal use remains the
   Streamlit command documented in README.  Do not expose local configuration
   in output.
5. Validate actual data only where access is authorized.  Codex actual-log
   behavior has been exercised during development; AGY and Claude actual logs
   were unavailable/unverified in the reported environment.  Preserve that
   limitation in final reporting unless new evidence is obtained.
6. Review provenance, composite identities, nullable usage semantics, monitor
   pause/replacement behavior, source-root diagnostics, and graph period/model
   filtering after any merge conflicts.  Avoid sid-only shortcuts.
7. Final verification must include: numeric before/after timing against the
   same snapshot; UI view-cache reuse; AppTest coverage for the new history pane
   selectors; toolbar/manual refresh behavior; and a selected-live changed-file
   poll proving it does not trigger whole-snapshot recombination.
8. Known performance TODO: `service.poll_session` currently calls
   `get_snapshot`, which can perform whole-snapshot recombination.  Benchmark
   changed live polling first, then consider a lighter selected-session path
   only if the measurement justifies it.
9. Browser visual QA was not run because Node ACL initialization failed.  An
   HTTP 200 response is a transport check, not render validation.

## Suggested safe process

1. Read `README.md`, `docs/validation.md`, `docs/ui-benchmark.md`, every core
   file under `src/agent_monitor/`, source files named above, and the current
   tests before changing code.  Use UTF-8 for all edits.
2. Bootstrap portably with Python 3.12 and managed dependencies:
   `uv sync --group dev`.  Run the UI with
   `uv run streamlit run app.py --server.address 127.0.0.1 --server.port 8501`
   and the suite with `uv run pytest -q`.  `.tools` and `.venv` are local,
   unversioned environments and must not be committed.
3. Make one bounded change at a time; run its target test first.  Before Git
   changes use this exact order: `git status` -> `git fetch origin` -> if clean
   `git switch main` -> `git pull --ff-only origin main`.  Preserve staged or
   local changes; never overwrite them.  Do not use destructive Git commands;
   inspect status/diff before every commit.
4. Run full tests only after target tests pass.  Record exact command and
   result, distinguishing focused checks from full-suite results.
5. Before final delivery, check the normal Streamlit startup/import path and
   ensure no private local artifacts were added.
6. Only when every checklist item above is complete: `git rm CODEX_HANDOFF.md`,
   inspect the final diff, create a reviewable commit, and push.  The current
   user authorization covers this documented WIP checkpoint and future
   completed changes.  Review `git status` and the final diff before every
   commit/push.
