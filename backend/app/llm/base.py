"""Abstract base class for LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator


class ChatEventType(str, Enum):
    TEXT_CHUNK = "text_chunk"
    TOOL_CALL = "tool_call"
    DONE = "done"
    ERROR = "error"


@dataclass
class ChatEvent:
    type: ChatEventType
    content: str = ""
    tool_name: str = ""
    tool_args: dict = field(default_factory=dict)
    tool_call_id: str = ""
    error: str = ""
    metrics: dict = field(default_factory=dict)


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema


@dataclass
class Message:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_call_id: str = ""
    tool_name: str = ""
    tool_calls: list[dict] = field(default_factory=list)


class LLMProvider(ABC):
    provider_name: str
    model_id: str
    display_name: str
    tier: str  # "free" | "paid"
    supports_tools: bool = True
    supports_streaming: bool = True

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        stream: bool = True,
    ) -> AsyncIterator[ChatEvent]:
        """Yield ChatEvents: text chunks, tool calls, done signal."""
        yield  # type: ignore  # pragma: no cover

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if this provider is reachable and configured."""
        ...
