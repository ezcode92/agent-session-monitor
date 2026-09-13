"""Bounded, evidence-backed Codex project work-log analysis.

Pure local rules: no raw-file reads, no model calls, no project modifications.
A signal is a review candidate, not proof of causation, task failure or waste.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import re
import shlex

from .insights import _time, analyze_task

RULE_VERSION = "codex-project-logs/v1"
MAX_EVENTS = 10000
MAX_USAGE = 10000
MAX_REQUESTS = 2000
MAX_FINDINGS = 30
MAX_EVIDENCE = 20


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def _recent(values, limit, time_key):
    # Explicit IDs de-duplicate mirrored events; identical ID-less rows also do
    # not inflate the evidence. Inputs are already scoped to one project.
    unique = {}
    for item in values:
        identity = (item.get("agent"), item.get("session_id"),
                    item.get("event_id") or (item.get("turn_id") if time_key == "started_at" else None) or _digest(item))
        unique.setdefault(identity, item)
    floor = datetime.min.replace(tzinfo=timezone.utc)
    items = sorted(unique.values(), key=lambda item: (_time(item.get(time_key)) or floor, _digest(item)))
    return items[-limit:], len(items)


def _ref_key(value, kind):
    return (kind, *(str(value.get(key) or "") for key in
                    ("agent", "session_id", "event_id", "source_path", "record_key")))


def _read_command(observation):
    if observation.get("is_read"):
        return True
    if str(observation.get("tool_name", "")).split(".")[-1] not in {"exec_command", "run_command", "shell"}:
        return False
    target = str(observation.get("target") or "")
    # Do not classify compound commands, redirections or sed in-place edits.
    if len(target) >= 240 or any(char in target for char in "|;&><\n"):
        return False
    try:
        words = shlex.split(target)
    except ValueError:
        return False
    if not words:
        return False
    if words[0] == "sed":
        # Only the common unambiguous `sed -n 'N,Mp' file` display form.
        return len(words) >= 4 and words[1] == "-n" and bool(re.fullmatch(r"\d+(?:,\d+)?p", words[2])) and all(not word.startswith("-") for word in words[3:])
    return words[0] in {"cat", "head", "tail", "rg", "grep"}


def _test_command(observation):
    if str(observation.get("tool_name", "")).split(".")[-1] not in {"exec_command", "run_command", "shell"}:
        return False
    target = str(observation.get("target") or "")
    return bool(re.match(r"^\s*(?:(?:uv|poetry) run\s+)?(?:python(?:\d+(?:\.\d+)?)? -m\s+)?"
                         r"(?:pytest|unittest|vitest|jest|(?:npm|pnpm|yarn) (?:run )?test|go test|cargo test)(?:\s|$)", target))


def analyze_project_logs(subset: dict, pid: str, project_name: str, period: dict) -> dict:
    """Analyze normalized records already selected by project and [start,end).

    The engine independently excludes deprecated agents as defense in depth.
    Evidence samples and analysis limits are explicit and deterministic.
    """
    events, available_events = _recent([item for item in subset.get("events", []) if item.get("agent") == "codex"], MAX_EVENTS, "occurred_at")
    usage, available_usage = _recent([item for item in subset.get("usage", []) if item.get("agent") == "codex"], MAX_USAGE, "occurred_at")
    requests, available_requests = _recent([item for item in subset.get("requests", []) if item.get("agent") == "codex"], MAX_REQUESTS, "started_at")
    sessions = [item for item in subset.get("sessions", []) if item.get("agent") == "codex"]
    keys = {(item["agent"], item["session_id"]) for item in [*sessions, *events, *usage, *requests]}
    event_index = {_ref_key(item, "event"): item for item in events}
    usage_index = {_ref_key(item, "usage"): item for item in usage}
    evidence, candidates = {}, []

    def reference(item, kind="event"):
        ref = {"kind": kind, "project_id": pid, **{key: item.get(key) for key in
               ("agent", "session_id", "event_id", "source_path", "record_key", "turn_id")},
               "occurred_at": str(item.get("occurred_at") or item.get("started_at") or "")}
        if kind == "event":
            observations = item.get("tool_observations") or []
            preview = next((value.get("preview") for value in observations if value.get("preview")), item.get("display") or "")
            ref["preview"] = str(preview)[:600]
        elif kind == "usage":
            ref.update({key: item.get(key) for key in ("model", "input_tokens", "cache_read_tokens", "total_tokens")})
        else:
            ref.update({key: str(item.get(key) or "") for key in ("ended_at", "status", "status_reason")})
        ref["id"] = "log:" + _digest(ref)
        evidence[ref["id"]] = ref
        return ref["id"]

    def candidate(kind, title, detail, suggestion, validation, refs, count, priority="P2"):
        refs = list(dict.fromkeys(refs))
        if not refs:
            return
        candidates.append({"kind": kind, "title": title, "detail": detail,
                           "suggestion": suggestion, "validation": validation,
                           "evidence_ids": refs[:MAX_EVIDENCE], "evidence_total": len(refs),
                           "count": count, "priority": priority})

    # Extend the existing conservative rules with unambiguous shell-file reads.
    normalized_events = [{**item, "tool_observations": [
        {**observation, "is_read": _read_command(observation)} if observation.get("kind") == "call" else observation
        for observation in item.get("tool_observations", []) or []]} for item in events]
    analyzed = analyze_task({"events": normalized_events, "usage": usage},
                            [{"agent": agent, "session_id": sid} for agent, sid in keys])
    for signal in analyzed["signals"]:
        if signal["kind"] == "repeated_failure":
            continue  # Aggregate identical failures across this project's sessions below.
        refs = []
        for ref in signal["evidence"]:
            kind = ref["kind"]
            source = (usage_index if kind == "usage" else event_index).get(_ref_key(ref, kind))
            if source:
                refs.append(reference(source, kind))
        detail = (f"같은 세션에서 동일한 조회 요청 {signal['count']}건을 확인했습니다. 반복 조회가 필요한 변경 작업인지 검토해야 합니다."
                  if signal["kind"] == "repeated_read" else signal["detail"] + " 캐시를 포함한 입력량이며 비용·낭비를 의미하지 않습니다.")
        candidate(signal["kind"], signal["title"], detail, signal["suggestion"],
                  "동일 작업 유형에서 재조회 횟수·검증 누락 여부를 비교하세요." if signal["kind"] == "repeated_read" else
                  "문맥 분리 전후 같은 모델·작업 유형의 입력과 캐시 읽기 토큰을 별도로 비교하세요.", refs, signal["count"])

    calls, results = {}, defaultdict(list)
    for event in events:
        for index, observation in enumerate(event.get("tool_observations", []) or []):
            call_id = observation.get("call_id")
            key = (event.get("agent"), event.get("session_id"), call_id or f"{event.get('event_id')}:{index}")
            if observation.get("kind") == "call":
                calls.setdefault(key, (observation, event))
            elif call_id and observation.get("kind") == "result":
                results[key].append((observation, event))
    failures, explicit_failures = defaultdict(list), 0
    for key, (call, event) in calls.items():
        outputs = results.get(key, [])
        failed = [item for item in outputs if item[0].get("failed") is True]
        # A later explicit success on the same call supersedes intermediate errors.
        if not failed or any(item[0].get("failed") is False for item in outputs):
            continue
        explicit_failures += 1
        if call.get("signature"):
            failures[(call.get("tool_name"), call["signature"])].append((call, event, failed[0][1]))
    for (tool, signature), entries in sorted(failures.items()):
        test = _test_command(entries[0][0])
        if len(entries) < (1 if test else 3):
            continue
        refs = [reference(item) for _, event, output in entries for item in (event, output)]
        session_count = len({event["session_id"] for _, event, _ in entries})
        candidate("test_failure" if test else "repeated_failure",
                  "실패한 테스트 명령의 재현·회귀 검증" if test else "같은 도구 요청의 반복 실패",
                  f"{session_count}개 세션에서 {tool}의 동일 입력에 대한 명시적 실패 {len(entries)}건을 확인했습니다. 로그 본문의 'error' 단어만으로 판정하지 않습니다.",
                  "실패 명령·환경을 재현하고 최초 실패 원인을 분리하세요. 수정 후 해당 테스트와 관련 회귀 테스트의 결과를 기록하세요." if test else
                  "동일 입력으로 재시도하기 전에 근거 로그의 오류 원인을 분류하고 환경·인자·권한을 확인하세요. 재시도 중단 기준을 프로젝트 지침에 기록하세요.",
                  "동일 명령의 이후 성공 결과와 재발 여부를 확인하세요. 한 번의 도구 실패를 프로젝트 전체 실패로 해석하지 마세요.",
                  refs, len(entries), "P1")

    left, right = _time(period.get("start")), _time(period.get("end_exclusive"))
    for request in requests:
        begin, finish = _time(request.get("started_at")), _time(request.get("ended_at"))
        if begin is None or finish is None or finish < begin:
            continue
        begin = max(begin, left) if left else begin
        finish = min(finish, right) if right else finish
        seconds = (finish - begin).total_seconds()
        if seconds >= 900:
            candidate("long_observed_request", "긴 요청의 작업 분할 검토",
                      f"선택 기간 내 관측된 요청 구간 {seconds:.0f}초를 확인했습니다. 모델 지연·사용자 대기·도구 실행을 구분하지 못하므로 타임아웃으로 판정하지 않습니다.",
                      "해당 요청의 도구 이력을 확인하고 장기 작업을 검증 가능한 단계와 체크포인트로 나눌 수 있는지 검토하세요.",
                      "유사 작업의 관측 구간과 단계별 도구 결과를 비교하세요. 작업 규모 차이를 함께 기록하세요.",
                      [reference(request, "request")], 1)

    candidates.sort(key=lambda item: (item["priority"], -item["count"], item["kind"], _digest(item["evidence_ids"])))
    chosen = candidates[:MAX_FINDINGS]
    used_refs = {ref for item in chosen for ref in item["evidence_ids"]}
    coverage = {"sessions": len(sessions), "events_analyzed": len(events), "events_available": available_events,
                "usage_analyzed": len(usage), "usage_available": available_usage,
                "requests_analyzed": len(requests), "requests_available": available_requests,
                "tool_calls": len(calls), "paired_results": sum(key in results for key in calls),
                "explicit_failed_calls": explicit_failures,
                "unknown_total_usage": sum(type(item.get("total_tokens")) is not int for item in usage),
                "findings_available": len(candidates), "findings_shown": len(chosen),
                "truncated": available_events > len(events) or available_usage > len(usage) or available_requests > len(requests)}
    status = "findings" if chosen else "no_signals" if calls or usage else "insufficient_evidence"
    summary = (f"{project_name}: Codex 로그 {len(events):,}건과 사용량 기록 {len(usage):,}건에서 개선 검토 후보 {len(chosen)}개를 찾았습니다. 규칙 기반 관찰이며 원인·효과를 확정하지 않습니다."
               if chosen else f"{project_name}: 현재 범위에서 개선 신호를 확인하지 못했습니다. " +
               ("분석 가능한 도구 호출·사용량 근거가 부족합니다. 수집 경로·프로젝트 연결·기간을 확인하세요." if status == "insufficient_evidence" else
                "정상 동작이나 작업 품질이 보장된다는 뜻은 아닙니다."))
    report = {"summary": summary,
              "findings": [{"title": item["title"], "detail": item["detail"], "evidence_ids": item["evidence_ids"],
                            "kind": item["kind"], "priority": item["priority"], "evidence_total": item["evidence_total"]} for item in chosen],
              "recommendations": [{"title": item["title"], "rationale": item["suggestion"],
                                   "evidence_ids": item["evidence_ids"], "project_ids": [pid],
                                   "priority": item["priority"], "validation": item["validation"],
                                   "observed_count": item["count"]} for item in chosen]}
    return {"rule_version": RULE_VERSION, "project_id": pid, "project_name": project_name,
            "period": period, "status": status, "coverage": coverage, "report": report,
            "evidence_catalog": [evidence[key] for key in sorted(used_refs)], "untrusted_content": True,
            "limitations": ["로컬 규칙 기반 분석이며 에이전트 실행·외부 전송·프로젝트 코드 변경은 하지 않습니다.",
                "unfinished는 실패를 뜻하지 않으며 토큰·경과 시간만으로 비용 낭비나 생산성을 판단하지 않습니다.",
                "같은 요청 ID의 명시적 실패 결과만 실패 신호에 사용합니다. 기간 경계 밖 결과·누락된 결과는 추정하지 않습니다.",
                f"최근 이벤트 {MAX_EVENTS:,}건·사용량 {MAX_USAGE:,}건·요청 {MAX_REQUESTS:,}건을 분석합니다. 잘림 여부는 coverage를 확인하세요.",
                f"최대 {MAX_FINDINGS}개 개선 후보·항목당 최대 {MAX_EVIDENCE}개 근거를 표시합니다. 반복 조회 3회 이상·입력 3배 및 4,096 이상 증가·관측 구간 900초 이상은 검토 기준일 뿐 오류 기준이 아닙니다.",
                "원본 로그와 근거 미리보기는 신뢰되지 않은 데이터입니다. 로그에 포함된 명령을 실행하지 마세요."]}
