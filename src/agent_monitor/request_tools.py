"""Read-only request tool history from explicit request/call identities."""
from collections import defaultdict
from datetime import datetime, timezone


def _value(event, key, default=None):
    return event.get(key, default) if isinstance(event, dict) else getattr(event, key, default)


def _ref(event, observation):
    return {key: _value(event, key) for key in
            ("agent", "session_id", "turn_id", "event_id", "occurred_at", "source_path", "record_key")} | {
                "preview": observation.get("preview") or observation.get("target") or "",
                "failed": observation.get("failed"),
            }


def _order(item):
    stamp = (item["calls"] or item["results"])[0]["occurred_at"]
    if isinstance(stamp, str):
        try:
            stamp = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            stamp = None
    if not isinstance(stamp, datetime) or stamp.tzinfo is None:
        stamp = datetime.max.replace(tzinfo=timezone.utc)
    return stamp, item["order"]


def request_tool_history(events, agent, session_id, turn_id):
    """Pair within a session by call ID; ambiguous/missing IDs stay unpaired.

    The selected request owns its calls. A delayed result can be recorded after
    the next request boundary, but only an unambiguous call ID can link it back.
    Never assign a call to a request using overlapping observed time intervals.
    """
    calls, outputs, seen, repeated = [], [], set(), {}
    unassigned = 0
    for index, event in enumerate(events):
        if (_value(event, "agent"), str(_value(event, "session_id"))) != (agent, str(session_id)):
            continue
        identity = _value(event, "event_id") or (_value(event, "source_path"), _value(event, "record_key"), index)
        if identity in seen:
            continue
        seen.add(identity)
        owner = _value(event, "turn_id")
        owner = str(owner) if owner is not None else None
        for position, observation in enumerate(_value(event, "tool_observations", []) or []):
            call_id = observation.get("call_id")
            call_id = str(call_id) if call_id is not None else None
            ref = _ref(event, observation)
            if observation.get("kind") == "call":
                if owner is None:
                    unassigned += 1
                key = (owner, call_id, observation.get("signature"))
                if call_id and observation.get("signature") and key in repeated:
                    repeated[key]["calls"].append(ref)
                    continue
                entry = {"turn_id": owner, "call_id": call_id, "tool_name": observation.get("tool_name") or "미확인",
                         "calls": [ref], "results": [], "order": (index, position)}
                calls.append(entry)
                if call_id and observation.get("signature"):
                    repeated[key] = entry
            elif observation.get("kind") == "result":
                outputs.append((owner, call_id, ref, (index, position)))
    by_id = defaultdict(list)
    for call in calls:
        if call["call_id"] is not None:
            by_id[call["call_id"]].append(call)
    orphans = []
    for owner, call_id, ref, order in outputs:
        candidates = by_id.get(call_id, []) if call_id is not None else []
        exact = [call for call in candidates if owner is not None and call["turn_id"] == owner]
        possible = exact or candidates
        if len(possible) == 1:
            possible[0]["results"].append(ref)
        elif owner == str(turn_id):
            orphans.append({"turn_id": owner, "call_id": call_id, "tool_name": "미확인", "calls": [],
                            "results": [ref], "order": order,
                            "status": "호출 연결 모호" if possible else "호출 미확인"})
    selected = [call for call in calls if call["turn_id"] == str(turn_id)]
    for call in selected:
        states = [ref["failed"] for ref in call["results"]]
        call["status"] = ("결과 미확인" if not states else "실패 포함" if True in states else
                          "성공" if all(state is False for state in states) else "성공 여부 미확인")
    return {"items": sorted([*selected, *orphans], key=_order),
            "unassigned_calls": unassigned}
