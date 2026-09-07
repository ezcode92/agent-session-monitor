from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class Usage:
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None
    cache_creation_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    source: str = ""
    response_id: Optional[str] = None
    record_key: Optional[str] = None
    occurred_at: Optional[datetime] = None
    session_id: Optional[str] = None
    turn_id: Optional[str] = None
    model: Optional[str] = None
    source_path: Optional[str] = None
    # Provenance is deliberately kept on every event: one session can be
    # reconstructed from more than one Antigravity installation.
    source_label: Optional[str] = None
    source_kind: Optional[str] = None
    event_id: Optional[str] = None
    agent: Optional[str] = None

    def value(self, name: str) -> int:
        return getattr(self, name) or 0


@dataclass(slots=True)
class Session:
    session_id: str
    agent: str
    parent_session_id: Optional[str]
    source_path: str
    project: Optional[str]
    title: Optional[str]
    started_at: Optional[datetime]
    last_activity_at: Optional[datetime]
    status: str = "unknown"
    status_reason: str = ""
    own_usage: list[Usage] = field(default_factory=list)
    child_usage: list[Usage] = field(default_factory=list)
    data_quality: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    source_label: Optional[str] = None
    source_kind: Optional[str] = None


@dataclass(slots=True)
class Turn:
    turn_id: str
    session_id: str
    user_preview: Optional[str]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    status: str = "unknown"
    status_reason: str = ""
    duration_kind: str = "unknown"
    usage: list[Usage] = field(default_factory=list)
    data_quality: list[str] = field(default_factory=list)
    agent: Optional[str] = None


@dataclass(slots=True)
class Diagnostic:
    source_path: str
    kind: str
    message: str
    record_key: Optional[str] = None


@dataclass(slots=True)
class LogEvent:
    """A displayable transcript record. ``raw_record`` is returned on demand."""
    event_id: str
    agent: str
    session_id: str
    occurred_at: Optional[datetime]
    display: str
    source_path: str
    source_label: str
    source_kind: str
    record_key: str
    sources: list[str] = field(default_factory=list)
    raw_record: Optional[dict] = None
    role: Optional[str] = None
    event_type: Optional[str] = None


@dataclass(slots=True)
class ParseResult:
    sessions: list[Session] = field(default_factory=list)
    turns: list[Turn] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    raw_records: dict[str, list[dict]] = field(default_factory=dict)
    events: list[LogEvent] = field(default_factory=list)
