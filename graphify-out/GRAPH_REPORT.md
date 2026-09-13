# Graph Report - agent-session-monitor  (2026-09-13)

## Corpus Check
- 85 files · ~77,407 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 778 nodes · 1741 edges · 46 communities (42 shown, 4 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 32 edges (avg confidence: 0.68)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8015c6a9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AgentMonitor
- build_view_data
- frame
- verify_ui.mjs
- ReviewStore
- test_ui_adapter.py
- test_live_completion.py
- test_history_navigation.py
- ProjectStore
- load_config
- adapter.py
- request_timeline
- ui/app.py
- insights.py
- load_snapshot
- design/README.md
- _filters
- Validation
- What You Must Do When Invoked
- Q: 이 프로젝트 chatgpt 앱이 tinyfish로 접속해서 점검할 수 있게 하려면 어떻게 해야해? 그리고 분석 결과를 chatgpt web이 확인할 수 있는 방법도 제공했으면 해. 현재 iptime ddns로 ezcode92.iptime.org 도메인을 지정했고, http로만 제공 가능해
- agent-session-monitor
- graphify reference: extra exports and benchmark
- graphify reference: query, path, explain
- forge-platform 에이전트 작업 지침 개선안
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- TinyFish 외부 점검과 ChatGPT Web 결과 조회
- extraction-spec.md
- 개인용 작업 회고·개선 계획
- 에이전트 분석과 MCP 연결
- Agent Session Monitor
- Q: 예정된 남은 작업 있나
- 디자인 지침 이식 기록
- 브랜드·색상·문구
- 공통 컴포넌트·상태
- 로컬 에이전트 모니터 UI 벤치마크
- 레이아웃·정보 밀도
- test_app_integration.py
- Q: 왜 로컬호스트로도 접속이 안되지
- clipped_duration_seconds
- test_request_tools.py
- _history_events
- README.md

## God Nodes (most connected - your core abstractions)
1. `AgentMonitor` - 38 edges
2. `ProjectStore` - 30 edges
3. `ProjectAnalysis` - 29 edges
4. `frame()` - 29 edges
5. `parse_codex()` - 24 edges
6. `ParseResult` - 22 edges
7. `ReviewStore` - 22 edges
8. `build_view_data()` - 22 edges
9. `go_page()` - 20 edges
10. `SourceFile` - 19 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `load_config()`  [INFERRED]
  mcp_server.py → src/agent_monitor/config.py
- `main()` --calls--> `AgentMonitor`  [INFERRED]
  mcp_server.py → src/agent_monitor/service.py
- `test_load_config_valid_json_wrong_shape_falls_back()` --calls--> `load_config()`  [EXTRACTED]
  tests/test_core.py → src/agent_monitor/config.py
- `test_codex_task_start_before_context_preserves_tool_only_request()` --calls--> `AgentMonitor`  [INFERRED]
  tests/test_request_tools.py → src/agent_monitor/service.py
- `test_analysis_groups_categories_by_local_day_week_month()` --calls--> `frame()`  [INFERRED]
  tests/test_app_integration.py → src/agent_monitor/ui/adapter.py

## Import Cycles
- None detected.

## Communities (46 total, 4 thin omitted)

### Community 0 - "AgentMonitor"
Cohesion: 0.05
Nodes (90): analyze(), download_data(), filter_data(), interval_for_dates(), orchestration_graph(), datetime, Canonical session graph based only on parser-provided explicit parents., report() (+82 more)

### Community 1 - "build_view_data"
Cohesion: 0.15
Nodes (21): filtered_requests(), filtered_sessions(), filtered_usage(), Apply every dashboard filter at the normalized usage-event level., Filter session metadata only. Model and period are usage-event filters in the…, build_view_data(), _event_timestamp(), Pure, deterministic view-model construction shared by dashboard pages. (+13 more)

### Community 2 - "frame"
Cohesion: 0.15
Nodes (28): raw_event(), duration_label(), export_csv(), frame(), Display elapsed seconds as hours:minutes:seconds, without a 24-hour wrap., usage_label(), weighted_cache_ratio(), analysis() (+20 more)

### Community 3 - "verify_ui.mjs"
Cohesion: 0.25
Nodes (17): browser, call(), evaluate(), exceptions, interactions(), layout(), navigate(), pause() (+9 more)

### Community 4 - "ReviewStore"
Cohesion: 0.14
Nodes (19): Local, user-authored retrospectives. Source transcripts are never stored here., ReviewStore, _text(), agent_analysis_page(), project_improvements(), _project_settings(), Project comparison and analysis delegated to a connected MCP agent., _report() (+11 more)

### Community 5 - "test_ui_adapter.py"
Cohesion: 0.09
Nodes (17): filter_events(), Apply UI filters without treating an empty selected-session set as all., usage_total(), _scalar_table(), _usage(), test_actual_entrypoint_populated_snapshot_pages_and_scalar_history(), test_event_filter_and_cursor_respect_time_agent_model_and_generation(), test_event_noise_filter_is_ui_only_and_follow_can_use_all_events() (+9 more)

### Community 6 - "test_live_completion.py"
Cohesion: 0.40
Nodes (10): codex_rows(), make_monitor(), parametrize, test_cancelled_and_failed_codex_continue_tracking(), test_deprecated_agy_is_not_read_by_dashboard_or_live_poll(), test_initial_complete_codex_does_not_stat(), test_legacy_poll_keeps_other_agent_with_same_id_running(), test_live_completion_stops_stat_after_returning_final_event() (+2 more)

### Community 7 - "test_history_navigation.py"
Cohesion: 0.34
Nodes (13): history_app(), parametrize, select_cell(), snapshot_fixture(), test_changed_visible_rows_clear_old_cell_selection(), test_completed_codex_graph_disables_live_control(), test_completed_codex_history_never_calls_live_service(), test_live_completion_keeps_final_events_and_stops_next_service_call() (+5 more)

### Community 8 - "ProjectStore"
Cohesion: 0.07
Nodes (32): main(), Standalone stdio MCP entrypoint; does not start or import Streamlit., create_results_server(), create_server(), MCP tools backed by exactly the same project analysis service as the UI., Return a completed report without local filesystem evidence locations., Create a read-only MCP surface for reviewing completed analysis reports., _result_view() (+24 more)

### Community 9 - "load_config"
Cohesion: 0.18
Nodes (23): codex_only_config(), default_config(), load_config(), normalized_timezone(), path_diagnostics(), Any, Path, Keep legacy paths inactive without deleting settings or source files. (+15 more)

### Community 10 - "adapter.py"
Cohesion: 0.18
Nodes (25): append_bounded(), append_unique(), event_is_noise(), event_rows(), get(), hierarchy_rows(), lazy_preview(), monitor_cursor() (+17 more)

### Community 11 - "request_timeline"
Cohesion: 0.47
Nodes (8): Keep each known request interval separate, clipped to the selected period., request_timeline(), request(), test_composite_session_filter_does_not_include_other_agents(), test_offset_times_are_converted_to_utc_and_missing_columns_are_empty(), test_request_intervals_keep_gaps_and_metadata_without_mutating_source(), test_selected_period_clips_partial_intervals_and_omits_outside_rows(), test_unknown_invalid_zero_and_reversed_intervals_are_omitted()

### Community 12 - "ui/app.py"
Cohesion: 0.14
Nodes (12): main(), Testable Streamlit entrypoint; importing this module has no UI side effects., poll_session(), render_page(), run(), _view(), Shared descriptions for dashboard table headers., navigation() (+4 more)

### Community 13 - "insights.py"
Cohesion: 0.13
Nodes (30): analyze_task(), _digest(), _failed(), _get(), _object(), _preview(), Deterministic review signals from explicit tool observations and known usage., Normalize supported content blocks; unknown schemas supply no observations. (+22 more)

### Community 14 - "load_snapshot"
Cohesion: 0.20
Nodes (11): fragment, RuntimeError, _dashboard_refresh(), Independent five-second collector refresh; no custom JS is used., _snapshot(), CoreContractError, load_snapshot(), Any (+3 more)

### Community 15 - "design/README.md"
Cohesion: 0.18
Nodes (7): graphify, UI design, 접근성·검증 기준, 화면 계약, Agent Session Monitor 디자인 안내, 우선순위와 가드레일, 읽는 순서

### Community 16 - "_filters"
Cohesion: 0.20
Nodes (10): Public manual-refresh path; unlike force=True it keeps parse cache hits., refresh_sources(), period_bounds(), datetime, _agent_status(), _filters(), Small sidebar inventory that also represents configured empty roots., test_agent_status_keeps_configured_empty_antigravity_root() (+2 more)

### Community 17 - "Validation"
Cohesion: 0.12
Nodes (16): 2026-09-12: Codex 전용 수집과 프로젝트 로그 분석, Actual-use browser and MCP integration (2026-09-09), Automated regression checks (2026-09-09), Daily chart date-axis correction (2026-09-09), Diagnostics link runtime correction (2026-09-13), Historical benchmark evidence, Historical monitor benchmark, Historical same-snapshot view benchmark (before this UI revision) (+8 more)

### Community 18 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 19 - "Q: 이 프로젝트 chatgpt 앱이 tinyfish로 접속해서 점검할 수 있게 하려면 어떻게 해야해? 그리고 분석 결과를 chatgpt web이 확인할 수 있는 방법도 제공했으면 해. 현재 iptime ddns로 ezcode92.iptime.org 도메인을 지정했고, http로만 제공 가능해"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: 이 프로젝트 chatgpt 앱이 tinyfish로 접속해서 점검할 수 있게 하려면 어떻게 해야해? 그리고 분석 결과를 chatgpt web이 확인할 수 있는 방법도 제공했으면 해. 현재 iptime ddns로 ezcode92.iptime.org 도메인을 지정했고, http로만 제공 가능해, Source Nodes

### Community 21 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 22 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 23 - "forge-platform 에이전트 작업 지침 개선안"
Cohesion: 0.05
Nodes (35): 1. 큰 조율 비용은 관측되지만 모두 불필요한 작업은 아니다, 2. 모델보다 먼저 작업 위험과 완료 조건을 맞춰야 한다, 3. 문서의 프로필 규칙과 실제 호출 사이에 틈이 있었다, 4. 직접 수행 사례는 실행 가능성을 보여주며 절감률 실험은 아니다, 5. 완료 범위·승인 근거의 전달도 작업 경로에 포함해야 한다, forge-platform 에이전트 지침 재분석 — 2026년 9월, 검증과 한계, 분석 범위와 근거 (+27 more)

### Community 24 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 25 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 26 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 29 - "TinyFish 외부 점검과 ChatGPT Web 결과 조회"
Cohesion: 0.33
Nodes (6): ChatGPT Web에서 완료 보고서 읽기, Secure MCP Tunnel로 실시간 확인, TinyFish 외부 점검과 ChatGPT Web 결과 조회, TinyFish용 합성 화면, 관련 문서, 파일로 확인

### Community 31 - "개인용 작업 회고·개선 계획"
Cohesion: 0.33
Nodes (6): 개인용 작업 회고·개선 계획, 검증 기준, 구현 경계, 이번 작업에서 확장한 범위, 이후 후보, 첫 버전

### Community 32 - "에이전트 분석과 MCP 연결"
Cohesion: 0.25
Nodes (8): 로컬 프로젝트 작업 로그 분석, 보고서 형식, 시작, 에이전트 분석과 MCP 연결, 작업 흐름, 저장과 해석, 제공 도구, 호출 시점: 명시적 분석 요청이 있을 때

### Community 33 - "Agent Session Monitor"
Cohesion: 0.25
Nodes (8): Agent Session Monitor, MCP 서버와 에이전트 분석, 개인 작업 회고, 검증 현황과 제한 (2026-09-09), 실행, 외부 브라우저 점검과 ChatGPT Web, 프로젝트 작업 로그 개선 분석, 화면

### Community 34 - "Q: 예정된 남은 작업 있나"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: 예정된 남은 작업 있나, Source Nodes

### Community 35 - "디자인 지침 이식 기록"
Cohesion: 0.40
Nodes (5): 검증 기록, 디자인 지침 이식 기록, 입력과 결정, 자료별 이관 판단, 충돌·제약 처리

### Community 36 - "브랜드·색상·문구"
Cohesion: 0.40
Nodes (4): 브랜드·색상·문구, 이후 색상·이미지 요청 처리, 토큰 원본과 대응, 확정한 방향

### Community 37 - "공통 컴포넌트·상태"
Cohesion: 0.40
Nodes (4): 공통 컴포넌트·상태, 데이터·차트·피드백, 입력과 저장, 탐색과 상태 복원

### Community 38 - "로컬 에이전트 모니터 UI 벤치마크"
Cohesion: 0.40
Nodes (5): 관찰한 공통 패턴, 권장 개선 순서, 로컬 에이전트 모니터 UI 벤치마크, 범위 판단, 제안 화면 구성

### Community 39 - "레이아웃·정보 밀도"
Cohesion: 0.50
Nodes (3): 레이아웃·정보 밀도, 반응형 기준, 순서와 간격

### Community 40 - "test_app_integration.py"
Cohesion: 0.05
Nodes (48): cache_resource, Streamlit presentation layer for Agent Monitor., fixture(), Synthetic browser audit fixture. No real collector, config or user databases.…, go_page(), parametrize, End-to-end Streamlit checks with representative, nonempty monitor data., Exercise the real history controls against a changing synthetic collector. (+40 more)

### Community 41 - "Q: 왜 로컬호스트로도 접속이 안되지"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: 왜 로컬호스트로도 접속이 안되지, Source Nodes

### Community 42 - "clipped_duration_seconds"
Cohesion: 0.25
Nodes (8): DataFrame, Series, clipped_duration_seconds(), Traverse only the service graph, at arbitrary depth and cycle-safe., Match canonical agent/session pairs without row-wise Python calls. Older…, _selected_session_mask(), subtree_keys(), test_clipped_duration_weighted_ratio_and_arbitrary_subtree()

### Community 43 - "test_request_tools.py"
Cohesion: 0.15
Nodes (24): main(), measure(), Path, Synthetic, local-only monitor benchmark; does not read configured user logs., Measure view construction from one reused synthetic snapshot., view_benchmark(), write_log(), _order() (+16 more)

### Community 44 - "_history_events"
Cohesion: 0.67
Nodes (3): _history_events(), Narrow transcript materialization to the selected composite session., test_history_log_filter_is_narrow_and_base_view_has_no_events()

### Community 47 - "README.md"
Cohesion: 0.28
Nodes (4): Codex 전용 전환과 프로젝트 작업 로그 개선 분석, 구현 순서와 수용 기준, 데이터와 배포, 판정과 적용 범위

## Knowledge Gaps
- **152 isolated node(s):** `agent-session-monitor`, `root`, `profile`, `server`, `browser` (+147 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Work-memory lessons

**Preferred sources** — corroborated by past sessions; start here.
- `README.md` (2× useful, score=1.98804112)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentMonitor` connect `AgentMonitor` to `build_view_data`, `frame`, `test_live_completion.py`, `ProjectStore`, `load_config`, `test_request_tools.py`, `ui/app.py`, `_filters`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Why does `ProjectStore` connect `ProjectStore` to `test_app_integration.py`, `ReviewStore`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `ProjectAnalysis` connect `ProjectStore` to `AgentMonitor`, `test_app_integration.py`, `ReviewStore`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `AgentMonitor` (e.g. with `main()` and `ParseResult`) actually correct?**
  _`AgentMonitor` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ProjectStore` (e.g. with `main()` and `ProjectAnalysis`) actually correct?**
  _`ProjectStore` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ProjectAnalysis` (e.g. with `main()` and `SourceFile`) actually correct?**
  _`ProjectAnalysis` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `agent-session-monitor`, `root`, `profile` to the rest of the system?**
  _152 weakly-connected nodes found - possible documentation gaps or missing edges._