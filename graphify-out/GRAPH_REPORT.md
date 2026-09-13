# Graph Report - agent-session-monitor  (2026-09-12)

## Corpus Check
- 82 files · ~76,871 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 817 nodes · 1828 edges · 50 communities (42 shown, 7 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 149 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d4799ce7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_core.py
- build_view_data
- frame
- verify_ui.mjs
- ReviewStore
- test_ui_adapter.py
- test_live_completion.py
- test_history_navigation.py
- ProjectAnalysis
- AgentMonitor
- adapter.py
- request_timeline
- ui/app.py
- test_request_tools.py
- browser_app.py
- design/README.md
- create_server
- Validation
- What You Must Do When Invoked
- test_design_ui.py
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
- test_project_logs.py
- 디자인 지침 이식 기록
- 브랜드·색상·문구
- 공통 컴포넌트·상태
- 로컬 에이전트 모니터 UI 벤치마크
- 레이아웃·정보 밀도
- test_app_integration.py
- clipped_duration_seconds
- benchmark_monitor.py
- go_page
- request_detail.py
- test_project_logs_ui.py
- Codex 전용 전환과 프로젝트 작업 로그 개선 분석
- test_actual_pause_raw_and_generation_refresh_actions
- test_analysis_groups_categories_by_local_day_week_month

## God Nodes (most connected - your core abstractions)
1. `AgentMonitor` - 38 edges
2. `ProjectAnalysis` - 30 edges
3. `ProjectStore` - 30 edges
4. `frame()` - 29 edges
5. `ParseResult` - 26 edges
6. `parse_codex()` - 24 edges
7. `build_view_data()` - 24 edges
8. `ReviewStore` - 22 edges
9. `SourceFile` - 21 edges
10. `Session` - 20 edges

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

## Communities (50 total, 7 thin omitted)

### Community 0 - "test_core.py"
Cohesion: 0.08
Nodes (77): analyze(), download_data(), filter_data(), interval_for_dates(), orchestration_graph(), depth(), subtree(), datetime (+69 more)

### Community 1 - "build_view_data"
Cohesion: 0.10
Nodes (30): DataFrame, split_duration_by_day(), filtered_requests(), filtered_sessions(), filtered_usage(), Apply every dashboard filter at the normalized usage-event level., Filter session metadata only. Model and period are usage-event filters in the…, Match canonical agent/session pairs without row-wise Python calls. Older… (+22 more)

### Community 2 - "frame"
Cohesion: 0.20
Nodes (21): poll_session(), duration_label(), export_csv(), frame(), Display elapsed seconds as hours:minutes:seconds, without a 24-hour wrap., weighted_cache_ratio(), analysis(), _chart() (+13 more)

### Community 3 - "verify_ui.mjs"
Cohesion: 0.25
Nodes (17): browser, call(), evaluate(), exceptions, interactions(), layout(), navigate(), pause() (+9 more)

### Community 4 - "ReviewStore"
Cohesion: 0.13
Nodes (21): Local, user-authored retrospectives. Source transcripts are never stored here., ReviewStore, _text(), agent_analysis_page(), project_improvements(), _project_settings(), Project comparison and analysis delegated to a connected MCP agent., _report() (+13 more)

### Community 5 - "test_ui_adapter.py"
Cohesion: 0.10
Nodes (14): period_bounds(), datetime, usage_total(), _usage(), test_duration_labels_preserve_unknown_and_do_not_wrap_at_one_day(), test_event_noise_filter_is_ui_only_and_follow_can_use_all_events(), test_event_source_and_csv_provenance(), test_event_type_noise_hides_metadata_but_keeps_tool() (+6 more)

### Community 6 - "test_live_completion.py"
Cohesion: 0.30
Nodes (11): codex_rows(), make_monitor(), parametrize, test_cancelled_and_failed_codex_continue_tracking(), test_deprecated_agy_is_not_read_by_dashboard_or_live_poll(), test_initial_complete_codex_does_not_stat(), test_legacy_poll_keeps_other_agent_with_same_id_running(), test_live_completion_stops_stat_after_returning_final_event() (+3 more)

### Community 7 - "test_history_navigation.py"
Cohesion: 0.30
Nodes (13): history_app(), parametrize, select_cell(), snapshot_fixture(), test_changed_visible_rows_clear_old_cell_selection(), test_completed_codex_graph_disables_live_control(), test_completed_codex_history_never_calls_live_service(), test_live_completion_keeps_final_events_and_stops_next_service_call() (+5 more)

### Community 8 - "ProjectAnalysis"
Cohesion: 0.05
Nodes (40): cache_resource, main(), Standalone stdio MCP entrypoint; does not start or import Streamlit., create_results_server(), get_analysis_report(), MCP tools backed by exactly the same project analysis service as the UI., Return a completed report without local filesystem evidence locations., Create a read-only MCP surface for reviewing completed analysis reports. (+32 more)

### Community 9 - "AgentMonitor"
Cohesion: 0.09
Nodes (37): codex_only_config(), default_config(), load_config(), normalized_timezone(), path_diagnostics(), Any, Path, Keep legacy paths inactive without deleting settings or source files. (+29 more)

### Community 10 - "adapter.py"
Cohesion: 0.13
Nodes (29): append_bounded(), append_unique(), event_is_noise(), event_rows(), filter_events(), get(), hierarchy_rows(), lazy_preview() (+21 more)

### Community 11 - "request_timeline"
Cohesion: 0.47
Nodes (8): Keep each known request interval separate, clipped to the selected period., request_timeline(), request(), test_composite_session_filter_does_not_include_other_agents(), test_offset_times_are_converted_to_utc_and_missing_columns_are_empty(), test_request_intervals_keep_gaps_and_metadata_without_mutating_source(), test_selected_period_clips_partial_intervals_and_omits_outside_rows(), test_unknown_invalid_zero_and_reversed_intervals_are_omitted()

### Community 12 - "ui/app.py"
Cohesion: 0.08
Nodes (28): main(), Testable Streamlit entrypoint; importing this module has no UI side effects., fragment, RuntimeError, Public manual-refresh path; unlike force=True it keeps parse cache hits., refresh_sources(), _agent_status(), _dashboard_refresh() (+20 more)

### Community 13 - "test_request_tools.py"
Cohesion: 0.08
Nodes (48): analyze_task(), _digest(), _failed(), _get(), _object(), _preview(), Deterministic review signals from explicit tool observations and known usage., Normalize supported content blocks; unknown schemas supply no observations. (+40 more)

### Community 14 - "browser_app.py"
Cohesion: 0.29
Nodes (3): Read-only local log analysis for coding agents., Streamlit presentation layer for Agent Monitor., Synthetic browser audit fixture. No real collector, config or user databases.…

### Community 15 - "design/README.md"
Cohesion: 0.18
Nodes (7): graphify, UI design, 접근성·검증 기준, 화면 계약, Agent Session Monitor 디자인 안내, 우선순위와 가드레일, 읽는 순서

### Community 17 - "Validation"
Cohesion: 0.13
Nodes (15): 2026-09-12: Codex 전용 수집과 프로젝트 로그 분석, Actual-use browser and MCP integration (2026-09-09), Automated regression checks (2026-09-09), Daily chart date-axis correction (2026-09-09), Historical benchmark evidence, Historical monitor benchmark, Historical same-snapshot view benchmark (before this UI revision), Previous actual-data checks and limits (2026-09-08) (+7 more)

### Community 18 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 19 - "test_design_ui.py"
Cohesion: 0.16
Nodes (11): luminance(), parametrize, Behavioral regression checks for navigation, recovery and accessible themes., test_automatic_refresh_failure_leaves_existing_dashboard_usable(), test_failed_analysis_request_keeps_objective_for_retry(), test_page_roundtrip_preserves_filters_search_selected_session_and_pane(), test_refresh_failure_retains_metrics_and_snapshot_then_retry_replaces_them(), unavailable() (+3 more)

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

### Community 34 - "test_project_logs.py"
Cohesion: 0.26
Nodes (12): event(), pair(), parametrize, test_empty_and_bounded_analysis_report_coverage(), test_explicit_test_failure_and_read_repetition(), test_failures_aggregate_across_sessions_but_not_projects_or_agents(), test_free_text_unfinished_and_unknown_results_are_not_failures(), test_mutating_or_truncated_shell_commands_are_not_file_read_signals() (+4 more)

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
Cohesion: 0.15
Nodes (14): parametrize, End-to-end Streamlit checks with representative, nonempty monitor data., Run the real app.py entrypoint, rather than a hand-written page stub., _snapshot(), test_actual_entrypoint_renders_all_pages_with_scalar_request_values(), test_composition_chart_keeps_missing_cache_components_unknown(), test_date_line_ticks_are_unique_without_compressing_missing_days(), test_duration_labels_and_composition_chart_use_values_and_explanations() (+6 more)

### Community 42 - "clipped_duration_seconds"
Cohesion: 0.40
Nodes (5): Series, clipped_duration_seconds(), Traverse only the service graph, at arbitrary depth and cycle-safe., subtree_keys(), test_clipped_duration_weighted_ratio_and_arbitrary_subtree()

### Community 43 - "benchmark_monitor.py"
Cohesion: 0.29
Nodes (8): main(), measure(), Path, Synthetic, local-only monitor benchmark; does not read configured user logs., Measure view construction from one reused synthetic snapshot., view_benchmark(), samples(), write_log()

### Community 44 - "go_page"
Cohesion: 0.25
Nodes (6): go_page(), test_failed_improvement_creation_keeps_text_and_success_clears_it(), test_settings_failure_preserves_draft_and_retry_saves_once(), test_irrelevant_global_filters_are_disabled_and_recover_on_navigation(), test_actual_entrypoint_populated_snapshot_pages_and_scalar_history(), test_populated_app_all_pages_render_without_exceptions()

### Community 45 - "request_detail.py"
Cohesion: 0.39
Nodes (7): raw_event(), usage_label(), metrics(), Each tuple is (label, value, explanation); CSS wraps by available space., Selected-session token summary and lazy request tool-call inspection., request_tools(), session_tokens()

### Community 46 - "test_project_logs_ui.py"
Cohesion: 0.36
Nodes (5): log_app(), Actual Streamlit interaction tests for local project work-log analysis., test_empty_project_logs_report_explicit_insufficient_evidence(), test_log_analysis_failure_is_retryable_and_does_not_create_job(), test_log_analysis_run_save_adopt_apply_and_reload()

### Community 47 - "Codex 전용 전환과 프로젝트 작업 로그 개선 분석"
Cohesion: 0.40
Nodes (4): Codex 전용 전환과 프로젝트 작업 로그 개선 분석, 구현 순서와 수용 기준, 데이터와 배포, 판정과 적용 범위

## Knowledge Gaps
- **142 isolated node(s):** `agent-session-monitor`, `root`, `profile`, `server`, `browser` (+137 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 289 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentMonitor` connect `AgentMonitor` to `test_core.py`, `build_view_data`, `frame`, `test_live_completion.py`, `ProjectAnalysis`, `benchmark_monitor.py`, `ui/app.py`, `request_detail.py`, `browser_app.py`, `test_request_tools.py`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `ProjectAnalysis` connect `ProjectAnalysis` to `test_core.py`, `ReviewStore`, `test_project_logs_ui.py`, `create_server`, `test_design_ui.py`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `ProjectStore` connect `ProjectAnalysis` to `ReviewStore`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `AgentMonitor` (e.g. with `main()` and `main()`) actually correct?**
  _`AgentMonitor` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ProjectAnalysis` (e.g. with `main()` and `create_server()`) actually correct?**
  _`ProjectAnalysis` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `ProjectStore` (e.g. with `main()` and `create_results_server()`) actually correct?**
  _`ProjectStore` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ParseResult` (e.g. with `analyze()` and `download_data()`) actually correct?**
  _`ParseResult` has 14 INFERRED edges - model-reasoned connections that need verification._