from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from time import monotonic
from datetime import datetime, timezone

from .config import load_config, normalized_timezone, path_diagnostics
from .analysis import orchestration_graph
from .discovery import scan_sources
from .models import ParseResult
from .parsers import PARSER_VERSION, _event_id, _merge_event, _merge_session, _merge_turn, parse_source


class AgentMonitor:
    """In-memory, read-only source scanner. Reuses parsed files unchanged on refresh."""
    def __init__(self, config=None):
        self.config = config or load_config(); self._cache = {}; self._snapshot = None; self._generation = 0; self._revision = None
        self._sources = []; self._next_discovery = 0.0

    def _discover_sources(self, force: bool = False):
        """Directory traversal is bounded to the slower dashboard refresh."""
        if force or monotonic() >= self._next_discovery:
            self._sources = scan_sources(self.config['paths'])
            self._next_discovery = monotonic() + 5
        return self._sources

    def get_snapshot(self, force: bool = False) -> dict:
        sources = self._discover_sources(force); active = set(); combined = ParseResult()
        revision = tuple(sorted((str(source.path), source.size, source.mtime_ns) for source in sources))
        if not force and self._snapshot is not None and revision == self._revision:
            return self._snapshot
        sessions: dict[tuple[str, str], object] = {}; turns: dict[tuple[str, str, str], object] = {}; events: dict[str, object] = {}; seen_usage: set[str] = set()
        for source in sources:
            key = (str(source.path), source.size, source.mtime_ns, PARSER_VERSION); active.add(key)
            if force or key not in self._cache:
                self._cache[key] = parse_source(source)
            # Combining de-duplicates and merges objects, so never mutate the
            # cached parse result: a mirrored source can disappear next poll.
            result = deepcopy(self._cache[key])
            for session in result.sessions:
                identity = (session.agent, session.session_id)
                if identity in sessions:
                    _merge_session(sessions[identity], session)
                else:
                    sessions[identity] = session; combined.sessions.append(session)
            for event in result.events:
                if event.event_id in events: _merge_event(events[event.event_id], event)
                else: events[event.event_id] = event; combined.events.append(event)
            for turn in result.turns:
                identity = (source.agent, turn.session_id, turn.turn_id)
                if identity in turns:
                    _merge_turn(turns[identity], turn)
                else:
                    turns[identity] = turn; combined.turns.append(turn)
            combined.diagnostics.extend(result.diagnostics); combined.raw_records.update(result.raw_records)
        for turn in combined.turns:
            unique = []
            for usage in turn.usage:
                identity = _event_id(usage, turn.agent or '', turn.session_id)
                usage.event_id = identity
                if identity not in seen_usage:
                    seen_usage.add(identity); unique.append(usage)
            turn.usage[:] = unique
        combined.turns[:] = [turn for turn in combined.turns if turn.usage or turn.user_preview]
        by_session = {(session.agent, session.session_id): session for session in combined.sessions}
        for session in combined.sessions:
            session.own_usage = [usage for turn in combined.turns if turn.agent == session.agent and turn.session_id == session.session_id for usage in turn.usage]
            session.child_usage = []
        for session in combined.sessions:
            if session.parent_session_id:
                parent = by_session.get((session.agent, str(session.parent_session_id)))
                if parent: parent.child_usage.extend(session.own_usage)
        self._cache = {key: value for key, value in self._cache.items() if key in active}
        if revision != self._revision:
            self._generation += 1
            self._revision = revision
        tz_name, timezone_diag = normalized_timezone(self.config)
        config_diags = path_diagnostics(self.config)
        if timezone_diag: config_diags.append(timezone_diag)
        public_config = {'timezone': tz_name, 'auto_refresh_seconds': self.config.get('auto_refresh_seconds', 5), 'paths': self.config.get('paths', {})}
        self._snapshot = {'sessions': combined.sessions, 'requests': combined.turns, 'usage': [u for t in combined.turns for u in t.usage], 'events': combined.events, 'orchestration': orchestration_graph(combined), 'diagnostics': combined.diagnostics, 'config_diagnostics': config_diags, 'config': public_config, 'timezone': tz_name, 'paths': self.config['paths'], 'scanned_at': datetime.now(timezone.utc), 'generation': self._generation, 'raw_records': combined.raw_records}
        return self._snapshot

    def update_config(self, config: dict) -> None:
        """Apply settings atomically and discard stale source/cache identities."""
        self.config = config
        self._cache.clear(); self._sources = []; self._next_discovery = 0.0; self._snapshot = None; self._revision = None

    def reload_config(self, config: dict | None = None) -> dict:
        self.update_config(config or load_config())
        return self.get_snapshot(force=True)

    def refresh(self) -> dict:
        """Re-scan changed files; safe to call from a one-second UI poll."""
        return self.get_snapshot()

    def refresh_sources(self) -> dict:
        """Discover/stat sources and reuse every unchanged parsed result."""
        # A user-initiated refresh should discover immediately, but still lets
        # get_snapshot return cached ParseResults for unchanged file revisions.
        self._next_discovery = 0
        return self.get_snapshot(force=False)

    def poll_session(self, session_id: str) -> dict:
        """One-second selected-session poll: stat known files, no directory walk."""
        # Bootstrap once; steady-state polling must not enter the discovery or
        # snapshot-combination path when nothing in the selected session moved.
        snapshot = self._snapshot or self.get_snapshot()
        selected = {path for session in snapshot['sessions'] if session.session_id == session_id for path in session.sources}
        refreshed = []; changed = []
        for source in self._sources:
            if str(source.path) not in selected:
                refreshed.append(source); continue
            try:
                stat = source.path.stat()
                current = type(source)(source.agent, source.path, stat.st_size, stat.st_mtime_ns, source.source_label, source.source_kind)
                refreshed.append(current)
                if (current.size, current.mtime_ns) != (source.size, source.mtime_ns): changed.append(current)
            except OSError:
                # Keep the old descriptor until the next discovery reports it missing.
                refreshed.append(source)
        self._sources = refreshed
        if not changed:
            return snapshot
        # Parse only changed selected files before rebuilding the derived view.
        for source in changed:
            key = (str(source.path), source.size, source.mtime_ns, PARSER_VERSION)
            self._cache[key] = parse_source(source)
        return self.get_snapshot()

    def recent_events(self, session_id: str | None = None, since: datetime | None = None, limit: int = 200, include_raw: bool = False) -> list:
        """Latest display logs for a selected session; raw JSON is opt-in."""
        snapshot = self.get_snapshot()
        events = snapshot['events']
        if session_id is not None:
            events = [event for event in events if event.session_id == session_id]
        if since is not None:
            events = [event for event in events if event.occurred_at and event.occurred_at > since]
        selected = sorted(events, key=lambda event: event.occurred_at or datetime.min.replace(tzinfo=timezone.utc))[-limit:]
        if include_raw:
            for event in selected:
                event.raw_record = self._read_event_raw(event)
        return selected

    def raw_event(self, agent: str, session_id: str, source_path: str, record_key: str) -> dict | None:
        """Fetch exactly one user-selected transcript record."""
        for event in self.get_snapshot()['events']:
            if event.agent == agent and event.session_id == session_id and event.source_path == source_path and event.record_key == str(record_key):
                return self._read_event_raw(event)
        return None

    @staticmethod
    def _read_event_raw(event) -> dict | None:
        """Read exactly one JSONL line only when a raw-event drawer is opened."""
        try:
            with Path(event.source_path).open(encoding='utf-8') as stream:
                for number, line in enumerate(stream, 1):
                    if number == int(event.record_key):
                        return json.loads(line)
        except (OSError, ValueError, json.JSONDecodeError):
            return None
        return None




_default_monitor: AgentMonitor | None = None

def get_snapshot(force: bool = False) -> dict:
    global _default_monitor
    if _default_monitor is None: _default_monitor = AgentMonitor()
    return _default_monitor.get_snapshot(force)


def refresh_sources() -> dict:
    """Public manual-refresh path; unlike force=True it keeps parse cache hits."""
    global _default_monitor
    if _default_monitor is None: _default_monitor = AgentMonitor()
    return _default_monitor.refresh_sources()


def update_config(config: dict) -> None:
    global _default_monitor
    if _default_monitor is None: _default_monitor = AgentMonitor(config)
    else: _default_monitor.update_config(config)


def reload_config(config: dict | None = None) -> dict:
    global _default_monitor
    if _default_monitor is None: _default_monitor = AgentMonitor(config)
    return _default_monitor.reload_config(config)


def poll_session(session_id: str) -> dict:
    global _default_monitor
    if _default_monitor is None: _default_monitor = AgentMonitor()
    return _default_monitor.poll_session(session_id)


def recent_events(session_id: str | None = None, since: datetime | None = None, limit: int = 200, include_raw: bool = False) -> list:
    global _default_monitor
    if _default_monitor is None: _default_monitor = AgentMonitor()
    return _default_monitor.recent_events(session_id, since, limit, include_raw)

def raw_event(agent: str, session_id: str, source_path: str, record_key: str) -> dict | None:
    global _default_monitor
    if _default_monitor is None: _default_monitor = AgentMonitor()
    return _default_monitor.raw_event(agent, session_id, source_path, record_key)
