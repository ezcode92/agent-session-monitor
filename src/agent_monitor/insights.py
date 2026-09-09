"""Deterministic review signals from explicit tool observations and known usage."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import re


def _get(value, key, default=None):
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def _object(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            pass
    return value


def _failed(node):
    output = _object(node.get("output", node.get("content")))
    for value in (node, output):
        if not isinstance(value, dict):
            continue
        if isinstance(value.get("is_error"), bool):
            return value["is_error"]
        code = value.get("exit_code")
        if type(code) is int:
            return code != 0
        if str(value.get("status", "")).lower() in {"failed", "error"}:
            return True
    # Codex command-result metadata precedes the actual command output.
    if isinstance(output, str) and "Final output:" in output:
        metadata = output.split("Final output:", 1)[0]
        match = re.search(r"(?m)^Process exited with code (-?\d+)\s*$", metadata)
        if match:
            return int(match.group(1)) != 0
    return None


def tool_observations(record):
    """Normalize supported content blocks; unknown schemas supply no observations."""
    body = record.get("payload") if isinstance(record.get("payload"), dict) else record
    nodes = [body]
    if isinstance(body.get("item"), dict):
        nodes.append(body["item"])
    message = body.get("message")
    for content in (body.get("content"), message.get("content") if isinstance(message, dict) else None):
        if isinstance(content, list):
            nodes.extend(node for node in content if isinstance(node, dict))
    for call in body.get("tool_calls", []) if isinstance(body.get("tool_calls"), list) else []:
        if isinstance(call, dict):
            function = call.get("function") if isinstance(call.get("function"), dict) else call
            nodes.append({**function, "type": "tool_call", "call_id": call.get("id") or call.get("call_id")})
    observations = []
    for node in nodes:
        kind = node.get("type")
        if not isinstance(kind, str):
            continue
        agy = kind in {"RUN_COMMAND", "VIEW_FILE"} and "created_at" in record
        if kind in {"function_call", "custom_tool_call", "tool_use", "tool_call"} or agy:
            name = node.get("name") or (kind if agy else None)
            arguments = _object(node.get("arguments", node.get("input")))
            if arguments is None and agy:
                arguments = {key: node[key] for key in ("command", "file_path", "path") if key in node} or None
            if not name:
                continue
            call_id = node.get("call_id") or node.get("id")
            if call_id is None and agy and node.get("step_index") is not None:
                call_id = f"step:{node['step_index']}"
            target = next((arguments[key] for key in ("cmd", "command", "file_path", "path") if arguments.get(key)), "") if isinstance(arguments, dict) else arguments
            observations.append({"kind": "call", "call_id": str(call_id) if call_id is not None else None,
                                 "tool_name": str(name), "signature": _digest([name, arguments]) if arguments is not None else None,
                                 "preview": _preview(arguments),
                                 "target": str(target)[:240] if target is not None else "",
                                 "is_read": str(name).lower() in {"read", "read_file", "view_file", "functions.read_file"}})
            if agy and _failed(node) is not None:
                observations.append({"kind": "result", "call_id": str(call_id) if call_id is not None else None, "failed": _failed(node), "preview": _preview(node.get("output", node.get("content")))})
        elif kind in {"function_call_output", "custom_tool_call_output", "tool_result"}:
            call_id = node.get("call_id") or node.get("tool_use_id")
            observations.append({"kind": "result", "call_id": str(call_id) if call_id is not None else None, "failed": _failed(node), "preview": _preview(node.get("output", node.get("content")))})
    return observations


def _preview(value):
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text[:1000] + ("…" if len(text) > 1000 else "")


def _reference(value, kind="event"):
    return {"kind": kind, **{key: str(_get(value, key) or "") for key in
                            ("agent", "session_id", "event_id", "source_path", "record_key")}}


def _time(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    return value.astimezone(timezone.utc)


def analyze_task(snapshot, members):
    keys = {(_get(member, "agent"), _get(member, "session_id")) for member in members}
    calls, results, seen_events = {}, defaultdict(list), set()
    for index, event in enumerate(snapshot.get("events", [])):
        owner = (_get(event, "agent"), _get(event, "session_id"))
        if owner not in keys:
            continue
        identity = (*owner, _get(event, "event_id") or f"row:{index}")
        if identity in seen_events:
            continue
        seen_events.add(identity)
        for position, observation in enumerate(_get(event, "tool_observations", []) or []):
            call_id = observation.get("call_id")
            key = (*owner, call_id or f"event:{identity[-1]}:{position}")
            if observation.get("kind") == "call":
                calls.setdefault(key, (observation, event))
            elif call_id and observation.get("kind") == "result":
                results[key].append((observation, event))
    failed_groups, read_groups = defaultdict(list), defaultdict(list)
    for key, (call, event) in calls.items():
        if not call.get("signature"):
            continue
        group = (*key[:2], call["signature"])
        if call.get("is_read"):
            read_groups[group].append((call, [_reference(event)]))
        outputs = results.get(key, [])
        failures = [item for item in outputs if item[0].get("failed") is True]
        if failures and not any(item[0].get("failed") is False for item in outputs):
            failed_groups[group].append((call, [_reference(event), _reference(failures[0][1])]))
    signals = []
    for kind, groups, title, suggestion in (
        ("repeated_failure", failed_groups, "같은 도구 요청의 반복 실패", "재시도 전에 실행 환경과 오류 원인을 확인하기"),
        ("repeated_read", read_groups, "동일한 파일 조회 요청의 반복", "이미 확인한 내용을 요약해 두고 다시 읽어야 하는 이유를 확인하기"),
    ):
        for group, entries in groups.items():
            if len(entries) < 3:
                continue
            call = entries[0][0]
            signals.append({"signal_id": _digest([kind, group]), "kind": kind, "title": title,
                            "count": len(entries), "detail": f"{group[0]} · {group[1]}: {call['tool_name']} 요청 {len(entries)}건. {call.get('target', '')}",
                            "suggestion": suggestion, "evidence": [ref for _, refs in entries for ref in refs]})
    usage_groups, seen_usage = defaultdict(list), set()
    usage_count = known_count = 0
    for index, usage in enumerate(snapshot.get("usage", [])):
        owner = (_get(usage, "agent"), _get(usage, "session_id"))
        if owner not in keys:
            continue
        identity = (*owner, _get(usage, "event_id") or f"row:{index}")
        if identity in seen_usage:
            continue
        seen_usage.add(identity)
        usage_count += 1
        tokens = _get(usage, "input_tokens")
        if type(tokens) is not int or tokens < 0:
            continue
        known_count += 1
        timestamp, model = _time(_get(usage, "occurred_at")), _get(usage, "model")
        if timestamp is not None and model:
            usage_groups[(*owner, model)].append((timestamp, tokens, usage))
    for group, rows in usage_groups.items():
        rows.sort(key=lambda row: row[0])
        for before, after in zip(rows, rows[1:]):
            if before[0] >= after[0] or before[1] <= 0 or after[1] < max(before[1] * 3, before[1] + 4096):
                continue
            refs = [_reference(before[2], "usage"), _reference(after[2], "usage")]
            signals.append({"signal_id": _digest(["input_growth", group, refs, after[0]]), "kind": "input_growth",
                            "title": "입력 토큰의 큰 증가", "count": 1,
                            "detail": f"{group[0]} · {group[1]} · {group[2]}: 직전 확인 가능한 입력 {before[1]:,} → {after[1]:,} 토큰. 같은 세션·모델의 기록을 비교했습니다.",
                            "suggestion": "작업을 나누거나 제공할 파일과 문맥을 줄일 수 있는지 검토하기", "evidence": refs})
    return {"signals": sorted(signals, key=lambda item: (item["kind"], item["signal_id"])),
            "coverage": {"tool_calls": len(calls), "paired_results": sum(key in results for key in calls),
                         "known_inputs": known_count, "usage_events": usage_count}}
