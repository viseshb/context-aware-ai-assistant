"""NVIDIA NIM provider — OpenAI-compatible API for 3 models."""
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

log = get_logger("llm.nvidia")

NVIDIA_MODELS = {
    "nvidia/llama-4-maverick": {
        "display": "Llama 4 Maverick",
        "api_model": "meta/llama-4-maverick-17b-128e-instruct",
    },
    "nvidia/ministral-14b": {
        "display": "Ministral 14B",
        "api_model": "mistralai/ministral-8b-instruct",
    },
    "nvidia/kimi-k2": {
        "display": "Kimi K2",
        "api_model": "moonshotai/kimi-k2-instruct",
    },
}

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaProvider(LLMProvider):
    def __init__(self, model_id: str):
        self.provider_name = "nvidia"
        self.model_id = model_id
        info = NVIDIA_MODELS[model_id]
        self.display_name = info["display"]
        self._api_model = info["api_model"]
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        stream: bool = True,
    ) -> AsyncIterator[ChatEvent]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.nvidia_api_key, base_url=NVIDIA_BASE_URL)
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
            log.error("nvidia_error", error=str(e), model=self.model_id)
            yield ChatEvent(type=ChatEventType.ERROR, error=str(e))

    def _build_request(self, messages: list[Message], tools: list[ToolDefinition] | None, stream: bool) -> dict:
        kwargs: dict = {
            "model": self._api_model,
            "messages": messages_to_openai_format(messages),
            "stream": stream,
        }
        if tools:
            kwargs["tools"] = tools_to_openai_format(tools)
        return kwargs

    async def health_check(self) -> bool:
        return bool(settings.nvidia_api_key)
