# 접근성·검증 기준

[디자인 안내](README.md)

- 기본 글자는 16px, 보조 설명은 14px 기준이다. 제목 위계로 중요도를 구분하고 작은 글자로 밀도를 높이지 않는다.
- 일반 글자 대비는 4.5:1 이상, 큰 글자와 식별에 필요한 비문자 UI는 3:1 이상을 확인한다.
  버튼·링크·상태·입력 경계는 놓이는 실제 표면과 비교한다.
- 페이지 H1 하나, H2 섹션, H3 하위 제목 순서를 따른다. 사이드바 제품명은 별도 H1으로 만들지 않는다.
- Native navigation·입력·표의 키보드 동작을 유지한다. Tab/Shift+Tab, Enter/Space, 방향키, Escape로 핵심 흐름을 확인한다.
- Select·펼침·오류·비활성 전환에서 라벨·포커스·크기·화살표 간격을 확인한다. 마우스 hover에만 기능을 두지 않는다.
- 상태 변화는 native Streamlit 피드백으로 알리고, 색상만으로 성공·실패를 구분하지 않는다.
- 두 테마와 시스템 설정을 지원한다. 비필수 움직임은 동작 줄이기 설정에서 제거하고 강제 색상에서 경계·포커스를 보존한다.
- 320px reflow, 200% 글자 확대, 400% 페이지 확대, 낮은 가로 화면을 확인한다.
  표·차트·코드의 관계 보존을 위한 내부 스크롤과 일반 본문의 넘침을 구분한다.

자동 계산·DOM 측정과 화면 캡처를 함께 사용한다. Headless 브라우저 검사만으로 실기기 터치,
가상 키보드, 실제 스크린리더 적합성을 확인했다고 하지 않는다. 미검증 환경은 [검증 기록](../validation.md)에 명시한다.

기준: [WCAG 2.2](https://www.w3.org/TR/WCAG22/),
[Reflow 해설](https://www.w3.org/WAI/WCAG22/Understanding/reflow),
[Streamlit 테마 설정](https://docs.streamlit.io/develop/concepts/configuration/theming).
