# Validation

## Diagnostics link runtime correction (2026-09-13)

The sidebar diagnostics branch now imports `pathlib.Path` before constructing
the Settings page link. This removes the `NameError` that occurred only when a
collector or configuration diagnostic was present; collection, filtering and
page-routing contracts are unchanged.

- Regression check: `.venv/bin/pytest
  tests/test_ui_adapter.py::test_sidebar_shows_configured_antigravity_and_diagnostics
  -q` — **1 passed in 1.10s**. The check now rejects any Streamlit exception.
- Related UI suites: `.venv/bin/pytest tests/test_ui_adapter.py
  tests/test_app_integration.py -q` — **49 passed in 8.65s**.

The affected failure state was exercised with Streamlit `AppTest`; a physical
browser click through the diagnostics link was not repeated.

## TinyFish audit access and ChatGPT report reader (2026-09-12)

The project now has two deliberately separate remote paths. The synthetic
`tests/browser_app.py` fixture can be bound to all interfaces for temporary
TinyFish UI inspection, while `mcp_server.py --scope results` exposes only
completed reports over stdio for an OpenAI Secure MCP Tunnel. The normal MCP
worker API, collectors and SQLite schema are unchanged.

- Corrected the attempted Streamlit wildcard bind from `0.0.0.1` to
  `0.0.0.0`. The documented local real-data commands still override it with
  `127.0.0.1`. The externally documented command runs the synthetic fixture,
  which now displays an explicit synthetic-data notice and uses temporary
  databases.
- The results MCP advertises exactly `list_analysis_reports` and
  `get_analysis_report`, both with `readOnlyHint=true`. An actual MCP client
  subprocess initialized the server, discovered both tools, listed and fetched
  a completed report, and confirmed that `source_path` and `record_key` were
  absent from returned evidence.
- Focused MCP/project-analysis checks passed: **8 passed in 4.30s** using a
  clean non-repository temporary root.
- Full suite: `.venv/bin/python -m pytest -q
  --basetemp=/var/tmp/asm-pytest-full-78418` — **149 passed in 22.08s**.
- A synthetic Streamlit process started on `0.0.0.0:18502` with the documented
  public-host/browser-port options. Local requests returned `ok` from
  `/_stcore/health` and HTTP **200** from `/`; the process was then stopped.
- `mcp_server.py --help` lists both `analysis` and `results` scopes, and
  `git diff --check` passed (Git only reported the repository's existing
  LF-to-CRLF normalization notices).

The sandbox cannot open listening sockets or complete the SDK's asynchronous
stdio transport, so the Streamlit and MCP process checks were run with host
permissions. `/tmp/.git` also makes pytest fixtures appear to share one Git
root, so project-analysis checks used `/var/tmp` as their isolated base.

Not tested: the user's ipTIME port-forward/firewall state, cellular access to
`ezcode92.iptime.org`, a real TinyFish run, or a real Secure MCP Tunnel/ChatGPT
workspace connection. Those require router changes, external network access and
user-owned OpenAI/TinyFish credentials. No router, ChatGPT workspace or tunnel
configuration was changed. Public plugin distribution still requires a stable
HTTPS Streamable HTTP endpoint; the HTTP-only DDNS path is documented only for
the temporary synthetic browser audit.

## Request tokens and tool-call history (2026-09-09)

History's Request view now displays selected-session input/output/total tokens,
per-request averages with known/total counts, and a request selector for tool
calls/results. Session totals use filtered direct usage; tool history follows the
entire selected request so a period boundary cannot hide its matching result.

- Added optional `LogEvent.turn_id`, populated from each parser's request
  boundary. Call/result matching is scoped to agent and session; repeated call
  IDs use request context. A delayed result can link across a request boundary
  only when the call ID identifies one candidate. Missing/ambiguous IDs and
  unknown success remain explicitly unconfirmed. Input/result previews are
  bounded to 1,000 characters; raw records are read only on button activation.
- Parser cache version is now 5. Codex task-start/user-message records preserve
  requests without token records. Claude user-role `tool_result` blocks no
  longer create phantom requests or steal subsequent usage; observed end times
  keep those requests available in the period-filtered history. Antigravity
  USER_INPUT boundaries include request ID 0. No SQLite migration or new MCP
  tool was introduced; usage arithmetic is unchanged.
- Full suite: `.venv/bin/python -m pytest -q` — **148 passed in 22.71s**.
  New checks cover Codex/Claude/Antigravity parsing, duplicate records, colliding
  IDs across agents/sessions/requests, late/unknown/ambiguous results, missing
  inputs, bounded previews, requests with no usage, token summaries, selection
  restoration, no implicit polling/raw reads and raw-read failure/retry.
- Browser: `VERIFY_REQUEST_TOOLS=1` with `tools/verify_ui.mjs` passed history
  layout and keyboard request/tool selection at 375px/1440px in light/dark.
  Success, failure and result-missing states and long inputs were captured;
  desktop and narrow screenshots were inspected. No browser runtime exceptions.
  Data and databases were temporary synthetic fixtures; physical mobile and
  screen-reader validation were not repeated.
- `git diff --check` passed. AST-only `graphify update .` completed with
  **665 nodes, 1,571 edges and 41 communities**.

Supported tool schemas are the existing function/custom-tool calls and results,
Claude tool_use/tool_result, normalized tool_calls, and recognized Antigravity
records. Unsupported formats or missing request metadata cannot establish a
complete history and are not interpreted as zero tool usage. Existing logs can
be reprocessed using Settings → Full rescan. Source logs remain read-only.

## Daily chart date-axis correction (2026-09-09)

Plotly's automatic sub-day ticks repeated calendar labels on daily token and
duration charts, especially with only one populated day. Date-line ticks now
start at the first bucket and advance by whole days, with larger intervals for
long ranges and a year in labels when the range crosses years. Data points,
missing-day spacing and totals are unchanged.

- `.venv/bin/python -m pytest -q tests/test_app_integration.py`: **15 passed in
  9.67s**, including single-day, adjacent-day, sparse-week and cross-year cases.
- `VERIFY_DATE_AXES=1` with `tools/verify_ui.mjs`: both overview date axes rendered
  unique labels at 375px and 1440px in light and dark mode (8 chart checks).
  Single-day screenshots were inspected; no browser runtime exceptions occurred.
  These checks use the existing isolated synthetic fixture, not real logs.
- `git diff --check` and the AST-only `graphify update .` completed.

## UI design adoption (2026-09-09)

The seven pages now use native URL navigation, a shared neutral/teal light and
dark theme, responsive layout and documented page contracts in
[docs/design](design/README.md). Collectors, usage calculations, MCP and database
schemas were not changed.

**Automated regression: 135 passed in 24.79s** using
`.venv/bin/python -m pytest -q`. Existing page tests now navigate through the
registered page files. Nine additional checks cover filter/search/selection
restoration, refresh failures and recovery, failed settings/review/analysis
writes with retained input, explicit restore/cancel, and theme palette contrast.
Failure checks inject actual exceptions into the save/read operations and verify
retry effects against isolated state or temporary databases.

**Browser: 98 page/viewport/theme combinations passed** using Chromium Headless
Shell 153.0.8010.36, Streamlit 1.63.0 and synthetic data in temporary databases.
The test process replaces collector/config operations; no real logs or user
databases are needed. HTTPS resources are blocked during verification.

- All seven direct routes at 320×850, 375×850, 768×1024, 1024×900, 1440×1000,
  1920×1080 and 812×375, in both system light and system dark mode.
- Explicit Dark/Light selection in Streamlit's native theme menu changed the
  computed app colors successfully; the menu remains open after a selection.
- One H1 per page, no document/body-content horizontal overflow (internally
  scrolling tables/charts/code are excluded), correct computed theme background,
  and no browser runtime exceptions. Screenshots were captured for every case;
  representative desktop, narrow and landscape captures were visually reviewed.
- Keyboard Tab/Shift+Tab, select ArrowDown/Escape, expander Space/Enter with
  stable trigger height, navigation-link Enter, search empty results and browser
  back/forward preserving the search value passed in both themes.
- 200% root-font scaling passed DOM reflow checks for overview, history and
  settings in both themes. This is CSS text scaling, not browser chrome zoom;
  native canvas data tables retain their own font size in this check.
- Native caption opacity was found to reduce contrast and was corrected to 1.
  DOM measurements confirmed 16px base font and 44px select inputs. Palette tests
  check text/link/status/primary-button contrast ≥4.5:1 and borders ≥3:1 on the
  configured adjacent surfaces. They do not certify every native canvas pixel.
- The single-day line charts now retain a visible point. Title inset was fixed
  after the initial capture showed overlap with native browser controls.

Reproduce with an installed Chrome/Chromium executable and Node.js (tested on 24):

```bash
BROWSER_BIN=/path/to/chrome VERIFY_OUTPUT=/tmp/asm-ui-matrix node tools/verify_ui.mjs
BROWSER_BIN=/path/to/chrome VERIFY_OUTPUT=/tmp/asm-ui-interactions VERIFY_INTERACTIONS=1 node tools/verify_ui.mjs
```

The scripts produce screenshots, JSON measurements and a server log outside the
repository, then stop their temporary server/browser. They add no runtime or npm
dependency. Captures are local QA artifacts, not a portable visual baseline.

Limitations: 320px reflow covers the effective layout width of a 1280px viewport
at 400% zoom; actual browser-menu 400% zoom was not tested. Physical mobile touch,
virtual keyboard, screen readers, Safari and Firefox remain unverified. This is
not a WCAG conformance certification. The earlier actual-log/MCP browser test
below predates this redesign and is not substituted for these checks.

`graphify update .` completed AST-only: **636 nodes, 1,476 edges, 40 communities**.
The existing dated graph backup was preserved. Semantic document extraction and
community relabeling were not run.

## Actual-use browser and MCP integration (2026-09-09)

A separate Streamlit process was launched on loopback port 18501 with actual
local logs and isolated temporary review/analysis databases. Chromium exercised
the running app; the health endpoint returned `ok`. Source logs were read only.

- Inputs: 12 Codex sessions and 27 Antigravity sessions; seven detected projects.
  All 27 Antigravity sessions remained unassigned to a project. No Claude logs
  were available in this environment. These counts are a separate sample from
  the historical 356-transcript dataset documented below.
- Browser: overview rendering, project comparison selection, instruction
  comparison, analysis request creation, session retrospective creation/editing,
  custom improvement creation, report display, recommendation adoption and
  applied-status update. Report, applied status and retrospective fields
  persisted after a browser reload. No browser `pageerror` events were observed.
- MCP: actual subprocess stdio initialization, discovery and calls to all 13
  tools, plus prompt listing/retrieval. Project statistics, instructions and
  their differences, session/event pages and validated original event reads
  returned successfully. Job creation, claim, completion, failure and retrieval
  were exercised against the same temporary database as the UI.
- End-to-end: an agent claimed the UI-created cross-project request through
  MCP, submitted a short report grounded in captured request-count evidence,
  and the UI displayed the report and saved the adopted recommendation.
- Expected rejections: cross-project event access, dates without timezone
  offsets, duplicate claims, fabricated evidence IDs, invalid claim tokens and
  repeated completion of an already completed request.
- Residual UI issue: mouse automation for the improvement-status dropdown
  reported an out-of-viewport option. Keyboard selection and saving succeeded;
  the root cause was not diagnosed. Mobile layouts were not tested.

This did not test an installed Codex MCP connector, unattended external-agent
launching or a separate external model invocation. No user's MCP configuration
or existing application databases were changed. Test drivers, private-log
captures and screenshots remain outside the repository in a temporary folder;
their paths are not a portable reproduction contract.

## Automated regression checks (2026-09-09)

```bash
.venv/bin/python -m pytest -q
graphify update .
```

Result: **126 passed in 15.53s**. The suite includes the existing dashboard
regression checks and 14 personal-review, project-analysis and MCP tests.

- SQLite persistence across store instances and UI restarts; composite session
  identities, atomic membership conflict handling, and improvement status changes.
- Repeated tool failures and file reads, input-token growth, unknown metadata,
  evidence locations, and duplicate signal handling using synthetic records.
- Cross-project usage coverage, unknown values, overlapping request intervals,
  period clipping, manual project assignments, and instruction-file comparisons.
- Instruction scope, excluded symlinks/dependency folders, original-event identity
  checks, and rejection of unsupported report evidence and stale claim tokens.
- Streamlit task creation, retrospective edits, signal capture, cross-project
  analysis requests, completed report display, and improvement adoption.
- A real stdio MCP subprocess: protocol initialization, tool discovery, statistics
  lookup, analysis creation/claim, and grounded report submission to the shared DB.

All data and databases in this automated suite are temporary and synthetic. No external model
was invoked and no user's MCP client configuration was changed. Agent analysis
requires connecting an MCP client and asking its agent to process the queued job;
queue creation alone does not start an agent.

The AST-only graph update completed with **544 nodes, 1,269 edges and 31
communities**. Markdown semantic extraction was not run. This automated run
checked UI behavior with Streamlit AppTest; subsequent actual-use browser checks
are recorded above. Documentation updates do not represent a new test run.

## Previous checks (2026-09-08)

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

## Previous runtime and browser checks (2026-09-08)

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

## Previous actual-data checks and limits (2026-09-08)

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

## 2026-09-12: Codex 전용 수집과 프로젝트 로그 분석

수집 진입점은 Codex만 사용하고 기존 Claude·AGY 경로·원본·회고는 보존한다. 프로젝트별 규칙 기반 분석, 근거·우선순위·검증 방법, 멱등 보고서 저장과 개선안 채택·적용 및 읽기 전용 MCP 도구를 추가했다.

로컬 Python 3.13 환경에서 순수 로직 테스트 73개와 compileall을 통과했다. Streamlit·MCP·graphify 설치는 DNS 제한으로 완료하지 못했으므로 전체 테스트는 GitHub Actions Python 3.12 환경에서 별도로 실행한다. 새 AppTest는 실행·저장·채택·적용·재실행·실패 재시도·빈 상태·필터를 검사하고 stdio MCP는 실제 새 도구 호출과 DB 불변·결과 범위의 미리보기 제외를 검사한다.

운영 DDNS 서버의 배포·재시작·실제 사용자 로그 실행, 실기기·스크린리더는 이번 검증에 포함하지 않는다. 정확한 CI 결과는 PR과 아래 실행 기록을 확인한다. 과거 검증 건수와 합산하지 않는다.

- GitHub Actions Python 3.12 전체 회귀 테스트: 170개 실행, pytest 종료 코드 0. 실행: https://github.com/ezcode92/agent-session-monitor/actions/runs/34680691161

- 최종 소스 재검증: Python 3.12 테스트 170개 통과, Chromium 합성 화면 98개 조합의 단일 H1·가로 넘침·런타임 예외 검사 통과. 실사용 로그가 아닌 tests/browser_app.py를 사용했다.
- graphify update . 완료: 코드 AST만 갱신, LLM 호출 없음. 임시 구현 스크립트와 생성된 egg-info는 최종 소스에서 제거했다.
- 검증 실행: https://github.com/ezcode92/agent-session-monitor/actions/runs/34680792442
