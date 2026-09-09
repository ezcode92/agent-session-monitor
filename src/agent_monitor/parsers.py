from __future__ import annotations

import json
import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .discovery import SourceFile
from .insights import tool_observations
from .models import Diagnostic, LogEvent, ParseResult, Session, Turn, Usage

PARSER_VERSION = '5'


def _provenance(source: SourceFile, session: Session, usages: list[Usage] | None = None) -> None:
    """Attach source data consistently after a parser has built its objects."""
    label, kind, path = source.source_label or source.agent, source.source_kind or source.agent, str(source.path)
    session.source_path = path
    session.source_label, session.source_kind = label, kind
    session.sources = list(dict.fromkeys([*session.sources, path]))
    for usage in usages or []:
        usage.source_path, usage.source_label, usage.source_kind = path, label, kind
        if not usage.event_id:
            stable = usage.response_id or usage.record_key or ''
            usage.event_id = f'{session.agent}:{session.session_id}:{usage.source}:{stable}'
        usage.agent = session.agent


def _time(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / (1000 if value > 10_000_000_000 else 1), timezone.utc)
    if not isinstance(value, str): return None
    try: return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except ValueError: return None


def _first(d: dict, *names: str) -> Any:
    for name in names:
        if name in d and d[name] is not None: return d[name]
    return None


def _integer(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


def _text(value: Any) -> str | None:
    """Normalize provider content blocks without discarding their text."""
    if isinstance(value, str): return value
    if isinstance(value, list):
        parts = [_text(item.get('text', item.get('content'))) for item in value if isinstance(item, dict)]
        return '\n'.join(part for part in parts if part) or None
    if isinstance(value, dict): return _text(value.get('text', value.get('content')))
    return None


def _usage(data: dict, source: str, record_key: str, at: datetime | None, response_id: str | None = None, claude: bool = False) -> Usage:
    cache_read = _integer(_first(data, 'cache_read_input_tokens', 'cached_input_tokens', 'cache_read_tokens'))
    cache_create = _integer(_first(data, 'cache_creation_input_tokens', 'cache_creation_tokens'))
    raw_input = _integer(_first(data, 'input_tokens', 'input'))
    # Claude's input_tokens excludes both cache fields. Codex cached_input_tokens is a subset.
    input_tokens = (raw_input + (cache_read or 0) + (cache_create or 0)) if claude and raw_input is not None else raw_input
    output = _integer(_first(data, 'output_tokens', 'output'))
    reasoning = _integer(_first(data, 'reasoning_tokens'))
    total = _integer(_first(data, 'total_tokens', 'total'))
    if total is None and input_tokens is not None and output is not None: total = input_tokens + output
    return Usage(input_tokens, output, cache_read, cache_create, reasoning, total, source, response_id, record_key, at,
                 model=_first(data, 'model', 'model_name'))


def _records(source: SourceFile, diagnostics: list[Diagnostic]) -> list[tuple[int, dict]]:
    result = []
    try:
        with source.path.open(encoding='utf-8') as file:
            for number, line in enumerate(file, 1):
                if not line.strip(): continue
                try: value = json.loads(line)
                except json.JSONDecodeError:
                    diagnostics.append(Diagnostic(str(source.path), 'invalid_json', 'JSONL record skipped', str(number))); continue
                if isinstance(value, dict): result.append((number, value))
    except OSError as exc:
        diagnostics.append(Diagnostic(str(source.path), 'unreadable', str(exc)))
    return result


def _event_records(source: SourceFile, sid: str, records: list[tuple[int, dict]], event_turns=None) -> list[LogEvent]:
    label, kind, path = source.source_label or source.agent, source.source_kind or source.agent, str(source.path)
    events = []
    for line, record in records:
        at = _time(_first(record, 'timestamp', 'time', 'created_at') or _first(record.get('payload', {}), 'timestamp'))
        body = record.get('payload') if isinstance(record.get('payload'), dict) else record
        message = body.get('message', record.get('message', {}))
        item = body.get('item') if isinstance(body.get('item'), dict) else {}
        role = body.get('role') or item.get('role') or (message.get('role') if isinstance(message, dict) else None) or body.get('type') or item.get('type') or 'record'
        content = _text(_first(body, 'content', 'text') or _first(item, 'content', 'text') or (message.get('content') if isinstance(message, dict) else None))
        if source.agent == 'antigravity' and 'created_at' in record:
            role = {'USER_INPUT': 'user', 'PLANNER_RESPONSE': 'assistant', 'ERROR_MESSAGE': 'error',
                    'SYSTEM_MESSAGE': 'system', 'CONVERSATION_HISTORY': 'system',
                    'DIRECTORY_RULES': 'system', 'CHECKPOINT': 'system', 'EPHEMERAL_MESSAGE': 'system'}.get(record.get('type'), role)
            if record.get('type') in {'VIEW_FILE', 'GREP_SEARCH', 'LIST_DIRECTORY', 'RUN_COMMAND', 'CODE_ACTION',
                                      'SEARCH_WEB', 'ASK_QUESTION', 'INVOKE_SUBAGENT', 'MCP_TOOL'}:
                role = 'tool'
            if not content and isinstance(record.get('tool_calls'), list):
                names = [call['name'] for call in record['tool_calls'] if isinstance(call, dict) and isinstance(call.get('name'), str)]
                content = ', '.join(names) or None
            content = content or _text(record.get('error'))
        display = f'{role}: {content[:240]}' if content else str(role)
        if source.agent == 'antigravity' and 'created_at' in record:
            detail = [str(record[key]) for key in ('type', 'status') if record.get(key)]
            if 'exit_code' in record: detail.append(f'exit_code={record["exit_code"]}')
            if 'error_code' in record: detail.append(f'error_code={record["error_code"]}')
            display += f' [{", ".join(detail)}]' if detail else ''
        stable = _first(body, 'id', 'uuid', 'response_id', 'record_id') or _first(record, 'uuid', 'id', 'requestId')
        if stable is None and source.agent == 'antigravity' and _integer(record.get('step_index')) is not None:
            stable = f'step:{record["step_index"]}'
        if stable is None:
            canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            stable = hashlib.sha256(canonical.encode()).hexdigest()
        event_id = f'{source.agent}:{sid}:{stable}'
        events.append(LogEvent(event_id, source.agent, sid, at, display, path, label, kind, str(line), [path], None, str(role), str(record.get('type') or body.get('type') or role), tool_observations(record), (event_turns or {}).get(line)))
    return events


def parse_codex(source: SourceFile) -> ParseResult:
    out = ParseResult(); records = _records(source, out.diagnostics)
    meta = next((r for _, r in records if r.get('type') == 'session_meta'), {})
    payload = meta.get('payload', meta); sid = str(_first(payload, 'id', 'session_id', 'thread_id') or source.path.stem)
    source_meta = payload.get('source') if isinstance(payload.get('source'), dict) else {}
    subagent = source_meta.get('subagent') if isinstance(source_meta.get('subagent'), dict) else {}
    spawn = subagent.get('thread_spawn') if isinstance(subagent.get('thread_spawn'), dict) else {}
    parent = _first(payload, 'parent_thread_id', 'parent_session_id', 'parent_id') or spawn.get('parent_thread_id')
    session = Session(sid, 'codex', str(parent) if parent is not None else None, str(source.path), _first(payload, 'cwd', 'project'), _first(payload, 'title'), None, None)
    turns: dict[str, Turn] = {}; current: str | None = None; cumulative: dict[str, dict[str, int]] = defaultdict(dict)
    turn_models: dict[str, str] = {}; event_turns = {}
    # calculate fallback deltas in original order, then suppress for turns with preferred usage
    fallback: dict[str, list[Usage]] = defaultdict(list); preferred: set[str] = set(); seen: set[str] = set()
    for line, rec in records:
        kind = rec.get('type'); body = rec.get('payload') if isinstance(rec.get('payload'), dict) else rec; at = _time(_first(rec, 'timestamp', 'time') or _first(body, 'timestamp'))
        if at:
            session.started_at = min(session.started_at, at) if session.started_at else at; session.last_activity_at = max(session.last_activity_at, at) if session.last_activity_at else at
        if kind == 'event_msg' and body.get('type') == 'task_started' and body.get('turn_id'):
            current = str(body['turn_id'])
            turns.setdefault(current, Turn(current, sid, None, at, None))
        if kind == 'turn_context':
            current = str(_first(body, 'turn_id', 'id') or f'line-{line}')
            turns.setdefault(current, Turn(current, sid, None, at, None, 'unknown', '', 'unknown'))
            if _first(body, 'model', 'model_name'): turn_models[current] = str(_first(body, 'model', 'model_name'))
        owner = _first(body, 'turn_id') or current
        event_turns[line] = str(owner) if owner is not None else None
        if kind == 'event_msg' and body.get('type') == 'user_message' and current:
            text = _text(body.get('message'))
            if text and not turns[current].user_preview:
                turns[current].user_preview = text[:80]
        if kind == 'response_item':
            item = body.get('item', body); item = item if isinstance(item, dict) else {}; role = item.get('role'); text = _text(item.get('content') or item.get('text'))
            if role == 'user' and current and not turns[current].user_preview and text: turns[current].user_preview = text[:80]
        if kind == 'token_usage_record':
            usage_data = body.get('usage', body); turn = str(_first(body, 'turn_id') or current or 'unclassified'); rid = _first(body, 'response_id')
            key = str(_first(body, 'id', 'record_id') or f'{line}:{rid or ""}')
            if key not in seen:
                seen.add(key); preferred.add(turn); usage = _usage(usage_data, 'codex.token_usage_record', key, at, rid); usage.session_id = sid; usage.turn_id = turn; usage.source_path = str(source.path); turns.setdefault(turn, Turn(turn, sid, None, at, at)).usage.append(usage)
        if kind == 'event_msg' and rec.get('payload', {}).get('type') == 'token_count':
            info = rec['payload'].get('info')
            # Some live Codex event records carry an explicit JSON null while
            # the producer is still assembling token information.
            if not isinstance(info, dict):
                continue
            turn = current or 'unclassified'; latest = info.get('total_token_usage') or info.get('last_token_usage') or info
            if not isinstance(latest, dict):
                continue
            # fields can be nested and cumulative; only positive deltas count.
            snapshot = _usage(latest, 'codex.cumulative_delta', str(line), at)
            total_now = snapshot.total_tokens
            if total_now is not None:
                # The producer periodically starts a new cumulative window.
                # Treat a decrease as a reset rather than losing that window.
                previous = cumulative[sid].get('total_tokens', 0)
                delta = total_now if total_now < previous else total_now - previous
                cumulative[sid]['total_tokens'] = total_now
                if delta:
                    changed = Usage(total_tokens=delta, source='codex.cumulative_delta', record_key=str(line), occurred_at=at)
                    for field in ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_creation_tokens', 'reasoning_tokens'):
                        value = getattr(snapshot, field)
                        if value is None: continue
                        prior = cumulative[sid].get(field, 0)
                        setattr(changed, field, value if value < prior else value - prior)
                        cumulative[sid][field] = value
                    fallback[turn].append(changed)
            else:
                # Older records expose only token components.  Delta each
                # known component so a missing total never becomes zero.
                changed = Usage(source='codex.cumulative_delta', record_key=str(line), occurred_at=at)
                any_delta = False
                for field in ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_creation_tokens', 'reasoning_tokens'):
                    value = getattr(snapshot, field)
                    if value is None: continue
                    previous = cumulative[sid].get(field, 0)
                    delta = value if value < previous else value - previous
                    cumulative[sid][field] = value
                    setattr(changed, field, delta); any_delta = any_delta or bool(delta)
                if any_delta: fallback[turn].append(changed)
    for tid, values in fallback.items():
        if tid not in preferred: turns.setdefault(tid, Turn(tid, sid, None, None, None)).usage.extend(values)
    for turn in turns.values():
        if turn.started_at is None: turn.started_at = session.started_at
        turn.ended_at = session.last_activity_at if turn.started_at else None
        if turn.started_at and turn.ended_at: turn.duration_kind = 'observed'
        for usage in turn.usage:
            usage.session_id, usage.turn_id = sid, turn.turn_id
            usage.model = usage.model or turn_models.get(turn.turn_id)
    session.title = session.title or next((t.user_preview for t in turns.values() if t.user_preview), None)
    _set_status(session, list(turns.values()))
    lifecycle = [(rec.get('payload') or {}, _time(_first(rec, 'timestamp', 'time'))) for _, rec in records if rec.get('type') == 'event_msg' and isinstance(rec.get('payload'), dict)]
    for payload, at in lifecycle:
        event_turn = _first(payload, 'turn_id') or current
        if event_turn in turns and payload.get('type') in ('task_complete', 'task_abort', 'task_error'):
            turn = turns[event_turn]; turn.ended_at = at or turn.ended_at
            turn.status = {'task_complete': 'completed', 'task_abort': 'cancelled', 'task_error': 'failed'}[payload.get('type')]
            turn.status_reason = 'explicit lifecycle event'
    for tid, turn in turns.items():
        for usage in turn.usage:
            usage.model = usage.model or turn_models.get(tid)
    last_lifecycle = lifecycle[-1][0].get('type') if lifecycle else None
    if last_lifecycle in ('task_complete', 'task_completed', 'session_end') and (not current or _first(lifecycle[-1][0], 'turn_id') in (None, current)):
        session.status, session.status_reason = 'completed', 'explicit completion event'
    elif last_lifecycle == 'task_abort':
        session.status, session.status_reason = 'cancelled', 'explicit lifecycle event'
    elif last_lifecycle == 'task_error':
        session.status, session.status_reason = 'failed', 'explicit lifecycle event'
    _provenance(source, session, [u for t in turns.values() for u in t.usage]); out.events = _event_records(source, sid, records, event_turns); out.sessions.append(session); out.turns.extend(turns.values()); return out


def parse_claude(source: SourceFile) -> ParseResult:
    out = ParseResult(); records = _records(source, out.diagnostics)
    event_turns = {}
    sid = source.path.stem; project = source.path.parent.name.replace('-', '/')
    session = Session(sid, 'claude', None, str(source.path), project, None, None, None); turns: dict[str, Turn] = {}; current: str | None = None; seen: set[str] = set()
    for line, rec in records:
        at = _time(_first(rec, 'timestamp', 'time')); message = rec.get('message'); message = message if isinstance(message, dict) else {}; role = message.get('role', rec.get('role')); rtype = rec.get('type', '')
        session.parent_session_id = session.parent_session_id or _first(rec, 'parentSessionId', 'parent_session_id', 'parentId')
        if at:
            session.started_at = min(session.started_at, at) if session.started_at else at; session.last_activity_at = max(session.last_activity_at, at) if session.last_activity_at else at
        content = message.get('content', rec.get('content'))
        result_blocks = isinstance(content, list) and any(isinstance(block, dict) and block.get('type') == 'tool_result' for block in content)
        is_tool_result = bool('toolUseResult' in rec or rec.get('isToolResult') or rtype in ('tool_result', 'user_tool_result') or result_blocks)
        if role == 'user' and not is_tool_result:
            current = str(_first(rec, 'uuid', 'id') or f'line-{line}'); text = _text(message.get('content', rec.get('content', ''))) or ''
            turns[current] = Turn(current, sid, text[:80] or None, at, None)
        event_turns[line] = current
        if current and at and turns[current].started_at and at >= turns[current].started_at:
            turn = turns[current]
            turn.ended_at = max(turn.ended_at, at) if turn.ended_at else at
            turn.duration_kind = 'observed'
        if role == 'assistant' and isinstance(message, dict) and isinstance(message.get('usage'), dict):
            usage_data = message['usage']; rid = _first(message, 'id', 'response_id') or _first(rec, 'requestId', 'uuid'); key = str(rid or f'{line}')
            # streaming records may repeat a response: keep the last record's usage.
            if key in seen:
                for turn in turns.values(): turn.usage[:] = [u for u in turn.usage if u.response_id != rid]
            seen.add(key); target = current or 'unclassified'; usage = _usage(usage_data, 'claude.message.usage', key, at, str(rid) if rid else None, True); usage.session_id = sid; usage.turn_id = target; usage.source_path = str(source.path); usage.model = _first(message, 'model') or usage.model; turns.setdefault(target, Turn(target, sid, None, at, at)).usage.append(usage)
    session.title = next((t.user_preview for t in turns.values() if t.user_preview), None); _set_status(session, list(turns.values())); _provenance(source, session, [u for t in turns.values() for u in t.usage]); out.events = _event_records(source, sid, records, event_turns); out.sessions.append(session); out.turns.extend(turns.values()); return out


def parse_antigravity(source: SourceFile) -> ParseResult:
    out = ParseResult(); records = _records(source, out.diagnostics)
    recognized = any(_time(_first(r, 'timestamp', 'time', 'created_at')) is not None and
                     (_first(r, 'role', 'type') or isinstance(r.get('message'), dict)) for _, r in records)
    if not recognized:
        out.diagnostics.append(Diagnostic(str(source.path), 'unsupported_format', 'Antigravity transcript schema is unverified'))
        return out
    # A brain conversation owns its logs; the immediate parent is just "logs".
    sid = next((parent.name for parent in source.path.parents if parent.parent.name == 'brain'), source.path.parent.name)
    session = Session(sid, 'antigravity', None, str(source.path), None, None, None, None)
    out.diagnostics.append(Diagnostic(str(source.path), 'usage_unavailable', '이 transcript에서 토큰 사용량을 확인할 수 없습니다.'))
    turns: list[Turn] = []; event_turns = {}
    for line, rec in records:
        at = _time(_first(rec, 'timestamp', 'time', 'created_at'))
        if at:
            session.started_at = min(session.started_at, at) if session.started_at else at
            session.last_activity_at = max(session.last_activity_at, at) if session.last_activity_at else at
        message = rec.get('message') if isinstance(rec.get('message'), dict) else {}
        role = _first(rec, 'role') or message.get('role')
        if role == 'user' or rec.get('type') == 'USER_INPUT':
            content = _text(_first(rec, 'content', 'text') or message.get('content'))
            identifier = _first(rec, 'id', 'step_index')
            turns.append(Turn(str(identifier if identifier is not None else line), sid, content[:80] if content else None,
                              at, None))
        event_turns[line] = turns[-1].turn_id if turns else None
        if turns and at and turns[-1].started_at and at >= turns[-1].started_at:
            turn = turns[-1]
            turn.ended_at = max(turn.ended_at, at) if turn.ended_at else at
            turn.duration_kind = 'observed'
    session.title = next((turn.user_preview for turn in turns if turn.user_preview), None)
    # DONE describes a single step, not completion of the conversation.
    _set_status(session, turns); _provenance(source, session)
    out.events = _event_records(source, sid, records, event_turns); out.sessions.append(session); out.turns.extend(turns)
    return out


def _set_status(session: Session, turns: list[Turn]) -> None:
    now = datetime.now(timezone.utc); active = session.last_activity_at and (now - session.last_activity_at).total_seconds() <= 60
    session.status = 'active_inferred' if active else 'unfinished'; session.status_reason = 'recent activity' if active else 'no explicit completion event'
    for turn in turns:
        turn.status, turn.status_reason = session.status, session.status_reason


def parse_source(source: SourceFile) -> ParseResult:
    result = {'codex': parse_codex, 'claude': parse_claude, 'antigravity': parse_antigravity}.get(source.agent, parse_antigravity)(source)
    for turn in result.turns: turn.agent = source.agent
    return result


def _event_id(usage: Usage, agent: str, session_id: str) -> str:
    if usage.event_id:
        return usage.event_id
    stable = usage.response_id or usage.record_key
    if stable:
        return f'{agent}:{session_id}:{usage.source}:{stable}'
    payload = f'{agent}|{session_id}|{usage.source}|{usage.occurred_at}|{usage.total_tokens}|{usage.input_tokens}|{usage.output_tokens}'
    return hashlib.sha256(payload.encode()).hexdigest()


def _merge_session(existing: Session, incoming: Session) -> None:
    existing.sources = list(dict.fromkeys([*(existing.sources or [existing.source_path]), *(incoming.sources or [incoming.source_path])]))
    if incoming.started_at and (not existing.started_at or incoming.started_at < existing.started_at): existing.started_at = incoming.started_at
    if incoming.last_activity_at and (not existing.last_activity_at or incoming.last_activity_at > existing.last_activity_at): existing.last_activity_at = incoming.last_activity_at
    existing.title = existing.title or incoming.title


def _merge_turn(existing: Turn, incoming: Turn) -> None:
    """Keep one logical turn when a mirrored session is found in two roots."""
    existing.user_preview = existing.user_preview or incoming.user_preview
    if incoming.started_at and (not existing.started_at or incoming.started_at < existing.started_at): existing.started_at = incoming.started_at
    if incoming.ended_at and (not existing.ended_at or incoming.ended_at > existing.ended_at): existing.ended_at = incoming.ended_at
    existing.usage.extend(incoming.usage)


def _merge_event(existing: LogEvent, incoming: LogEvent) -> None:
    existing.sources = list(dict.fromkeys([*existing.sources, *incoming.sources]))
    existing.turn_id = existing.turn_id or incoming.turn_id
    if incoming.occurred_at and (not existing.occurred_at or incoming.occurred_at < existing.occurred_at): existing.occurred_at = incoming.occurred_at


def parse_sources(sources: Iterable[SourceFile]) -> ParseResult:
    combined = ParseResult(); sessions: dict[tuple[str, str], Session] = {}; turns: dict[tuple[str, str, str], Turn] = {}; events: dict[str, LogEvent] = {}; seen_usage: set[str] = set()
    for source in sources:
        result = parse_source(source); combined.diagnostics.extend(result.diagnostics); combined.raw_records.update(result.raw_records)
        for session in result.sessions:
            key = (session.agent, session.session_id)
            if key in sessions: _merge_session(sessions[key], session)
            else: sessions[key] = session; combined.sessions.append(session)
        for event in result.events:
            if event.event_id in events: _merge_event(events[event.event_id], event)
            else: events[event.event_id] = event; combined.events.append(event)
        for turn in result.turns:
            turn_key = (source.agent, turn.session_id, turn.turn_id)
            if turn_key in turns: _merge_turn(turns[turn_key], turn)
            else: turns[turn_key] = turn; combined.turns.append(turn)
    for turn in combined.turns:
        unique = []
        for usage in turn.usage:
            key = _event_id(usage, turn.agent or '', turn.session_id); usage.event_id = key
            if key not in seen_usage: seen_usage.add(key); unique.append(usage)
        turn.usage[:] = unique
    combined.turns[:] = [turn for turn in combined.turns if turn.usage or turn.user_preview or turn.agent == 'antigravity']
    # Relationship summaries are separate from turn totals: analysis continues
    # to consume turns once, avoiding parent/child double counting.
    by_id = {(session.agent, session.session_id): session for session in combined.sessions}
    for session in combined.sessions:
        session.own_usage = [usage for turn in combined.turns if turn.agent == session.agent and turn.session_id == session.session_id for usage in turn.usage]
    for session in combined.sessions:
        if session.parent_session_id:
            parent = by_id.get((session.agent, str(session.parent_session_id)))
            if parent: parent.child_usage.extend(session.own_usage)
    return combined
