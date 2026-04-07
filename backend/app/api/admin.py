"""Admin endpoints: user management, audit logs, system status — with logging."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_user_service, require_admin, get_mcp_manager
from app.schemas.auth import ApprovalRequest, RejectionRequest, UserPublic
from app.security.audit_log import audit_logger
from app.security.jwt_auth import decode_access_token
from app.services.user_service import UserService
from app.utils.errors import AuthorizationError, DatabaseError, NotFoundError, ValidationError
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/admin", tags=["admin"])
log = get_logger("api.admin")


def _to_public(u: dict) -> UserPublic:
    return UserPublic(
        id=u["id"], username=u["username"], email=u["email"],
        role=u["role"], status=u.get("status", "active"),
        allowed_repos=u["allowed_repos"], allowed_channels=u["allowed_channels"],
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


# ─── Approval endpoints ────────────────────────────────────────────

@router.get("/pending-users")
async def list_pending_users(
    _admin: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> list[UserPublic]:
    users = await user_service.get_pending_users()
    return [_to_public(u) for u in users]


@router.get("/approve/verify")
async def verify_approval_token(token: str) -> dict:
    """Decode approval token and return pending user info."""
    payload = decode_access_token(token)
    if not payload or payload.get("purpose") != "approval":
        raise AuthorizationError("Invalid or expired approval token")

    user_id = payload["sub"]
    from app.dependencies import get_user_service
    user_svc = await get_user_service()
    user = await user_svc.get_by_id(user_id)

    if not user:
        raise NotFoundError("User not found")
    if user.get("status") != "pending":
        raise ValidationError(f"User is already {user.get('status', 'processed')}")

    log.info("approval_token_verified", user_id=user_id, username=user["username"])
    return {
        "user_id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "created_at": user["created_at"],
        "action": payload.get("action", "approve"),
    }


@router.post("/approve")
async def approve_user(
    body: ApprovalRequest,
    user_service: UserService = Depends(get_user_service),
) -> dict:
    """Approve a pending user — set role and permissions."""
    payload = decode_access_token(body.token)
    if not payload or payload.get("purpose") != "approval":
        raise AuthorizationError("Invalid or expired approval token")

    user_id = payload["sub"]
    user = await user_service.get_by_id(user_id)
    if not user:
        raise NotFoundError("User not found")

    await user_service.update_user(
        user_id,
        status="active",
        role=body.role,
        allowed_repos=body.allowed_repos,
        allowed_channels=body.allowed_channels,
        allowed_db_tables=body.allowed_db_tables,
    )

    log.info("user_approved", user_id=user_id, username=user["username"], role=body.role)
    audit_logger.log_event("admin_approve_user", details=f"Approved {user['username']} as {body.role}")

    # Send notification email
    try:
        from app.services.email_service import send_user_notification
        updated = await user_service.get_by_id(user_id)
        await send_user_notification(updated, approved=True)
    except Exception as e:
        log.warning("approval_notification_failed", error=str(e))

    return {"success": True, "message": f"User {user['username']} approved as {body.role}"}


@router.post("/reject")
async def reject_user(
    body: RejectionRequest,
    user_service: UserService = Depends(get_user_service),
) -> dict:
    """Reject a pending user."""
    payload = decode_access_token(body.token)
    if not payload or payload.get("purpose") != "approval":
        raise AuthorizationError("Invalid or expired approval token")

    user_id = payload["sub"]
    user = await user_service.get_by_id(user_id)
    if not user:
        raise NotFoundError("User not found")

    await user_service.update_user(user_id, status="rejected")

    log.info("user_rejected", user_id=user_id, username=user["username"], reason=body.reason)
    audit_logger.log_event("admin_reject_user", details=f"Rejected {user['username']}: {body.reason}")

    try:
        from app.services.email_service import send_user_notification
        await send_user_notification(user, approved=False, reason=body.reason)
    except Exception as e:
        log.warning("rejection_notification_failed", error=str(e))

    return {"success": True, "message": f"User {user['username']} rejected"}


@router.post("/approve-user/{user_id}")
async def approve_user_direct(
    user_id: str,
    updates: dict,
    _admin: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    """Approve a user directly from admin panel (no email token needed)."""
    user = await user_service.get_by_id(user_id)
    if not user:
        raise NotFoundError("User not found")

    role = updates.get("role", "member")
    await user_service.update_user(
        user_id,
        status="active",
        role=role,
        allowed_repos=updates.get("allowed_repos", ["*"]),
        allowed_channels=updates.get("allowed_channels", ["*"]),
        allowed_db_tables=updates.get("allowed_db_tables", ["*"]),
    )

    log.info("user_approved_direct", user_id=user_id, username=user["username"], role=role, admin=_admin["username"])
    audit_logger.log_event("admin_approve_user", user_id=_admin["id"], username=_admin["username"],
                           details=f"Directly approved {user['username']} as {role}")

    return {"success": True, "message": f"User {user['username']} approved as {role}"}
