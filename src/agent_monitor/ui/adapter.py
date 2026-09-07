"""Mapping helpers used by the Streamlit presentation layer."""
from __future__ import annotations
from dataclasses import fields, is_dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import PurePath
from typing import Any, Iterable
import json
import pandas as pd

USAGE_COLUMNS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens", "total_tokens")

def record(value: Any) -> dict[str, Any]:
    if value is None: return {}
    if is_dataclass(value): return {field.name:getattr(value,field.name) for field in fields(value)}
    if isinstance(value, dict): return dict(value)
    return {name: getattr(value, name) for name in dir(value) if not name.startswith("_") and not callable(getattr(value, name))}

def records(values: Any) -> list[dict[str, Any]]:
    if values is None: return []
    if isinstance(values, pd.DataFrame): return values.to_dict("records")
    if isinstance(values, dict): return [record(values)]
    return [record(value) for value in values]

def get(value: dict[str, Any], *names: str, default: Any = None) -> Any:
    return next((value[name] for name in names if value.get(name) is not None), default)

def source_label(value: Any) -> str:
    item = record(value); path = str(get(item, "source_path", "path", default="") or "").replace("\\", "/").lower()
    for label in ("antigravity-cli", "antigravity-ide", "antigravity"):
        if f"/{label}/" in f"/{path.strip('/')}" or path.endswith(f"/{label}"): return label
    return str(get(item, "source_label", "agent", "source", default="unknown") or "unknown").split(".", 1)[0]

def source_kind(value: Any) -> str:
    item = record(value)
    return str(get(item, "source_kind", default="") or PurePath(str(get(item, "source_path", "path", default="") or "")).suffix.lstrip(".") or "unknown")

def frame(values: Any) -> pd.DataFrame:
    data = pd.DataFrame(records(values))
    for old, new in {"last_activity_at":"last_activity", "user_preview":"title", "data_quality":"data_status", "display":"message"}.items():
        if old in data and new not in data: data[new] = data[old]
    if not data.empty and ("source_label" not in data or "source_kind" not in data):
        rows = data.to_dict("records")
        if "source_label" not in data: data["source_label"] = [source_label(row) for row in rows]
        if "source_kind" not in data: data["source_kind"] = [source_kind(row) for row in rows]
    for name in ("occurred_at", "started_at", "ended_at", "last_activity", "timestamp"):
        if name in data: data[name] = pd.to_datetime(data[name], errors="coerce", utc=True)
    return data

def usage_total(item: dict[str, Any]) -> int | None:
    total = get(item, "total_tokens", "total")
    if total is not None and not pd.isna(total): return int(total)
    # Cache reads are a subset of input in normalized collector records, so
    # adding them again would inflate a fallback total.
    input_tokens, output_tokens = get(item, "input_tokens"), get(item, "output_tokens")
    if input_tokens is None or output_tokens is None or pd.isna(input_tokens) or pd.isna(output_tokens): return None
    return int(input_tokens) + int(output_tokens)

def usage_label(value: int | float | None) -> str: return "—" if value is None or pd.isna(value) else f"{int(value):,}"

def period_bounds(choice: str, start=None, end=None, now: datetime | None=None, tz_name: str = "UTC"):
    zone = ZoneInfo(tz_name)
    now = (now or datetime.now(timezone.utc)).astimezone(zone); day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if choice == "오늘": left, right = day, day + timedelta(days=1)
    elif choice == "최근 30일": left, right = day - timedelta(days=29), day + timedelta(days=1)
    elif choice == "직접 선택" and start and end: left, right = datetime.combine(start, datetime.min.time(), tzinfo=zone), datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    else: left, right = day - timedelta(days=6), day + timedelta(days=1)
    return left.astimezone(timezone.utc), right.astimezone(timezone.utc)

def filtered_sessions(sessions, start, end, agents=(), projects=(), models=()):
    """Filter session metadata only.

    Model and period are usage-event filters in the dashboard.  Sessions with
    no usage must remain visible, so neither may exclude a session here.
    """
    data = frame(sessions)
    if data.empty: return data
    for name, selected in (("agent",agents),("project",projects)):
        if selected and name in data: data = data[data[name].isin(selected)]
    if start is not None and end is not None and {"started_at", "last_activity"} <= set(data):
        data = data[data.started_at.notna() & data.last_activity.notna() & (data.last_activity >= start) & (data.started_at < end)]
    return data.copy()


def _selected_session_mask(data: pd.DataFrame, selected: pd.DataFrame) -> pd.Series:
    """Match canonical agent/session pairs without row-wise Python calls.

    Older records without an agent keep the legacy session-ID membership path.
    Empty selected data remains an empty selection rather than becoming "all".
    """
    if selected.empty:
        return pd.Series(False, index=data.index)
    paired = {"agent", "session_id"} <= set(data) and {"agent", "session_id"} <= set(selected)
    if paired and data["agent"].notna().any() and selected["agent"].notna().any():
        allowed_rows = selected.dropna(subset=["agent", "session_id"])
        allowed = pd.MultiIndex.from_frame(allowed_rows[["agent", "session_id"]].astype(str))
        values = pd.MultiIndex.from_arrays([data["agent"].astype("string").fillna(""), data["session_id"].astype(str)])
        return pd.Series(values.isin(allowed), index=data.index)
    allowed = set(selected.get("session_id", pd.Series(dtype=str)).dropna().astype(str))
    return data["session_id"].astype(str).isin(allowed)

def filtered_requests(requests, start=None, end=None, agents=(), sessions=None):
    data = frame(requests)
    if data.empty: return data
    if sessions is not None and "session_id" in data:
        selected = frame(sessions)
        data = data[_selected_session_mask(data, selected)]
    if start is not None and "ended_at" in data: data = data[data.ended_at.notna() & (data.ended_at >= start)]
    if end is not None and "started_at" in data: data = data[data.started_at.notna() & (data.started_at < end)]
    if agents and "agent" in data: data = data[data.agent.isin(agents)]
    return data.copy()

def filtered_usage(usage, start=None, end=None, agents=(), projects=(), models=(), sessions=None):
    """Apply every dashboard filter at the normalized usage-event level."""
    data = frame(usage)
    if data.empty:
        return data
    if sessions is not None and "session_id" in data:
        selected = frame(sessions)
        data = data[_selected_session_mask(data, selected)]
    if start is not None and "occurred_at" in data:
        data = data[data.occurred_at.notna() & (data.occurred_at >= start)]
    if end is not None and "occurred_at" in data:
        data = data[data.occurred_at.notna() & (data.occurred_at < end)]
    for name, selected in (("agent", agents), ("project", projects), ("model", models)):
        if selected and name in data:
            data = data[data[name].isin(selected)]
    return data.copy()

def clipped_duration_seconds(sessions, start, end) -> pd.Series:
    data = frame(sessions)
    if not {"started_at", "last_activity"} <= set(data):
        return pd.Series(dtype=float)
    left = data.started_at.clip(lower=start)
    right = data.last_activity.clip(upper=end)
    return (right - left).dt.total_seconds().where(right > left).dropna()

def weighted_cache_ratio(usage) -> float | None:
    data = frame(usage)
    if not {"input_tokens", "cache_read_tokens"} <= set(data):
        return None
    paired = data.dropna(subset=["input_tokens", "cache_read_tokens"])
    total_input = paired.input_tokens.sum()
    return float(paired.cache_read_tokens.sum() / total_input) if total_input else None

def subtree_keys(graph: dict[str, Any], root) -> list:
    """Traverse only the service graph, at arbitrary depth and cycle-safe."""
    result, pending, seen = [], [tuple(root)], set()
    children = graph.get("children", {})
    while pending:
        key = pending.pop(0)
        if key in seen:
            continue
        seen.add(key); result.append(key)
        pending.extend(tuple(child) for child in children.get(key, []))
    return result

def export_csv(items) -> bytes: return frame(items).to_csv(index=False).encode("utf-8-sig")

def event_is_noise(event: dict[str, Any]) -> bool:
    row = record(event); text = str(get(row, "display", "message", default="")).strip().lower(); role = str(get(row, "role", "type", default="")).lower()
    event_type = str(row.get("event_type", "")).lower()
    return not text or text in {"ping", "heartbeat"} or role in {"system", "developer", "metadata", "reasoning"} or event_type in {"session_meta", "turn_context", "token_usage_record", "token_count"}

def event_rows(events, hide_noise=True):
    rows = records(events)
    for row in rows:
        role = str(get(row, "role", "type", default="")).lower()
        if role in {"tool", "tool_result"}:
            text = str(get(row, "display", "message", default="")); row["display"] = (text[:240] + "…") if len(text) > 240 else text
    return [row for row in rows if not hide_noise or not event_is_noise(row)]

def append_unique(buffer, incoming) -> int:
    known = {str(row.get("event_id") or json.dumps(row, default=str, sort_keys=True)) for row in buffer}; added = 0
    for value in incoming:
        row = record(value); key = str(row.get("event_id") or json.dumps(row, default=str, sort_keys=True))
        if key not in known: buffer.append(row); known.add(key); added += 1
    return added

def recent_records(buffer, limit=200): return buffer[-max(1, limit):]

def append_bounded(buffer, incoming, maximum=2000) -> int:
    """Keep a bounded live buffer while preserving the newest unique events."""
    added = append_unique(buffer, incoming)
    if len(buffer) > maximum:
        del buffer[:-maximum]
    return added

def monitor_view(buffer, frozen=None, limit=200, follow=True):
    """Pause uses its captured view; follow controls only presentation ordering."""
    rows = recent_records(frozen if frozen is not None else buffer, limit)
    return rows if follow else list(reversed(rows))

def hierarchy_rows(sessions) -> list[dict[str, Any]]:
    """Build a display hierarchy from the stable session parent contract."""
    rows = records(sessions); ids = {str(row.get("session_id")) for row in rows}
    for row in rows:
        parent = row.get("parent_session_id")
        row["parent_session_id"] = parent
        row["depth"] = 1 if parent and str(parent) in ids else 0
        row["relationship"] = "child" if row["depth"] else "root"
    return rows

def filter_events(events, start=None, end=None, agents=(), models=()):
    """Apply UI filters without treating an empty selected-session set as all."""
    data = frame(events)
    if data.empty: return data
    if start is not None and "occurred_at" in data: data = data[data.occurred_at.isna() | (data.occurred_at >= start)]
    if end is not None and "occurred_at" in data: data = data[data.occurred_at.isna() | (data.occurred_at < end)]
    if agents and "agent" in data: data = data[data.agent.isin(agents)]
    if models and "model" in data: data = data[data.model.isin(models)]
    return data.copy()

def monitor_cursor(events, cursor=None, generation=None):
    """Return only records after the opaque cursor and the newest cursor."""
    rows = records(events)
    prior_generation = cursor.get("generation") if isinstance(cursor, dict) else None
    token = cursor.get("event_id") if isinstance(cursor, dict) else cursor
    # A collector revision can replace/truncate the file.  Reset the opaque
    # cursor rather than suppressing newly reconstructed events.
    if generation is not None and prior_generation is not None and generation != prior_generation: token = None
    index = next((i for i, row in enumerate(rows) if str(row.get("event_id")) == str(token)), -1) if token else -1
    fresh = rows[index + 1:]
    latest = str(rows[-1].get("event_id")) if rows else token
    return fresh, ({"event_id": latest, "generation": generation} if generation is not None else latest)

def lazy_preview(event: dict[str, Any], maximum: int = 2000) -> str:
    """Never fetch raw content; cap the already-normalized display preview."""
    text = str(get(record(event), "display", "message", default=""))
    return text if len(text) <= maximum else text[:maximum] + "…"

def prior_period(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """The immediately preceding interval, preserving the selected duration."""
    return start - (end - start), start

def comparison_summary(current: pd.DataFrame, previous: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    current_total = current.get("total_tokens", pd.Series(dtype=float)).sum(min_count=1)
    previous_total = previous.get("total_tokens", pd.Series(dtype=float)).sum(min_count=1)
    current_value = None if pd.isna(current_total) else int(current_total)
    previous_value = None if pd.isna(previous_total) else int(previous_total)
    delta = None if current_value is None or previous_value is None else current_value - previous_value
    direction = "비교할 사용량이 부족합니다" if delta is None else ("증가" if delta > 0 else "감소" if delta < 0 else "동일")
    table = pd.DataFrame({"항목":["선택 기간 토큰","직전 동일 기간 토큰","증감"], "값":[current_value, previous_value, delta]})
    return table, f"토큰 사용량은 {direction}" + (f" ({delta:+,})" if delta is not None else "") + "."
