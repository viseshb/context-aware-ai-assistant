from __future__ import annotations

from pydantic import BaseModel


class SignupRequest(BaseModel):
    username: str
    email: str
    password: str
    team_code: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class UserPublic(BaseModel):
    id: str
    username: str
    email: str
    role: str
    status: str
    allowed_repos: list[str]
    allowed_channels: list[str]
    allowed_db_tables: list[str]
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class PendingResponse(BaseModel):
    status: str = "pending"
    pending_token: str
    message: str = "Your signup request has been sent to the admin. You'll be notified once approved."


class ApprovalRequest(BaseModel):
    token: str
    role: str = "member"
    allowed_repos: list[str] = ["*"]
    allowed_channels: list[str] = ["*"]
    allowed_db_tables: list[str] = ["*"]


class RejectionRequest(BaseModel):
    token: str
    reason: str = ""
