"""Local, user-authored retrospectives. Source transcripts are never stored here."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4


TASK_TYPES = {"other": "기타", "feature": "기능 구현", "bugfix": "문제 해결", "refactor": "리팩터링", "research": "조사·설계"}
OUTCOMES = {"unreviewed": "아직 평가하지 않음", "success": "만족스럽게 완료", "partial": "일부만 완료", "abandoned": "중단"}
ACTION_STATES = {"open": "실천 예정", "applied": "적용함", "dismissed": "보류"}
EVIDENCE_FIELDS = ("kind", "agent", "session_id", "event_id", "source_path", "record_key")


def _text(value, label, limit, required=False):
    value = str(value or "").strip()
    if required and not value:
        raise ValueError(f"{label}을 입력하세요.")
    if len(value) > limit:
        raise ValueError(f"{label}은 {limit}자 이내로 입력하세요.")
    return value


class ReviewStore:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get("AGENT_MONITOR_REVIEW_DB") or ".agent-monitor/reviews.sqlite3")

    @contextmanager
    def _connection(self, write=False):
        if not write and not self.path.exists():
            yield None
            return
        if write:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        target = str(self.path) if write else self.path.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(target, timeout=5, uri=not write)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("더 새로운 버전의 회고 저장소입니다. 앱을 업데이트하세요.")
            if write:
                connection.executescript("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY, title TEXT NOT NULL,
                        task_type TEXT NOT NULL, outcome TEXT NOT NULL,
                        went_well TEXT NOT NULL, blocked_by TEXT NOT NULL, next_change TEXT NOT NULL,
                        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS task_sessions (
                        agent TEXT NOT NULL, session_id TEXT NOT NULL,
                        task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
                        title TEXT NOT NULL, project TEXT NOT NULL,
                        PRIMARY KEY (agent, session_id)
                    );
                    CREATE TABLE IF NOT EXISTS actions (
                        action_id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
                        title TEXT NOT NULL, status TEXT NOT NULL, evidence_json TEXT NOT NULL,
                        signal_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                        applied_at TEXT, UNIQUE (task_id, signal_id)
                    );
                    PRAGMA user_version = 1;
                """)
            with connection:
                yield connection
        finally:
            connection.close()

    def list_tasks(self):
        with self._connection() as connection:
            if connection is None:
                return []
            tasks = [dict(row, sessions=[]) for row in connection.execute("SELECT * FROM tasks ORDER BY updated_at DESC, task_id")]
            by_id = {task["task_id"]: task for task in tasks}
            for row in connection.execute("SELECT * FROM task_sessions ORDER BY agent, session_id"):
                member = dict(row)
                by_id[member.pop("task_id")]["sessions"].append(member)
            return tasks

    def get_task(self, task_id):
        return next((task for task in self.list_tasks() if task["task_id"] == task_id), None)

    def task_for_session(self, agent, session_id):
        return next((task for task in self.list_tasks() if any(
            (member["agent"], member["session_id"]) == (agent, session_id) for member in task["sessions"]
        )), None)

    def save_task(self, *, title, sessions, task_id=None, task_type="other", outcome="unreviewed",
                  went_well="", blocked_by="", next_change=""):
        title = _text(title, "작업 이름", 200, required=True)
        if task_type not in TASK_TYPES or outcome not in OUTCOMES:
            raise ValueError("작업 유형 또는 결과를 확인하세요.")
        notes = [_text(value, "회고 내용", 4000) for value in (went_well, blocked_by, next_change)]
        members = {}
        for member in sessions:
            key = (_text(member.get("agent"), "에이전트", 100, True),
                   _text(member.get("session_id"), "세션 ID", 500, True))
            members[key] = (str(member.get("title") or "")[:200], str(member.get("project") or "")[:2000])
        if not members:
            raise ValueError("작업에 세션을 하나 이상 연결하세요.")
        now = datetime.now(timezone.utc).isoformat()
        identity = task_id or uuid4().hex
        with self._connection(write=True) as connection:
            if task_id and not connection.execute("SELECT 1 FROM tasks WHERE task_id = ?", (task_id,)).fetchone():
                raise ValueError("작업을 찾을 수 없습니다.")
            for agent, sid in members:
                existing = connection.execute("SELECT task_id FROM task_sessions WHERE agent = ? AND session_id = ?", (agent, sid)).fetchone()
                if existing and existing[0] != identity:
                    raise ValueError("이미 다른 작업에 연결된 세션입니다. 기존 작업에서 먼저 연결을 해제하세요.")
            connection.execute("""INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET title=excluded.title, task_type=excluded.task_type,
                outcome=excluded.outcome, went_well=excluded.went_well, blocked_by=excluded.blocked_by,
                next_change=excluded.next_change, updated_at=excluded.updated_at""",
                (identity, title, task_type, outcome, *notes, now, now))
            connection.execute("DELETE FROM task_sessions WHERE task_id = ?", (identity,))
            connection.executemany("INSERT INTO task_sessions VALUES (?, ?, ?, ?, ?)",
                                   [(agent, sid, identity, *values) for (agent, sid), values in members.items()])
        return identity

    def add_action(self, task_id, title, evidence=(), signal_id=None):
        title = _text(title, "개선 내용", 1000, required=True)
        refs = [{key: str(ref.get(key) or "") for key in EVIDENCE_FIELDS} for ref in evidence]
        now = datetime.now(timezone.utc).isoformat()
        identity = uuid4().hex
        with self._connection(write=True) as connection:
            connection.execute("""INSERT INTO actions VALUES (?, ?, ?, 'open', ?, ?, ?, ?, NULL)
                ON CONFLICT(task_id, signal_id) DO NOTHING""",
                (identity, task_id, title, json.dumps(refs, ensure_ascii=False), signal_id, now, now))
            if signal_id:
                identity = connection.execute("SELECT action_id FROM actions WHERE task_id = ? AND signal_id = ?", (task_id, signal_id)).fetchone()[0]
        return identity

    def list_actions(self, task_id=None):
        with self._connection() as connection:
            if connection is None:
                return []
            query = "SELECT actions.*, tasks.title AS task_title FROM actions JOIN tasks USING (task_id)"
            params = ()
            if task_id:
                query += " WHERE task_id = ?"
                params = (task_id,)
            actions = []
            for row in connection.execute(query + " ORDER BY actions.created_at DESC, action_id", params):
                action = dict(row)
                action["evidence"] = json.loads(action.pop("evidence_json"))
                actions.append(action)
            return actions

    def update_action(self, action_id, *, title, status):
        title = _text(title, "개선 내용", 1000, required=True)
        if status not in ACTION_STATES:
            raise ValueError("개선 항목의 상태를 확인하세요.")
        now = datetime.now(timezone.utc).isoformat()
        with self._connection(write=True) as connection:
            changed = connection.execute("""UPDATE actions SET title = ?, status = ?, updated_at = ?,
                applied_at = CASE WHEN ? = 'applied' THEN COALESCE(applied_at, ?) ELSE NULL END
                WHERE action_id = ?""", (title, status, now, status, now, action_id))
            if not changed.rowcount:
                raise ValueError("개선 항목을 찾을 수 없습니다.")

    def export_json(self):
        return json.dumps({"schema_version": 1, "tasks": self.list_tasks(), "actions": self.list_actions()},
                          ensure_ascii=False, indent=2)
