"""Pure, deterministic view-model construction shared by dashboard pages."""
from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import fields, is_dataclass
import pandas as pd

from .adapter import clipped_duration_seconds, filtered_requests, filtered_sessions, filtered_usage, frame, record, weighted_cache_ratio
from agent_monitor.analysis import split_duration_by_day


def _union_seconds(rows, start, end):
    intervals = []
    for row in rows:
        left, right = row.get("started_at"), row.get("ended_at", row.get("last_activity"))
        if left is None or right is None: continue
        left, right = max(left, start), min(right, end)
        if right > left: intervals.append((left, right))
    intervals.sort(); merged = []
    for left, right in intervals:
        if merged and left <= merged[-1][1]: merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else: merged.append((left, right))
    return sum((right-left).total_seconds() for left, right in merged)


def _scalar_rows(values, omit=("own_usage", "child_usage", "usage")):
    rows=[]
    for value in values:
        if is_dataclass(value): rows.append({field.name:getattr(value,field.name) for field in fields(value) if field.name not in omit})
        elif isinstance(value,dict): rows.append({key:item for key,item in value.items() if key not in omit})
        else: rows.append(value)
    return rows


def _event_timestamp(value):
    """Return a UTC Timestamp, avoiding parser work for collector datetimes."""
    if isinstance(value, (datetime, pd.Timestamp)):
        stamp = pd.Timestamp(value)
        return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")
    return pd.to_datetime(value, errors="coerce", utc=True)


def build_view_data(snapshot: dict, state: dict) -> dict:
    start, end = state.get("start"), state.get("end")
    agents, projects, models = state.get("agents", ()), state.get("projects", ()), state.get("models", ())
    sessions = filtered_sessions(_scalar_rows(snapshot.get("sessions", [])), start, end, agents, projects)
    usage = filtered_usage(snapshot.get("usage", []), start, end, agents, projects, models, sessions)
    # Usage events from the collector are intentionally compact; enrich their
    # display/filter fields from the canonical composite session identity.
    canonical = frame(snapshot.get("sessions", []))
    # Never join compact usage by session ID alone: two agents may legitimately
    # reuse it.  It is enriched only when its (session, turn) maps uniquely.
    if not usage.empty and {"session_id", "turn_id"} <= set(usage) and not canonical.empty:
        candidates = frame(snapshot.get("requests", []))
        if {"session_id", "turn_id", "agent"} <= set(candidates):
            if "agent" not in usage: usage["agent"] = pd.NA
            for index, row in usage[usage.agent.isna()].iterrows():
                pool = candidates[(candidates.session_id.astype(str)==str(row.session_id)) & (candidates.turn_id.astype(str)==str(row.turn_id))]
                source = row.get("source_path")
                if source and "source_path" in pool:
                    exact = pool[pool.source_path.astype(str)==str(source)]
                    if exact.agent.nunique() == 1: pool = exact
                if pool.agent.nunique() == 1: usage.at[index,"agent"] = pool.agent.iloc[0]
    if not usage.empty and not canonical.empty and {"agent", "session_id"} <= set(usage) and {"agent", "session_id"} <= set(canonical):
        usage = usage[usage.agent.notna()].copy()
        fields = [name for name in ("agent", "session_id", "project") if name in canonical]
        usage = usage.drop(columns=["project"], errors="ignore").merge(canonical[fields], on=["agent", "session_id"], how="left")
    # Only history renders/exports transcript events.  Other pages avoid a
    # potentially large event DataFrame entirely.
    if not state.get("include_events", True):
        events = pd.DataFrame()
    else:
        # Avoid recursively materializing every transcript event on each dashboard
    # rerun.  Filter lightweight dataclasses/mappings first.
        selected_keys={(str(row.agent),str(row.session_id)) for row in sessions.itertuples() if hasattr(row,"agent")}
        raw_events=[]
        left_bound = pd.Timestamp(start).tz_localize("UTC") if start is not None and pd.Timestamp(start).tzinfo is None else (pd.Timestamp(start).tz_convert("UTC") if start is not None else None)
        right_bound = pd.Timestamp(end).tz_localize("UTC") if end is not None and pd.Timestamp(end).tzinfo is None else (pd.Timestamp(end).tz_convert("UTC") if end is not None else None)
        for event in snapshot.get("events", []):
            # `record` is shallow: provenance/raw location fields remain
            # available without expanding transcript payloads.
            value = record(event)
            at = _event_timestamp(value.get("occurred_at"))
            if left_bound is not None and (pd.isna(at) or at < left_bound): continue
            if right_bound is not None and (pd.isna(at) or at >= right_bound): continue
            if agents and value.get("agent") not in agents: continue
            if models and value.get("model") not in models: continue
            if projects and (str(value.get("agent")),str(value.get("session_id"))) not in selected_keys: continue
            raw_events.append(value)
        events = frame(raw_events)
    if not events.empty:
        if start is not None: events = events[events.occurred_at.notna() & (events.occurred_at >= start)]
        if end is not None: events = events[events.occurred_at.notna() & (events.occurred_at < end)]
        for name, selected in (("agent", agents), ("model", models)):
            if selected and name in events: events = events[events[name].isin(selected)]
        if projects:
            allowed = {(str(row.agent), str(row.session_id)) for row in sessions.itertuples() if hasattr(row, "agent")}
            if {"agent", "session_id"} <= set(events): events = events[events.apply(lambda row: (str(row.agent), str(row.session_id)) in allowed, axis=1)]
    requests = filtered_requests(snapshot.get("requests", []), start, end, agents, sessions)
    if not usage.empty and {"input_tokens", "output_tokens"} <= set(usage):
        missing = usage.total_tokens.isna() if "total_tokens" in usage else pd.Series(True, index=usage.index)
        if "total_tokens" not in usage: usage["total_tokens"] = pd.NA
        valid = missing & usage.input_tokens.notna() & usage.output_tokens.notna()
        usage.loc[valid,"total_tokens"] = usage.loc[valid,"input_tokens"] + usage.loc[valid,"output_tokens"]
    # Requests are scalar presentation rows.  Attach usage only on the exact
    # source-qualified request identity; ambiguous compact usage is left unknown.
    if not requests.empty:
        requests = requests.copy()
        for name in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens", "total_tokens"):
            requests[name] = pd.NA
        request_keys = {(str(row.agent), str(row.session_id), str(row.turn_id)) for row in requests.itertuples() if hasattr(row, "agent") and hasattr(row, "turn_id")}
        aggregates = {}
        for row in usage.to_dict("records"):
            key = (str(row.get("agent")), str(row.get("session_id")), str(row.get("turn_id")))
            if key not in request_keys: continue
            bucket = aggregates.setdefault(key, [])
            bucket.append(row)
        for index, request in requests.iterrows():
            key = (str(request.get("agent")), str(request.get("session_id")), str(request.get("turn_id")))
            rows = aggregates.get(key, [])
            for name in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens", "total_tokens"):
                known = [row.get(name) for row in rows if pd.notna(row.get(name))]
                if known: requests.at[index, name] = sum(known)
            if pd.isna(requests.at[index, "total_tokens"]) and pd.notna(requests.at[index,"input_tokens"]) and pd.notna(requests.at[index,"output_tokens"]):
                requests.at[index,"total_tokens"] = requests.at[index,"input_tokens"] + requests.at[index,"output_tokens"]
        requests["cache_read_ratio"] = pd.NA
        for index, request in requests.iterrows():
            key = (str(request.get("agent")), str(request.get("session_id")), str(request.get("turn_id")))
            paired = [row for row in aggregates.get(key, []) if pd.notna(row.get("input_tokens")) and pd.notna(row.get("cache_read_tokens"))]
            paired_input = sum(row["input_tokens"] for row in paired)
            if paired_input: requests.at[index,"cache_read_ratio"] = sum(row["cache_read_tokens"] for row in paired) / paired_input
        if start is not None and end is not None and {"started_at", "ended_at"} <= set(requests):
            left=requests.started_at.clip(lower=start); right=requests.ended_at.clip(upper=end)
            requests["clipped_duration_seconds"]=(right-left).dt.total_seconds().where(right>left)
    totals = {name: usage[name].sum(min_count=1) if name in usage else None for name in ("input_tokens", "output_tokens", "total_tokens")}
    duration_rows = requests.to_dict("records") if not requests.empty else []
    graph = snapshot.get("orchestration", {})
    own = {}
    if not usage.empty:
        for key, group in usage.groupby(["agent", "session_id"]): own[tuple(key)] = group.to_dict("records")
    children = {tuple(k): [tuple(c) for c in v] for k, v in graph.get("children", {}).items()}
    def descendants(key, seen=frozenset()):
        if key in seen: return set()
        return {key} | set().union(*(descendants(child, seen | {key}) for child in children.get(key, [])))
    rollups = {}
    request_records = requests.to_dict("records")
    for key in set(graph.get("depths", {})) | set(own):
        nodes = descendants(key); rows = [row for node in nodes for row in own.get(node, [])]
        unique_map = {f"{row.get('agent')}:{row.get('session_id')}:{row.get('event_id') or f'{row.get('turn_id')}:{row.get('record_key')}'}": row for row in rows}
        unique = unique_map.values()
        totals_known = [row.get("total_tokens") for row in unique if pd.notna(row.get("total_tokens"))]
        unique = list(unique); paired = [row for row in unique if pd.notna(row.get("input_tokens")) and pd.notna(row.get("cache_read_tokens"))]
        input_total = sum(row["input_tokens"] for row in paired)
        own_rows = [row for event,row in unique_map.items() if (row.get("agent"), str(row.get("session_id"))) == key]
        desc_rows = [row for event,row in unique_map.items() if (row.get("agent"), str(row.get("session_id"))) != key]
        own_known = [row.get("total_tokens") for row in own_rows if pd.notna(row.get("total_tokens"))]
        desc_known = [row.get("total_tokens") for row in desc_rows if pd.notna(row.get("total_tokens"))]
        request_rows = [row for row in request_records if (row.get("agent"), str(row.get("session_id"))) in nodes]
        rollups[key] = {"own_total": sum(own_known) if own_known else None,
                        "descendant_total": sum(desc_known) if desc_known else None,
                        "total_tokens": sum(totals_known) if totals_known else None,
                        "cache_read_ratio": sum(row["cache_read_tokens"] for row in paired) / input_total if input_total else None,
                        "coverage": {"known_total_events": len(totals_known), "usage_events": len(unique)},
                        "duration_seconds": _union_seconds(request_rows, start, end) if start and end else None}
    tz = snapshot.get("timezone", "UTC")
    daily = usage.copy()
    if not daily.empty and "occurred_at" in daily:
        daily["date"] = daily.occurred_at.dt.tz_convert(tz).dt.date
        daily = daily.groupby("date")[[name for name in ("input_tokens","output_tokens","cache_read_tokens","cache_creation_tokens","total_tokens") if name in daily]].sum(min_count=1).reset_index()
    daily_request_duration=pd.DataFrame(columns=["date","duration_seconds"])
    if not requests.empty and "clipped_duration_seconds" in requests:
        rows=[]; zone=tz
        for row in requests.dropna(subset=["started_at","ended_at"]).to_dict("records"):
            left=max(row["started_at"],start); right=min(row["ended_at"],end)
            left_dt = left.to_pydatetime() if hasattr(left, "to_pydatetime") else left
            right_dt = right.to_pydatetime() if hasattr(right, "to_pydatetime") else right
            for date, seconds in split_duration_by_day(left_dt, right_dt, zone).items():
                rows.append({"date":date,"duration_seconds":seconds})
        if rows: daily_request_duration=pd.DataFrame(rows).groupby("date").duration_seconds.sum().reset_index()
    request_duration=requests.get("clipped_duration_seconds",pd.Series(dtype=float)).sum(min_count=1)
    summary={**totals, "cache_read_ratio": weighted_cache_ratio(usage), "request_duration_seconds": None if pd.isna(request_duration) else float(request_duration), "union_duration_seconds": _union_seconds(duration_rows, start, end) if start and end else None}
    return {"sessions_df": sessions, "requests_df": requests, "usage_df": usage, "events_df": events, "summary": summary, "daily": daily, "daily_request_duration":daily_request_duration, "graph_view": {"context": graph, "own": own, "rollups": rollups}, "export_frames": {"sessions": sessions, "requests": requests, "usage": usage, "events": events}}
