# Agent Session Monitor

Codex, Claude Code, Antigravity 세션 로그를 읽어 보여 주는 로컬 Streamlit 대시보드입니다. 원본 로그를 수정하지 않으며 DB, 외부 API, LLM 호출을 사용하지 않습니다.

Antigravity는 `.gemini/antigravity`, `.gemini/antigravity-cli`, `.gemini/antigravity-ide`를 하나의 에이전트로 수집합니다. 표와 상세 화면, CSV에는 `source_label`, `source_kind`, `source_path`를 표시해 실제 유입 경로를 확인할 수 있습니다.

## 실행

Python 3.12 이상과 `uv`가 필요합니다. Windows에서는 패키지 캐시와 Python 설치 위치를 작업 폴더 안에 두면 권한 또는 전역 캐시 잠금 문제를 피할 수 있습니다.

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

- 개요: 선택 기간의 세션, 요청, 토큰과 시간별 사용량을 표시합니다.
- 작업 이력: 세션별 출처·경로·데이터 품질을 보며 선택 세션의 요청을 CSV로 내려받을 수 있습니다. 실시간 로그는 1초마다 확인하고 기본 최근 200건을 보여 줍니다. 일시정지 중에도 수집 버퍼는 계속 갱신되므로 재개 시 누락 없이 표시됩니다.
- 기간 분석: 에이전트·모델·프로젝트·출처별 토큰과 작업 시간 통계를 CSV/Markdown으로 내보냅니다.
- 설정: 실제 수집 경로와 파서 진단을 표시합니다.
- 오케스트레이션: 루트와 임의 깊이의 하위 세션을 탐색하고, 직접·하위·전체 토큰, 캐시 비율, 구간 합집합 시간을 표시합니다. 타임라인과 드릴다운, CSV·Markdown 내보내기를 제공합니다.

현재 실제 Codex 로그로 동작을 검증했습니다. Claude와 Antigravity 실제 로그 형식은 이 환경에서 사용할 수 없어 스키마 검증이 제한됩니다.

토큰 또는 캐시 필드가 로그에 없으면 0으로 바꾸지 않고 `—`로 표시합니다. 지원되지 않는 Antigravity 스키마는 진단으로 드러납니다.

선택 로그는 1초 간격으로 변경 여부를 확인하지만, 변경된 큰 파일을 다시 파싱하는 동안 화면 반영에는 처리 시간이 추가될 수 있습니다.
