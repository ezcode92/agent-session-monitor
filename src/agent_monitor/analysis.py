from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Iterable
from zoneinfo import ZoneInfo

from .models import ParseResult, Session, Turn, Usage


TOKEN_FIELDS = ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_creation_tokens', 'reasoning_tokens', 'total_tokens')


def orchestration_graph(result: ParseResult, start: datetime | None = None, end: datetime | None = None, models: Iterable[str] | None = None) -> dict:
    """Canonical session graph based only on parser-provided explicit parents."""
    if start or end or models:
        result = filter_data(result, start=start, end=end, models=models)
    sessions = {(session.agent, session.session_id): session for session in result.sessions}
    children: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list); edges = []; placeholders = []
    missing = 0
    for key, session in sessions.items():
        if session.parent_session_id:
            parent = (session.agent, str(session.parent_session_id))
            evidence = {'child': key, 'parent': parent, 'source_path': session.source_path, 'source_label': session.source_label, 'source_kind': session.source_kind}
            if parent in sessions: children[parent].append(key); edges.append(evidence)
            else: missing += 1; placeholders.append(parent); edges.append({**evidence, 'missing_parent': True})
    roots = [key for key, session in sessions.items() if not session.parent_session_id or (session.agent, str(session.parent_session_id)) not in sessions]
    depths, cycles = {}, set()
    def depth(key, trail=()):
        nonlocal cycles
        if key in trail:
            cycles.add(tuple(sorted((*trail[trail.index(key):], key)))); return 0
        session = sessions[key]; parent = (session.agent, str(session.parent_session_id)) if session.parent_session_id else None
        return 0 if parent not in sessions else 1 + depth(parent, (*trail, key))
    for key in sessions: depths[key] = depth(key)
    usages = defaultdict(dict)
    for turn in result.turns:
        agent = turn.agent or next((s.agent for s in result.sessions if s.session_id == turn.session_id), '')
        for usage in turn.usage:
            usages[(agent, turn.session_id)][usage.event_id or f'{turn.turn_id}:{usage.record_key}'] = usage
    def subtree(key, visited=frozenset()):
        if key in visited: return set()
        return {key} | set().union(*(subtree(child, visited | {key}) for child in children.get(key, [])))
    rollups = {}
    for key in sessions:
        ids = subtree(key); unique = {event: usage for node in ids for event, usage in usages[node].items()}
        known_total = [usage.total_tokens for usage in unique.values() if usage.total_tokens is not None]
        known_cache = [usage.cache_read_tokens for usage in unique.values() if usage.cache_read_tokens is not None]
        paired_cache = [usage for usage in unique.values() if usage.input_tokens is not None and usage.cache_read_tokens is not None]
        token_total = sum(known_total) if known_total else None
        cache_total = sum(known_cache) if known_cache else None
        intervals = sorted((sessions[node].started_at, sessions[node].last_activity_at) for node in ids if sessions[node].started_at and sessions[node].last_activity_at)
        merged = []
        for left, right in intervals:
            if merged and left <= merged[-1][1]: merged[-1] = (merged[-1][0], max(merged[-1][1], right))
            else: merged.append((left, right))
        duration = sum((right - left).total_seconds() for left, right in merged)
        paired_input = sum(usage.input_tokens for usage in paired_cache)
        rollups[key] = {'session_count': len(ids), 'usage_event_count': len(unique), 'known_total_events': len(known_total), 'known_cache_events': len(known_cache), 'total_tokens': token_total, 'cache_read_tokens': cache_total, 'cache_read_ratio': (sum(usage.cache_read_tokens for usage in paired_cache) / paired_input) if paired_input else None, 'duration_seconds': duration}
    return {'roots': roots, 'children': dict(children), 'edges': edges, 'missing_placeholders': placeholders, 'depths': depths, 'rollups': rollups, 'relation_count': sum(len(items) for items in children.values()), 'missing_parent_count': missing, 'cycle_count': len(cycles)}


def filter_data(result: ParseResult, start: datetime | None = None, end: datetime | None = None, agents: Iterable[str] | None = None, projects: Iterable[str] | None = None, models: Iterable[str] | None = None) -> ParseResult:
    allowed_agents, allowed_projects, allowed_models = set(agents or []), set(projects or []), set(models or [])
    base = [s for s in result.sessions if (not allowed_agents or s.agent in allowed_agents) and (not allowed_projects or s.project in allowed_projects)]
    keys = {(s.agent, s.session_id) for s in base}
    turns = []
    for turn in result.turns:
        turn_agent = turn.agent or next((s.agent for s in base if s.session_id == turn.session_id), None)
        if (turn_agent, turn.session_id) not in keys: continue
        copy = deepcopy(turn)
        copy.usage[:] = [u for u in copy.usage if (not allowed_models or u.model in allowed_models) and (not start or (u.occurred_at is not None and u.occurred_at >= start)) and (not end or (u.occurred_at is not None and u.occurred_at < end))]
        session = next((s for s in base if s.agent == turn_agent and s.session_id == turn.session_id), None)
        overlaps = session and (not start or (session.last_activity_at and session.last_activity_at >= start)) and (not end or (session.started_at and session.started_at < end))
        if copy.usage or (not start and not end) or (copy.user_preview and overlaps): turns.append(copy)
    active_keys = {(t.agent or next((s.agent for s in base if s.session_id == t.session_id), None), t.session_id) for t in turns}
    sessions = [deepcopy(s) for s in base if (s.agent, s.session_id) in active_keys]
    events = [deepcopy(e) for e in result.events if (e.agent, e.session_id) in active_keys and (not start or (e.occurred_at is not None and e.occurred_at >= start)) and (not end or (e.occurred_at is not None and e.occurred_at < end))]
    return ParseResult(sessions, turns, result.diagnostics, result.raw_records, events)


def _sum_known(values: list[Usage], field: str) -> int | None:
    known = [getattr(v, field) for v in values if getattr(v, field) is not None]
    return sum(known) if known else None


def analyze(result: ParseResult, tz_name: str = 'UTC') -> dict:
    usages = [u for t in result.turns for u in t.usage]
    totals = {field: _sum_known(usages, field) for field in TOKEN_FIELDS}
    known_input = [u for u in usages if u.input_tokens is not None and u.cache_read_tokens is not None]
    cache_ratio = (sum(u.cache_read_tokens or 0 for u in known_input) / sum(u.input_tokens or 0 for u in known_input)) if sum(u.input_tokens or 0 for u in known_input) else None
    return {'sessions': len(result.sessions), 'requests': len(result.turns), 'usage': totals, 'cache_read_ratio': cache_ratio,
            'known_usage_events': len([u for u in usages if u.total_tokens is not None]), 'usage_events': len(usages),
            'diagnostics': result.diagnostics, 'timezone': tz_name}


def interval_for_dates(start_date, end_date, tz_name: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    start = datetime.combine(start_date, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
    return start, end


def split_duration_by_day(start: datetime, end: datetime, tz_name: str) -> dict[str, float]:
    if end <= start: return {}
    zone = ZoneInfo(tz_name); cursor = start; result: dict[str, float] = defaultdict(float)
    while cursor < end:
        local = cursor.astimezone(zone); next_midnight = datetime.combine(local.date() + timedelta(days=1), datetime.min.time(), tzinfo=zone).astimezone(timezone.utc)
        boundary = min(end, next_midnight); result[local.date().isoformat()] += (boundary - cursor).total_seconds(); cursor = boundary
    return dict(result)


def report(result: ParseResult, tz_name: str = 'UTC') -> str:
    summary = analyze(result, tz_name)
    return '\n'.join([f"# Agent Monitor report", f"Sessions: {summary['sessions']}", f"Requests: {summary['requests']}", f"Known usage events: {summary['known_usage_events']}/{summary['usage_events']}"])


def download_data(result: ParseResult) -> list[dict]:
    rows = []
    for turn in result.turns:
        for usage in turn.usage:
            row = {'session_id': turn.session_id, 'turn_id': turn.turn_id, 'started_at': turn.started_at, 'status': turn.status, 'model': usage.model, 'source': usage.source, 'provenance': usage.source_path}
            row.update({field: getattr(usage, field) for field in TOKEN_FIELDS}); rows.append(row)
    return rows
