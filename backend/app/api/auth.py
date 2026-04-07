"""Authentication endpoints: signup, login, me — with full audit logging."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, get_user_service
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserPublic
from app.security.audit_log import audit_logger
from app.security.jwt_auth import create_access_token
from app.services.user_service import UserService
from app.utils.errors import AuthenticationError, DatabaseError, ValidationError
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = get_logger("api.auth")


def _user_to_public(user: dict) -> UserPublic:
    return UserPublic(
        id=user["id"], username=user["username"], email=user["email"],
        role=user["role"], allowed_repos=user["allowed_repos"],
        allowed_channels=user["allowed_channels"],
        allowed_db_tables=user["allowed_db_tables"], is_active=user["is_active"],
    )


@router.post("/signup", response_model=TokenResponse)
async def signup(
    body: SignupRequest,
    user_service: UserService = Depends(get_user_service),
) -> TokenResponse:
    log.info("signup_attempt", email=body.email, username=body.username)

    # Validate password strength
    if len(body.password) < 8:
        log.warning("signup_weak_password", email=body.email, reason="too_short")
        raise ValidationError("Password must be at least 8 characters")
    if not any(c.isupper() for c in body.password):
        log.warning("signup_weak_password", email=body.email, reason="no_uppercase")
        raise ValidationError("Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in body.password):
        log.warning("signup_weak_password", email=body.email, reason="no_digit")
        raise ValidationError("Password must contain at least one number")

    # Check duplicates
    try:
        existing = await user_service.get_by_email(body.email)
    except Exception as e:
        log.error("signup_db_error", error=str(e), email=body.email)
        raise DatabaseError("Failed to check existing user") from e

    if existing:
        log.warning("signup_duplicate_email", email=body.email)
        raise ValidationError("Email already registered")

    # Create user
    try:
        user = await user_service.create_user(
            username=body.username, email=body.email,
            password=body.password, role="viewer",
        )
    except Exception as e:
        log.error("signup_create_failed", error=str(e), email=body.email)
        raise DatabaseError("Failed to create user account") from e

    token = create_access_token({"sub": user["id"], "role": user["role"]})

    log.info("signup_success", user_id=user["id"], username=user["username"], role=user["role"])
    audit_logger.log_event("auth_signup", user_id=user["id"], username=user["username"])

    return TokenResponse(access_token=token, user=_user_to_public(user))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    user_service: UserService = Depends(get_user_service),
) -> TokenResponse:
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

    token = create_access_token({"sub": user["id"], "role": user["role"]})

    log.info("login_success", user_id=user["id"], username=user["username"], role=user["role"])
    audit_logger.log_event("auth_login", user_id=user["id"], username=user["username"])

    return TokenResponse(access_token=token, user=_user_to_public(user))


@router.get("/me", response_model=UserPublic)
async def get_me(user: dict = Depends(get_current_user)) -> UserPublic:
    return _user_to_public(user)
