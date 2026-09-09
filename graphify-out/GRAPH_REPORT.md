# Graph Report - agent-session-monitor  (2026-09-09)

## Corpus Check
- 71 files · ~48,701 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 638 nodes · 1478 edges · 40 communities (34 shown, 6 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 116 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ca5f1ba7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_core.py
- build_view_data
- ui/app.py
- verify_ui.mjs
- history
- test_ui_adapter.py
- adapter.py
- test_history_navigation.py
- ProjectAnalysis
- AgentMonitor
- _live_monitor
- request_timeline
- test_live_completion.py
- ReviewStore
- benchmark_monitor.py
- design/README.md
- monitor_cursor
- Validation
- What You Must Do When Invoked
- test_app_integration.py
- agent-session-monitor
- graphify reference: extra exports and benchmark
- graphify reference: query, path, explain
- Q: 이 프로젝트 분석해서 전반적인 에이전트 세션 이력 모니터링 및 분석 후 작업 개선점을 파악하는 툴로 만드는거 어때. 이 프로젝트의 범위를 어디까지 가져갈까
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- AGENTS.md
- extraction-spec.md
- 개인용 작업 회고·개선 계획
- 에이전트 분석과 MCP 연결
- Agent Session Monitor
- 디자인 지침 이식 기록
- 브랜드·색상·문구
- 공통 컴포넌트·상태
- 로컬 에이전트 모니터 UI 벤치마크
- 레이아웃·정보 밀도
- Agent Session Monitor 디자인 안내

## God Nodes (most connected - your core abstractions)
1. `AgentMonitor` - 36 edges
2. `frame()` - 29 edges
3. `ProjectAnalysis` - 26 edges
4. `ProjectStore` - 25 edges
5. `ParseResult` - 24 edges
6. `parse_codex()` - 23 edges
7. `ReviewStore` - 22 edges
8. `build_view_data()` - 22 edges
9. `SourceFile` - 20 edges
10. `Session` - 18 edges

## Surprising Connections (you probably didn't know these)
- `test_monitor_logs_merge_mirrored_sources_and_filter_to_selected_session()` --uses--> `AgentMonitor`  [INFERRED]
  tests/test_core.py → src/agent_monitor/service.py
- `test_monitor_reparses_replaced_or_growing_jsonl_and_exposes_recent_events()` --uses--> `AgentMonitor`  [INFERRED]
  tests/test_core.py → src/agent_monitor/service.py
- `test_poll_session_generation_changes_only_when_selected_file_changes()` --uses--> `AgentMonitor`  [INFERRED]
  tests/test_core.py → src/agent_monitor/service.py
- `test_snapshot_timezone_is_normalized_and_invalid_value_is_diagnostic()` --uses--> `AgentMonitor`  [INFERRED]
  tests/test_core.py → src/agent_monitor/service.py
- `main()` --uses--> `AgentMonitor`  [INFERRED]
  benchmark_monitor.py → src/agent_monitor/service.py

## Import Cycles
- None detected.

## Communities (40 total, 6 thin omitted)

### Community 0 - "test_core.py"
Cohesion: 0.08
Nodes (72): analyze(), download_data(), filter_data(), interval_for_dates(), orchestration_graph(), datetime, Canonical session graph based only on parser-provided explicit parents., report() (+64 more)

### Community 1 - "build_view_data"
Cohesion: 0.12
Nodes (26): DataFrame, Series, filtered_requests(), filtered_sessions(), filtered_usage(), Apply every dashboard filter at the normalized usage-event level., Filter session metadata only. Model and period are usage-event filters in the…, Match canonical agent/session pairs without row-wise Python calls. Older… (+18 more)

### Community 2 - "ui/app.py"
Cohesion: 0.10
Nodes (25): main(), Testable Streamlit entrypoint; importing this module has no UI side effects., RuntimeError, normalized_timezone(), _agent_status(), _dashboard_refresh(), _filters(), Small sidebar inventory that also represents configured empty roots. (+17 more)

### Community 3 - "verify_ui.mjs"
Cohesion: 0.25
Nodes (17): browser, call(), evaluate(), exceptions, interactions(), layout(), navigate(), pause() (+9 more)

### Community 4 - "history"
Cohesion: 0.17
Nodes (23): duration_label(), export_csv(), Display elapsed seconds as hours:minutes:seconds, without a 24-hour wrap., analysis(), _chart(), _duration_axis(), _duration_line(), _duration_table() (+15 more)

### Community 5 - "test_ui_adapter.py"
Cohesion: 0.09
Nodes (17): period_bounds(), datetime, usage_label(), usage_total(), _scalar_table(), test_duration_labels_preserve_unknown_and_do_not_wrap_at_one_day(), test_event_noise_filter_is_ui_only_and_follow_can_use_all_events(), test_event_source_and_csv_provenance() (+9 more)

### Community 6 - "adapter.py"
Cohesion: 0.18
Nodes (25): append_unique(), clipped_duration_seconds(), event_is_noise(), event_rows(), frame(), get(), hierarchy_rows(), lazy_preview() (+17 more)

### Community 7 - "test_history_navigation.py"
Cohesion: 0.34
Nodes (13): history_app(), parametrize, select_cell(), snapshot_fixture(), test_changed_visible_rows_clear_old_cell_selection(), test_completed_codex_graph_disables_live_control(), test_completed_codex_history_never_calls_live_service(), test_live_completion_keeps_final_events_and_stops_next_service_call() (+5 more)

### Community 8 - "ProjectAnalysis"
Cohesion: 0.08
Nodes (25): main(), Standalone stdio MCP entrypoint; does not start or import Streamlit., create_server(), MCP tools backed by exactly the same project analysis service as the UI., event_evidence(), project_id(), project_root(), ProjectAnalysis (+17 more)

### Community 9 - "AgentMonitor"
Cohesion: 0.08
Nodes (38): default_config(), load_config(), path_diagnostics(), Any, Path, Validate configured roots without making scan failure fatal., save_config(), scan_sources() (+30 more)

### Community 10 - "_live_monitor"
Cohesion: 0.25
Nodes (9): fragment, append_bounded(), monitor_view(), Keep a bounded live buffer while preserving the newest unique events., Pause uses its captured view; follow controls only presentation ordering., recent_records(), _live_monitor(), test_monitor_is_bounded_and_pause_view_is_frozen_with_follow_order() (+1 more)

### Community 11 - "request_timeline"
Cohesion: 0.47
Nodes (8): Keep each known request interval separate, clipped to the selected period., request_timeline(), request(), test_composite_session_filter_does_not_include_other_agents(), test_offset_times_are_converted_to_utc_and_missing_columns_are_empty(), test_request_intervals_keep_gaps_and_metadata_without_mutating_source(), test_selected_period_clips_partial_intervals_and_omits_outside_rows(), test_unknown_invalid_zero_and_reversed_intervals_are_omitted()

### Community 12 - "test_live_completion.py"
Cohesion: 0.40
Nodes (10): codex_rows(), make_monitor(), parametrize, test_agy_empty_user_input_survives_dashboard_and_live_merge(), test_cancelled_and_failed_codex_continue_tracking(), test_initial_complete_codex_does_not_stat(), test_legacy_poll_keeps_other_agent_with_same_id_running(), test_live_completion_stops_stat_after_returning_final_event() (+2 more)

### Community 13 - "ReviewStore"
Cohesion: 0.09
Nodes (36): analyze_task(), _digest(), _failed(), _get(), _object(), Deterministic review signals from explicit tool observations and known usage., Normalize supported content blocks; unknown schemas supply no observations., _reference() (+28 more)

### Community 14 - "benchmark_monitor.py"
Cohesion: 0.36
Nodes (7): main(), measure(), Path, Synthetic, local-only monitor benchmark; does not read configured user logs., Measure view construction from one reused synthetic snapshot., view_benchmark(), write_log()

### Community 16 - "monitor_cursor"
Cohesion: 0.33
Nodes (6): filter_events(), monitor_cursor(), Apply UI filters without treating an empty selected-session set as all., Return only records after the opaque cursor and the newest cursor., test_event_filter_and_cursor_respect_time_agent_model_and_generation(), test_live_generation_resets_cursor_and_tool_is_collapsed()

### Community 17 - "Validation"
Cohesion: 0.18
Nodes (11): Actual-use browser and MCP integration (2026-09-09), Automated regression checks (2026-09-09), Historical benchmark evidence, Historical monitor benchmark, Historical same-snapshot view benchmark (before this UI revision), Previous actual-data checks and limits (2026-09-08), Previous checks (2026-09-08), Previous runtime and browser checks (2026-09-08) (+3 more)

### Community 18 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 19 - "test_app_integration.py"
Cohesion: 0.07
Nodes (32): cache_resource, Streamlit presentation layer for Agent Monitor., fixture(), Synthetic browser fixture. No real collector, config or user databases. Run…, go_page(), parametrize, End-to-end Streamlit checks with representative, nonempty monitor data., Exercise the real history controls against a changing synthetic collector. (+24 more)

### Community 21 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 22 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 23 - "Q: 이 프로젝트 분석해서 전반적인 에이전트 세션 이력 모니터링 및 분석 후 작업 개선점을 파악하는 툴로 만드는거 어때. 이 프로젝트의 범위를 어디까지 가져갈까"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: 이 프로젝트 분석해서 전반적인 에이전트 세션 이력 모니터링 및 분석 후 작업 개선점을 파악하는 툴로 만드는거 어때. 이 프로젝트의 범위를 어디까지 가져갈까, Source Nodes

### Community 24 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 25 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 26 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 31 - "개인용 작업 회고·개선 계획"
Cohesion: 0.25
Nodes (6): 개인용 작업 회고·개선 계획, 검증 기준, 구현 경계, 이번 작업에서 확장한 범위, 이후 후보, 첫 버전

### Community 32 - "에이전트 분석과 MCP 연결"
Cohesion: 0.29
Nodes (7): 보고서 형식, 시작, 에이전트 분석과 MCP 연결, 작업 흐름, 저장과 해석, 제공 도구, 호출 시점: 명시적 분석 요청이 있을 때

### Community 33 - "Agent Session Monitor"
Cohesion: 0.33
Nodes (6): Agent Session Monitor, MCP 서버와 에이전트 분석, 개인 작업 회고, 검증 현황과 제한 (2026-09-09), 실행, 화면

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

### Community 40 - "Agent Session Monitor 디자인 안내"
Cohesion: 0.67
Nodes (3): Agent Session Monitor 디자인 안내, 우선순위와 가드레일, 읽는 순서

## Knowledge Gaps
- **100 isolated node(s):** `agent-session-monitor`, `root`, `profile`, `server`, `browser` (+95 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 198 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentMonitor` connect `AgentMonitor` to `test_core.py`, `build_view_data`, `ProjectAnalysis`, `test_live_completion.py`, `ReviewStore`, `benchmark_monitor.py`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `ProjectAnalysis` connect `ProjectAnalysis` to `test_core.py`, `test_app_integration.py`, `ReviewStore`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `ProjectStore` connect `ProjectAnalysis` to `test_app_integration.py`, `ReviewStore`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `AgentMonitor` (e.g. with `main()` and `main()`) actually correct?**
  _`AgentMonitor` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ProjectAnalysis` (e.g. with `main()` and `create_server()`) actually correct?**
  _`ProjectAnalysis` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `ProjectStore` (e.g. with `main()` and `ProjectAnalysis`) actually correct?**
  _`ProjectStore` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ParseResult` (e.g. with `analyze()` and `download_data()`) actually correct?**
  _`ParseResult` has 14 INFERRED edges - model-reasoned connections that need verification._