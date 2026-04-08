"""Google Gemini provider - 4 model variants."""
from __future__ import annotations

import importlib
import json
from typing import AsyncIterator

from app.config import settings
from app.llm.base import ChatEvent, ChatEventType, LLMProvider, Message, ToolDefinition
from app.utils.logging import get_logger

log = get_logger("llm.gemini")

GEMINI_MODELS = {
    "gemini-2.5-flash-lite": {
        "display": "Gemini 2.5 Flash Lite",
        "api_model": "gemini-2.5-flash-lite",
    },
    "gemini-2.5-flash": {
        "display": "Gemini 2.5 Flash",
        "api_model": "gemini-2.5-flash",
    },
    "gemini-3.1-flash-lite": {
        "display": "Gemini 3.1 Flash Lite",
        "api_model": "gemini-3.1-flash-lite-preview",
    },
    "gemini-3-flash": {
        "display": "Gemini 3 Flash",
        "api_model": "gemini-3-flash-preview",
    },
}


def gemini_sdk_available() -> bool:
    try:
        importlib.import_module("google.genai")
        return True
    except Exception:
        return False


def _load_genai_module():
    try:
        return importlib.import_module("google.genai")
    except Exception as e:
        raise RuntimeError(
            "Gemini SDK is not installed. Install backend dependencies with "
            "`pip install -r backend/requirements.txt`."
        ) from e


def _build_system_instruction(messages: list[Message]) -> str | None:
    parts = [m.content for m in messages if m.role == "system"]
    return "\n".join(parts) if parts else None


def _parse_tool_arguments(raw: str | dict | None) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def _build_contents(messages: list[Message]) -> list[dict]:
    contents: list[dict] = []
    for message in messages:
        if message.role == "system":
            continue
        if message.role == "assistant" and message.tool_calls:
            parts = []
            if message.content:
                parts.append({"text": message.content})
            # Gemini preview models can reject replayed function calls unless the original
            # thought signature is preserved. We don't retain that provider-specific field,
            # so only carry assistant text forward and rely on the functionResponse turn.
            if parts:
                contents.append({"role": "model", "parts": parts})
            continue
        if message.role == "tool":
            function_response: dict = {
                "name": message.tool_name,
                "response": {"result": message.content},
            }
            if message.tool_call_id:
                function_response["id"] = message.tool_call_id
            contents.append({
                "role": "user",
                "parts": [{"functionResponse": function_response}],
            })
            continue

        contents.append({
            "role": "user" if message.role == "user" else "model",
            "parts": [{"text": message.content}],
        })
    return contents


def _build_tools(tools: list[ToolDefinition]) -> list[dict]:
    declarations = [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in tools]
    return [{"function_declarations": declarations}]


def _extract_events_from_parts(parts) -> list[ChatEvent]:
    events = []
    if not parts:
        return events
    for part in parts:
        if hasattr(part, "function_call") and part.function_call:
            fc = part.function_call
            events.append(ChatEvent(
                type=ChatEventType.TOOL_CALL,
                tool_name=fc.name,
                tool_args=dict(fc.args) if fc.args else {},
                tool_call_id=getattr(fc, "id", None) or f"call_{fc.name}",
            ))
        elif hasattr(part, "text") and part.text:
            events.append(ChatEvent(type=ChatEventType.TEXT_CHUNK, content=part.text))
    return events


class GeminiProvider(LLMProvider):
    def __init__(self, model_id: str):
        self.provider_name = "google"
        self.model_id = model_id
        info = GEMINI_MODELS.get(model_id, {"display": model_id, "api_model": model_id})
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
        try:
            genai = _load_genai_module()
        except RuntimeError as e:
            log.error("gemini_sdk_missing", model=self.model_id, error=str(e))
            yield ChatEvent(type=ChatEventType.ERROR, error=str(e))
            return

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

    async def _stream(self, client, contents, config):
        response = client.models.generate_content_stream(
            model=self._api_model, contents=contents, config=config,
        )
        for chunk in response:
            if chunk.candidates and getattr(chunk.candidates[0], "content", None):
                for event in _extract_events_from_parts(getattr(chunk.candidates[0].content, "parts", None)):
                    yield event

    def _non_stream(self, client, contents, config):
        response = client.models.generate_content(
            model=self._api_model, contents=contents, config=config,
        )
        if response.candidates and getattr(response.candidates[0], "content", None):
            yield from _extract_events_from_parts(getattr(response.candidates[0].content, "parts", None))

    async def health_check(self) -> bool:
        return bool(settings.google_api_key) and gemini_sdk_available()
