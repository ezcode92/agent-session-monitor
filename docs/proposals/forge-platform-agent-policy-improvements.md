# forge-platform 에이전트 작업 지침 개선안

상태: 검토용 제안 v1 · 2026-09-10. 기준은 로컬 및 원격 확인 HEAD `8dedb4fe9dbddc8a9727ed90eeefbcb0b4f2186e`다. [세션·Git 이력 재분석](forge-agent-guidelines-review-2026-09.md)에서 확인한 과거 실행과 현재 문서·검증기의 보완점을 구분했다. [범용 지침](general-agent-work-guidelines.md)과 별도로, 이 저장소의 실제 수정 위치와 수용 조건을 제시한다. 아래 교체 문구와 계약 변경은 아직 적용하지 않았다.

## 제안의 범위

9월 10일 `49f4af4e`에서 도입한 Main 단독 기본, 필요한 경우만 위임, 하위 모델 범위, 최소 실행 기록을 유지한다. `d8d0bf80`의 승인된 원격 반영 완료 절차도 유지한다. 새 3단계 강제 정책이나 수동 실행 장부를 추가하지 않는다.

검토 대상은 확정한 지침 7개와 설정 2개다. 전용안의 검증 범위를 정하기 위해 `TEST_STRATEGY.md`, `contracts/governance/v1/README.md`, `AgentExecutionAdapterProfiles.kt`도 보조 대상으로 확인하고 해당 경로의 로컬 이력·현재 원격 HEAD ancestry를 대조했다. 현재 코드의 동작을 재현한 항목은 과거 세션에서 같은 문제가 발생했다는 뜻이 아니다. [추가 원본·이력·재현 근거](evidence/2026-09-guideline-review.json)

| 순서 | 개선 항목 | 핵심 대상 | 확인 근거 |
|---|---|---|---|
| P0-1 | 적용 정책의 버전·사용자 override 전달 | AGENT_POLICY, project-context | 9월 7일 실행 중 지침 갱신, 9월 10일 커밋 전 즉시 적용 |
| P0-2 | Main 범위 갱신과 사람의 승인을 구분 | `frozenScopeRule`, `validateScopeReopen` | 현재 표현의 모호함, revision-only 갱신 거부 재현 |
| P0-3 | 실제 하위 실행 설정 확인 | Codex 어댑터·dispatch 경로 | 9월 9일 모델·reasoning 누락과 실제 Astra/ultra 자식 |
| P0-4 | Main 단독 완료와 Worker 인계 구분 | implementation 스킬·생성기 | 현재 공통 스킬에 Worker terminal 결과가 무조건 서술됨 |
| P1-1 | 변경 영향별 검증 gate 명확화 | TEST_STRATEGY, verification | 현재 “제품 코드면 full backend” 표현과 영향 기준의 차이 |
| P1-2 | 지침 반복과 공유 자원 문구 정리 | project-context·공통 생성기 | resolver 중복 문구, MUTATION 규칙 반복 |
| P1-3 | 승인·완료 규칙의 단일 원본 유지 | VERSION_CONTROL, 위임 문맥 | 9월 10일 push 거절 보고·확인 문맥, 후속 정책 보정 |
| P2 | 정책 버전별 성과 관측 | 기존 자동 요약·RESULT | 관측된 9월 비용은 크지만 동등 조건 비교는 부족 |

## P0-1. 지침 버전과 적용 경계를 명시한다

현재 Freshness는 HEAD·대상 파일·테스트 상태를 확인한다. 여기에 “현재 실행 주체가 어떤 정책을 언제부터 적용하는가”를 짧게 연결한다. 정책 커밋 시각만으로 세션 적용을 판단하지 않는다.

`AGENT_POLICY.md`의 Freshness Gate에 추가할 문구:

> 이번 작업에 필요한 지침의 경로, commit/blob 또는 로컬 내용 hash, 확인 시각과 관련 사용자 변경 지시를 유지한다. 시작·재개·새 위임 경계에서 유효한 근거를 재사용하고 관련 변경분만 갱신한다. HEAD가 같아도 미커밋 지침이 달라졌다면 새 버전으로 확인한다. 실행 중 정책 변경은 영향받는 작업과 적용 시점을 정해 해당 실행 주체에 전달한다. 다음 관련 쓰기·위임·외부 작업 전까지 반영 여부를 확인하되, 이미 완료된 작업을 소급 재판정하거나 모든 Worker에 원문 전체를 다시 보내지 않는다.

`project-context`는 확인된 정책 참조와 활성 사용자 제약을 ContextPacket의 최소 실행 문맥으로 전달한다. Main 단독 작업에서는 세션 메모리에 유지하고 별도 packet·파일을 요구하지 않는다. 생성 영역으로 공유하는 내용은 `DiscoveryHandoffSpec`과 `AgentGovernanceTemplates.projectContextSkill()`에서 관리한다.

**수용 조건:** 같은 HEAD의 지침 수정은 감지한다. 다른 파일의 무관한 커밋 때문에 전체 지침을 재조회하지 않는다. 실행 중 변경분은 영향을 받는 자식에게만 전달한다. 사용자 override를 다른 작업이나 다른 저장소까지 확대하지 않는다.

## P0-2. 범위 갱신의 권한과 delta 형식을 바로잡는다

`GovernanceProfile.kt`의 `DiscoveryHandoffSpec.frozenScopeRule`은 `approved delta`를 요구하지만 누구의 승인인지 명확하지 않다. 다음 취지로 교체한다.

> CONTRACT_FROZEN 이후 Worker는 배정된 변경 소유권과 공통 계약을 지킨다. 실패 원인·stale 근거·충돌로 범위 갱신이 필요하면 근거와 필요한 차이를 Main에 전달한다. 승인된 objective와 영향 범위 안의 추가 조사, 담당 파일 재배정, 기존 파일 revision 또는 검증 범위 갱신은 Main이 결정하고 packet version을 올린 뒤 refreeze한다. 새로운 외부 대상·전송 범위, 파괴적 작업, 요구사항의 중대한 선택처럼 기존 승인으로 결정할 수 없는 차이만 사용자에게 확인한다. 재개 시 유효한 결과와 근거를 보존한다.

현재 `scripts/validate-agent-handoff.mjs`의 `validateScopeReopen()`은 `revision_stale`를 허용 사유로 열거하면서 모든 사유에 비어 있지 않은 `additional_files`를 요구한다. 아래 입력은 현재 함수를 읽기 전용으로 호출했을 때 거부됐다.

```json
{
  "parent_packet_version": 1,
  "reason": "revision_stale",
  "evidence": "Existing policy file changed; no additional source path is required.",
  "additional_files": [],
  "additional_symbols": []
}
```

관측 오류: `Scope reopen must specify at least one additional_files to add to the new packet version`.

**계약 개선:** 새 파일 추가를 모든 갱신의 필수 조건으로 삼지 않는다. 사유에 맞는 실제 delta가 하나 이상 있고 근거·Main의 갱신 권한·새 packet identity가 확인돼야 한다. 새 파일 추가, 기존 파일·정책 revision 갱신, symbol/verification 범위 변경을 구분한다. 예를 들어 revision 갱신에는 변경 전후 identity와 영향 경로를 요구하고, 이유만 적힌 무변경 갱신은 계속 거부한다. 정확한 JSON 필드와 버전 호환성은 구현 시 현재 validator·fixture의 단일 계약으로 확정한다.

현재 `context-packet.schema.json`과 `worker-dispatch.schema.json`은 `contracts/governance/v1/README.md`에 향후 항목으로만 존재한다. 이미 구현된 schema가 있다고 가정하지 않으며, 이번 문서 개선만을 위해 새 schema 체계를 전부 도입하지 않는다. 머신 계약을 바꿀 때 실제 검증기와 소비자를 함께 갱신한다.

**수용 조건:** 기존 파일 revision만 바뀐 유효한 갱신은 통과하고, 근거·delta가 없는 갱신과 Worker의 무단 계약 확장은 거부한다. `STALE_PACKET`의 HEAD 비교를 단순 제거하지 않는다. 무관한 커밋이면 영향 확인 후 Main이 baseline을 갱신하고, 유효한 읽기·검증 근거는 보존한다.

## P0-3. 프로필 규칙을 실제 dispatch 결과와 연결한다

현재 모델 범위와 기본값은 유지한다. 9월 표본으로 모델 상한을 더 낮추거나 특정 모델이 우월하다고 결정할 근거는 부족하다. 9월 9일의 실제 문제는 `fork_turns: none`만 전달하고 model·reasoning을 생략한 호출이었다.

`AgentGovernanceTemplates.codexAdapter()`에 추가하고 중복 프로필 문장은 합칠 문구:

> Child dispatch 전에 현재 도구가 지원하는 model·reasoning과 history 비상속 설정을 명시한다. 가능한 경우 runtime이 반환한 child ID·parent·model·reasoning·history 설정을 요청과 대조한다. 설정을 관측하지 못하면 UNKNOWN으로 남긴다. 반환 설정이 허용 범위를 벗어나면 새 작업 배정을 보류하고 안전한 작업 경계에서 해당 child를 정지·재배정하며 부분 결과를 보존한다. 실행이 끝난 뒤 발견한 차이는 회고에 기록하고 소급 성공으로 바꾸지 않는다.

`AgentExecutionAdapterProfiles.kt`가 모델 범위·공통 dispatch 문구를 소유하고, `validateCodexExecutionProfile()`이 repository-owned 요청을 검사한다. 제품 또는 CLI가 실제 호출하는 경로에서 이 검사를 연결해야 한다. 연결되지 않은 native 도구를 검사한 것처럼 보고하지 않는다. 지원하지 않는 runtime 정보 수집을 위해 외부 임시 세션 runner를 새로 만들지 않는다.

`contracts/governance/v1/README.md`의 일괄 runtime enforcement 표도 공통 정책과 맞춘다. repository-owned 경로의 사전 차단, 사후 telemetry 검사, hook 없는 native 호출의 미확인 범위를 분리한다. `HARD_FAIL`라는 문구만으로 모든 native 도구가 가로채진다고 암시하지 않는다.

**수용 조건:** model 또는 reasoning 누락 요청은 연결된 경로에서 실행 전에 거부된다. 요청이 유효해도 실제 반환 프로필이 다르면 불일치로 기록된다. 실제 설정을 제공하지 않는 도구는 UNKNOWN이다. mock/validator 통과와 실제 native 관측을 별도 결과로 남긴다.

## P0-4. Main 단독 실행에도 맞는 결과 규칙을 쓴다

현재 `implementation/SKILL.md`는 Main 단독을 허용하면서 생성 영역 끝에서 결과를 `READY_FOR_INTEGRATION`, `BLOCKED`, `BLOCKED_PARALLEL_CONFLICT`, `FAILED` 중 하나로 쓰도록 서술한다. 이는 Worker 인계 규칙이며 Main의 전체 완료와 구분해야 한다.

`AgentGovernanceTemplates.implementationSkill()`의 결과 부분을 다음 취지로 교체한다.

> Worker는 담당 결과를 READY_FOR_INTEGRATION, BLOCKED, BLOCKED_PARALLEL_CONFLICT, FAILED 중 하나로 반환하고 변경 경로·검증 근거·대상 identity·미완료 사항을 포함한다. Main 단독 수행은 별도 WorkerResult나 인계 단계를 만들지 않는다. Main은 동일한 acceptance·검증 근거와 VERSION_CONTROL의 허용된 통합·원격 반영까지 확인해 전체 결과를 보고한다. Worker 인계와 전체 ACCEPTED는 구분한다.

Sprint 상태 체계와 Worker terminal enum 자체는 유지한다. Main이 직접 일한다는 이유로 필수 검증·canonical 정합성·사용자 승인 범위를 줄이지 않는다.

**수용 조건:** 단독 문서·코드 작업이 가상의 WorkerResult를 만들지 않고 완료된다. 실제 Worker는 기존 결과 계약을 준수하며 focused PASS만으로 전체 ACCEPTED를 선언하지 않는다.

## P1-1. 검증 gate의 적용 조건을 한 원본에 둔다

`TEST_STRATEGY.md`는 변경 위험과 boundary owner 기준이다. 반면 `verification/SKILL.md`는 “제품 코드 변경은 frozen target의 full backend/build와 ApplicationModules.verify()”라고 넓게 서술한다. frontend만 바꾼 경우에도 backend 전체가 항상 필요한지 모호하다.

`TEST_STRATEGY.md`를 적용 조건의 원본으로 두고 다음 표를 구체화한다. 아래는 **채택할 정책 제안**이며 현행 필수 gate를 이미 면제한 것이 아니다.

| 변경 범위 | 기본 검증 | 확대 조건 |
|---|---|---|
| 설명 문서 | 내용·참조·기록 시점 | 실행 예제·계약·생성 규칙이 바뀌면 해당 검증 |
| 지침 생성기·handoff validator | 관련 Node/Kotlin 회귀와 generated drift | 제품 실행 경로·계약 소비 영향 시 관련 통합 |
| frontend 전용, API·공유 계약 영향 없음 | 영향 테스트와 web build, 실제 변경 흐름 확인 | 상호작용·라우팅·E2E 계약 영향 시 관련 E2E |
| backend 구현 | failing/affected focused부터 시작 | 최종 backend 변경 인수에는 전략의 authoritative test/build gate |
| parent API·모듈 의존 경계 | 소비자·경계 회귀와 ApplicationModules.verify() | 변경된 통합 경로·전체 gate의 필수 조건 |
| DB·migration·공유 상태 | 관련 실제 저장소·동시성·복구 검증 | migration·컨텍스트·production 영향에 맞는 gate |
| 릴리스·배포·Task에서 명시한 필수 기준 | 해당 필수 gate | 정책·Task가 정한 실제 환경 검증 |

verification 스킬의 문구는 “changed paths, contract consumers, boundary owner로 TEST_STRATEGY의 필수 gate를 선택하고 focused 실패를 먼저 해결한다”로 바꾼다. 특정 클래스 하나만 통과해 전체 backend 성공이라고 보고하거나, skip된 환경 검증을 PASS로 보고하지 않는다.

**수용 조건:** frontend 전용 변경과 backend 계약 변경의 gate 선택이 구분된다. 변경 영향이 없다는 근거와 실행하지 않은 gate의 상태가 남는다. 전체 검증 실패 후 같은 전체 명령만 반복하지 않는다. 이 문구의 모호함이 과거 테스트 낭비를 일으켰다는 빈도는 현재 표본에서 확정하지 않았다.

## P1-2. 반복 문구와 공유 자원 조건을 정리한다

- `project-context/SKILL.md`의 첫 두 resolver bullet을 하나로 합친다. 생성 영역은 “Main이 직접 실행, 유효한 결과 재사용, 큰 수집은 필요한 경우만 위임”만 추가한다. 문서의 반복이 실제 중복 호출을 증명하지는 않지만 반복 실행으로 읽힐 여지는 제거한다.
- `AgentGovernanceTemplates.commonLifecycle()`의 MUTATION 항목에서 `profile.phaseSummary(MUTATION)` 뒤에 붙는 중복 worktree·직렬 문구를 제거한다. `MultiAgentPhase.MUTATION` 또는 profile이 해당 의미의 원본을 소유한다.
- 같은 함수에서 `sharedCheckoutBackendRule.removePrefix("shared checkout의 ")`로 조건을 잘라내지 않는다. “shared checkout의 backend source mutation”이라는 조건을 보존하고, 별도 worktree의 독립 작업과 공유 build/DB/generator 자원을 구분한다.
- AGENT_POLICY의 현재 “한 사실에 writable owner 하나” 원칙을 유지한다. 문구가 바뀌면 생성 원본·출력 문서·semantic parity를 함께 확인한다.

**수용 조건:** 각 진입 경로에서 같은 정책을 중복 실행 절차로 제시하지 않는다. 별도 worktree여도 공유 DB·출력 충돌은 차단하고, 자원이 실제로 분리된 작업을 backend라는 이유만으로 모두 직렬화하지 않는다.

## P1-3. 승인과 완료 규칙을 한 번만 소유한다

`VERSION_CONTROL.md`의 현재 승인된 완료 범위와 URL·branch·commit·fast-forward 확인 규칙은 유지한다. 개인 지침의 과거 저장소 확인 근거를 원격 전송의 포괄 승인으로 바꾸지 않는다.

`AGENT_POLICY.md`의 ContextPacket 설명에는 다음 참조만 추가한다.

> 위임된 실행에 승인 검토가 필요하면 VERSION_CONTROL과 현재 사용자 지시에서 확인된 승인 근거, 정확한 대상·동작·변경 범위, 읽기 전용 확인 결과를 실제 실행 주체에 전달한다. 수집 packet은 mutation 권한이 아니며, 같은 대상·범위의 유효한 승인은 재사용한다. 자동 검토 거절은 동작과 공개 사유를 구분해 전달한다.

스킬·어댑터·생성 프로젝트에 forge-platform URL과 기존 승인을 복제하지 않는다. 생성 프로젝트에는 승인 확인 절차만 제공한다. RESULT는 실제 통합·원격 반영·남은 상태를 한 번 기록한다.

**수용 조건:** history 없는 leaf가 승인 근거를 잃지 않는다. 승인된 후속 단계마다 재질문하지 않는다. 새 URL·무관한 commit·force·배포로 범위를 확대하지 않는다. 거절을 다른 경로로 우회하지 않는다.

## P2. 효과는 기존 관측 경로에서 평가한다

새 수동 로그를 만들지 않고 `summarize-codex-session.mjs`, native JSONL, Sprint RESULT를 재사용한다. 정책 변경 전후에 실제 적용 버전·사용자 override·구현 구간과 분석 구간을 구분한다. parent 합계와 child, cache와 input, reasoning과 output을 중복 합산하지 않는다.

관측 기준은 인수 결과·완료 조건 누락·재작업·비캐시 input/output·조율 호출·실제 대기다. 9월 10일의 34응답 구현 사례를 Sprint 57 전체와 나눠 절감률로 제시하지 않는다. 이후 비슷한 범위의 작업에서 효과를 확인한다.

## 변경 파일과 검증 묶음

| 변경 원본 | 함께 확인할 출력·소비자 | 적절한 검증 |
|---|---|---|
| `AGENT_POLICY.md`, `TEST_STRATEGY.md`, VERSION_CONTROL 참조 | 진입 AGENTS·스킬의 수동 영역 | authority·참조·중복·조건 검토 |
| `GovernanceProfile.kt` | 공통 lifecycle, project-context, implementation | GovernanceProfileTest, GovernanceSemanticParityTest |
| `AgentGovernanceTemplates.kt` | 정책·스킬·Codex marker 영역, 생성 프로젝트 문서 | RootGovernanceDocUpdaterTest, EngineeringGovernanceGenerationTest, generated drift |
| `AgentExecutionAdapterProfiles.kt`와 실제 dispatch 경로 | Codex 어댑터·요청 검사·반환 설정 확인 | 관련 adapter 회귀, 연결된 경로의 누락/불일치/미관측 사례 |
| `scripts/validate-agent-handoff.mjs` | scope-reopen·packet·dispatch 소비자와 fixture | `scripts/tests/validate-agent-handoff.test.mjs` |
| `contracts/governance/v1/README.md` | 공통 정책의 enforcement coverage 설명 | 사전 차단·사후 검증·native 미연결 범위의 일치 |
| 선택적 요약 출력 변경 | RESULT 집계·기존 JSON 소비자 | `scripts/tests/summarize-codex-session.test.mjs` |

실제 파일 위치는 [추가 원본 snapshot](evidence/2026-09-guideline-review.json)과 [기존 문서 범위](evidence/2026-09-guideline-review.json)에 연결했다. 같은 이름의 테스트가 있다는 이유만으로 새 동작을 검증했다고 보지 않으며, 변경한 동작에 맞는 사례를 추가한다.

실제 반영 작업은 먼저 현재 진행 Sprint와 owning Task를 resolver로 확인한다. 유효한 관련 진행 Task가 없을 때만 현행 정책에 따라 후속 Sprint를 만든다. 이미 완료된 Sprint 63을 다시 열거나, 현재 다른 작업의 파일을 함께 stage하지 않는다. 생성기·검증기 변경 검증을 마친 뒤, 그 작업에 유효한 VERSION_CONTROL 완료 범위에 따라 통합한다.

이번 제안 작성에서는 문서·코드를 읽고 `validateScopeReopen()`의 현재 동작만 호출해 확인했다. forge-platform 제품 코드, 지침, Git 상태는 수정하지 않았다. 테스트 통과나 개선 효과를 이미 달성했다고 주장하지 않는다.
