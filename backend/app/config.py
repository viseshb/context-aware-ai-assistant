from __future__ import annotations

import secrets
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _csv_to_list(val: str) -> list[str]:
    """Split comma-separated string into list, stripping whitespace."""
    if not val:
        return []
    return [s.strip() for s in val.split(",") if s.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM API keys
    google_api_key: str = ""
    nvidia_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    claude_cli_path: str = "claude"

    # Data sources
    github_token: str = ""
    slack_bot_token: str = ""
    database_url: str = ""

    # Security — stored as CSV strings, accessed as lists via properties
    allowed_repos_csv: str = ""
    allowed_slack_channels_csv: str = ""
    rate_limit: str = "30/minute"
    max_message_length: int = 10_000

    # Auth
    jwt_secret: str = ""
    jwt_expiry_minutes: int = 30
    users_db_path: str = "users.db"

    # Contact form
    contact_email: str = "visesh66@gmail.com"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # App
    cors_origins_csv: str = "http://localhost:3000"
    log_level: str = "INFO"

    @property
    def allowed_repos(self) -> list[str]:
        return _csv_to_list(self.allowed_repos_csv)

    @property
    def allowed_channels(self) -> list[str]:
        return _csv_to_list(self.allowed_slack_channels_csv)

    @property
    def cors_origins(self) -> list[str]:
        return _csv_to_list(self.cors_origins_csv)

    def ensure_jwt_secret(self) -> str:
        if not self.jwt_secret:
            self.jwt_secret = secrets.token_urlsafe(32)
        return self.jwt_secret


settings = Settings()
