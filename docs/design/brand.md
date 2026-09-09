# 브랜드·색상·문구

[디자인 안내](README.md)

## 확정한 방향

사용자는 7개 화면 전체 적용, 틸 계열의 라이트·다크 테마, 데스크톱 중심 구성을 선택했다.
기존 저장소에서는 별도 CI 색상·로고·서체 규정을 찾지 못했다. 기존 Streamlit 기본값을
승인된 CI로 간주하지 않는다. 제품 이름과 한국어 중심 문구는 유지한다.
사용자가 별도 색상값이나 이미지를 제공하지 않았으며 이미지 분석·생성은 수행하지 않았다.

중립 표면 위에 틸을 주요 행동·선택·링크에 사용한다. 안내·성공·주의·오류는 각 상태색과
명시적 문구를 함께 사용한다. 사용량 증가·감소를 작업 성공이나 생산성으로 평가하지 않는다.
외부 폰트나 CDN 없이 운영체제 글꼴과 코드용 고정폭 대체 글꼴을 사용한다.

## 토큰 원본과 대응

실행값의 원본은 [config.toml](../../.streamlit/config.toml)이다. CSS는 색상값을 복제하지 않는다.

| 의미 | Streamlit 옵션 |
|---|---|
| 페이지·입력 표면 | `backgroundColor`, `secondaryBackgroundColor` |
| 본문·링크·코드 | `textColor`, `linkColor`, `codeBackgroundColor` |
| 대표 행동·선택·기본 포커스 | `primaryColor` |
| 식별 가능한 경계 | `borderColor`, `showWidgetBorder` |
| 표 머리글 | `dataframeHeaderBackgroundColor` |
| 안내·성공·주의·오류 | `blue*`, `green*`, `orange*`, `red*` |
| 시각화 범주 | `chartCategoricalColors` |
| 글자 계층·곡률 | `font`, `headingFontSizes`, `metricValueFontSize`, `baseRadius`, `buttonRadius` |

라이트의 대표 행동색은 참고 자료의 틸을 사용한다. 다크의 대표 행동색은 흰 글자와의 대비를 위해
더 짙게 조정했다. 참고 자료의 밝은 다크 틸은 링크·차트 역할로 대응한다.
버튼 글자가 흰색인 [Streamlit 동작](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-colors-and-borders)을 고려한 결정이다.
본문·링크·버튼·상태 글자와 실제 인접 표면의 대비를 테스트에서 계산한다.

## 이후 색상·이미지 요청 처리

1. 지정값·용도·고정 조건·적용 화면을 기록한다. 색상 이름의 실제 값 해석은 따로 밝힌다.
2. 제품 목적·기존 CI·지원 테마를 확인한다. 이미지는 실제로 열어 정보 계층·여백·글자·색상의 관찰과 해석을 나눈다.
3. 지정색과 이미지 참조 범위를 의미 역할에 매핑해 한 조합으로 정한다. 미관만으로 기능·데이터 의미를 바꾸지 않는다.
4. 대비를 위해 조정한 파생색과 이유를 기록하고, 고정값끼리 충돌할 때만 필요한 결정을 확인한다.
5. 토큰 원본과 해당 영구 문서를 갱신하고 두 테마·상태·확대에서 검증한다.
6. 이미지가 구현의 참조 자산으로 필요하면 영구 위치에 출처와 함께 보존한다. 이미지 분석 요청을 배포·생성 요청으로 확대하지 않는다.
