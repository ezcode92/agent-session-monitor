"""Persistence shared by the dashboard and its MCP analysis workers."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
from uuid import uuid4


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(value):
    return json.dumps(value, ensure_ascii=False, default=str)


class ProjectStore:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get("AGENT_MONITOR_ANALYSIS_DB") or ".agent-monitor/analysis.sqlite3")

    @contextmanager
    def connection(self, write=False):
        if not write and not self.path.exists():
            yield None
            return
        if write:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.path) if write else self.path.resolve().as_uri() + "?mode=ro", uri=not write, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            if connection.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
                raise ValueError("지원되지 않는 프로젝트 분석 저장소 버전입니다.")
            if write:
                connection.executescript("""
                    CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, name TEXT NOT NULL, root TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS project_sessions (
                        agent TEXT NOT NULL, session_id TEXT NOT NULL,
                        project_id TEXT NOT NULL REFERENCES projects(project_id), PRIMARY KEY(agent, session_id)
                    );
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY, status TEXT NOT NULL, context_json TEXT NOT NULL,
                        agent_name TEXT, token_hash TEXT, report_json TEXT, error TEXT,
                        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS improvements (
                        job_id TEXT NOT NULL REFERENCES jobs(job_id), item_index INTEGER NOT NULL,
                        title TEXT NOT NULL, status TEXT NOT NULL, applied_at TEXT,
                        PRIMARY KEY(job_id, item_index)
                    );
                    PRAGMA user_version = 1;
                """)
            with connection:
                yield connection
        finally:
            connection.close()

    def projects(self):
        with self.connection() as connection:
            if connection is None:
                return [], []
            return ([dict(row) for row in connection.execute("SELECT * FROM projects ORDER BY name")],
                    [dict(row) for row in connection.execute("SELECT * FROM project_sessions")])

    def save_project(self, project_id, name, root, sessions):
        if not name.strip() or len(name) > 200:
            raise ValueError("프로젝트 이름은 1~200자로 입력하세요.")
        with self.connection(write=True) as connection:
            connection.execute("INSERT INTO projects VALUES (?, ?, ?) ON CONFLICT(project_id) DO UPDATE SET name=excluded.name, root=excluded.root", (project_id, name.strip(), root))
            # The selection replaces only this project's explicit assignments.
            connection.execute("DELETE FROM project_sessions WHERE project_id = ?", (project_id,))
            connection.executemany("INSERT INTO project_sessions VALUES (?, ?, ?) ON CONFLICT(agent, session_id) DO UPDATE SET project_id=excluded.project_id",
                                   [(agent, sid, project_id) for agent, sid in set(sessions)])

    def create_job(self, context):
        identity, now = uuid4().hex, _now()
        with self.connection(write=True) as connection:
            connection.execute("INSERT INTO jobs VALUES (?, 'pending', ?, NULL, NULL, NULL, NULL, ?, ?)", (identity, _json(context), now, now))
        return identity

    def save_log_report(self, context, report):
        """Atomically save one deterministic local report; preserve accepted actions."""
        payload = json.dumps([context, report], ensure_ascii=False, sort_keys=True, default=str)
        identity = "logs-" + hashlib.sha256(payload.encode()).hexdigest()[:32]
        now = _now()
        with self.connection(write=True) as connection:
            connection.execute("""INSERT INTO jobs VALUES (?, 'completed', ?, ?, NULL, ?, NULL, ?, ?)
                ON CONFLICT(job_id) DO NOTHING""", (identity, _json(context),
                "local-codex-rules/v1", _json(report), now, now))
        return self.get_job(identity)

    @staticmethod
    def _job(row):
        if row is None:
            return None
        job = dict(row)
        job.pop("token_hash", None)
        job["context"] = json.loads(job.pop("context_json"))
        report = job.pop("report_json")
        job["report"] = json.loads(report) if report else None
        return job

    def jobs(self, status=None):
        with self.connection() as connection:
            if connection is None:
                return []
            query = "SELECT * FROM jobs" + (" WHERE status = ?" if status else "") + " ORDER BY created_at DESC, job_id"
            return [self._job(row) for row in connection.execute(query, (status,) if status else ())]

    def get_job(self, job_id):
        with self.connection() as connection:
            return self._job(connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()) if connection else None

    def claim(self, job_id, agent_name):
        if not agent_name.strip() or len(agent_name) > 200:
            raise ValueError("분석 에이전트 이름을 입력하세요.")
        token = secrets.token_urlsafe(32)
        with self.connection(write=True) as connection:
            updated = connection.execute("UPDATE jobs SET status='running', agent_name=?, token_hash=?, updated_at=?, error=NULL WHERE job_id=? AND status='pending'",
                                         (agent_name, hashlib.sha256(token.encode()).hexdigest(), _now(), job_id))
            if not updated.rowcount:
                raise ValueError("대기 중인 분석 요청만 가져갈 수 있습니다.")
        return {"job": self.get_job(job_id), "claim_token": token}

    def finish(self, job_id, token, *, report=None, context=None, error=None):
        if error is not None and (not isinstance(error, str) or not error.strip() or len(error) > 4000):
            raise ValueError("실패 원인은 1~4,000자로 입력하세요.")
        with self.connection(write=True) as connection:
            updated = connection.execute("""UPDATE jobs SET status=?, report_json=?, error=?,
                context_json=COALESCE(?, context_json), token_hash=NULL, updated_at=?
                WHERE job_id=? AND status='running' AND token_hash=?""",
                ("failed" if error is not None else "completed", _json(report) if report is not None else None, error,
                 _json(context) if context is not None else None, _now(), job_id, hashlib.sha256(token.encode()).hexdigest()))
            if not updated.rowcount:
                raise ValueError("분석 요청 상태 또는 소유 토큰이 일치하지 않습니다.")
        return self.get_job(job_id)

    def retry(self, job_id):
        with self.connection(write=True) as connection:
            updated = connection.execute("UPDATE jobs SET status='pending', token_hash=NULL, agent_name=NULL, error=NULL, updated_at=? WHERE job_id=? AND status IN ('running','failed')", (_now(), job_id))
            if not updated.rowcount:
                raise ValueError("실패했거나 진행 중인 요청만 다시 대기시킬 수 있습니다.")

    def accept(self, job_id, item_index):
        job = self.get_job(job_id)
        if not job or job["status"] != "completed" or not 0 <= item_index < len(job["report"]["recommendations"]):
            raise ValueError("완료된 분석의 개선 제안을 선택하세요.")
        title = job["report"]["recommendations"][item_index]["title"]
        with self.connection(write=True) as connection:
            connection.execute("INSERT INTO improvements VALUES (?, ?, ?, 'open', NULL) ON CONFLICT DO NOTHING", (job_id, item_index, title))

    def improvements(self):
        with self.connection() as connection:
            if connection is None:
                return []
            return [dict(row) for row in connection.execute("SELECT * FROM improvements ORDER BY job_id, item_index")]

    def update_improvement(self, job_id, item_index, status):
        if status not in {"open", "applied", "dismissed"}:
            raise ValueError("올바른 개선 상태를 선택하세요.")
        with self.connection(write=True) as connection:
            updated = connection.execute("UPDATE improvements SET status=?, applied_at=CASE WHEN ?='applied' THEN COALESCE(applied_at, ?) ELSE NULL END WHERE job_id=? AND item_index=?", (status, status, _now(), job_id, item_index))
            if not updated.rowcount:
                raise ValueError("기록한 개선 항목이 없습니다.")
