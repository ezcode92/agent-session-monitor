# forge-platform 에이전트 지침 재분석 — 2026년 9월

현재 지침의 간소화 방향은 유지하는 것이 타당하다. 9월 기록에서 큰 조율 비용은 확인되지만, 당시에는 3단계 위임·low Worker 조회가 지침과 사용자 지시로 요구됐다. 과거 실행 전체를 현재의 Main 직접 수행 원칙 위반으로 판정해서는 안 된다. 추가 개선의 우선순위는 **적용 지침의 버전·시점 확인, 실제 하위 실행 설정 검증, 완료·승인 문맥 전달, 조건이 명확한 검증 규칙**이다.

바로 검토할 수 있는 [범용 작업 지침 제안문](general-agent-work-guidelines.md)과 [forge-platform 전용 개선안](forge-platform-agent-policy-improvements.md)을 별도로 작성했다. 전용안에는 문구 교체·생성 원본·검증기 개선과 수용 조건을 포함한다. 이번 산출물은 제안이며 forge-platform 또는 개인 Codex 지침에는 적용하지 않았다.

## 분석 범위와 근거

세션은 앞선 MCP 분석과 동일한 **2026-09-01 00:00:00부터 09-10 17:18:57.112004 직전까지, Asia/Seoul**로 고정했다. 이번 분석 세션과 그 자동 승인 검토는 제외했다. 9월 전체가 종료된 자료는 아니다. Downloads나 8월 세션을 추가하지 않았다.

- 전체 161개 로컬 Codex 세션에서 같은 저장소 URL에 연결된 forge-platform의 Windows·Mac 경로 3개, **124개 세션**을 재분석했다. 이 중 실제 관측 모델로 구분한 자동 승인 검토 세션은 48개다.
- 프로젝트 MCP의 기존 이벤트·정규화 사용량을 사용하고, 대표 원문 20개를 실제 stdio MCP `get_event_source`로 다시 조회했다. 지침 적용 시점과 모델 설정은 원본 JSONL의 지침 메시지·사용자 발언·`turn_context`·도구 결과로 확인했다.
- 지침·설정 경로 9개의 Git 이력에서 **9월 커밋 26개**, 진입 기준을 위한 8월 31일 커밋 3개를 확인했다. 8월 자료는 정책 기준선에만 사용했으며 세션 성과 집계에는 포함하지 않았다.
- GitHub 커넥터로 원격 최근 커밋과 주요 정책 커밋을 조회했다. **09-10 18:19:02 KST**, 원격 `main`과 로컬 기준 SHA `8dedb4fe9dbddc8a9727ed90eeefbcb0b4f2186e`의 비교 결과는 `identical`, ahead/behind 모두 0이었다. [원격 기준 커밋](https://github.com/ezcode92/forge-platform/commit/8dedb4fe9dbddc8a9727ed90eeefbcb0b4f2186e)
- 18:23:53 KST 로컬 snapshot에서 아래 지침·설정 9개는 모두 미수정 상태였다. 제품 소스 등 다른 작업의 변경은 존재했으며 분석 대상으로 읽기만 했다. 124개 세션의 metadata 기준 SHA는 모두 로컬에서 확인됐고 위 원격 검증 HEAD의 조상이었다. 이것이 각 세션 시작 당시의 원격 게시 상태를 증명하지는 않는다.

원격 기준 커밋의 작성 시각 17:21:32는 세션 cutoff보다 늦다. 이 커밋은 현재 문서·원격 상태 확인에만 사용했다. 마지막 지침 변경 `d8d0bf80`은 17:17:03이지만, cutoff 전 관측 시간이 짧으므로 그 변경의 효율 효과를 평가하지 않았다.

저장소용 근거: [집계·버전·원문 인덱스·검증 요약](evidence/2026-09-guideline-review.json)에 문서 hash, 로컬·원격 이력, 세션별 대조, 원문 근거 ID를 함께 보관했다. 원문 로그와 지침 전문은 로컬 분석 폴더에 보관하며, 요약에는 포함하지 않았다.

## 확정한 지침 문서

| 구분 | 대상 | 확인한 책임 |
|---|---|---|
| 진입 | `AGENTS.md` | 필요한 정책으로 안내, 역할·작업 경계 |
| 공통 정책 | `docs/00_governance/AGENT_POLICY.md` | 실행·위임·탐색·검증·완료 |
| Git 정책 | `docs/00_governance/VERSION_CONTROL.md` | 로컬 통합, 원격 반영, 승인 근거 |
| Codex 어댑터 | `.agents/adapters/codex.md` | 모델·reasoning·history·도구별 실행 |
| 작업 스킬 3개 | `.agents/skills/{project-context,implementation,verification}/SKILL.md` | 진입·구현·검증 단계의 실제 절차 |
| 보조 설정 2개 | `.codex/config.toml`, `.codex/rules/default.rules` | 저장소 설정값과 도구 허용 규칙; 실제 세션 설정과 구분 |

추가로 `.project/document-authority.yaml`, `.project/project.yaml`, 관련 Task/RESULT, `GovernanceProfile.kt`, `AgentGovernanceTemplates.kt`, `RootGovernanceDocUpdater.kt`, handoff validator와 세션 요약기를 확인했다. 현재 Codex 분석의 어댑터는 Codex 문서로 한정하고, 9월 중 AGY 제거는 지침 버전 변화의 배경으로 다뤘다.

Graphify는 관계 탐색에 사용했다. 설치된 CLI 실행이 실패해 기존 `graph.json`의 관련 노드·연결을 직접 조회했다. 그래프 생성 기준 `dd94bd44`는 현재 HEAD보다 오래돼 문서의 현재 내용이나 정책 적용 시점을 입증하는 근거로 사용하지 않았다.

## 시간과 적용 지침을 판정한 방법

증거는 **실제 로드된 지침·관련 사용자 변경 지시 → 당시 도구로 읽은 내용·로컬 diff → 세션 기준 Git blob → 시간상 인접한 커밋** 순으로 평가했다. 상위 실행 지침에 따른 제약도 구분한다. 시간상 인접한 커밋만으로 적용 지침을 확정하지 않는다.

`author time`, `committer time`, 원격 게시를 확인한 도구 결과 시각, 세션에 지침이 전달된 시각은 별개다. 예를 들어 AGY 제거 커밋 두 개는 9월 9일에 작성됐지만 committer time은 9월 10일 00:33:16이다. 날짜만으로 버전을 정하면 다른 결과가 나온다.

124개 중 79개에서 명시적인 `AGENTS.md` 메시지를 관측했다. 74개는 세션 기준 문서와 동일하거나 그 문서를 포함했고, 5개는 세션 기준과 다른 갱신본·로컬 상태를 포함했다. 나머지 45개는 해당 메시지를 관측하지 못한 것으로, 규칙을 읽지 않았다는 판정이 아니다. 이 확인은 `AGENTS.md`에 관한 것이며 나머지 정책 전체의 로드를 증명하지 않는다.

자식 metadata에는 조상의 `session_id`와 자신의 `id`가 함께 있는 경우가 있다. 파일 identity와 자신의 `id`를 대조해 세션 소유권을 확인했다. 6개 파일의 복수 metadata와 불투명한 메시지 인자도 구분했다. 실제 MCP 정규화 총량과 재집계가 일치하는지 검증했다.

## 지침 변화와 세션 적용 시점

모든 시각은 KST다. 아래의 커밋 시각은 별도 표시가 없으면 committer time이다.

| 시각 | 지침·세션 근거 | 해석 |
|---|---|---|
| 09-04 10:50:30 | Sol 세션 `01a069ec…`, 당시 `AGENTS.md` 로드. 기준 `67103e4f` | 직접 수행 대비 순가치가 있을 때 위임하는 규칙이 존재. 후일 Worker 우선 정책을 소급하지 않음 |
| 09-05 22:37:34 | [`a38d7647`](https://github.com/ezcode92/forge-platform/commit/a38d764790ddab07fc95969e18cfe8dfa07b3110) | Worker 우선 위임과 Main 직접 수행 예외 복원 |
| 09-07 17:25:09 | [`e5711b00`](https://github.com/ezcode92/forge-platform/commit/e5711b005218672ce2b048856dc06e5bea71335f) | 3단계 구조·Sub/Worker 역할·프로필 명문화 |
| 09-07 18:51:37~18:52:18 | Sprint 57 Main `01a07b46…`의 초기 지침과 정책 조회, 기준 `eb59e951` | 3단계·Worker 우선 정책을 실제 읽음. S01~S02 |
| 09-07 19:07:22 / 19:08:20 | 로컬 변경 흡수 요청 / resolver도 low Worker에 위임하라는 사용자 지시 | 커밋 전 적용 근거가 존재. S03~S04 |
| 09-07 19:16:00 / 19:57:20 | [`393afc09`](https://github.com/ezcode92/forge-platform/commit/393afc09b3d3cc5be78094e9efe5cc071f66ddd1), [`ac6d96ea`](https://github.com/ezcode92/forge-platform/commit/ac6d96ea4cd9c39fd1a7972025b60032e797ead6) | 로컬 수집 위임 정책 흡수, project-context 생성 영역의 resolver 위임 정합화 |
| 09-07 20:31:08 | [`77d25e51`](https://github.com/ezcode92/forge-platform/commit/77d25e514e08686c659048b50b5f2f471c6c5a7f) | 짧은 판단용 원문 직접 조회 허용. resolver 위임 예외는 여전히 불허 |
| 09-07 21:17:26 / 21:23:39 | 사용자 “오케스트레이션 정책에 따라 작업 전환” / [`e29482fb`](https://github.com/ezcode92/forge-platform/commit/e29482fb06e031ce89e2c684c5027c00b8c5c429) | Worker 전용 구현 지시를 재확인하고 문서화. S06 |
| 09-07 22:59:52 | Sub `01a07b57…`에 기존 지침을 대체하는 AGENTS 메시지 도착 | 새 문서가 이 시점에 세션에 들어온 것은 확인. 커밋과 즉시 동기화됐다고 가정할 수 없음. S07 |
| 09-09 16:43:45~16:43:48 | 모델·reasoning 없는 spawn, 자식의 실제 Astra/ultra 설정 | history 분리와 프로필 지정은 별도 검증 대상. S10~S11 |
| 09-10 13:43:24 | 사용자 “이번 작업부터 적용” 재지시, Main 구현 turn Astra/high | 체크인된 구정책보다 먼저 새 작업 방식을 적용한 명시 근거. S12~S13 |
| 09-10 14:37:53 | [`49f4af4e`](https://github.com/ezcode92/forge-platform/commit/49f4af4e7a822c3c6d93331e9873697db4603e60) | Main 단독 기본, 필요한 위임, 모델 범위, 기록 축소를 커밋. S14 |
| 09-10 15:30:57 | 실제 push 결과 `a7da51b..49f4af4 main -> main`, exit 0 | 이 시각까지 원격 반영된 증거. 14:38 보고에는 아직 원격 미반영이라고 명시. S15~S16 |
| 09-10 15:36:47 | 후속 UI 세션에 `49f4af4e`의 AGENTS와 개인 승인 지침이 함께 로드됨 | 변경 이후 실제 적용 사례이지만 cutoff 시점에 작업 진행 중. S20 |
| 09-10 17:17:03 | [`d8d0bf80`](https://github.com/ezcode92/forge-platform/commit/d8d0bf808096aa938dfb7621fe713dceea0c8240) | 이미 승인된 원격 반영까지 완료하도록 Git 정책 보정. 효과 측정은 아직 부족 |

## 세션 재분석 결과

### 1. 큰 조율 비용은 관측되지만 모두 불필요한 작업은 아니다

forge-platform은 전체 관측 토큰의 **70.7%, 626,993,477 tokens**를 사용했다. input 623,664,017 중 cache 590,456,576, 비캐시 input 33,207,441, output 3,329,460이다. 총량에는 자동 승인 검토도 포함한다. 총 토큰을 그대로 비용으로 해석하지 않았다.

도구 호출 7,197개 중 `send_message`, `wait_agent`, `followup_task`, `list_agents` 합계가 **2,679개, 37.2%**다. 952개 `wait_agent` 호출에서 완료 반환 580개, timeout 371개를 식별했다. 한 건은 해당 반환 분류가 없었다. timeout 횟수는 낭비 시간이나 실패율이 아니다.

Sprint 57 가족은 자동 승인 검토를 제외한 실행 세션 7개, 모델 응답 2,794개, **224,289,433 tokens**다. Main+Sub 두 세션이 104,520,360 tokens로 **46.6%**를 차지했다. 이 두 세션에는 판단·검토·직접 도구 실행도 들어 있으므로 46.6% 전부를 제거 가능한 중계 비용이라고 볼 수 없다. 다만 resolver까지 필수 위임하던 경로와 조율량은 간소화할 충분한 관측 근거다. [세션 가족별 재집계](evidence/2026-09-guideline-review.json)

### 2. 모델보다 먼저 작업 위험과 완료 조건을 맞춰야 한다

9월 7일 Main은 필수 동시성·복구 실패 테스트가 빠졌다며 통합을 보류하고 reasoning을 높인 Worker로 넘긴다고 보고했다(S05). 원본 설정은 초기 담당 Terra/low, 후속 담당 Terra/high로 확인됐다. 이는 완료 조건 누락과 재작업의 사례다. **low가 단독 원인이라거나 high면 재작업이 사라진다는 비교 실험은 아니다.**

범용 규칙에는 어려운 의미·동시성 작업까지 low로 시작하도록 강제하지 않고, 필수 실패 경로를 배정 시점에 드러내도록 제안했다. 환경 오류와 요구 누락, 구현 오류, 검증 누락을 나눠 조치해야 한다.

### 3. 문서의 프로필 규칙과 실제 호출 사이에 틈이 있었다

9월 9일 `ideas_document_preflight` spawn에는 `fork_turns: none`만 명시되고 `model`, `reasoning_effort`가 없었다. 자식 `01a0851f…`의 실제 설정은 **Astra/ultra**였다. 당시 기준 `8947660e`의 Codex 어댑터는 프로필 명시와 암묵 상속 금지를 규정하고 있었다. 따라서 history 분리만으로 프로필 제어까지 보장된다고 볼 수 없다(S10~S11).

현재 지침은 이미 native hook 미적용 범위를 `UNKNOWN`으로 구분한다. 추가할 것은 또 다른 선언이 아니라 **실제 spawn 요청과 반환 세션 설정의 대조**다. 불투명한 메시지 본문은 해독하거나 내용 위반의 근거로 사용하지 않았다.

### 4. 직접 수행 사례는 실행 가능성을 보여주며 절감률 실험은 아니다

| 구간 | 적용 근거·실제 모델 | 모델 응답·총 토큰 | 확인한 결과와 한계 |
|---|---|---|---|
| 09-04 Sol 작업 세션 | 당시 지침 로드, Sol/high | 189 / 16,475,240 | spawn 0. backend 결과 610 tests, 실패·오류 0, skipped 7. 세션에 서로 다른 작업 요청이 포함됨. S08~S09 |
| 09-10 정책 개선 구현 turn | 사용자 즉시 적용 지시, Astra/high | 34 / 2,650,359 | 해당 구간 spawn·조율 호출 0. 기존 분석용 자식 둘의 구간 사용량 기록도 0. 자동 승인 검토는 별도 5응답 / 227,310 tokens |

두 번째 구간은 **13:43:24.545~14:08:22 KST**다. Main의 비캐시 input은 178,657, output은 37,782였다. 같은 세션의 사전 분석은 Astra/max로 수행했고 자식도 사용했으므로 전체 세션을 “단독 구현 34응답”이라고 부르면 잘못이다. 마지막 사용량 기록 시각은 14:07:47.395이며 구간 길이 또는 응답 간 경과를 순수 작업 시간으로 해석하지 않았다.

저장소의 기존 `session-usage.json` 숫자를 그대로 인용하는 데 그치지 않고, 원본에 저장소 요약기를 다시 실행해 34응답·사용량·조율 0을 일치 확인했다. 관련 회귀와 drift 통과는 Sprint 63의 결과 기록으로 확인했으며 이번 분석에서 제품 테스트를 재실행한 것은 아니다. [원본 재집계](evidence/2026-09-guideline-review.json), [같은 구간의 자식·승인 검토 분리](evidence/2026-09-guideline-review.json), [해당 커밋의 Sprint 63 결과](https://github.com/ezcode92/forge-platform/blob/49f4af4e7a822c3c6d93331e9873697db4603e60/sprints/sprint-63/RESULT.md)

작업 난이도·산출물·세션 기간이 다르므로 Sprint 57의 224M과 이 구간의 2.65M을 나눠 정책 개선 절감률로 제시하지 않는다. 기존 Sprint 63 보고의 8월·Downloads 비교 역시 이번 9월 로컬 표본에 합치지 않았다.

### 5. 완료 범위·승인 근거의 전달도 작업 경로에 포함해야 한다

9월 10일 컴파일 수정 세션에서 사용자 main 반영 요청 뒤, Main은 push 자동 검토 거절을 알렸고 사용자는 확인된 GitHub인데 왜 미확인으로 표시하느냐고 물었다(S17~S19). “검토기가 목적지를 미확인으로 분류했다”는 사실과 “실제로 사용자에게 확인되지 않은 저장소다”라는 판단은 구분해야 한다.

이 자료만으로 leaf에 전달된 정확한 justification 누락이 거절의 원인이라고 단정하지 않았다. 개선안에는 실제 실행 주체까지 승인 근거를 전달하는 규칙과, 같은 범위의 기존 승인을 재사용하는 규칙을 함께 뒀다. 현재 개인 지침과 17:17 Git 정책 보정에도 이미 반영된 내용이다. 해당 저장소의 승인을 범용 문서나 다른 저장소로 복사하지 않는다.

## 현재 정책에서 유지할 것과 추가로 바꿀 것

| 항목 | 현재 상태 | 개선안의 차이 |
|---|---|---|
| Main 직접 수행, 필요한 경우만 계층 추가 | `49f4af4e`에 이미 반영 | 유지. 새 제안의 절감 성과로 재포장하지 않음 |
| history 없는 compact 위임, 실제 모델 범위 | 이미 반영, native 강제 적용은 제한 있음 | 실제 요청·반환 프로필 대조와 적용 범위 기록 |
| 지침 버전·활성 시점 | source freshness 규칙은 있으나 관측한 정책 적용 시점과 같지 않음 | 지침 경로/hash·사용자 override·적용 경계를 한 번 보존, 관련 변경만 전파 |
| 범위 갱신 권한 | Main 소유와 `approved delta`가 함께 등장 | 승인 목표 안의 내부 배정 변경은 Main이 처리; 사용자 판단이 필요한 차이를 분리 |
| 검증 범위 | canonical은 변경 영향 범위 기준, verification 스킬은 “제품 코드 변경은 full backend/build” | UI 등에도 backend 전체가 필수인지 조건을 명확화. 기존 gate를 임의 면제하지 않음 |
| 생성 문구 | MUTATION 설명의 worktree·직렬 규칙 반복, “backend source mutation은 직렬”의 문맥이 넓게 읽힐 수 있음 | shared checkout·공유 자원 조건을 명확히 하고 생성 원본에서 반복 제거 |
| 실패 후 재실행 | focused 실패 뒤 broad 반복 금지는 이미 있음 | 환경·명령·구현·완료 조건 실패를 구분하고 바뀐 조건 없이 재시도하지 않도록 보완 |
| 완료·원격 반영 | `d8d0bf80`과 개인 승인 지침에서 보정 | 유지하되 승인된 대상·범위와 leaf 실행 근거를 함께 전달 |
| 측정과 기록 | 자동 요약·중복 제거·cutoff 규칙은 이미 있음 | 정책 버전과 실제 작업 구간을 측정에 연결; 수동 기록을 늘리지 않음 |

검증 범위의 표현 차이는 **현재 문서의 모호함**이다. 이것 때문에 과거 특정 불필요한 전체 테스트가 실행됐다고 입증한 것은 아니다. 원문은 [verification 스킬](https://github.com/ezcode92/forge-platform/blob/8dedb4fe9dbddc8a9727ed90eeefbcb0b4f2186e/.agents/skills/verification/SKILL.md), [공통 정책](https://github.com/ezcode92/forge-platform/blob/8dedb4fe9dbddc8a9727ed90eeefbcb0b4f2186e/docs/00_governance/AGENT_POLICY.md)에서 비교할 수 있다.

## 적용 위치와 확인 기준

범용 제안문은 공통 실행 규칙만 담는다. forge-platform에 실제 반영할 때는 다음 순서가 적절하다. 이번 분석에서는 이 변경을 수행하지 않았다.

1. 공통 정책에서 지침 버전·적용 시점, 내부 범위 변경 권한, 검증 조건을 먼저 명확히 한다. `AGENTS.md`에는 짧은 진입 규칙과 참조만 둔다.
2. 생성 영역의 내용은 `GovernanceProfile.kt`와 `AgentGovernanceTemplates.kt`에서 바꾼다. `RootGovernanceDocUpdater.kt`가 공통 정책·스킬·어댑터의 marker 내부를 생성하므로 출력 문서만 고치면 변경이 다시 덮일 수 있다.
3. provider별 실제 모델·reasoning·history 확인은 Codex 어댑터와 지원되는 실제 dispatch 경로에서 처리한다. validator 단독 PASS를 native 호출 강제 적용 PASS로 보고하지 않는다.
4. 검증 스킬과 생성 문서를 동기화하고 관련 회귀·drift 검증을 수행한다. 제품 소스를 변경할 경우 해당 프로젝트의 필수 검증 조건도 따른다.

확인할 대표 동작은 다음과 같다.

- 짧은 조회·문서 수정: 별도 계층·제품 전체 빌드 없이 필요한 근거와 완료 결과를 제공한다.
- 서로 독립된 두 작업: 실제 병행할 일이 있을 때만 위임하고 공유 자원과 통합 순서를 확인한다.
- 실행 중 지침 변경·미커밋 정책: 기존 HEAD만 재사용하지 않고 영향을 받는 주체에 변경분을 적용한다. 무관한 문서는 다시 읽지 않는다.
- 프로필 누락: 실제 dispatch 전에 보완하거나, 설정을 확인할 수 없는 한계를 남긴다. 자동 상속을 명시 지정 성공으로 기록하지 않는다.
- 이미 승인된 Git 후속 단계: leaf에도 정확한 승인·대상·범위 근거를 전달한다. 자동 검토 거절은 실제 동작과 공개 사유로 구분한다.
- 검증 실패: failing/affected 범위를 먼저 해결하고 필요한 broad gate로 복귀한다. 기존 무관한 실패를 숨기거나 같은 gate만 반복하지 않는다.

후속 효과는 유사한 범위·완료 조건의 작업을 모아 인수 성공, 재작업, 비캐시 input/output, 조율·대기, 실제 경과를 함께 비교해야 한다. 현재 자료로 수치 절감 목표나 특정 모델의 우월성을 확정하지 않는다.

## 검증과 한계

이번 산출물의 검증은 지침·세션 identity, 시간대, Git ancestry, 원격 HEAD 비교, MCP 원문 대응, 사용량 재집계, 문서 참조 확인이다. 제품 동작을 바꾸지 않았으므로 제품 빌드와 전체 테스트는 실행하지 않았다.

원격 현재 이력에 커밋이 존재하는 것만으로 과거 push 시점을 복원할 수 없다. 명시적인 push 결과가 없는 경우 원격 게시 시점은 미확인이다. 지침이 로드됐다는 사실도 모든 규칙이 실제 행동에 적용됐다는 보장은 아니다. 일부 기록의 메시지 인자는 불투명하고, MCP의 일반 도구 실패 표시는 중첩 실행 결과를 놓칠 수 있어 실패율을 만들지 않았다.

원문 로그·분석 스크립트·전체 snapshot은 로컬 전용 `.agent-monitor/september-2026/guideline-review/`에 보관했다. 저장소에는 [검증 요약](evidence/2026-09-guideline-review.json)의 `analysis_validation`과 `publication_validation`을 포함한다. 전자는 원문 대조·총량 일치, 후자는 반영 문서의 hash와 로컬 참조 검증을 기록한다.
