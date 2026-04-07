"""FastAPI dependencies for auth and services."""
from __future__ import annotations

from fastapi import Depends, Header

from app.security.jwt_auth import decode_access_token
from app.services.user_service import UserService
from app.llm.registry import LLMRegistry
from app.mcp_layer.manager import MCPManager
from app.utils.errors import AuthenticationError, AuthorizationError

# ─── Singletons ─────────────────────────────────────────────────────

_user_service: UserService | None = None
_llm_registry: LLMRegistry | None = None
_mcp_manager: MCPManager | None = None


async def get_user_service() -> UserService:
    global _user_service
    if _user_service is None:
        _user_service = UserService()
        await _user_service.initialize()
    return _user_service


def get_llm_registry() -> LLMRegistry:
    global _llm_registry
    if _llm_registry is None:
        from app.llm import create_registry
        _llm_registry = create_registry()
    return _llm_registry


async def get_mcp_manager() -> MCPManager:
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
        await _mcp_manager.start_all()
    return _mcp_manager


# ─── Auth dependencies ──────────────────────────────────────────────

async def get_current_user(
    authorization: str | None = Header(default=None),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    """Extract and verify JWT from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)
    if payload is None:
        raise AuthenticationError("Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")

    user = await user_service.get_by_id(user_id)
    if not user or not user["is_active"]:
        raise AuthenticationError("User not found or deactivated")

    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require admin role."""
    if user["role"] != "admin":
        raise AuthorizationError("Admin access required")
    return user
