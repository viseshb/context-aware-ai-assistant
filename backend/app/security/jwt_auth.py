"""JWT authentication and password hashing — with error logging.

CLI usage for creating admin:
    python -m app.security.jwt_auth create-admin --username admin --email admin@local
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings
from app.utils.logging import get_logger

log = get_logger("security.jwt")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    try:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except Exception as e:
        log.error("password_hash_failed", error=str(e))
        raise


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception as e:
        log.error("password_verify_failed", error=str(e))
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expiry_minutes)
    )
    to_encode["exp"] = expire
    secret = settings.ensure_jwt_secret()
    log.info("token_created", sub=data.get("sub", ""), role=data.get("role", ""))
    return jwt.encode(to_encode, secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        secret = settings.ensure_jwt_secret()
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        log.warning("token_decode_failed", error=str(e))
        return None


# ─── CLI: create-admin ──────────────────────────────────────────────

async def _create_admin_cli() -> None:
    import argparse
    import getpass

    parser = argparse.ArgumentParser(description="Create admin user")
    parser.add_argument("command", choices=["create-admin"])
    parser.add_argument("--username", default="admin")
    parser.add_argument("--email", default="admin@local")
    args = parser.parse_args()

    password = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.")
        sys.exit(1)

    from app.services.user_service import UserService

    svc = UserService()
    await svc.initialize()

    existing = await svc.get_by_email(args.email)
    if existing:
        print(f"User with email {args.email} already exists.")
        sys.exit(1)

    user = await svc.create_user(
        username=args.username, email=args.email,
        password=password, role="admin",
    )
    print(f"Admin user created: {user['username']} ({user['email']})")
    await svc.close()


if __name__ == "__main__":
    asyncio.run(_create_admin_cli())
