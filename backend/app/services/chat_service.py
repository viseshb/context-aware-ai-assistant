"""Chat service — orchestrates LLM calls, MCP tool execution, security checks."""
from __future__ import annotations

import time

from fastapi import WebSocket

from app.llm.base import ChatEvent, ChatEventType, Message
from app.llm.registry import LLMRegistry
from app.llm.tool_adapter import filter_tools_for_user, mcp_to_tool_definitions
from app.mcp_layer.manager import MCPManager
from app.security.rbac import validate_tool_call
from app.utils.errors import AuthorizationError
from app.utils.logging import get_logger

log = get_logger("chat_service")

MAX_TOOL_CALLS_PER_TURN = 5

SYSTEM_PROMPT = """You are a Context-Aware AI Assistant that helps users query their GitHub repositories, Slack conversations, and PostgreSQL databases using natural language.

When answering questions:
- Be concise and informative
- If you used tools, mention the data source in your response
- Format code and data clearly using markdown
- If you don't have access to a tool needed, explain what access is required"""


class ChatService:
    def __init__(self, registry: LLMRegistry, mcp_manager: MCPManager | None = None):
        self._registry = registry
        self._mcp = mcp_manager

    async def handle_ws_chat(
        self,
        ws: WebSocket,
        model_id: str,
        message: str,
        conversation_id: str,
        user: dict,
    ) -> None:
        """Handle a chat message via WebSocket with streaming + tool calls."""
        provider = self._registry.get(model_id)

        # Get RBAC-filtered tools
        tools = None
        tool_defs = None
        if self._mcp and provider.supports_tools:
            all_tools = self._mcp.get_all_tools()
            user_tools = filter_tools_for_user(all_tools, user)
            if user_tools:
                tool_defs = mcp_to_tool_definitions(user_tools)
                tools = user_tools

        messages = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=message),
        ]

        await ws.send_json({"type": "stream_start", "conversation_id": conversation_id})

        context_sources: list[dict] = []
        tool_call_count = 0

        try:
            # Tool call loop — LLM may call multiple tools sequentially
            while True:
                full_content = ""
                pending_tool_calls: list[ChatEvent] = []

                async for event in provider.chat(messages, tool_defs, stream=True):
                    if event.type == ChatEventType.TEXT_CHUNK:
                        full_content += event.content
                        await ws.send_json({
                            "type": "stream_chunk",
                            "content": event.content,
                            "conversation_id": conversation_id,
                        })
                    elif event.type == ChatEventType.TOOL_CALL:
                        pending_tool_calls.append(event)
                    elif event.type == ChatEventType.ERROR:
                        await ws.send_json({
                            "type": "error",
                            "message": event.error,
                            "code": "LLM_ERROR",
                        })
                        return
                    elif event.type == ChatEventType.DONE:
                        break

                # If no tool calls, we're done
                if not pending_tool_calls:
                    break

                # Execute tool calls
                if tool_call_count >= MAX_TOOL_CALLS_PER_TURN:
                    await ws.send_json({
                        "type": "stream_chunk",
                        "content": "\n\n*Tool call limit reached (max 5 per turn).*",
                        "conversation_id": conversation_id,
                    })
                    break

                # Add assistant message with tool calls
                if full_content:
                    messages.append(Message(role="assistant", content=full_content))

                for tc_event in pending_tool_calls:
                    tool_call_count += 1
                    tool_name = tc_event.tool_name
                    tool_args = tc_event.tool_args

                    # Send tool call start to frontend
                    await ws.send_json({
                        "type": "tool_call_start",
                        "tool": {"name": tool_name, "args": tool_args},
                        "conversation_id": conversation_id,
                    })

                    # RBAC validation
                    try:
                        validate_tool_call(user, tool_name, tool_args)
                    except AuthorizationError as e:
                        result = f"Permission denied: {e.message}"
                        await ws.send_json({
                            "type": "tool_call_result",
                            "tool": {"name": tool_name, "result": result, "duration_ms": 0},
                            "conversation_id": conversation_id,
                        })
                        messages.append(Message(
                            role="tool", content=result,
                            tool_call_id=tc_event.tool_call_id, tool_name=tool_name,
                        ))
                        continue

                    # Execute tool
                    start = time.monotonic()
                    result = await self._mcp.execute_tool(tool_name, tool_args)
                    duration_ms = int((time.monotonic() - start) * 1000)

                    # Track context source
                    server = self._mcp.get_server_for_tool(tool_name)
                    if server:
                        detail = tool_args.get("repo") or tool_args.get("channel") or tool_args.get("table") or ""
                        context_sources.append({"type": server, "detail": str(detail)})

                    # Send result to frontend
                    await ws.send_json({
                        "type": "tool_call_result",
                        "tool": {"name": tool_name, "result": result[:1000], "duration_ms": duration_ms},
                        "conversation_id": conversation_id,
                    })

                    # Feed result back to LLM
                    messages.append(Message(
                        role="tool", content=result,
                        tool_call_id=tc_event.tool_call_id, tool_name=tool_name,
                    ))

                # Continue the loop — LLM will generate response with tool results

            await ws.send_json({
                "type": "stream_end",
                "conversation_id": conversation_id,
                "context_sources": context_sources,
                "summary": None,
            })

        except Exception as e:
            log.error("chat_error", error=str(e), model=model_id)
            await ws.send_json({"type": "error", "message": str(e), "code": "CHAT_ERROR"})

    async def handle_rest_chat(self, model_id: str, message: str, user: dict) -> dict:
        """Non-streaming REST fallback."""
        provider = self._registry.get(model_id)
        messages = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=message),
        ]

        full_content = ""
        async for event in provider.chat(messages, tools=None, stream=False):
            if event.type == ChatEventType.TEXT_CHUNK:
                full_content += event.content
            elif event.type == ChatEventType.ERROR:
                return {"error": event.error}

        return {"content": full_content, "tool_calls": [], "context_sources": [], "model_id": model_id}
