"""Shared helpers for OpenAI-compatible providers (OpenAI, NVIDIA NIM)."""
from __future__ import annotations

import json
from typing import AsyncIterator

from app.llm.base import ChatEvent, ChatEventType, Message, ToolDefinition


def messages_to_openai_format(messages: list[Message]) -> list[dict]:
    result = []
    for msg in messages:
        entry: dict = {"role": msg.role, "content": msg.content}
        if msg.role == "tool":
            entry["tool_call_id"] = msg.tool_call_id
        result.append(entry)
    return result


def tools_to_openai_format(tools: list[ToolDefinition]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


def _parse_tool_args(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def _tool_call_event(tc) -> ChatEvent | None:
    """Extract a ChatEvent from an OpenAI tool call object."""
    if not tc.function or not tc.function.name:
        return None
    return ChatEvent(
        type=ChatEventType.TOOL_CALL,
        tool_name=tc.function.name,
        tool_args=_parse_tool_args(tc.function.arguments),
        tool_call_id=tc.id or f"call_{tc.function.name}",
    )


async def stream_openai_response(response) -> AsyncIterator[ChatEvent]:
    """Yield ChatEvents from an OpenAI streaming response."""
    async for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if not delta:
            continue
        if delta.content:
            yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content=delta.content)
        if delta.tool_calls:
            for tc in delta.tool_calls:
                event = _tool_call_event(tc)
                if event:
                    yield event


def extract_openai_response(response) -> list[ChatEvent]:
    """Extract ChatEvents from a non-streaming OpenAI response."""
    events: list[ChatEvent] = []
    choice = response.choices[0]
    if choice.message.content:
        events.append(ChatEvent(type=ChatEventType.TEXT_CHUNK, content=choice.message.content))
    if choice.message.tool_calls:
        for tc in choice.message.tool_calls:
            event = _tool_call_event(tc)
            if event:
                events.append(event)
    return events
