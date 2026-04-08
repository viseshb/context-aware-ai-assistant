from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.config import settings


class ChatRequest(BaseModel):
    model_id: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=settings.max_message_length)
    conversation_id: str = Field(default="", max_length=120)

    @field_validator("model_id", "message")
    @classmethod
    def strip_required_fields(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("conversation_id")
    @classmethod
    def strip_conversation_id(cls, value: str) -> str:
        return value.strip()


class ToolCallInfo(BaseModel):
    name: str
    args: dict = {}
    result: str = ""
    duration_ms: int = 0
    status: str = "success"


class ContextSource(BaseModel):
    type: str  # "github", "slack", "db"
    detail: str = ""


class ChatMetrics(BaseModel):
    model_id: str = ""
    ttft_ms: int | None = None
    total_time_ms: int = 0
    tool_time_ms: int = 0
    tool_call_count: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    provider_model: str = ""
    response_chars: int = 0


class ChatResponse(BaseModel):
    content: str
    tool_calls: list[ToolCallInfo] = []
    context_sources: list[ContextSource] = []
    model_id: str = ""
    metrics: ChatMetrics | None = None
    summary: str | None = None
