# 에이전트 분석과 MCP 연결

앱은 개인용 로컬 MCP 서버로도 동작한다. 에이전트는 앱이 계산한 통계를 조회하고,
프로젝트 지침과 세션 근거를 분석한 뒤 보고서와 개선 제안을 앱에 저장한다.
서버를 실행하는 데 Streamlit 화면을 띄울 필요는 없다.

## 호출 시점: 명시적 분석 요청이 있을 때

개인용 기본 운영 방침으로, 사용자가 회고·작업 분석·프로젝트 비교를 요청할 때만
이 MCP의 통계·로그를 조회하고 분석 작업을 처리하는 방식을 권장한다.
일반 코딩 대화마다 확인하거나 세션 종료 때마다 자동 분석하지 않는다.

- 연결: 클라이언트는 서버를 시작하면서 프로토콜 초기화와 도구 목록 조회를 할 수 있다. 이것만으로 분석 작업이 실행되지는 않는다.
- 조회: 통계·지침·세션 원문은 해당 도구를 실제 호출할 때 읽는다. 읽기 전용 도구라도 내용이 에이전트에 전달되므로 필요한 프로젝트와 범위만 요청한다.
- 분석: 요청 생성은 대기열에 기록할 뿐이다. 연결된 에이전트에게 처리하라고 요청해야 인수·분석·보고서 저장이 진행된다.
- 제어: 서버는 사용자의 자연어 요청 여부를 판별하지 않는다. 아래 지침을 연결한 에이전트에 적용하고, 필요하면 클라이언트의 도구 승인·허용 목록 기능을 함께 사용한다.

에이전트 지침 예시:

```text
agent-session-monitor MCP는 사용자가 회고, 작업 분석 또는 프로젝트 비교를
명시적으로 요청한 경우에만 사용한다. 일반 코딩 작업의 시작·종료 시 자동으로
조회하거나 분석 요청을 만들지 않는다. 요청 범위에 필요한 프로젝트 통계부터
확인하고, 지침과 세션 원문은 근거가 필요한 경우에만 추가로 조회한다.
```

이 문서의 권장 지침은 클라이언트 설정에 자동 설치되지 않는다.

## 시작

```bash
uv sync --locked --group dev
uv run --locked python mcp_server.py
```

두 번째 명령은 stdio MCP 서버를 시작하므로 터미널에서 HTTP 주소를 출력하지 않는다.
MCP 클라이언트가 자식 프로세스로 시작해 stdin/stdout으로 통신하도록 설정한다.

완료된 분석 보고서를 읽기만 하는 별도 범위는 다음과 같이 시작한다.

```bash
uv run --locked python mcp_server.py --scope results
```

이 범위는 `list_analysis_reports`, `get_analysis_report`만 제공한다. 완료 보고서가 참조한
근거는 함께 반환하지만 로컬 `source_path`와 `record_key`는 제거하며, 원본 로그 조회나
분석 상태 변경은 허용하지 않는다. ChatGPT Web에서는 이 stdio 명령을 OpenAI Secure MCP
Tunnel에 연결할 수 있다. HTTP 전용 DDNS 주소는 공개 MCP URL 요건을 충족하지 않는다.
구체적인 터널·수동 JSON 업로드 절차는 [외부 점검·연결 안내](remote-access.md)를 따른다.

Codex 연결 예시에서 `/path/to/agent-session-monitor`는 저장소의 절대 경로다.
앱의 `에이전트 분석 > MCP 연결 안내`에는 현재 경로가 반영된 명령이 표시된다.

```bash
codex mcp add agent-session-monitor -- uv --directory /path/to/agent-session-monitor run --locked python /path/to/agent-session-monitor/mcp_server.py
```

다른 MCP 클라이언트에서도 다음 실행 설정을 사용한다.

```json
{
  "mcpServers": {
    "agent-session-monitor": {
      "command": "uv",
      "args": ["--directory", "/path/to/agent-session-monitor", "run", "--locked", "python", "/path/to/agent-session-monitor/mcp_server.py"]
    }
  }
}
```

서버 옵션 `--config /absolute/config.json`과 `--analysis-db /absolute/analysis.sqlite3`로
수집 설정과 분석 저장소를 지정할 수 있다. 기본값은 이 저장소의 `.agent-monitor/`이다.
UI와 MCP가 같은 분석 저장소를 사용해야 요청·결과를 서로 볼 수 있다.
`AGENT_MONITOR_ANALYSIS_DB` 환경 변수도 지원한다.

## 작업 흐름

1. `에이전트 분석`에서 프로젝트 또는 여러 프로젝트를 선택한다. 프로젝트 정보가 없는 세션은 `프로젝트 연결 관리`에서 폴더에 연결한다.
2. `작업 세션`을 선택하면 회고에서 만든 작업에 속한 세션만 분석한다. 연결된 프로젝트의 지침도 제공한다.
3. 분석 기간과 목적을 정하고 `에이전트 분석 요청 만들기`를 누른다. 요청 당시 통계·지침 해시·근거 목록을 저장한다.
4. MCP로 연결한 에이전트에게 화면의 `에이전트에 전달할 요청` 내용을 전달하거나 MCP 프롬프트 `analyze_agent_work`를 사용한다.
5. 에이전트가 요청을 인수하고 통계·지침·세션 원문을 조회한 뒤 보고서를 저장한다.
6. 앱에서 `분석 결과 새로고침`으로 보고서를 확인하고 제안을 개선 항목으로 채택한다. 적용 여부는 회고·개선에서도 관리한다.

요청을 만드는 것만으로 에이전트가 자동 실행되지는 않는다. 분석은 사용 중인 에이전트
세션이 수행하며 해당 에이전트의 데이터 전송·과금 설정이 적용된다. 앱은 모델 API를
직접 호출하거나 별도 CLI 프로세스를 자동 실행하지 않는다.

## 로컬 프로젝트 작업 로그 분석

전체 범위의 `analyze_project_work_logs(project_id, start?, end?)`는 단일 프로젝트의 Codex 작업 로그를 읽기 전용으로 분석한다. 결과는 `rule_version`, `project_id`, `period`, `status`, `coverage`, `report`, `evidence_catalog`, `limitations`를 포함한다. DB 저장·외부 모델 호출·코드 수정은 없으며 시작 포함·종료 제외, 시간대 검증·프로젝트 범위 검증을 적용한다.

UI의 실행·저장 버튼은 같은 엔진의 보고서를 완료 상태로 저장하고 같은 내용의 재분석과 채택을 중복 저장하지 않는다. 단일 프로젝트 심층 요청에는 `context.log_analysis`와 근거가 추가된다. 기존 보고서·SQLite 계약은 유지한다.

`--scope results`는 계속 두 개의 보고서 조회 도구만 제공한다. 새 분석 도구나 근거의 `source_path`, `record_key`, `preview`는 노출하지 않는다. 사용자 작성 보고서 본문은 그대로 포함하므로 별도의 비밀정보 제거 기능으로 간주하지 않는다.

## 제공 도구

| 도구 | 기능 |
| --- | --- |
| `list_projects` | 프로젝트와 연결 세션, 미연결 세션 확인 |
| `analyze_project_work_logs` | 단일 프로젝트의 Codex 로그 개선 후보·우선순위·근거·검증 방법; 로컬 읽기 전용 |
| `get_project_statistics` | 프로젝트별 사용량·관측 시간·적용 범위·문제 신호; 여러 ID로 프로젝트 간 비교 |
| `get_project_instructions` | 프로젝트 지침의 원문·상대 경로·적용 폴더·SHA256·수집 진단 |
| `compare_project_instructions` | 첫 프로젝트를 기준으로 같은 상대 경로의 지침 차이와 동일 파일 확인 |
| `list_project_sessions` | 프로젝트 세션을 페이지 단위로 조회 |
| `get_session_events` | 세션 이벤트 미리보기·도구 관측값·보고서 근거 ID 조회 |
| `get_event_source` | 해당 프로젝트의 확인된 이벤트 ID로 원문 한 건 조회 |
| `create_analysis_job` | 프로젝트·프로젝트 간·선택 세션 분석 요청 생성 |
| `list_analysis_jobs` | 상태별 분석 요청 목록 |
| `get_analysis_job` | 요청 당시 통계·근거 목록과 분석 결과 |
| `claim_analysis_job` | 대기 요청 인수 및 소유 토큰 발급 |
| `complete_analysis_job` | 소유 토큰과 검증 가능한 근거를 포함한 보고서 저장 |
| `fail_analysis_job` | 수행하지 못한 이유 기록 |

시간은 시간대가 포함된 ISO 8601 형식이고 종료 시각은 제외한다. 시간 인자가 없으면 전체
기록을 사용한다. 프로젝트는 요청당 1~8개, 세션·이벤트 페이지는 최대 100개다.
로그 원문은 32,768자까지 반환하며 잘림 여부를 표시한다. 원문 조회는 임의 파일 경로를
받지 않으며, 수집된 이벤트와 원문이 일치하는지 확인한다.

지침은 루트 및 하위 폴더의 `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
`.github/copilot-instructions.md`, `.github/instructions/`, `.cursor/rules/`, `.agents/rules/`를
읽는다. 하위 지침의 적용 폴더를 별도로 표시하며 전역·사용자 지침은 포함하지 않는다.
의존성·빌드 폴더와 심볼릭 링크는 제외한다. 최대 1,000개 폴더, 64개 지침,
파일당 64KiB·전체 256KiB 제한과 미수집 사유를 표시한다.

## 보고서 형식

`claim_analysis_job`이 반환한 `context.evidence_catalog`의 ID를 사용한다.
`get_session_events`의 이벤트 근거 ID도 사용할 수 있으며 완료 시 프로젝트·기간·선택 세션
범위와 현재 이벤트에 실제로 존재하는지 확인한다.

```json
{
  "summary": "분석 요약",
  "findings": [
    {"title": "관찰한 내용", "detail": "근거와 해석을 구분한 설명", "evidence_ids": ["조회한 근거 ID"]}
  ],
  "recommendations": [
    {"title": "실천할 개선", "rationale": "이 개선을 제안하는 이유", "evidence_ids": ["조회한 근거 ID"], "project_ids": ["분석 대상 프로젝트 ID"]}
  ]
}
```

요약·설명은 최대 4,000자, 제목은 최대 200자, 발견 사항과 제안은 각각 최대 30개다.
각 항목에는 최소 하나의 유효한 근거 ID가 필요하다. 지침이 분석 도중 변경됐다면 새 분석
요청을 만들어 현재 버전으로 분석한다. 근거 ID 검증은 출처 검증이며 에이전트 해석의
정확성을 보장하는 자동 평가가 아니다.

중복 인수는 거부한다. 실패했거나 멈춘 요청은 앱에서 다시 대기시킬 수 있으며,
이전 소유 토큰은 무효화되어 늦게 도착한 결과가 새 분석을 덮어쓰지 못한다.

## 저장과 해석

수동 회고는 `.agent-monitor/reviews.sqlite3`, 프로젝트 연결·분석 요청·보고서·채택한
개선 항목은 `.agent-monitor/analysis.sqlite3`에 저장한다. 원문 로그나 지침 파일은 DB에
자동 복사하지 않는다. 분석 요청에는 통계 스냅샷과 지침 메타데이터를 저장한다.
두 DB 모두 첫 쓰기 때 생성되고 로컬 원본 로그를 변경하지 않는다.

토큰·모델·시각·도구 결과가 없으면 추정하지 않는다. 프로젝트별 수집 적용 범위를 함께
비교해야 한다. 관측 구간은 모델 지연이나 사람의 노동 시간이 아니며, 토큰·시간·완료 상태만으로
생산성이나 작업 성공을 판단하지 않는다. 지침과 로그는 분석 대상 데이터이며 실행할 명령으로
취급하지 않는다. 제안된 코드·프로젝트 지침 변경을 자동 적용하는 도구는 제공하지 않는다.

연결 형식은 [Codex 공식 MCP 문서](https://developers.openai.com/codex/mcp),
서버 구현은 [공식 MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)를 참고했다.
