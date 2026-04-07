"""Google Gemini provider — 4 model variants."""
from __future__ import annotations

from typing import AsyncIterator

from app.config import settings
from app.llm.base import ChatEvent, ChatEventType, LLMProvider, Message, ToolDefinition
from app.utils.logging import get_logger

log = get_logger("llm.gemini")

GEMINI_MODELS = {
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash Lite",
    "gemini-3-flash": "Gemini 3 Flash",
}


def _build_system_instruction(messages: list[Message]) -> str | None:
    parts = [m.content for m in messages if m.role == "system"]
    return "\n".join(parts) if parts else None


def _build_contents(messages: list[Message]) -> list[dict]:
    return [
        {"role": "user" if m.role == "user" else "model", "parts": [{"text": m.content}]}
        for m in messages if m.role != "system"
    ]


def _build_tools(tools: list[ToolDefinition]) -> list[dict]:
    declarations = [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in tools]
    return [{"function_declarations": declarations}]


def _extract_events_from_parts(parts) -> list[ChatEvent]:
    events = []
    for part in parts:
        if hasattr(part, "function_call") and part.function_call:
            fc = part.function_call
            events.append(ChatEvent(
                type=ChatEventType.TOOL_CALL,
                tool_name=fc.name,
                tool_args=dict(fc.args) if fc.args else {},
                tool_call_id=f"call_{fc.name}",
            ))
        elif hasattr(part, "text") and part.text:
            events.append(ChatEvent(type=ChatEventType.TEXT_CHUNK, content=part.text))
    return events


class GeminiProvider(LLMProvider):
    def __init__(self, model_id: str):
        self.provider_name = "google"
        self.model_id = model_id
        self.display_name = GEMINI_MODELS.get(model_id, model_id)
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        stream: bool = True,
    ) -> AsyncIterator[ChatEvent]:
        from google import genai

        client = genai.Client(api_key=settings.google_api_key)
        config = self._build_config(messages, tools)
        contents = _build_contents(messages)

        try:
            if stream:
                async for event in self._stream(client, contents, config):
                    yield event
            else:
                for event in self._non_stream(client, contents, config):
                    yield event
            yield ChatEvent(type=ChatEventType.DONE)
        except Exception as e:
            log.error("gemini_error", model=self.model_id, error=str(e))
            yield ChatEvent(type=ChatEventType.ERROR, error=str(e))

    def _build_config(self, messages: list[Message], tools: list[ToolDefinition] | None) -> dict | None:
        config: dict = {}
        system = _build_system_instruction(messages)
        if system:
            config["system_instruction"] = system
        if tools:
            config["tools"] = _build_tools(tools)
        return config or None

    def _stream(self, client, contents, config):
        response = client.models.generate_content_stream(
            model=self.model_id, contents=contents, config=config,
        )
        for chunk in response:
            if chunk.candidates:
                yield from _extract_events_from_parts(chunk.candidates[0].content.parts)

    def _non_stream(self, client, contents, config):
        response = client.models.generate_content(
            model=self.model_id, contents=contents, config=config,
        )
        if response.candidates:
            yield from _extract_events_from_parts(response.candidates[0].content.parts)

    async def health_check(self) -> bool:
        return bool(settings.google_api_key)
