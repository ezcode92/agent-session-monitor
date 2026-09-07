# Agent Session Monitor

Codex, Claude Code, Antigravity 세션 로그를 읽어 보여 주는 로컬 Streamlit 대시보드입니다. 원본 로그를 수정하지 않으며 DB, 외부 API, LLM 호출을 사용하지 않습니다.

Antigravity는 `~/.gemini/antigravity/brain`, `~/.gemini/antigravity-cli/brain`, `~/.gemini/antigravity-ide/brain`을 기본 수집 경로로 사용합니다. 기존 설정의 설치 폴더도 재귀 탐색하므로 계속 사용할 수 있습니다. 실제 로그는 `brain/<세션 ID>/.system_generated/logs/transcript.jsonl`이며, `transcript_full.jsonl`과 chunk 사본은 중복 수집하지 않습니다. 이 구조는 [공식 Hooks 문서](https://www.antigravity.google/docs/hooks) 및 [IDE Hooks 문서](https://antigravity.google/docs/ide/hooks)에 명시되어 있습니다.

`source_path`는 대표 원본 파일이고 `sources`는 병합된 모든 원본 파일 목록입니다. 작업 이력에서는 경로를 상세 영역에 한 번씩 표시합니다.

## 실행

Python 3.12 이상과 `uv`가 필요합니다. 테이블 셀 선택을 위해 Streamlit 1.63 이상을 사용하며 `uv sync --locked --group dev`로 검증된 의존성을 설치할 수 있습니다. Windows에서는 패키지 캐시와 Python 설치 위치를 작업 폴더 안에 두면 권한 또는 전역 캐시 잠금 문제를 피할 수 있습니다.

```powershell
$env:UV_CACHE_DIR="$PWD\.tools\uv-cache"
$env:UV_PYTHON_INSTALL_DIR="$PWD\.tools\python"
.\.tools\bin\uv.exe run streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

일반 `uv`가 PATH에 있다면 같은 환경 변수 설정 후 다음 명령을 사용할 수 있습니다.

```powershell
uv run streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

가상환경을 이미 만들었다면 다음 명령으로도 실행할 수 있습니다.

```powershell
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

`python app.py`는 `src` 패키지 import를 지원하는 엔트리포인트입니다. 일반적인 대시보드 실행은 위 Streamlit 명령을 사용합니다.

브라우저에서 `http://127.0.0.1:8501`을 엽니다.

## 화면

- 개요: 전체·입력·출력 토큰, 요청당 평균 입력·출력 토큰과 작업 시간을 표시합니다. 입력·출력·캐시 차트는 행 개수가 아닌 실제 토큰 합계를 사용합니다.
- 작업 이력: 핵심 열만 표시하며 테이블의 세션 ID를 선택하면 아래 상세가 바뀝니다. 부모 ID는 같은 에이전트의 부모 상세를 엽니다. 요청 CSV와 로그 원문 조회는 상세에서 제공합니다.
- 실시간 로그: 선택 로그를 1초마다 확인합니다. Codex 상태가 `complete` 또는 `completed`이면 추적을 중단합니다. 추적 중 완료되면 마지막 이벤트를 유지하며, 세션 재개 후에는 수동 새로고침으로 추적을 다시 시작할 수 있습니다. 일시정지는 표시만 멈추고 수집 버퍼는 유지합니다.
- 기간 분석: 에이전트·모델·출처별 사용량을 일별·주별·월별로 비교합니다. 주는 월요일, 월은 1일 기준입니다. 분석 CSV/Markdown에는 같은 집계 단위가 적용되며 직전 동일 기간 비교는 제공하지 않습니다.
- 설정: 수집 경로와 파서·설정 진단을 표시합니다. 사용하지 않는 `data_quality`·`data_status` 컬럼과 처리 과정은 제거했습니다.
- 오케스트레이션: 임의 깊이의 하위 세션과 직접·하위·전체 토큰을 표시합니다. 타임라인은 요청별 관측 구간을 나눠 요청 사이 공백을 보존합니다. Graph CSV/Markdown은 제공하지 않습니다.

작업 시간은 `시:분:초`로 표시하며 24시간 이상도 누적 시간으로 표현합니다. CSV의 원본 시간 값은 초 단위를 유지합니다. 차트 제목 아래에는 설명을, 주요 지표와 테이블 헤더에는 툴팁을 제공합니다.

실제 Codex 로그와 Antigravity CLI의 356개 transcript(요청 868건, 이벤트 70,953건)를 확인했습니다. AGY의 `created_at`, `step_index`, `USER_INPUT`을 읽어 요청과 로그를 표시합니다. 이 표본에는 토큰·모델·부모 관계 정보가 없어 추정하지 않습니다. 개별 step의 `DONE`은 세션 완료로 간주하지 않습니다. Claude 실제 샘플은 아직 확보하지 못했습니다.

토큰 또는 캐시 필드가 로그에 없으면 0으로 바꾸지 않고 `—`로 표시합니다. 지원되지 않는 Antigravity 스키마는 진단으로 드러납니다.

선택 로그는 1초 간격으로 변경 여부를 확인하지만, 변경된 큰 파일을 다시 파싱하는 동안 화면 반영에는 처리 시간이 추가될 수 있습니다.
