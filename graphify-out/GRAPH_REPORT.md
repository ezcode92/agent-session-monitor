# Graph Report - agent-session-monitor  (2026-09-09)

## Corpus Check
- 52 files · ~42,204 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 548 nodes · 1274 edges · 31 communities (25 shown, 6 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 106 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fc84dd14`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_core.py
- build_view_data
- _filters
- test_antigravity.py
- ui/app.py
- test_ui_adapter.py
- frame
- test_history_navigation.py
- ProjectStore
- test_live_completion.py
- adapter.py
- request_timeline
- benchmark_monitor.py
- ReviewStore
- CoreContractError
- hierarchy_rows
- monitor_cursor
- Validation
- What You Must Do When Invoked
- ui/__init__.py
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

## God Nodes (most connected - your core abstractions)
1. `AgentMonitor` - 36 edges
2. `frame()` - 29 edges
3. `ProjectStore` - 25 edges
4. `ParseResult` - 24 edges
5. `ProjectAnalysis` - 24 edges
6. `parse_codex()` - 23 edges
7. `build_view_data()` - 22 edges
8. `SourceFile` - 20 edges
9. `ReviewStore` - 20 edges
10. `Session` - 18 edges

## Surprising Connections (you probably didn't know these)
- `test_analysis_groups_categories_by_local_day_week_month()` --calls--> `frame()`  [INFERRED]
  tests/test_app_integration.py → src/agent_monitor/ui/adapter.py
- `main()` --uses--> `AgentMonitor`  [INFERRED]
  benchmark_monitor.py → src/agent_monitor/service.py
- `main()` --calls--> `load_config()`  [INFERRED]
  mcp_server.py → src/agent_monitor/config.py
- `main()` --uses--> `AgentMonitor`  [INFERRED]
  mcp_server.py → src/agent_monitor/service.py
- `test_default_roots_target_brain_directories()` --calls--> `default_config()`  [EXTRACTED]
  tests/test_antigravity.py → src/agent_monitor/config.py

## Import Cycles
- None detected.

## Communities (31 total, 6 thin omitted)

### Community 0 - "test_core.py"
Cohesion: 0.05
Nodes (96): analyze(), download_data(), filter_data(), interval_for_dates(), orchestration_graph(), datetime, Canonical session graph based only on parser-provided explicit parents., report() (+88 more)

### Community 1 - "build_view_data"
Cohesion: 0.10
Nodes (27): build_view_data(), _event_timestamp(), Pure, deterministic view-model construction shared by dashboard pages., Return a UTC Timestamp, avoiding parser work for collector datetimes., _scalar_rows(), _union_seconds(), End-to-end Streamlit checks with representative, nonempty monitor data., Exercise the real history controls against a changing synthetic collector. (+19 more)

### Community 2 - "_filters"
Cohesion: 0.17
Nodes (12): fragment, Public manual-refresh path; unlike force=True it keeps parse cache hits., refresh_sources(), _agent_status(), _dashboard_refresh(), _filters(), Independent five-second collector refresh; no custom JS is used., Small sidebar inventory that also represents configured empty roots. (+4 more)

### Community 3 - "test_antigravity.py"
Cohesion: 0.33
Nodes (11): scan_sources(), Directory traversal is bounded to the slower dashboard refresh., step(), test_brain_mirrors_merge_stable_steps_even_when_display_changes(), test_brain_steps_produce_sessions_turns_events_and_unknown_usage(), test_brain_user_step_without_content_remains_a_turn(), test_default_roots_target_brain_directories(), test_discovery_ignores_full_and_chunk_transcripts() (+3 more)

### Community 4 - "ui/app.py"
Cohesion: 0.14
Nodes (26): main(), Testable Streamlit entrypoint; importing this module has no UI side effects., poll_session(), reload_config(), duration_label(), Display elapsed seconds as hours:minutes:seconds, without a 24-hour wrap., usage_label(), analysis() (+18 more)

### Community 5 - "test_ui_adapter.py"
Cohesion: 0.09
Nodes (16): filtered_requests(), filtered_sessions(), filtered_usage(), Apply every dashboard filter at the normalized usage-event level., Filter session metadata only. Model and period are usage-event filters in the…, usage_total(), _usage(), test_event_noise_filter_is_ui_only_and_follow_can_use_all_events() (+8 more)

### Community 6 - "frame"
Cohesion: 0.29
Nodes (17): event_is_noise(), event_rows(), export_csv(), frame(), get(), lazy_preview(), Any, Never fetch raw content; cap the already-normalized display preview. (+9 more)

### Community 7 - "test_history_navigation.py"
Cohesion: 0.34
Nodes (13): history_app(), parametrize, select_cell(), snapshot_fixture(), test_changed_visible_rows_clear_old_cell_selection(), test_completed_codex_graph_disables_live_control(), test_completed_codex_history_never_calls_live_service(), test_live_completion_keeps_final_events_and_stops_next_service_call() (+5 more)

### Community 8 - "ProjectStore"
Cohesion: 0.07
Nodes (27): fixture, main(), Standalone stdio MCP entrypoint; does not start or import Streamlit., create_server(), MCP tools backed by exactly the same project analysis service as the UI., event_evidence(), project_id(), project_root() (+19 more)

### Community 9 - "test_live_completion.py"
Cohesion: 0.40
Nodes (10): codex_rows(), make_monitor(), parametrize, test_agy_empty_user_input_survives_dashboard_and_live_merge(), test_cancelled_and_failed_codex_continue_tracking(), test_initial_complete_codex_does_not_stat(), test_legacy_poll_keeps_other_agent_with_same_id_running(), test_live_completion_stops_stat_after_returning_final_event() (+2 more)

### Community 10 - "adapter.py"
Cohesion: 0.13
Nodes (21): DataFrame, Series, append_bounded(), append_unique(), clipped_duration_seconds(), monitor_view(), period_bounds(), datetime (+13 more)

### Community 11 - "request_timeline"
Cohesion: 0.47
Nodes (8): Keep each known request interval separate, clipped to the selected period., request_timeline(), request(), test_composite_session_filter_does_not_include_other_agents(), test_offset_times_are_converted_to_utc_and_missing_columns_are_empty(), test_request_intervals_keep_gaps_and_metadata_without_mutating_source(), test_selected_period_clips_partial_intervals_and_omits_outside_rows(), test_unknown_invalid_zero_and_reversed_intervals_are_omitted()

### Community 12 - "benchmark_monitor.py"
Cohesion: 0.36
Nodes (7): main(), measure(), Path, Synthetic, local-only monitor benchmark; does not read configured user logs., Measure view construction from one reused synthetic snapshot., view_benchmark(), write_log()

### Community 13 - "ReviewStore"
Cohesion: 0.09
Nodes (35): analyze_task(), _digest(), _failed(), _get(), _object(), Deterministic review signals from explicit tool observations and known usage., Normalize supported content blocks; unknown schemas supply no observations., _reference() (+27 more)

### Community 14 - "CoreContractError"
Cohesion: 0.29
Nodes (7): RuntimeError, CoreContractError, load_snapshot(), Any, Optional core-service discovery. Keeps Streamlit usable during initial setup., Call the first available stable service entrypoint, else return an empty…, The application was installed without its required collector service.

### Community 15 - "hierarchy_rows"
Cohesion: 0.67
Nodes (3): hierarchy_rows(), Build a display hierarchy from the stable session parent contract., test_hierarchy_rows_marks_root_and_child_sessions()

### Community 16 - "monitor_cursor"
Cohesion: 0.33
Nodes (6): filter_events(), monitor_cursor(), Apply UI filters without treating an empty selected-session set as all., Return only records after the opaque cursor and the newest cursor., test_event_filter_and_cursor_respect_time_agent_model_and_generation(), test_live_generation_resets_cursor_and_tool_is_collapsed()

### Community 17 - "Validation"
Cohesion: 0.05
Nodes (34): 보고서 형식, 시작, 에이전트 분석과 MCP 연결, 작업 흐름, 저장과 해석, 제공 도구, 호출 시점: 명시적 분석 요청이 있을 때, 개인용 작업 회고·개선 계획 (+26 more)

### Community 18 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

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

## Knowledge Gaps
- **75 isolated node(s):** `agent-session-monitor`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)`, `Step 1 - Ensure graphify is installed` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 165 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentMonitor` connect `test_core.py` to `build_view_data`, `_filters`, `test_antigravity.py`, `ui/app.py`, `ProjectStore`, `test_live_completion.py`, `benchmark_monitor.py`, `ReviewStore`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `ProjectStore` connect `ProjectStore` to `ReviewStore`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `ProjectAnalysis` connect `ProjectStore` to `test_core.py`, `ReviewStore`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `AgentMonitor` (e.g. with `main()` and `main()`) actually correct?**
  _`AgentMonitor` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `ProjectStore` (e.g. with `main()` and `ProjectAnalysis`) actually correct?**
  _`ProjectStore` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ParseResult` (e.g. with `analyze()` and `download_data()`) actually correct?**
  _`ParseResult` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `ProjectAnalysis` (e.g. with `main()` and `create_server()`) actually correct?**
  _`ProjectAnalysis` has 6 INFERRED edges - model-reasoned connections that need verification._