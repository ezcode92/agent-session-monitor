# Graph Report - agent-session-monitor  (2026-09-12)

## Corpus Check
- 78 files · ~72,225 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 712 nodes · 1608 edges · 42 communities (38 shown, 4 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 32 edges (avg confidence: 0.68)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `120a7763`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_core.py
- build_view_data
- ui/app.py
- verify_ui.mjs
- test_antigravity.py
- test_ui_adapter.py
- frame
- test_history_navigation.py
- ProjectStore
- test_live_completion.py
- adapter.py
- request_timeline
- filtered_sessions
- ReviewStore
- test_request_tools.py
- design/README.md
- monitor_cursor
- Validation
- What You Must Do When Invoked
- test_app_integration.py
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
- weighted_cache_ratio
- 디자인 지침 이식 기록
- 브랜드·색상·문구
- 공통 컴포넌트·상태
- 로컬 에이전트 모니터 UI 벤치마크
- 레이아웃·정보 밀도
- Agent Session Monitor 디자인 안내

## God Nodes (most connected - your core abstractions)
1. `AgentMonitor` - 37 edges
2. `frame()` - 29 edges
3. `ProjectStore` - 28 edges
4. `ProjectAnalysis` - 26 edges
5. `parse_codex()` - 24 edges
6. `ParseResult` - 22 edges
7. `ReviewStore` - 22 edges
8. `build_view_data()` - 22 edges
9. `SourceFile` - 19 edges
10. `history()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `load_config()`  [INFERRED]
  mcp_server.py → src/agent_monitor/config.py
- `main()` --calls--> `AgentMonitor`  [INFERRED]
  mcp_server.py → src/agent_monitor/service.py
- `test_default_roots_target_brain_directories()` --calls--> `default_config()`  [EXTRACTED]
  tests/test_antigravity.py → src/agent_monitor/config.py
- `test_load_config_valid_json_wrong_shape_falls_back()` --calls--> `load_config()`  [EXTRACTED]
  tests/test_core.py → src/agent_monitor/config.py
- `test_original_event_tool_checks_scope_and_returns_actual_record()` --calls--> `SourceFile`  [INFERRED]
  tests/test_project_analysis.py → src/agent_monitor/discovery.py

## Import Cycles
- None detected.

## Communities (42 total, 4 thin omitted)

### Community 0 - "test_core.py"
Cohesion: 0.05
Nodes (88): analyze(), download_data(), filter_data(), interval_for_dates(), orchestration_graph(), datetime, Canonical session graph based only on parser-provided explicit parents., report() (+80 more)

### Community 1 - "build_view_data"
Cohesion: 0.19
Nodes (15): build_view_data(), _event_timestamp(), Pure, deterministic view-model construction shared by dashboard pages., Return a UTC Timestamp, avoiding parser work for collector datetimes., _scalar_rows(), _union_seconds(), test_populated_rollup_period_and_day_split_contract(), test_view_day_split_handles_new_york_dst_fall_back() (+7 more)

### Community 2 - "ui/app.py"
Cohesion: 0.05
Nodes (78): main(), Testable Streamlit entrypoint; importing this module has no UI side effects., RuntimeError, default_config(), load_config(), normalized_timezone(), path_diagnostics(), Any (+70 more)

### Community 3 - "verify_ui.mjs"
Cohesion: 0.25
Nodes (17): browser, call(), evaluate(), exceptions, interactions(), layout(), navigate(), pause() (+9 more)

### Community 4 - "test_antigravity.py"
Cohesion: 0.47
Nodes (10): scan_sources(), step(), test_brain_mirrors_merge_stable_steps_even_when_display_changes(), test_brain_steps_produce_sessions_turns_events_and_unknown_usage(), test_brain_user_step_without_content_remains_a_turn(), test_default_roots_target_brain_directories(), test_discovery_ignores_full_and_chunk_transcripts(), test_saved_installation_roots_remain_unchanged_and_scan_same_logs() (+2 more)

### Community 5 - "test_ui_adapter.py"
Cohesion: 0.10
Nodes (13): usage_total(), _usage(), test_apptest_refresh_rerenders_visible_snapshot_value(), test_event_noise_filter_is_ui_only_and_follow_can_use_all_events(), test_event_source_and_csv_provenance(), test_event_type_noise_hides_metadata_but_keeps_tool(), test_lazy_preview_never_requires_raw_and_caps_display(), test_missing_usage_is_never_shown_as_zero() (+5 more)

### Community 6 - "frame"
Cohesion: 0.21
Nodes (20): fragment, event_is_noise(), event_rows(), frame(), get(), hierarchy_rows(), lazy_preview(), Any (+12 more)

### Community 7 - "test_history_navigation.py"
Cohesion: 0.34
Nodes (13): history_app(), parametrize, select_cell(), snapshot_fixture(), test_changed_visible_rows_clear_old_cell_selection(), test_completed_codex_graph_disables_live_control(), test_completed_codex_history_never_calls_live_service(), test_live_completion_keeps_final_events_and_stops_next_service_call() (+5 more)

### Community 8 - "ProjectStore"
Cohesion: 0.07
Nodes (30): main(), Standalone stdio MCP entrypoint; does not start or import Streamlit., create_results_server(), create_server(), MCP tools backed by exactly the same project analysis service as the UI., Return a completed report without local filesystem evidence locations., Create a read-only MCP surface for reviewing completed analysis reports., _result_view() (+22 more)

### Community 9 - "test_live_completion.py"
Cohesion: 0.40
Nodes (10): codex_rows(), make_monitor(), parametrize, test_agy_empty_user_input_survives_dashboard_and_live_merge(), test_cancelled_and_failed_codex_continue_tracking(), test_initial_complete_codex_does_not_stat(), test_legacy_poll_keeps_other_agent_with_same_id_running(), test_live_completion_stops_stat_after_returning_final_event() (+2 more)

### Community 10 - "adapter.py"
Cohesion: 0.22
Nodes (12): append_bounded(), append_unique(), monitor_view(), period_bounds(), datetime, Mapping helpers used by the Streamlit presentation layer., Keep a bounded live buffer while preserving the newest unique events., Pause uses its captured view; follow controls only presentation ordering. (+4 more)

### Community 11 - "request_timeline"
Cohesion: 0.47
Nodes (8): Keep each known request interval separate, clipped to the selected period., request_timeline(), request(), test_composite_session_filter_does_not_include_other_agents(), test_offset_times_are_converted_to_utc_and_missing_columns_are_empty(), test_request_intervals_keep_gaps_and_metadata_without_mutating_source(), test_selected_period_clips_partial_intervals_and_omits_outside_rows(), test_unknown_invalid_zero_and_reversed_intervals_are_omitted()

### Community 12 - "filtered_sessions"
Cohesion: 0.20
Nodes (12): DataFrame, filtered_requests(), filtered_sessions(), filtered_usage(), Apply every dashboard filter at the normalized usage-event level., Filter session metadata only. Model and period are usage-event filters in the…, Match canonical agent/session pairs without row-wise Python calls. Older…, _selected_session_mask() (+4 more)

### Community 13 - "ReviewStore"
Cohesion: 0.12
Nodes (24): analyze_task(), _digest(), _failed(), _get(), _object(), _preview(), Deterministic review signals from explicit tool observations and known usage., Normalize supported content blocks; unknown schemas supply no observations. (+16 more)

### Community 14 - "test_request_tools.py"
Cohesion: 0.15
Nodes (24): main(), measure(), Path, Synthetic, local-only monitor benchmark; does not read configured user logs., Measure view construction from one reused synthetic snapshot., view_benchmark(), write_log(), _order() (+16 more)

### Community 15 - "design/README.md"
Cohesion: 0.24
Nodes (4): graphify, UI design, 접근성·검증 기준, 화면 계약

### Community 16 - "monitor_cursor"
Cohesion: 0.33
Nodes (6): filter_events(), monitor_cursor(), Apply UI filters without treating an empty selected-session set as all., Return only records after the opaque cursor and the newest cursor., test_event_filter_and_cursor_respect_time_agent_model_and_generation(), test_live_generation_resets_cursor_and_tool_is_collapsed()

### Community 17 - "Validation"
Cohesion: 0.14
Nodes (14): Actual-use browser and MCP integration (2026-09-09), Automated regression checks (2026-09-09), Daily chart date-axis correction (2026-09-09), Historical benchmark evidence, Historical monitor benchmark, Historical same-snapshot view benchmark (before this UI revision), Previous actual-data checks and limits (2026-09-08), Previous checks (2026-09-08) (+6 more)

### Community 18 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 19 - "test_app_integration.py"
Cohesion: 0.08
Nodes (30): cache_resource, Streamlit presentation layer for Agent Monitor., fixture(), Synthetic browser audit fixture. No real collector, config or user databases.…, go_page(), parametrize, End-to-end Streamlit checks with representative, nonempty monitor data., Exercise the real history controls against a changing synthetic collector. (+22 more)

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
Cohesion: 0.29
Nodes (7): 보고서 형식, 시작, 에이전트 분석과 MCP 연결, 작업 흐름, 저장과 해석, 제공 도구, 호출 시점: 명시적 분석 요청이 있을 때

### Community 33 - "Agent Session Monitor"
Cohesion: 0.29
Nodes (7): Agent Session Monitor, MCP 서버와 에이전트 분석, 개인 작업 회고, 검증 현황과 제한 (2026-09-09), 실행, 외부 브라우저 점검과 ChatGPT Web, 화면

### Community 34 - "weighted_cache_ratio"
Cohesion: 0.33
Nodes (6): Series, clipped_duration_seconds(), Traverse only the service graph, at arbitrary depth and cycle-safe., subtree_keys(), weighted_cache_ratio(), test_clipped_duration_weighted_ratio_and_arbitrary_subtree()

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
- **136 isolated node(s):** `agent-session-monitor`, `root`, `profile`, `server`, `browser` (+131 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentMonitor` connect `test_core.py` to `build_view_data`, `ui/app.py`, `ProjectStore`, `test_live_completion.py`, `test_request_tools.py`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `ProjectStore` connect `ProjectStore` to `ui/app.py`, `test_app_integration.py`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `SourceFile` connect `test_core.py` to `ProjectStore`, `test_antigravity.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `AgentMonitor` (e.g. with `main()` and `ParseResult`) actually correct?**
  _`AgentMonitor` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ProjectStore` (e.g. with `main()` and `ProjectAnalysis`) actually correct?**
  _`ProjectStore` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ProjectAnalysis` (e.g. with `main()` and `SourceFile`) actually correct?**
  _`ProjectAnalysis` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `agent-session-monitor`, `root`, `profile` to the rest of the system?**
  _136 weakly-connected nodes found - possible documentation gaps or missing edges._