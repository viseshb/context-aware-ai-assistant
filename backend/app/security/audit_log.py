"""Audit logging — records all tool calls, security events, and user actions."""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from app.utils.logging import get_logger

log = get_logger("security.audit")


class AuditLogger:
    def __init__(self, db_path: str = "audit.db"):
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user_id TEXT,
                username TEXT,
                model_id TEXT,
                tool_name TEXT,
                tool_args TEXT,
                result_summary TEXT,
                duration_ms INTEGER,
                ip_address TEXT,
                details TEXT
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)
        """)
        self._conn.commit()

    def log_event(
        self,
        event_type: str,
        user_id: str = "",
        username: str = "",
        model_id: str = "",
        tool_name: str = "",
        tool_args: dict | None = None,
        result_summary: str = "",
        duration_ms: int = 0,
        ip_address: str = "",
        details: str = "",
    ) -> None:
        if not self._conn:
            self.initialize()

        assert self._conn
        self._conn.execute(
            """INSERT INTO audit_log
               (timestamp, event_type, user_id, username, model_id,
                tool_name, tool_args, result_summary, duration_ms, ip_address, details)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                event_type,
                user_id,
                username,
                model_id,
                tool_name,
                json.dumps(tool_args) if tool_args else "",
                result_summary[:500],
                duration_ms,
                ip_address,
                details,
            ),
        )
        self._conn.commit()
        log.info("audit_event", event_type=event_type, user=username, tool=tool_name)

    def get_logs(
        self,
        user_id: str = "",
        event_type: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        if not self._conn:
            self.initialize()

        assert self._conn
        query = "SELECT * FROM audit_log WHERE 1=1"
        params: list = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        if not self._conn:
            self.initialize()

        assert self._conn
        total = self._conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        tool_calls = self._conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE event_type = 'tool_call'"
        ).fetchone()[0]
        security_events = self._conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE event_type LIKE 'security_%'"
        ).fetchone()[0]
        return {
            "total_events": total,
            "tool_calls": tool_calls,
            "security_events": security_events,
        }


# Singleton
audit_logger = AuditLogger()
