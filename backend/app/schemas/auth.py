from __future__ import annotations

from pydantic import BaseModel


class SignupRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserPublic(BaseModel):
    id: str
    username: str
    email: str
    role: str
    allowed_repos: list[str]
    allowed_channels: list[str]
    allowed_db_tables: list[str]
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
