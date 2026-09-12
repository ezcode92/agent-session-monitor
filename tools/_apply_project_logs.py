"""One-time, branch-only application of the reviewed Codex/project-log changes.

Removed before merge. Every replacement checks its source; no user files read.
"""
from pathlib import Path


def edit(name, before, after):
    path = Path(name)
    text = path.read_text(encoding="utf-8")
    if before not in text:
        raise RuntimeError(f"Source changed before applying {name}: {before[:90]!r}")
    path.write_text(text.replace(before, after), encoding="utf-8")


if "def codex_only_config" in Path("src/agent_monitor/config.py").read_text():
    raise SystemExit("Changes already applied; nothing to transform.")

edit('src/agent_monitor/config.py', "    claude = Path(os.environ.get('CLAUDE_CONFIG_DIR', Path.home() / '.claude'))\n    gemini = Path.home() / '.gemini'\n", '')
edit('src/agent_monitor/config.py', "            'claude': [str(claude / 'projects')],\n            'antigravity': [str(gemini / x / 'brain') for x in ('antigravity', 'antigravity-cli', 'antigravity-ide')],\n", '')
edit('src/agent_monitor/config.py', 'def load_config(', '''def codex_only_config(config: dict[str, Any]) -> dict[str, Any]:
    """Keep legacy paths inactive without deleting settings or source files."""
    result = dict(config)
    paths = config.get('paths', {})
    if not isinstance(paths, dict):
        paths = {}
    archived = config.get('deprecated_paths', {})
    archived = dict(archived) if isinstance(archived, dict) else {}
    archived.update({agent: roots for agent, roots in paths.items() if agent != 'codex'})
    result['paths'] = {'codex': list(paths.get('codex', [])) if isinstance(paths.get('codex'), list) else []}
    if archived:
        result['deprecated_paths'] = archived
    return result


def load_config(''')
edit('src/agent_monitor/config.py', '    return base\n', '    return codex_only_config(base)\n')
edit('src/agent_monitor/config.py', 'json.dumps(config, ensure_ascii=False, indent=2)', 'json.dumps(codex_only_config(config), ensure_ascii=False, indent=2)')
edit('src/agent_monitor/config.py', "for agent, roots in config.get('paths', {}).items():", "for agent, roots in codex_only_config(config)['paths'].items():")
edit('src/agent_monitor/service.py', 'from .config import load_config,', 'from .config import codex_only_config, load_config,')
edit('src/agent_monitor/service.py', 'self.config = config or load_config();', 'self.config = codex_only_config(config or load_config());')
edit('src/agent_monitor/service.py', '        self.config = config\n', '        self.config = codex_only_config(config)\n')

edit('src/agent_monitor/project_analysis.py', '    def instructions(self, project_ids):', '''    def analyze_logs(self, pid, start=None, end=None, session_keys=None):
        """Analyze one project's Codex logs locally without writes or model calls."""
        from .project_logs import analyze_project_logs
        snapshot, projects, keys, left, right = self._selection([pid], start, end, session_keys)
        keys = {key for key in keys if key[0] == "codex"}
        subset = self._subset(snapshot, keys, left, right)
        period = {"start": left.isoformat() if left else None,
                  "end_exclusive": right.isoformat() if right else None}
        result = analyze_project_logs(subset, pid, projects[0]["name"], period)
        result["coverage"]["events_excluded_missing_time"] = sum(
            (row(event).get("agent"), row(event).get("session_id")) in keys
            and row(event).get("occurred_at") is None
            for event in snapshot.get("events", [])
        ) if left or right else 0
        return result

    def save_log_analysis(self, pid, start=None, end=None, session_keys=None):
        result = self.analyze_logs(pid, start, end, session_keys)
        context = {"objective": f"프로젝트 작업 로그 개선 분석: {result['project_name']}",
                   "analysis_kind": "project_logs", "rule_version": result["rule_version"],
                   "project_ids": [pid], "session_keys": sorted(map(list, session_keys)) if session_keys is not None else None,
                   "statistics": {"period": result["period"]}, "coverage": result["coverage"],
                   "limitations": result["limitations"], "evidence_catalog": result["evidence_catalog"],
                   "analysis_status": result["status"]}
        return self.store.save_log_report(context, result["report"])

    def instructions(self, project_ids):''')
edit('src/agent_monitor/project_analysis.py', '        identity = self.store.create_job(context)', '''        if len(context["project_ids"]) == 1:
            logs = self.analyze_logs(context["project_ids"][0], start, end, session_keys)
            context["log_analysis"] = {key: logs[key] for key in ("report", "coverage", "limitations", "rule_version")}
            context["evidence_catalog"].extend(logs["evidence_catalog"])
        identity = self.store.create_job(context)''')
edit('src/agent_monitor/project_store.py', '    @staticmethod\n    def _job(row):', '''    def save_log_report(self, context, report):
        """Atomically save one deterministic local report; preserve accepted actions."""
        payload = json.dumps([context, report], ensure_ascii=False, sort_keys=True, default=str)
        identity = "logs-" + hashlib.sha256(payload.encode()).hexdigest()[:32]
        now = _now()
        with self.connection(write=True) as connection:
            connection.execute("""INSERT INTO jobs VALUES (?, 'completed', ?, ?, NULL, ?, NULL, ?, ?)
                ON CONFLICT(job_id) DO NOTHING""", (identity, _json(context),
                "local-codex-rules/v1", _json(report), now, now))
        return self.get_job(identity)

    @staticmethod
    def _job(row):''')
edit('src/agent_monitor/mcp_server.py', '{"source_path", "record_key"}', '{"source_path", "record_key", "preview"}')
edit('src/agent_monitor/mcp_server.py', '    @server.tool(annotations=read)\n    def get_project_instructions(', '''    @server.tool(annotations=read)
    def analyze_project_work_logs(project_id: str, start: str | None = None, end: str | None = None) -> dict:
        """Read-only local Codex work-log analysis for ONE project.

        Returns priorities, evidence, coverage and limitations; not a causal diagnosis.
        No external model calls or writes. ISO times need offsets; end is exclusive.
        """
        return analysis.analyze_logs(project_id, start, end)

    @server.tool(annotations=read)
    def get_project_instructions(''')

edit('src/agent_monitor/ui/agent_analysis.py', '    st.header("에이전트 분석 결과")\n    st.write(report["summary"])', '''    local = job["context"].get("analysis_kind") == "project_logs"
    st.header("프로젝트 작업 로그 개선 분석 결과" if local else "에이전트 분석 결과")
    st.write(report["summary"])
    if local:
        period = job["context"]["statistics"]["period"]
        st.caption(f"저장 당시 분석 범위: {period['start'] or '전체'} ~ {period['end_exclusive'] or '전체'} (종료 미포함) · 규칙 기반 · 추가 AI 호출 없음")
        coverage = job["context"]["coverage"]
        st.caption(f"분석한 이벤트 {coverage['events_analyzed']:,}/{coverage['events_available']:,}건 · 도구 호출 {coverage['tool_calls']:,}건 · 결과 연결 {coverage['paired_results']:,}건")
        if coverage["truncated"]:
            st.warning("분석 상한으로 최근 로그 일부만 분석했습니다. 기간을 좁혀 다시 확인하세요.")
        if job["context"]["analysis_status"] == "insufficient_evidence":
            st.info("분석 근거가 부족합니다. 프로젝트 연결·Codex 수집 경로·선택 기간을 확인하세요.")
        st.json(coverage, expanded=False)
        with st.expander("분석 한계와 판정 기준"):
            for limitation in job["context"]["limitations"]:
                st.write(limitation)
        if report["recommendations"]:
            st.dataframe([{"우선순위": item.get("priority", "P2"), "개선 제안": item["title"],
                           "근거 건수": item.get("observed_count", len(item["evidence_ids"])),
                           "검증 방법": item.get("validation", "")}
                          for item in report["recommendations"]], hide_index=True, width="stretch")''')
edit('src/agent_monitor/ui/agent_analysis.py', '            st.write(recommendation["rationale"])\n            st.json', '            st.write(recommendation["rationale"])\n            if recommendation.get("validation"):\n                st.caption("개선 후 확인: " + recommendation["validation"])\n            st.json')
edit('src/agent_monitor/ui/agent_analysis.py', '프로젝트 통계와 지침을 비교하고 연결한 에이전트의 분석을 검토합니다.', 'Codex 작업 로그에서 프로젝트별 개선안을 분석하고, 필요하면 연결한 Codex의 심층 분석을 요청합니다.')
edit('src/agent_monitor/ui/agent_analysis.py', '            st.header("에이전트에게 분석 요청")', '''            if len(selected) == 1:
                st.header("프로젝트 작업 로그 개선 분석")
                st.caption("선택한 프로젝트·기간의 Codex 로그만 로컬 규칙으로 분석합니다. 반복 실패·테스트 실패·반복 조회·입력 토큰 급증과 근거를 검토할 수 있습니다. 원본 로그와 프로젝트 코드는 변경하지 않습니다.")
                if st.button("작업 로그 분석 실행·저장", type="primary"):
                    with st.spinner("프로젝트 로그의 근거를 분석하는 중…"):
                        job = service.save_log_analysis(selected[0], state.get("start"), state.get("end"), session_keys)
                    st.session_state["selected-analysis-job"] = job["job_id"]
                    st.session_state.pop("_ui:selected-analysis-job", None)
                    saved_notice("작업 로그 분석을 저장했습니다. 같은 범위·근거의 재분석은 기존 보고서를 사용합니다.")
                    st.rerun()
            st.header("Codex에게 심층 분석 요청")''')
edit('src/agent_monitor/ui/agent_analysis.py', '            with st.expander("에이전트에 전달할 요청"):\n                st.code(service.agent_prompt(identity), language=None, wrap_lines=True)', '            if job["context"].get("analysis_kind") != "project_logs":\n                with st.expander("에이전트에 전달할 요청"):\n                    st.code(service.agent_prompt(identity), language=None, wrap_lines=True)')
edit('src/agent_monitor/ui/presentation.py', 'st.session_state[identity] = [item for item in value if item in options]', 'st.session_state[identity] = [item for item in value if item in options] if isinstance(value, (list, tuple)) else []')
edit('src/agent_monitor/ui/app.py', 'st.caption("로컬 세션 기록 · 작업 회고")', 'st.caption("Codex 전용 · 로컬 세션 기록 · 작업 회고")')
edit('src/agent_monitor/ui/app.py', '        choice=remember(st.selectbox,"기간",options=["최근 7일","오늘","최근 30일","직접 선택"],key="filter-period")', '        period_disabled = page in {"회고·개선", "설정"}\n        scope_disabled = period_disabled or page == "에이전트 분석"\n        choice=remember(st.selectbox,"기간",options=["최근 7일","오늘","최근 30일","직접 선택"],key="filter-period", disabled=period_disabled)')
edit('src/agent_monitor/ui/app.py', 'key="filter-dates") if choice==', 'key="filter-dates", disabled=period_disabled) if choice==')
edit('src/agent_monitor/ui/app.py', 'else value)\n        projects=remember', 'else value, disabled=scope_disabled)\n        projects=remember')
edit('src/agent_monitor/ui/app.py', 'key="filter-projects")', 'key="filter-projects", disabled=scope_disabled)')
edit('src/agent_monitor/ui/app.py', 'key="filter-models")', 'key="filter-models", disabled=scope_disabled)')
edit('src/agent_monitor/ui/app.py', '        refresh = st.toggle("고급:', '        if scope_disabled:\n            st.caption("이 화면은 저장한 전체 기록·설정을 표시합니다." if period_disabled else "기간만 적용합니다. 분석할 프로젝트는 본문에서 선택하세요.")\n        refresh = st.toggle("고급:')
edit('src/agent_monitor/ui/app.py', '            st.warning(f"진단 {len(diagnostics)}건: 설정에서 수집 상태와 형식 안내를 확인하세요.")', '            st.warning(f"진단 {len(diagnostics)}건: 설정에서 수집 상태와 형식 안내를 확인하세요.")\n            st.page_link(str(Path(__file__).with_name("pages") / "settings.py"), label="수집 진단 확인")')
edit('src/agent_monitor/ui/app.py', '변경한 경로와 시간대는 설정 저장을 눌렀을 때 적용됩니다.', 'Codex만 수집합니다. Claude·AGY 수집은 지원 종료되었으며 기존 원본 로그와 저장된 회고는 삭제하지 않습니다.')
edit('src/agent_monitor/ui/app.py', 'column_config={name: {"help": COLUMN_HELP[name]} for name in ("agent", "path")}', 'column_config={"agent": st.column_config.SelectboxColumn("에이전트", options=["codex"], required=True, default="codex"), "path": {"help": COLUMN_HELP["path"]}}')
edit('src/agent_monitor/ui/app.py', '                            new_paths.setdefault(str(row["agent"]), []).append(str(row["path"]))', '                            if row["agent"] != "codex":\n                                raise ValueError("Codex 수집 경로만 설정할 수 있습니다.")\n                            new_paths["codex"].append(str(row["path"]))')
edit('src/agent_monitor/ui/app.py', 'AGY는 brain/<세션 ID>/.system_generated/logs/transcript.jsonl을 읽습니다. 설치 폴더와 brain 폴더를 모두 지정할 수 있습니다.', 'Codex의 sessions·archived_sessions 아래 JSONL을 읽습니다. 비활성화된 수집기의 경로는 검사하지 않습니다.')
edit('src/agent_monitor/ui/app.py', '            _table(frame(items), width="stretch", hide_index=True, column_config={"message": {"help": "진단 원인과 수집에 미치는 영향입니다."}})', '''            data = frame(items)
            if "kind" in data:
                counts = data.groupby("kind", dropna=False).size().reset_index(name="건수")
                _table(counts, width="stretch", hide_index=True)
                kinds = st.multiselect("진단 유형", sorted(data["kind"].dropna().unique()), key=f"diagnostic-kinds:{label}")
                if kinds:
                    data = data[data["kind"].isin(kinds)]
            _table(data, width="stretch", hide_index=True, column_config={"message": {"help": "진단 원인과 수집에 미치는 영향입니다."}})''')

edit('tests/test_core.py', "== {('codex', 'same'): 1, ('claude', 'same'): 1}", "== {('codex', 'same'): 1}")
edit('tests/test_core.py', "== {('codex', 'same'): 30, ('claude', 'same'): 1}", "== {('codex', 'same'): 30}")
edit('tests/test_core.py', "    assert len(events) == 1\n    assert len(events[0].sources) == 3 and events[0].source_kind == 'antigravity'\n    assert events[0].raw_record['content'] == 'live'", "    assert events == []  # Deprecated collectors never read historical sources.\n    assert monitor.get_snapshot()['diagnostics'] == []\n    assert monitor.get_snapshot()['paths'] == {'codex': []}")
edit('tests/test_antigravity.py', "def test_default_roots_target_brain_directories", "def test_default_roots_only_enable_codex")
edit('tests/test_antigravity.py', "    assert default_config()['paths']['antigravity'] == [\n        str(tmp_path / '.gemini' / name / 'brain')\n        for name in ('antigravity', 'antigravity-cli', 'antigravity-ide')\n    ]", "    assert set(default_config()['paths']) == {'codex'}")
edit('tests/test_antigravity.py', "    assert loaded['paths']['antigravity'] == [str(root)]", "    assert 'antigravity' not in loaded['paths']\n    assert loaded['deprecated_paths']['antigravity'] == [str(root)]")
edit('tests/test_live_completion.py', 'def test_agy_empty_user_input_survives_dashboard_and_live_merge', 'def test_deprecated_agy_is_not_read_by_dashboard_or_live_poll')
edit('tests/test_live_completion.py', "    assert len(snapshot['requests']) == 1 and snapshot['requests'][0].user_preview is None", "    assert snapshot['requests'] == []")
edit('tests/test_live_completion.py', "    assert len(live['requests']) == 1 and live['requests'][0].ended_at.second == 5", "    assert live['requests'] == []\n    assert path.exists()  # Deprecation never deletes original logs.")
edit('tests/test_mcp_server.py', '        statistics = call("get_project_statistics", {"project_ids": [pid]})', '''        logs_tool = next(item for item in tools if item["name"] == "analyze_project_work_logs")
        assert logs_tool["annotations"]["readOnlyHint"]
        before = database.read_bytes()
        logs = call("analyze_project_work_logs", {"project_id": pid})
        assert logs["project_id"] == pid and logs["status"] == "insufficient_evidence"
        assert logs["report"]["recommendations"] == []
        assert database.read_bytes() == before
        statistics = call("get_project_statistics", {"project_ids": [pid]})''')
edit('tests/test_mcp_server.py', '"record_key": "7"}', '"record_key": "7", "preview": "private command must not be exported"}')
edit('tests/test_mcp_server.py', '"record_key" not in item for item', '"record_key" not in item and "preview" not in item for item')
edit('tests/browser_app.py', ', "claude": [], "antigravity": []', '')

# Documentation keeps historical evidence but supersedes the active collector contract.
p = Path('README.md')
s = p.read_text()
start, end = s.index('Codex, Claude Code'), s.index('`source_path`')
s = s[:start] + '''Codex 세션 로그를 읽고 개인 작업을 회고·분석하는 로컬 Streamlit 대시보드이자 stdio MCP 서버입니다. 프로젝트별 작업 로그에서 근거 있는 개선 후보를 즉시 분석하고 연결한 Codex의 심층 분석과 함께 실천할 개선 항목으로 관리합니다. 원본 로그·프로젝트 코드를 수정하거나 외부 LLM을 자동 호출하지 않습니다.

**2026-09-12부터 Codex 전용입니다.** Claude Code·Antigravity(AGY) 수집은 deprecated 상태로 실행하지 않습니다. 기존 설정의 Codex 이외 경로는 `deprecated_paths`로 보존하며 명시적 설정 저장 때 이관합니다. 로드만으로 파일을 쓰지 않습니다. 원본 로그·기존 회고·보고서·프로젝트 연결을 삭제하지 않으며 비활성 수집기의 missing path·usage_unavailable 진단도 생성하지 않습니다. 호환 파서는 보존하되 대시보드·MCP 수집 진입점에서는 호출하지 않습니다.

기본 경로는 `$CODEX_HOME/sessions`, `$CODEX_HOME/archived_sessions`이며 미설정 시 `~/.codex`를 사용합니다.

''' + s[end:]
s = s.replace('이전 환경에서 실제 Codex 로그와 Antigravity', '**지원 종료 전 과거 검증 기록:** 이전 환경에서 실제 Codex 로그와 Antigravity')
s = s.replace('지원되지 않는 Antigravity 스키마는 진단으로 드러납니다.', 'Codex의 경로·JSON 형식 문제는 설정의 유형별 진단에서 확인합니다.')
s = s.replace('## MCP 서버와 에이전트 분석', '''## 프로젝트 작업 로그 개선 분석

`에이전트 분석 → 프로젝트 선택 → 작업 로그 분석 실행·저장`에서 선택한 프로젝트·기간의 **Codex 로그만** 로컬 규칙으로 분석합니다. 작업 세션을 선택하면 연결된 세션만 사용하며 기간 종료는 제외합니다. 추가 모델 API 비용이나 무인 실행은 없습니다.

동일 입력 반복 실패, 명시적 테스트 명령 실패, 반복 조회, 같은 세션·모델 입력 급증과 긴 관측 요청 구간을 검토 후보로 제시합니다. 각 항목은 우선순위·세션/이벤트 근거·실천 제안·검증 방법을 포함합니다. 보고서를 저장하고 `실천할 개선 항목으로 채택`한 뒤 회고·개선에서 적용 상태를 관리할 수 있습니다. 동일 내용 재분석은 중복 저장하지 않습니다.

최근 이벤트 10,000건·사용량 10,000건·요청 2,000건, 후보 30개·항목당 근거 20개로 제한하며 적용 범위·잘림·근거 부족을 표시합니다. `unfinished`를 실패로, 큰 토큰이나 긴 시간을 낭비·타임아웃·생산성으로 단정하지 않습니다. JSON에는 근거 미리보기가 포함되므로 외부 공유 전에 민감 정보를 확인하세요. 로그는 실행할 명령이 아닌 신뢰되지 않은 분석 데이터입니다.

심층 해석은 기존 `에이전트 분석 요청 만들기`로 요청합니다. 단일 프로젝트 요청에는 로컬 로그 분석 결과·근거가 함께 제공되고 실제 심층 분석은 연결한 Codex가 수행합니다. 연결한 클라이언트의 데이터 전송·과금 설정이 적용됩니다.

계획과 수용 기준은 [Codex 전용 전환과 프로젝트 로그 분석](docs/codex-project-log-plan.md), 실제 실행 결과는 [검증 기록](docs/validation.md)을 참고하세요.

## MCP 서버와 에이전트 분석''')
p.write_text(s, encoding='utf-8')
edit('docs/mcp.md', '## 제공 도구', '''## 로컬 프로젝트 작업 로그 분석

전체 범위의 `analyze_project_work_logs(project_id, start?, end?)`는 단일 프로젝트의 Codex 작업 로그를 읽기 전용으로 분석한다. 결과는 `rule_version`, `project_id`, `period`, `status`, `coverage`, `report`, `evidence_catalog`, `limitations`를 포함한다. DB 저장·외부 모델 호출·코드 수정은 없으며 시작 포함·종료 제외, 시간대 검증·프로젝트 범위 검증을 적용한다.

UI의 실행·저장 버튼은 같은 엔진의 보고서를 완료 상태로 저장하고 같은 내용의 재분석과 채택을 중복 저장하지 않는다. 단일 프로젝트 심층 요청에는 `context.log_analysis`와 근거가 추가된다. 기존 보고서·SQLite 계약은 유지한다.

`--scope results`는 계속 두 개의 보고서 조회 도구만 제공한다. 새 분석 도구나 근거의 `source_path`, `record_key`, `preview`는 노출하지 않는다. 사용자 작성 보고서 본문은 그대로 포함하므로 별도의 비밀정보 제거 기능으로 간주하지 않는다.

## 제공 도구''')
edit('docs/mcp.md', '| `get_project_statistics`', '| `analyze_project_work_logs` | 단일 프로젝트의 Codex 로그 개선 후보·우선순위·근거·검증 방법; 로컬 읽기 전용 |\n| `get_project_statistics`')
edit('docs/design/pages.md', '범위·대상·통계 → 요청 작성', '범위·대상·통계 → 프로젝트 로그 분석·저장 → 심층 분석 요청 작성')
edit('docs/design/pages.md', '새 분석 기능·필터 URL 공유', '필터 URL 공유')
with Path('docs/design/pages.md').open('a', encoding='utf-8') as f:
    f.write('\n2026-09-12 요청 확장: 수집은 Codex 전용, 회고·설정의 공통 필터는 비활성화한다. 프로젝트 로그 분석은 근거·우선순위·검증 방법·제한을 표시하며 명시적 버튼으로만 저장한다. 기존 원본·회고는 삭제하지 않는다.\n')
with Path('docs/validation.md').open('a', encoding='utf-8') as f:
    f.write('''
## 2026-09-12: Codex 전용 수집과 프로젝트 로그 분석

수집 진입점은 Codex만 사용하고 기존 Claude·AGY 경로·원본·회고는 보존한다. 프로젝트별 규칙 기반 분석, 근거·우선순위·검증 방법, 멱등 보고서 저장과 개선안 채택·적용 및 읽기 전용 MCP 도구를 추가했다.

로컬 Python 3.13 환경에서 순수 로직 테스트 73개와 compileall을 통과했다. Streamlit·MCP·graphify 설치는 DNS 제한으로 완료하지 못했으므로 전체 테스트는 GitHub Actions Python 3.12 환경에서 별도로 실행한다. 새 AppTest는 실행·저장·채택·적용·재실행·실패 재시도·빈 상태·필터를 검사하고 stdio MCP는 실제 새 도구 호출과 DB 불변·결과 범위의 미리보기 제외를 검사한다.

운영 DDNS 서버의 배포·재시작·실제 사용자 로그 실행, 실기기·스크린리더는 이번 검증에 포함하지 않는다. 정확한 CI 결과는 PR과 아래 실행 기록을 확인한다. 과거 검증 건수와 합산하지 않는다.
''')
print('Applied reviewed source, UI, test and documentation changes.')
