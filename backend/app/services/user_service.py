"""User service backed by SQLite — with full error logging."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from app.config import settings
from app.security.jwt_auth import hash_password, verify_password
from app.utils.logging import get_logger

log = get_logger("services.user")


class UserService:
    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or settings.users_db_path
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
        return d

    async def create_user(self, username: str, email: str, password: str, role: str = "viewer") -> dict:
        assert self._conn
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        try:
            pw_hash = hash_password(password)
            self._conn.execute(
                """INSERT INTO users (id, username, email, password_hash, role, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, username, email, pw_hash, role, now),
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

    async def authenticate(self, email: str, password: str) -> dict | None:
        assert self._conn
        try:
            row = self._conn.execute(
                "SELECT * FROM users WHERE email = ? AND is_active = 1", (email,)
            ).fetchone()
        except sqlite3.Error as e:
            log.error("auth_db_query_failed", email=email, error=str(e))
            raise

        if not row:
            log.info("auth_user_not_found", email=email)
            return None

        user = self._row_to_dict(row)
        if not verify_password(password, user["password_hash"]):
            log.warning("auth_bad_password", email=email, user_id=user["id"])
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

    async def update_user(self, user_id: str, **fields: object) -> dict | None:
        assert self._conn
        allowed = {
            "username", "email", "role", "is_active",
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
