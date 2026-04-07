"""Authentication endpoints: signup, login, me — mode-aware with status checks."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.config import settings as app_settings
from app.dependencies import get_current_user, get_user_service
from app.schemas.auth import (
    LoginRequest, PendingResponse, SignupRequest, TokenResponse, UserPublic,
)
from app.security.audit_log import audit_logger
from app.security.jwt_auth import create_access_token
from app.services.user_service import UserService
from app.utils.errors import AuthenticationError, AuthorizationError, DatabaseError, ValidationError
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = get_logger("api.auth")


def _user_to_public(user: dict) -> UserPublic:
    return UserPublic(
        id=user["id"], username=user["username"], email=user["email"],
        role=user["role"], status=user.get("status", "active"),
        allowed_repos=user["allowed_repos"], allowed_channels=user["allowed_channels"],
        allowed_db_tables=user["allowed_db_tables"], is_active=user["is_active"],
    )


def _validate_password(password: str, email: str) -> None:
    if len(password) < 8:
        log.warning("signup_weak_password", email=email, reason="too_short")
        raise ValidationError("Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        log.warning("signup_weak_password", email=email, reason="no_uppercase")
        raise ValidationError("Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in password):
        log.warning("signup_weak_password", email=email, reason="no_digit")
        raise ValidationError("Password must contain at least one number")


@router.post("/signup")
async def signup(
    body: SignupRequest,
    user_service: UserService = Depends(get_user_service),
) -> TokenResponse | PendingResponse:
    log.info("signup_attempt", email=body.email, username=body.username, mode=app_settings.instance_mode)

    # Solo mode: no signup allowed — admin created via CLI
    if app_settings.instance_mode == "solo":
        log.warning("signup_blocked_solo_mode", email=body.email)
        raise AuthorizationError("Solo mode — admin account is created via CLI. Please log in.")

    # Team mode: validate team code
    if not body.team_code:
        raise ValidationError("Team code is required to join a team")
    if body.team_code != app_settings.team_code:
        log.warning("signup_invalid_team_code", email=body.email)
        raise AuthorizationError("Invalid team code")

    _validate_password(body.password, body.email)

    # Check duplicates
    try:
        existing = await user_service.get_by_email(body.email)
    except Exception as e:
        log.error("signup_db_error", error=str(e), email=body.email)
        raise DatabaseError("Failed to check existing user") from e

    if existing:
        log.warning("signup_duplicate_email", email=body.email)
        raise ValidationError("Email already registered")

    # Create pending user
    try:
        user = await user_service.create_user(
            username=body.username, email=body.email,
            password=body.password, role="viewer", status="pending",
        )
    except Exception as e:
        log.error("signup_create_failed", error=str(e), email=body.email)
        raise DatabaseError("Failed to create user account") from e

    # Send approval email to admin
    try:
        from app.services.email_service import send_approval_email
        await send_approval_email(user)
    except Exception as e:
        log.warning("signup_approval_email_failed", error=str(e), email=body.email)

    # Return pending token (limited scope — can only poll status)
    pending_token = create_access_token(
        {"sub": user["id"], "purpose": "pending_check"},
    )

    log.info("signup_pending", user_id=user["id"], username=user["username"])
    audit_logger.log_event("auth_signup_pending", user_id=user["id"], username=user["username"])

    return PendingResponse(pending_token=pending_token)


@router.post("/login")
async def login(
    body: LoginRequest,
    user_service: UserService = Depends(get_user_service),
) -> TokenResponse | PendingResponse:
    log.info("login_attempt", email=body.email)

    try:
        user = await user_service.authenticate(body.email, body.password)
    except Exception as e:
        log.error("login_db_error", error=str(e), email=body.email)
        raise DatabaseError("Authentication service unavailable") from e

    if not user:
        log.warning("login_failed", email=body.email, reason="invalid_credentials")
        audit_logger.log_event("auth_login_failed", details=f"Failed login for {body.email}")
        raise AuthenticationError("Invalid email or password")

    # Check user status
    status = user.get("status", "active")

    if status == "pending":
        log.info("login_pending_user", email=body.email)
        pending_token = create_access_token({"sub": user["id"], "purpose": "pending_check"})
        return PendingResponse(pending_token=pending_token)

    if status == "rejected":
        log.warning("login_rejected_user", email=body.email)
        raise AuthorizationError("Your signup request was denied. Contact the admin.")

    token = create_access_token({"sub": user["id"], "role": user["role"]})

    log.info("login_success", user_id=user["id"], username=user["username"], role=user["role"])
    audit_logger.log_event("auth_login", user_id=user["id"], username=user["username"])

    return TokenResponse(access_token=token, user=_user_to_public(user))


@router.get("/me", response_model=UserPublic)
async def get_me(user: dict = Depends(get_current_user)) -> UserPublic:
    return _user_to_public(user)
