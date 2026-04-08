"""User service backed by SQLite — with full error logging."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.security.jwt_auth import hash_password, verify_password
from app.utils.logging import get_logger

log = get_logger("services.user")


class UserService:
    def __init__(self, db_path: str | None = None):
        raw_path = Path(db_path or settings.users_db_path)
        if raw_path.is_absolute():
            resolved_path = raw_path
        elif len(raw_path.parts) == 1:
            # Keep the default `users.db` anchored to the backend folder.
            resolved_path = Path(__file__).resolve().parents[2] / raw_path
        else:
            # Respect explicit relative paths from the repo root, e.g. `backend/users.db`.
            resolved_path = Path(__file__).resolve().parents[3] / raw_path

        self._db_path = str(resolved_path)
        self._conn: sqlite3.Connection | None = None

    async def initialize(self) -> None:
        try:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    allowed_repos TEXT NOT NULL DEFAULT '[]',
                    allowed_channels TEXT NOT NULL DEFAULT '[]',
                    allowed_db_tables TEXT NOT NULL DEFAULT '[]',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_login TEXT
                )
            """)
            # Migration: add status column if missing
            import contextlib
            with contextlib.suppress(sqlite3.OperationalError):
                self._conn.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
                self._conn.commit()

            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_turn_metrics (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL DEFAULT '',
                    model_id TEXT NOT NULL,
                    provider_model TEXT NOT NULL DEFAULT '',
                    ttft_ms INTEGER,
                    total_time_ms INTEGER NOT NULL DEFAULT 0,
                    tool_time_ms INTEGER NOT NULL DEFAULT 0,
                    tool_call_count INTEGER NOT NULL DEFAULT 0,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost_usd REAL,
                    response_chars INTEGER NOT NULL DEFAULT 0,
                    tool_calls TEXT NOT NULL DEFAULT '[]',
                    context_sources TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_turn_metrics_user_created_at
                ON chat_turn_metrics (user_id, created_at DESC)
            """)

            self._conn.commit()
            log.info("user_db_initialized", path=self._db_path)
        except sqlite3.Error as e:
            log.error("user_db_init_failed", path=self._db_path, error=str(e))
            raise

    async def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
            log.info("user_db_closed")

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        d["allowed_repos"] = json.loads(d["allowed_repos"])
        d["allowed_channels"] = json.loads(d["allowed_channels"])
        d["allowed_db_tables"] = json.loads(d["allowed_db_tables"])
        d["is_active"] = bool(d["is_active"])
        d.setdefault("status", "active")
        return d

    @staticmethod
    def _metric_row_to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["tool_calls"] = json.loads(d["tool_calls"])
        d["context_sources"] = json.loads(d["context_sources"])
        return d

    async def create_user(self, username: str, email: str, password: str, role: str = "viewer", status: str = "active") -> dict:
        assert self._conn
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        try:
            pw_hash = hash_password(password)
            self._conn.execute(
                """INSERT INTO users (id, username, email, password_hash, role, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, username, email, pw_hash, role, status, now),
            )
            self._conn.commit()
            log.info("user_created", user_id=user_id, username=username, role=role)
        except sqlite3.IntegrityError as e:
            log.warning("user_create_duplicate", username=username, email=email, error=str(e))
            raise
        except Exception as e:
            log.error("user_create_failed", username=username, error=str(e))
            raise

        return await self.get_by_id(user_id)  # type: ignore[return-value]

    async def authenticate(self, username: str, password: str) -> dict | None:
        assert self._conn
        try:
            row = self._conn.execute(
                "SELECT * FROM users WHERE lower(username) = lower(?) AND is_active = 1",
                (username,),
            ).fetchone()
        except sqlite3.Error as e:
            log.error("auth_db_query_failed", username=username, error=str(e))
            raise

        if not row:
            log.info("auth_user_not_found", username=username)
            return None

        user = self._row_to_dict(row)
        if not verify_password(password, user["password_hash"]):
            log.warning("auth_bad_password", username=username, user_id=user["id"])
            return None

        # Update last login
        try:
            self._conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), user["id"]),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            log.warning("auth_update_last_login_failed", user_id=user["id"], error=str(e))

        log.info("auth_success", user_id=user["id"], username=user["username"])
        return user

    async def get_by_id(self, user_id: str) -> dict | None:
        assert self._conn
        try:
            row = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return self._row_to_dict(row) if row else None
        except sqlite3.Error as e:
            log.error("user_get_by_id_failed", user_id=user_id, error=str(e))
            raise

    async def get_by_email(self, email: str) -> dict | None:
        assert self._conn
        try:
            row = self._conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            return self._row_to_dict(row) if row else None
        except sqlite3.Error as e:
            log.error("user_get_by_email_failed", email=email, error=str(e))
            raise

    async def list_users(self) -> list[dict]:
        assert self._conn
        try:
            rows = self._conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
            return [self._row_to_dict(r) for r in rows]
        except sqlite3.Error as e:
            log.error("user_list_failed", error=str(e))
            raise

    async def get_pending_users(self) -> list[dict]:
        assert self._conn
        try:
            rows = self._conn.execute(
                "SELECT * FROM users WHERE status = 'pending' ORDER BY created_at DESC"
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        except sqlite3.Error as e:
            log.error("user_get_pending_failed", error=str(e))
            raise

    async def update_user(self, user_id: str, **fields: object) -> dict | None:
        assert self._conn
        allowed = {
            "username", "email", "role", "status", "is_active",
            "allowed_repos", "allowed_channels", "allowed_db_tables",
        }
        updates = {}
        for k, v in fields.items():
            if k not in allowed:
                continue
            if k in ("allowed_repos", "allowed_channels", "allowed_db_tables"):
                updates[k] = json.dumps(v)
            elif k == "is_active":
                updates[k] = int(v)  # type: ignore[arg-type]
            else:
                updates[k] = v

        if not updates:
            return await self.get_by_id(user_id)

        try:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [user_id]
            self._conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            self._conn.commit()
            log.info("user_updated", user_id=user_id, fields=list(updates.keys()))
        except sqlite3.Error as e:
            log.error("user_update_failed", user_id=user_id, error=str(e))
            raise

        return await self.get_by_id(user_id)

    async def record_chat_metric(
        self,
        user_id: str,
        conversation_id: str,
        metrics: dict,
        tool_calls: list[dict],
        context_sources: list[dict],
    ) -> dict | None:
        assert self._conn
        metric_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        tool_summaries = [
            {
                "name": str(tool.get("name", "")),
                "status": str(tool.get("status", "")),
                "duration_ms": int(tool.get("duration_ms", 0) or 0),
            }
            for tool in tool_calls
        ]
        source_summaries = [
            {
                "type": str(source.get("type", "")),
                "detail": str(source.get("detail", "")),
            }
            for source in context_sources
        ]

        try:
            self._conn.execute(
                """INSERT INTO chat_turn_metrics (
                       id, user_id, conversation_id, model_id, provider_model,
                       ttft_ms, total_time_ms, tool_time_ms, tool_call_count,
                       input_tokens, output_tokens, cost_usd, response_chars,
                       tool_calls, context_sources, created_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    metric_id,
                    user_id,
                    conversation_id,
                    str(metrics.get("model_id", "")),
                    str(metrics.get("provider_model", "")),
                    metrics.get("ttft_ms"),
                    int(metrics.get("total_time_ms", 0) or 0),
                    int(metrics.get("tool_time_ms", 0) or 0),
                    int(metrics.get("tool_call_count", 0) or 0),
                    metrics.get("input_tokens"),
                    metrics.get("output_tokens"),
                    metrics.get("cost_usd"),
                    int(metrics.get("response_chars", 0) or 0),
                    json.dumps(tool_summaries),
                    json.dumps(source_summaries),
                    now,
                ),
            )
            self._conn.commit()
            log.info("chat_metric_recorded", user_id=user_id, conversation_id=conversation_id, model_id=metrics.get("model_id", ""))
        except sqlite3.Error as e:
            log.error("chat_metric_record_failed", user_id=user_id, error=str(e))
            raise

        row = self._conn.execute("SELECT * FROM chat_turn_metrics WHERE id = ?", (metric_id,)).fetchone()
        return self._metric_row_to_dict(row) if row else None

    async def list_chat_metrics(self, user_id: str, limit: int = 100) -> list[dict]:
        assert self._conn
        try:
            rows = self._conn.execute(
                """SELECT * FROM chat_turn_metrics
                   WHERE user_id = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (user_id, limit),
            ).fetchall()
            return [self._metric_row_to_dict(row) for row in rows]
        except sqlite3.Error as e:
            log.error("chat_metric_list_failed", user_id=user_id, error=str(e))
            raise

    async def get_chat_metrics_summary(self, user_id: str) -> dict:
        assert self._conn
        try:
            row = self._conn.execute(
                """SELECT
                       COUNT(*) AS total_turns,
                       CAST(AVG(ttft_ms) AS INTEGER) AS avg_ttft_ms,
                       COALESCE(SUM(tool_call_count), 0) AS total_tool_calls,
                       COALESCE(SUM(total_time_ms), 0) AS total_time_ms,
                       COALESCE(SUM(input_tokens), 0) AS total_input_tokens,
                       COALESCE(SUM(output_tokens), 0) AS total_output_tokens,
                       COALESCE(SUM(cost_usd), 0) AS total_cost_usd,
                       MAX(created_at) AS last_turn_at
                   FROM chat_turn_metrics
                   WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
        except sqlite3.Error as e:
            log.error("chat_metric_summary_failed", user_id=user_id, error=str(e))
            raise

        summary = dict(row) if row else {}
        total_turns = int(summary.get("total_turns", 0) or 0)
        if total_turns == 0:
            summary["avg_ttft_ms"] = None
            summary["total_cost_usd"] = 0.0
        return summary
