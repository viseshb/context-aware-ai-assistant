"""OpenAI provider for gpt-4.1-mini."""
from __future__ import annotations

from typing import AsyncIterator

from app.config import settings
from app.llm.base import ChatEvent, ChatEventType, LLMProvider, Message, ToolDefinition
from app.llm.providers._openai_compat import (
    extract_openai_response,
    messages_to_openai_format,
    stream_openai_response,
    tools_to_openai_format,
)
from app.utils.logging import get_logger

log = get_logger("llm.openai")


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "openai"
        self.model_id = "gpt-4.1-mini"
        self.display_name = "OpenAI GPT-4.1 Mini"
        self.tier = "paid"
        self.supports_tools = True
        self.supports_streaming = True

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        stream: bool = True,
    ) -> AsyncIterator[ChatEvent]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        kwargs = self._build_request(messages, tools, stream)

        try:
            response = await client.chat.completions.create(**kwargs)

            if stream:
                async for event in stream_openai_response(response):
                    yield event
            else:
                for event in extract_openai_response(response):
                    yield event

            yield ChatEvent(type=ChatEventType.DONE)
        except Exception as e:
            log.error("openai_error", error=str(e), model=self.model_id)
            yield ChatEvent(type=ChatEventType.ERROR, error=str(e))

    def _build_request(self, messages: list[Message], tools: list[ToolDefinition] | None, stream: bool) -> dict:
        kwargs: dict = {
            "model": self.model_id,
            "messages": messages_to_openai_format(messages),
            "stream": stream,
        }
        if tools:
            kwargs["tools"] = tools_to_openai_format(tools)
        return kwargs

    async def health_check(self) -> bool:
        return bool(settings.openai_api_key)
