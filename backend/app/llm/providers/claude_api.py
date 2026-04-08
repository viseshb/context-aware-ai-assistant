"""Claude API provider via Anthropic SDK."""
from __future__ import annotations

import importlib
import json
from typing import AsyncIterator

from app.config import settings
from app.llm.base import ChatEvent, ChatEventType, LLMProvider, Message, ToolDefinition
from app.utils.logging import get_logger

log = get_logger("llm.claude_api")


def anthropic_sdk_available() -> bool:
    try:
        importlib.import_module("anthropic")
        return True
    except Exception:
        return False


def _load_anthropic_module():
    try:
        return importlib.import_module("anthropic")
    except Exception as e:
        raise RuntimeError(
            "Anthropic SDK is not installed. Install backend dependencies with "
            "`pip install -r backend/requirements.txt`."
        ) from e


def _parse_tool_arguments(raw: str | dict | None) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def _split_messages(messages: list[Message]) -> tuple[str, list[dict]]:
    """Split into (system_prompt, conversation) in Anthropic format."""
    system_parts = []
    conv = []
    for msg in messages:
        if msg.role == "system":
            system_parts.append(msg.content)
        elif msg.role == "tool":
            conv.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": msg.tool_call_id, "content": msg.content}],
            })
        elif msg.role == "assistant" and msg.tool_calls:
            blocks = []
            if msg.content:
                blocks.append({"type": "text", "text": msg.content})
            for tool_call in msg.tool_calls:
                function = tool_call.get("function", {})
                blocks.append({
                    "type": "tool_use",
                    "id": tool_call.get("id") or f"call_{function.get('name', 'tool')}",
                    "name": function.get("name", ""),
                    "input": _parse_tool_arguments(function.get("arguments")),
                })
            conv.append({"role": "assistant", "content": blocks})
        else:
            conv.append({"role": msg.role, "content": msg.content})
    return "\n".join(system_parts), conv


def _tools_to_anthropic(tools: list[ToolDefinition]) -> list[dict]:
    return [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools]


def _extract_from_content_blocks(blocks) -> list[ChatEvent]:
    events = []
    for block in blocks:
        if block.type == "text":
            events.append(ChatEvent(type=ChatEventType.TEXT_CHUNK, content=block.text))
        elif block.type == "tool_use":
            events.append(ChatEvent(
                type=ChatEventType.TOOL_CALL,
                tool_name=block.name,
                tool_args=block.input if isinstance(block.input, dict) else {},
                tool_call_id=block.id,
            ))
    return events


class ClaudeAPIProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "anthropic"
        self.model_id = "claude-api"
        self.display_name = "Claude API"
        self.tier = "paid"
        self.supports_tools = True
        self.supports_streaming = True

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        stream: bool = True,
    ) -> AsyncIterator[ChatEvent]:
        try:
            anthropic = _load_anthropic_module()
        except RuntimeError as e:
            log.error("claude_api_sdk_missing", error=str(e))
            yield ChatEvent(type=ChatEventType.ERROR, error=str(e))
            return

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        kwargs = self._build_request(messages, tools)

        try:
            if stream:
                async for event in self._stream(client, kwargs):
                    yield event
            else:
                for event in await self._non_stream(client, kwargs):
                    yield event
            yield ChatEvent(type=ChatEventType.DONE)
        except Exception as e:
            log.error("claude_api_error", error=str(e))
            yield ChatEvent(type=ChatEventType.ERROR, error=str(e))

    def _build_request(self, messages: list[Message], tools: list[ToolDefinition] | None) -> dict:
        system_prompt, conv = _split_messages(messages)
        kwargs: dict = {"model": "claude-sonnet-4-20250514", "max_tokens": 4096, "messages": conv}
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = _tools_to_anthropic(tools)
        return kwargs

    async def _stream(self, client, kwargs) -> AsyncIterator[ChatEvent]:
        async with client.messages.stream(**kwargs) as stream_resp:
            async for event in stream_resp:
                if event.type == "content_block_delta" and hasattr(event.delta, "text"):
                    yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content=event.delta.text)
                elif event.type == "message_stop":
                    final = stream_resp.get_final_message()
                    for evt in _extract_from_content_blocks(final.content):
                        if evt.type == ChatEventType.TOOL_CALL:
                            yield evt

    async def _non_stream(self, client, kwargs) -> list[ChatEvent]:
        response = await client.messages.create(**kwargs)
        return _extract_from_content_blocks(response.content)

    async def health_check(self) -> bool:
        return bool(settings.anthropic_api_key) and anthropic_sdk_available()
