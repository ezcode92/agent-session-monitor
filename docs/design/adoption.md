# 디자인 지침 이식 기록

[디자인 안내](README.md)

## 입력과 결정

- 대상: Agent Session Monitor. 참고 자료: `/Users/apple/test-lab/UI-DESIGN-SETUP`, 버전 5.0, 2026-09-08.
- 사용자의 최초 경로는 `test-labs`였으나 실제 자료를 `test-lab`에서 확인했다.
- 확정 요구: 지침과 7개 화면 전체 적용, 틸 라이트·다크, 데스크톱 중심과 좁은 화면 대응.
- 기존 근거: README의 제품·데이터 계약, UI 벤치마크의 배경 제안, Streamlit 설정과 기존 화면·회귀 테스트.
- 확인된 고정 CI는 없었다. 이름·한국어 문구는 유지하며, 레이아웃·밀도·상태는 새 기준으로 검토했다.
- 별도 지정색·참고 이미지는 없었다. 새 로고·이미지·아이콘·폰트 자산을 생성하거나 이식하지 않았다.

## 자료별 이관 판단

| 자료 | 영구 반영 또는 생략 이유 |
|---|---|
| README, DESIGN_SYSTEM, UI_SPECIFICATION, DESIGN_MIGRATION_PROMPT | 이 안내·화면 계약·이식 기록으로 통합. 외부 폴더를 다시 읽을 필요 없음 |
| guidelines/brand.md | 브랜드 근거·지정색·이미지 분석 절차를 brand.md에 통합 |
| guidelines/layout.md, mobile-toss.md | layout.md에 정보 위계·간격 소유·데스크톱 폭·모바일 적용 근거 통합 |
| guidelines/components.md, contracts/actions.md | components.md에 native 컴포넌트·상태·저장·복원 기준 통합 |
| guidelines/accessibility.md | accessibility.md에 대비·키보드·확대·검증 범위 통합 |
| guidelines/guardrails.md | 안내와 영역별 지침에 분산 통합 |
| guidelines/icons.md | components.md에 기존 아이콘 우선·향후 라이선스 보존 기준만 반영 |
| contracts/shells.md, pages-base.md, pages-workspace.md | 제품에 해당하는 application shell 및 P02/P03/P05/P06/P07/P11/P15 개념만 pages.md에 적용 |
| contracts/pages-commerce.md, pages-erp.md, pages-cms.md | 상거래·ERP·CMS 기능은 적용 대상 아님 |
| assets/tokens.css | 색·글자·테두리는 Streamlit 설정, 간격·배치는 공통 CSS에 역할별 대응 |
| assets/reference.css | 배치 원칙만 적용. 예시 DOM용 스타일은 복사하지 않음 |
| DESIGN_SYSTEM.html, UI_SPECIFICATION.html, assets의 모든 JS | 데모·가짜 데이터·예시 탐색·브라우저 저장 코드는 이식 불필요 |
| resources/icons/lucide의 SVG·LICENSE·manifest·README | SVG·생성 결과를 사용하지 않으므로 자산 이식 불필요 |
| tools/build-reference.py, tools/check-reference.py, tests/verify.mjs | 참고 묶음 전용 검사이므로 이식하지 않음. 제품의 자체 회귀·브라우저 검사로 대체 |

원본은 프로젝트 외부의 참고 폴더이므로 삭제하지 않는다. 임시 자료 폴더를 프로젝트에 복사하지 않았으며,
삭제·정리 단계의 대상도 없다. 위 경로는 출처 기록이며 실행·문서 탐색의 의존성이 아니다.

## 충돌·제약 처리

- 기본 자료의 41종 페이지·TypeScript Action 형태·HTML 컴포넌트는 제품 API 요구가 아니다.
- native Streamlit의 흰 버튼 글자에 맞춰 다크 primary를 조정했다. 테마를 Python에서 강제로 변경하지 않는다.
- URL은 페이지 위치를 복원한다. 필터·검색·선택은 세션 범위로 복원하고 URL 공유는 확대 도입하지 않는다.
- 실제 입력·펼침은 native Streamlit 컴포넌트를 사용한다. 예시 HTML의 native select 도형을 별도로 복제하지 않는다.
- 기존 `clear_on_submit`으로 실패 시에도 지워지던 신규 개선 입력은 저장 성공 시에만 초기화한다.
- 데이터 저장소·권한·원문 조회·집계 규칙은 유지한다. 새 DB 마이그레이션이나 런타임 의존성은 없다.

## 검증 기록

변경 전 전체 회귀 테스트는 126개 통과했다. 적용 후 실행 결과와 브라우저·실기기 검증의 구분은
[검증 현황](../validation.md)에 기록한다. 문서·코드 적용과 실제 브라우저 검증을 별개로 보고한다.
