"""Admin endpoints: user management, audit logs, system status — with logging."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_user_service, require_admin, get_mcp_manager
from app.schemas.auth import UserPublic
from app.security.audit_log import audit_logger
from app.services.user_service import UserService
from app.utils.errors import DatabaseError, NotFoundError
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/admin", tags=["admin"])
log = get_logger("api.admin")


def _to_public(u: dict) -> UserPublic:
    return UserPublic(
        id=u["id"], username=u["username"], email=u["email"],
        role=u["role"], allowed_repos=u["allowed_repos"],
        allowed_channels=u["allowed_channels"],
        allowed_db_tables=u["allowed_db_tables"], is_active=u["is_active"],
    )


@router.get("/users", response_model=list[UserPublic])
async def list_users(
    admin: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> list[UserPublic]:
    log.info("admin_list_users", admin_id=admin["id"])
    try:
        users = await user_service.list_users()
    except Exception as e:
        log.error("admin_list_users_failed", error=str(e))
        raise DatabaseError("Failed to list users") from e
    return [_to_public(u) for u in users]


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    updates: dict,
    admin: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserPublic:
    log.info("admin_update_user", admin_id=admin["id"], target_user=user_id, fields=list(updates.keys()))
    try:
        user = await user_service.update_user(user_id, **updates)
    except Exception as e:
        log.error("admin_update_user_failed", user_id=user_id, error=str(e))
        raise DatabaseError("Failed to update user") from e

    if not user:
        log.warning("admin_update_user_not_found", user_id=user_id)
        raise NotFoundError(f"User {user_id} not found")

    audit_logger.log_event(
        "admin_update_user",
        user_id=admin["id"], username=admin["username"],
        details=f"Updated user {user_id}: {list(updates.keys())}",
    )
    return _to_public(user)


@router.get("/audit-logs")
async def get_audit_logs(
    admin: dict = Depends(require_admin),
    event_type: str = Query("", description="Filter by event type"),
    user_id: str = Query("", description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    log.info("admin_view_audit_logs", admin_id=admin["id"], event_type=event_type or "all")
    try:
        logs = audit_logger.get_logs(user_id=user_id, event_type=event_type, limit=limit, offset=offset)
        stats = audit_logger.get_stats()
    except Exception as e:
        log.error("admin_audit_logs_failed", error=str(e))
        raise DatabaseError("Failed to retrieve audit logs") from e
    return {"logs": logs, "stats": stats}


@router.get("/status")
async def system_status(
    admin: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    log.info("admin_system_status", admin_id=admin["id"])
    try:
        mcp = await get_mcp_manager()
        users = await user_service.list_users()
        tools = mcp.get_all_tools()
    except Exception as e:
        log.error("admin_status_failed", error=str(e))
        raise DatabaseError("Failed to retrieve system status") from e

    return {
        "users": {"total": len(users), "active": sum(u["is_active"] for u in users)},
        "mcp": {"total_tools": len(tools), "servers": list({t.server_name for t in tools})},
        "audit": audit_logger.get_stats(),
    }
