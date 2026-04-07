from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    model_id: str
    message: str
    conversation_id: str = ""


class ToolCallInfo(BaseModel):
    name: str
    args: dict = {}
    result: str = ""
    duration_ms: int = 0
    status: str = "success"


class ContextSource(BaseModel):
    type: str  # "github", "slack", "db"
    detail: str = ""


class ChatResponse(BaseModel):
    content: str
    tool_calls: list[ToolCallInfo] = []
    context_sources: list[ContextSource] = []
    model_id: str = ""
    summary: str | None = None
