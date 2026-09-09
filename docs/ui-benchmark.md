# 로컬 에이전트 모니터 UI 벤치마크

> 현재 디자인 기준과 화면 계약은 [디자인 안내](design/README.md)를 따릅니다. 아래 내용은 초기 조사·제안의 배경 기록입니다.

이 메모는 외부 서비스 도입 없이 현재 Streamlit, pandas, Plotly 구성에 적용할 수 있는
화면 개선 우선순위다. 비교 대상은 공식 문서와 공식 화면 설명만 사용했다.

> 상태: 초기 개선 제안 기록입니다. 직전 기간 비교와 Graph 내보내기는 이후 사용자 요청으로 제거했습니다. 현재 동작과 검증은 [README](../README.md)와 [validation](validation.md)을 따릅니다.

## 관찰한 공통 패턴

| 제품 | 확인한 패턴 | 이 앱에 적용할 점 |
| --- | --- | --- |
| [Langfuse Sessions](https://langfuse.com/docs/observability/features/sessions) | 여러 trace를 하나의 세션 replay로 보고, 세션을 클릭해 전체 상호작용으로 내려간다. | 세션 표의 행 선택을 상세 화면의 단일 진입점으로 유지하고, 요청·도구·응답은 시간순으로 같은 상세에 둔다. |
| [Langfuse data model](https://langfuse.com/docs/observability/data-model) | observation → trace → session 계층을 분리한다. | 이벤트, 요청, 세션, 오케스트레이션 root를 섞지 않고 표와 KPI의 집계 단위를 명시한다. |
| [Phoenix Sessions](https://arize.com/docs/phoenix/tracing/llm-traces/sessions) | 세션 목록 검색, 대화형 I/O 이력, 대화별 token·latency를 함께 제공한다. | 작업 이력에는 제목 검색, 요청별 토큰·관측시간·상태와 역할별 이벤트를 함께 둔다. |
| [AgentOps Dashboard](https://docs.agentops.ai/v2/usage/dashboard-info) | session drawer와 event waterfall을 결합하고, 선택 이벤트 상세를 우측에 둔다. | 현재 Plotly timeline은 유지하되, 선택 세션에서 요청/도구/오류 이벤트를 한 lane씩 표시하고 표 행 선택으로 상세를 연다. |
| [Grafana variables](https://grafana.com/docs/grafana/latest/visualizations/dashboards/variables/) | 시간·필터 변수를 대시보드 상단의 공통 상태로 두고 모든 panel이 이를 따른다. | 기간, 시간대, agent, project, model을 공통 필터로 고정하고 KPI·차트·CSV·Markdown에 같은 필터 설명을 표시한다. |

## 권장 개선 순서

1. **공통 필터 상태를 한 줄로 요약한다.** 사이드바 선택값 바로 아래에 `최근 7일 · Asia/Seoul · Codex/Claude` 같은 상태 문구와 데이터 범위(확인된 usage 이벤트 수)를 표시한다. CSV와 Markdown 첫 줄에도 같은 값을 넣는다. Grafana처럼 하나의 선택이 모든 panel에 적용됐는지 확인하기 쉽다.

2. **개요의 KPI를 행동 가능한 링크로 만든다.** 세션·요청·총 토큰·입력/출력·작업시간·캐시 읽기 비율은 유지하되, 각 KPI 아래에 `확인됨 n/m`, `이전 동일 기간 대비`를 작게 둔다. KPI를 누르면 작업 이력의 해당 정렬/필터로 이동하는 것은 v2 후보이며, v1에서는 상위 요청 표를 바로 아래에 둔다.

3. **세션 상세를 세 열로 정돈한다.** 왼쪽은 요청 목록, 중앙은 역할별 이벤트, 오른쪽은 선택 이벤트의 짧은 미리보기와 원문 열기 버튼으로 만든다. AgentOps waterfall처럼 timeline과 이벤트 선택을 연결하되, 긴 tool 출력은 기본 2,000자와 lazy raw 조회를 유지한다.

4. **오케스트레이션 화면은 tree 표를 기준으로 둔다.** 재귀 들여쓰기 표에 root/main, task/title, source, 상태, self·descendant·subtree token, cache 비율, 기간 내 duration을 둔다. Plotly timeline은 보조 시각화로 쓰고, 관계 근거가 없으면 `부모 미확인` 그룹으로 별도 표시한다. 명시적 관계만 사용한다.

5. **차트 수를 늘리기보다 비교 축을 통일한다.** 토큰은 일/주/월 단위 선택, 작업시간은 같은 단위, 캐시는 known-pair 기반 비율만 보인다. 스택 막대에서는 비캐시 입력·캐시 읽기·캐시 생성·출력을 구분해 중복 누적을 피한다.

6. **실시간 화면을 운영 화면으로 구분한다.** 선택 세션 상세에서만 1초 polling을 사용한다. 개요의 5초 자동 갱신은 기본값이 아닌 선택 기능으로 두고, 수동 새로고침을 기본 흐름으로 유지한다. `일시정지`는 화면만 고정하고 새 이벤트 수를 보여주며, `최신 따라가기`를 끄면 현재 위치를 유지한다. 최근 200개 기본과 bounded 버퍼를 유지한다.

7. **데이터 품질을 빈 화면의 일부로 만든다.** agent별로 `발견 파일`, `읽기 가능`, `지원 transcript`, `미지원/권한 거부`를 설정 화면과 개요 보조 카드에 표시한다. 예를 들어 AGY는 파일이 없거나 CLI가 접근 거부인 경우를 `0` 사용량과 구분한다.

## 제안 화면 구성

```text
공통 필터: 기간 | 시간대 | agent | project | model | 마지막 스캔 | 데이터 품질

개요: 6 KPI → 토큰/작업시간/캐시 추이 → 상위 세션/요청
작업 이력: 검색·표 → 요청/이벤트 상세 + timeline + live monitor
기간 분석: 이전 기간 비교 → 분포/오류/coverage → CSV·Markdown
오케스트레이션: root selector → 계층 표 → lane timeline → 관계/고아 CSV
설정: 3 agent 경로 · 상태 · 시간대 · 재스캔
```

## 범위 판단

이 제안은 DB, 외부 telemetry, 별도 프런트엔드, 새 차트 컴포넌트를 요구하지 않는다.
Streamlit의 sidebar/tabs/dataframe/fragment와 Plotly Express만으로 구현할 수 있다. 사용자
필터를 URL 또는 영속 대시보드 정의로 공유하는 Grafana 기능은 단일 로컬 사용자 v1에서 제외한다.
