"""Chat service - orchestrates LLM calls, MCP tool execution, and chat context."""
from __future__ import annotations

import ast
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from fastapi import WebSocket

from app.config import settings
from app.llm.base import ChatEvent, ChatEventType, Message, ToolDefinition
from app.llm.registry import LLMRegistry
from app.llm.tool_adapter import filter_tools_for_user, mcp_to_tool_definitions
from app.mcp_layer.manager import MCPManager, MCPTool
from app.security.audit_log import audit_logger
from app.security.pii_filter import pii_filter
from app.security.rbac import filter_tool_result_for_user, validate_tool_call
from app.services.user_service import UserService
from app.utils.errors import AppError, AuthorizationError, ValidationError
from app.utils.logging import get_logger

log = get_logger("chat_service")

MAX_TOOL_CALLS_PER_TURN = 8
MAX_HISTORY_MESSAGES = 20
MAX_TOOL_RESULT_PREVIEW_CHARS = 1000
OUT_OF_SCOPE_RESPONSE = (
    "That request is outside this assistant's scope. I can only help with "
    "GitHub repositories/code/issues/PRs/commits, Slack channels/messages/threads, "
    "PostgreSQL tables/schema/queries, and questions about this assistant's models, "
    "roles, permissions, MCP tools, or chat behavior."
)

DIRECT_RELEVANCE_PATTERNS = (
    r"\bgithub\b",
    r"\brepos?\b",
    r"\brepositor(?:y|ies)\b",
    r"\bpull requests?\b",
    r"\bprs?\b",
    r"\bissues?\b",
    r"\bcommits?\b",
    r"\bworkflows?\b",
    r"\bdeploy(?:ment)?\b",
    r"\bbranches?\b",
    r"\breadme\b",
    r"\bslack\b",
    r"\bchannels?\b",
    r"\bthreads?\b",
    r"\bpostgres(?:ql)?\b",
    r"\bdatabase\b",
    r"\bsql\b",
    r"\btables?\b",
    r"\bschema\b",
    r"\bcolumns?\b",
    r"\bmcp\b",
    r"\btools?\b",
    r"\bmodels?\b",
    r"\bprovider\b",
    r"\bllm\b",
    r"\bprompt\b",
    r"\badmin\b",
    r"\bmember\b",
    r"\bviewer\b",
    r"\ballowlists?\b",
    r"\bpermissions?\b",
    r"\bprivate repos?\b",
    r"\btoken\b",
    r"\bwebsocket\b",
    r"\bconversation[_ -]?id\b",
    r"\bfollow[- ]?up\b",
    r"\btimestamp\b",
    r"\blocal time\b",
    r"\bcurrent year\b",
)
FOLLOW_UP_RELEVANCE_PATTERNS = (
    r"\bthat (repo|repository|file|branch|channel|thread|table|query|issue|pr|pull request|commit|result|one)\b",
    r"\bthose (repos|results|issues|prs|pull requests|messages|rows|commits)\b",
    r"\bsame (repo|repository|file|branch|channel|thread|table|query)\b",
    r"\b(previous|earlier|above|last one|last result)\b",
    r"^(what|how) about\b",
    r"^(and\s+)?how many did i (make|author|commit)\b",
    r"^(and\s+)?how many of (those|them)\b",
    r"^(and\s+)?what about (me|mine)\b",
    r"\b(open|closed|private) ones\b",
    r"^from (today|yesterday|last week|this week|this month|this year)\b",
)
DIRECT_RELEVANCE_REGEX = re.compile("|".join(DIRECT_RELEVANCE_PATTERNS), re.IGNORECASE)
FOLLOW_UP_RELEVANCE_REGEX = re.compile("|".join(FOLLOW_UP_RELEVANCE_PATTERNS), re.IGNORECASE)
REPO_OR_PATH_REGEX = re.compile(r"\b(?:[\w.-]+/)+[\w.-]+\b")
SQL_QUERY_REGEX = re.compile(r"\bselect\b[\s\S]{0,400}\bfrom\b", re.IGNORECASE)
SERIALIZED_TEXT_BLOCK_REGEX = re.compile(r"\[[^\[\]]{1,4000}\]", re.DOTALL)

BASE_SYSTEM_PROMPT = """You are the Context-Aware AI Assistant - a tool-calling agent that answers questions by querying live GitHub, Slack, and PostgreSQL data through MCP (Model Context Protocol).

=== HARD RULES (never violate) ===
1. NEVER fabricate tool outputs, repo names, channel messages, table names, SQL results, file contents, issue numbers, or user info. If you did not call a tool this turn, you do not have live data.
2. NEVER run or suggest mutating SQL (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE). All database access is read-only. If asked to mutate, explain the restriction and suggest an alternative.
3. NEVER expose raw API tokens, connection strings, or credentials that appear in tool responses.
4. If a tool returns an error, permission denial, or empty result, say so plainly with the exact error context and suggest a concrete next step (check allowlists, verify resource name, adjust filters, etc.).
5. ONLY answer requests that are relevant to this assistant's supported scope: GitHub, Slack, PostgreSQL, or this assistant's own models, permissions, tools, and chat behavior. Politely refuse unrelated requests.

=== TEMPORAL CONTEXT ===

Current timestamp: {current_timestamp}

Use this to resolve all relative time references:
- "this year" / "in 2026" -> since January 1 of the current year from the timestamp above.
- "this month" -> since the 1st of the current month.
- "last week" -> the 7-day window ending at the start of the current week.
- "recently" / "latest" -> last 7 days from now.
- "today" -> the current date from the timestamp.
- "yesterday" -> the day before the current date.

When building tool calls with date filters (commit history, Slack search, SQL WHERE clauses), always compute concrete ISO-8601 dates from the timestamp above - never pass vague words like "recent" to tool parameters.

=== TOOLS AVAILABLE (18 across 3 MCP servers) ===

GitHub Server (9):
- github_list_repos - list org/user repositories
- github_get_repo_metrics - repo-level counts for commits, PRs, workflows, and deployment workflows
- github_count_commits - exact commit counts with optional author/date/branch/path filters
- github_search_code - search code across repos by query
- github_get_issues - list/filter issues (state, labels, assignee)
- github_get_pull_requests - list/filter PRs (state, branch, author)
- github_read_file - read a file's contents at a given ref/branch
- github_get_repo_info - repo metadata (stars, language, description, default branch)
- github_get_commit_history - recent commits (branch, author, path, date range)

Slack Server (5):
- slack_search_messages - full-text search across accessible channels
- slack_list_channels - list channels the bot can see
- slack_get_thread - fetch all replies in a thread by timestamp
- slack_get_channel_history - recent messages in a channel
- slack_get_user_info - look up a Slack user's profile by ID

PostgreSQL Server (4):
- db_list_tables - list all tables in the connected database
- db_get_schema - show columns, types, and constraints for a table
- db_query - execute a read-only SELECT query
- db_explain_query - run EXPLAIN ANALYZE on a query (for optimization)

=== WHEN AND HOW TO USE TOOLS ===

Use tools when the question involves live/current data: specific repos, files, issues, PRs, commits, Slack messages/channels/threads, database tables/rows/metrics, or anything that depends on external state.

Do NOT use tools for general knowledge, coding help, explanations, or anything answerable from conversation context alone.

Tool selection principles:
- Use the fewest tools that fully answer the question.
- Chain tools when the question spans multiple sources (e.g., "find the commit that caused incident #142 and check Slack for discussion" -> github_get_commit_history + slack_search_messages).
- If a first tool's output is needed to parameterize a second call (e.g., get a table schema before writing a query), chain them sequentially.
- When a question is ambiguous about which tool to use, prefer the tool that gives the most specific answer. For example, prefer github_get_issues over github_search_code when the user asks about a bug by number.
- For repository summary/count questions such as "how many commits, PRs, or deployment workflows are there?", prefer github_get_repo_metrics before piecing counts together from narrower tools.
- For exact commit-count questions such as "how many commits are there?" or "how many commits did I make?", prefer github_count_commits. If the user refers to themselves, infer the author from the signed-in username unless the conversation clearly names someone else.

=== MULTI-TURN CONTEXT RESOLUTION ===

This is a multi-turn conversation. Use prior turns to resolve references:
- Pronouns and demonstratives: "that repo" -> the repo from the last tool call or mention. "those results" -> the last tool output. "same channel" -> the channel from the prior Slack query.
- Implicit continuations: "what about PRs?" after an issues query -> same repo, switch to github_get_pull_requests. "show me the schema" after a SQL query -> db_get_schema for the table just queried.
- Refinements: "only the open ones" -> re-run the prior tool with a state filter. "from last week" -> add a date range to the prior query.
- If a follow-up is genuinely ambiguous and cannot be resolved from the last 3-5 turns, ask exactly one clarifying question targeting the missing parameter. Do not ask for information already available in the conversation.

=== PARAMETER INFERENCE ===

Before asking the user for a missing parameter, try to infer it:
- If only one repo/org is in the user's allowlist or was mentioned earlier, use it.
- Default issue/PR state to "open" unless the user specifies otherwise.
- Default branch to the repo's default branch (main/master) unless specified.
- Default time ranges to the last 7 days (computed from the current timestamp) for commit history and Slack search unless the user specifies a range.
- For SQL, prefer common aggregations (COUNT, AVG, SUM) and sensible LIMIT (default 25) unless the user asks for something specific.

If a required parameter truly cannot be inferred, ask for only that one parameter - not a menu of options.
- For GitHub repositories, if the user gives only a short repo name like `Interview-Helper`, try the GitHub tool with that short name first. The system can resolve it against accessible repos before asking for an owner/org prefix.

=== RESPONSE FORMAT ===

Structure:
1. Lead with the answer or key finding - not "Let me check..." or "I'll look that up."
2. Present data clearly using the best format for the content:
   - Structured results (issues, PRs, repos, tables): compact markdown table.
   - Code or file contents: fenced code block with language tag.
   - SQL queries you ran: show the query in a fenced sql block.
   - Narrative answers (incident summaries, explanations): concise paragraphs with key details bolded.
3. Keep it concise. Summarize tool output - do not dump raw JSON unless the user explicitly requests it.
4. If multiple tools were called, synthesize across sources into one coherent answer rather than presenting each tool's output separately.

Source attribution:
- End every response that used tools with a `Sources:` line.
- Format: `Sources: GitHub (org/repo - issues) · Slack (#channel - search) · PostgreSQL (table_name - query)`
- Only list sources actually used in this response turn.

=== EDGE CASES ===

- If the user asks about a resource outside their allowlist, the tool will return an access error. Explain that the resource isn't in their configured allowlist and suggest they contact an admin.
- If a tool returns no results, say so clearly and suggest broadening the search (wider date range, different keywords, checking the resource name spelling).
- If the user asks you to do something tools can't support (e.g., create a GitHub issue, post to Slack, write to the database), explain what's possible (read-only access) and suggest they do it directly in the relevant platform.
- If you're uncertain which of two tools is correct, briefly state your reasoning and use the more likely one. Don't ask unless truly ambiguous.
- For complex cross-source queries, outline your plan briefly (1 line) before executing, so the user knows what to expect during streaming."""


def build_system_prompt() -> str:
    """Build the base system prompt with the current time injected."""
    local_now = datetime.now().astimezone()
    utc_now = local_now.astimezone(timezone.utc)
    current_timestamp = (
        f"{utc_now.strftime('%Y-%m-%d %H:%M:%S UTC (%A)')} | "
        f"Local server time: {local_now.strftime('%Y-%m-%d %H:%M:%S %Z (%A)')}"
    )
    return BASE_SYSTEM_PROMPT.format(current_timestamp=current_timestamp)


class ChatService:
    _conversation_history: dict[str, list[Message]] = {}

    def __init__(
        self,
        registry: LLMRegistry,
        mcp_manager: MCPManager | None = None,
        user_service: UserService | None = None,
    ):
        self._registry = registry
        self._mcp = mcp_manager
        self._user_service = user_service

    async def handle_ws_chat(
        self,
        ws: WebSocket,
        model_id: str,
        message: str,
        conversation_id: str,
        user: dict,
    ) -> None:
        """Handle a chat message via WebSocket with streaming + tool calls."""
        await ws.send_json({"type": "stream_start", "conversation_id": conversation_id})

        try:
            result = await self._run_chat_turn(
                model_id=model_id,
                message=message,
                conversation_id=conversation_id,
                user=user,
                emitter=lambda payload: ws.send_json(payload),
            )
        except AppError as e:
            log.warning("chat_rejected", code=e.code, error=e.message, model=model_id)
            await ws.send_json({"type": "error", "message": e.message, "code": e.code})
            return
        except Exception as e:
            log.error("chat_error", error=str(e), model=model_id)
            await ws.send_json({"type": "error", "message": str(e), "code": "CHAT_ERROR"})
            return

        await ws.send_json({
            "type": "stream_end",
            "conversation_id": conversation_id,
            "context_sources": result["context_sources"],
            "tool_calls": result.get("tool_calls", []),
            "metrics": result.get("metrics", {}),
            "summary": None,
        })

    async def handle_rest_chat(
        self,
        model_id: str,
        message: str,
        user: dict,
        conversation_id: str = "",
    ) -> dict:
        """Non-streaming REST fallback with the same tool loop as WebSocket chat."""
        try:
            return await self._run_chat_turn(
                model_id=model_id,
                message=message,
                conversation_id=conversation_id,
                user=user,
                emitter=None,
            )
        except AppError as e:
            log.warning("rest_chat_rejected", code=e.code, error=e.message, model=model_id)
            return {"error": e.message, "code": e.code}
        except Exception as e:
            log.error("rest_chat_error", error=str(e), model=model_id)
            return {"error": str(e)}

    async def _run_chat_turn(
        self,
        model_id: str,
        message: str,
        conversation_id: str,
        user: dict,
        emitter: Callable[[dict], Awaitable[None]] | None,
    ) -> dict:
        history = self._get_conversation_history(conversation_id)
        normalized_message = self._normalize_user_message(message)
        user_message = Message(role="user", content=normalized_message)
        request_started_at = time.monotonic()
        is_relevant = self._is_relevant_request(normalized_message, history)
        if not is_relevant and self._is_kimi_model(model_id):
            is_relevant = self._is_kimi_db_identifier_request(normalized_message)
        if not is_relevant:
            if emitter is not None:
                await emitter({
                    "type": "stream_chunk",
                    "content": OUT_OF_SCOPE_RESPONSE,
                    "conversation_id": conversation_id,
                })
            return await self._complete_turn(
                user=user,
                conversation_id=conversation_id,
                user_message=user_message,
                assistant_text=OUT_OF_SCOPE_RESPONSE,
                model_id=model_id,
                request_started_at=request_started_at,
                ttft_ms=None,
                tool_calls=[],
                provider_metrics={},
                context_sources=[],
            )
        provider = self._registry.get(model_id)
        tools, tool_defs = self._get_user_tools(provider, user)
        system_prompt = self._build_system_prompt(user=user, tools=tools)
        messages = [Message(role="system", content=system_prompt), *history, user_message]

        context_sources: list[dict] = []
        context_source_keys: set[tuple[str, str]] = set()
        tool_calls: list[dict] = []
        cached_tool_results: dict[str, dict] = {}
        response_parts: list[str] = []
        tool_call_count = 0
        provider_metrics: dict[str, Any] = {}
        ttft_ms: int | None = None

        while True:
            turn_started_at = time.monotonic()
            turn_content = ""
            pending_tool_calls: list[ChatEvent] = []

            async for event in provider.chat(messages, tool_defs, stream=emitter is not None):
                if event.metrics:
                    provider_metrics.update({k: v for k, v in event.metrics.items() if v not in (None, "")})
                if event.type == ChatEventType.TEXT_CHUNK:
                    if ttft_ms is None and event.content:
                        ttft_ms = int((time.monotonic() - request_started_at) * 1000)
                    turn_content += event.content
                elif event.type == ChatEventType.TOOL_CALL:
                    pending_tool_calls.append(event)
                elif event.type == ChatEventType.ERROR:
                    raise RuntimeError(event.error)
                elif event.type == ChatEventType.DONE:
                    break

            sanitized_turn_content = self._sanitize_text(
                turn_content,
                user=user,
                model_id=model_id,
                source="assistant_output",
            )
            if not pending_tool_calls:
                implicit_tool_call = self._extract_implicit_tool_call(turn_content)
                if implicit_tool_call:
                    pending_tool_calls.append(implicit_tool_call)
                    turn_content = ""
                    sanitized_turn_content = ""

            if not pending_tool_calls:
                if sanitized_turn_content:
                    response_parts.append(sanitized_turn_content)
                if not tool_calls:
                    forced_result = await self._try_live_data_tool_fallback(
                        message=normalized_message,
                        user=user,
                        context_sources=context_sources,
                        context_source_keys=context_source_keys,
                        tool_calls=tool_calls,
                    )
                    if forced_result:
                        provider_metrics.setdefault("provider_model", "")
                        final_content = forced_result["content"]
                        if emitter is not None and final_content:
                            await emitter({
                                "type": "stream_chunk",
                                "content": final_content,
                                "conversation_id": conversation_id,
                            })
                        return await self._complete_turn(
                            user=user,
                            conversation_id=conversation_id,
                            user_message=user_message,
                            assistant_text=final_content,
                            model_id=model_id,
                            request_started_at=request_started_at,
                            ttft_ms=ttft_ms,
                            tool_calls=tool_calls,
                            provider_metrics=provider_metrics,
                            context_sources=context_sources,
                        )
                final_content = self._sanitize_text(
                    "".join(response_parts).strip(),
                    user=user,
                    model_id=model_id,
                    source="assistant_output_final",
                )
                final_content = self._finalize_response_content(final_content, tool_calls, context_sources)
                repo_usage_fallback = await self._try_repo_model_usage_fallback(
                    message=normalized_message,
                    user=user,
                    final_content=final_content,
                    context_sources=context_sources,
                    context_source_keys=context_source_keys,
                    tool_calls=tool_calls,
                )
                if repo_usage_fallback:
                    final_content = repo_usage_fallback
                kimi_override = await self._try_kimi_grounded_override(
                    model_id=model_id,
                    message=normalized_message,
                    user=user,
                    final_content=final_content,
                    context_sources=context_sources,
                    context_source_keys=context_source_keys,
                    tool_calls=tool_calls,
                )
                if kimi_override:
                    final_content = kimi_override
                if emitter is not None and final_content:
                    await emitter({
                        "type": "stream_chunk",
                        "content": final_content,
                        "conversation_id": conversation_id,
                    })
                return await self._complete_turn(
                    user=user,
                    conversation_id=conversation_id,
                    user_message=user_message,
                    assistant_text=final_content,
                    model_id=model_id,
                    request_started_at=request_started_at,
                    ttft_ms=ttft_ms,
                    tool_calls=tool_calls,
                    provider_metrics=provider_metrics,
                    context_sources=context_sources,
                )

            assistant_message = self._build_assistant_tool_message(turn_content, pending_tool_calls)
            messages.append(assistant_message)

            for tc_event in pending_tool_calls:
                if tool_call_count >= MAX_TOOL_CALLS_PER_TURN:
                    limit_note = f"\n\nTool call limit reached (max {MAX_TOOL_CALLS_PER_TURN} per turn)."
                    response_parts.append(limit_note)
                    final_content = self._sanitize_text(
                        "".join(response_parts).strip(),
                        user=user,
                        model_id=model_id,
                        source="assistant_output_final",
                    )
                    final_content = self._finalize_response_content(final_content, tool_calls, context_sources)
                    repo_usage_fallback = await self._try_repo_model_usage_fallback(
                        message=normalized_message,
                        user=user,
                        final_content=final_content,
                        context_sources=context_sources,
                        context_source_keys=context_source_keys,
                        tool_calls=tool_calls,
                    )
                    if repo_usage_fallback:
                        final_content = repo_usage_fallback
                    kimi_override = await self._try_kimi_grounded_override(
                        model_id=model_id,
                        message=normalized_message,
                        user=user,
                        final_content=final_content,
                        context_sources=context_sources,
                        context_source_keys=context_source_keys,
                        tool_calls=tool_calls,
                    )
                    if kimi_override:
                        final_content = kimi_override
                    if emitter is not None:
                        await emitter({
                            "type": "stream_chunk",
                            "content": final_content,
                            "conversation_id": conversation_id,
                        })
                    return await self._complete_turn(
                        user=user,
                        conversation_id=conversation_id,
                        user_message=user_message,
                        assistant_text=final_content,
                        model_id=model_id,
                        request_started_at=request_started_at,
                        ttft_ms=ttft_ms,
                        tool_calls=tool_calls,
                        provider_metrics=provider_metrics,
                        context_sources=context_sources,
                    )

                tool_name = tc_event.tool_name
                tool_args, resolution_error = await self._normalize_tool_args(tool_name, tc_event.tool_args)
                tool_args = self._infer_user_tool_args(tool_name, tool_args, user, normalized_message)
                if self._is_kimi_model(model_id):
                    tool_args = self._normalize_kimi_tool_args(tool_name, tool_args, normalized_message)

                if resolution_error:
                    result = resolution_error
                    tool_record = {
                        "name": tool_name,
                        "args": tool_args,
                        "result": result,
                        "duration_ms": 0,
                        "status": "error",
                    }
                    tool_calls.append(tool_record)
                    if emitter is not None:
                        await emitter({
                            "type": "tool_call_result",
                            "tool": {
                                "name": tool_name,
                                "result": result,
                                "duration_ms": 0,
                            },
                            "conversation_id": conversation_id,
                        })
                    messages.append(Message(
                        role="tool",
                        content=result,
                        tool_call_id=tc_event.tool_call_id,
                        tool_name=tool_name,
                    ))
                    continue

                if emitter is not None:
                    await emitter({
                        "type": "tool_call_start",
                        "tool": {"name": tool_name, "args": tool_args},
                        "conversation_id": conversation_id,
                    })

                try:
                    validate_tool_call(user, tool_name, tool_args)
                except AuthorizationError as e:
                    result = f"Permission denied: {e.message}"
                    tool_record = {
                        "name": tool_name,
                        "args": tool_args,
                        "result": result,
                        "duration_ms": 0,
                        "status": "error",
                    }
                    tool_calls.append(tool_record)
                    audit_logger.log_event(
                        "security_tool_denied",
                        user_id=user.get("id", ""),
                        username=user.get("username", ""),
                        model_id=model_id,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        details=result,
                    )
                    if emitter is not None:
                        await emitter({
                            "type": "tool_call_result",
                            "tool": {
                                "name": tool_name,
                                "result": result,
                                "duration_ms": 0,
                            },
                            "conversation_id": conversation_id,
                        })
                    messages.append(Message(
                        role="tool",
                        content=result,
                        tool_call_id=tc_event.tool_call_id,
                        tool_name=tool_name,
                    ))
                    continue

                tool_cache_key = json.dumps({"name": tool_name, "args": tool_args}, sort_keys=True)
                cached_tool = cached_tool_results.get(tool_cache_key)
                if cached_tool is not None:
                    self._track_context_source(
                        context_sources=context_sources,
                        seen_keys=context_source_keys,
                        tool_name=tool_name,
                        tool_args=tool_args,
                    )
                    if emitter is not None:
                        await emitter({
                            "type": "tool_call_result",
                            "tool": {
                                "name": tool_name,
                                "result": cached_tool["result"][:MAX_TOOL_RESULT_PREVIEW_CHARS],
                                "duration_ms": 0,
                            },
                            "conversation_id": conversation_id,
                        })
                    messages.append(Message(
                        role="tool",
                        content=cached_tool["result"],
                        tool_call_id=tc_event.tool_call_id,
                        tool_name=tool_name,
                    ))
                    continue

                tool_call_count += 1
                start = time.monotonic()
                result = await self._mcp.execute_tool(tool_name, tool_args) if self._mcp else "Error: MCP not configured"
                duration_ms = int((time.monotonic() - start) * 1000)
                result = filter_tool_result_for_user(user, tool_name, result)
                result = self._sanitize_text(
                    result,
                    user=user,
                    model_id=model_id,
                    tool_name=tool_name,
                    source="tool_result",
                )

                tool_record = {
                    "name": tool_name,
                    "args": tool_args,
                    "result": result,
                    "duration_ms": duration_ms,
                    "status": "error" if self._tool_result_is_error(result) else "success",
                }
                tool_calls.append(tool_record)
                cached_tool_results[tool_cache_key] = {
                    "result": result,
                    "status": tool_record["status"],
                }

                audit_logger.log_event(
                    "tool_call",
                    user_id=user.get("id", ""),
                    username=user.get("username", ""),
                    model_id=model_id,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    result_summary=result[:500],
                    duration_ms=duration_ms,
                )

                self._track_context_source(
                    context_sources=context_sources,
                    seen_keys=context_source_keys,
                    tool_name=tool_name,
                    tool_args=tool_args,
                )

                if emitter is not None:
                    await emitter({
                        "type": "tool_call_result",
                        "tool": {
                            "name": tool_name,
                            "result": result[:MAX_TOOL_RESULT_PREVIEW_CHARS],
                            "duration_ms": duration_ms,
                        },
                        "conversation_id": conversation_id,
                    })

                messages.append(Message(
                    role="tool",
                    content=result,
                    tool_call_id=tc_event.tool_call_id,
                    tool_name=tool_name,
                ))

    def _get_user_tools(
        self,
        provider,
        user: dict,
    ) -> tuple[list[MCPTool], list[ToolDefinition] | None]:
        if not self._mcp or not provider.supports_tools:
            return [], None

        all_tools = self._mcp.get_all_tools()
        user_tools = filter_tools_for_user(all_tools, user)
        if not user_tools:
            return [], None
        return user_tools, mcp_to_tool_definitions(user_tools)

    def _build_system_prompt(self, user: dict, tools: list[MCPTool]) -> str:
        tools_by_source = {
            "github": [tool for tool in tools if tool.server_name == "github"],
            "slack": [tool for tool in tools if tool.server_name == "slack"],
            "postgres": [tool for tool in tools if tool.server_name == "postgres"],
        }

        role = user.get("role", "viewer")
        allowed_repos = user.get("allowed_repos") or []
        allowed_channels = user.get("allowed_channels") or []
        allowed_tables = user.get("allowed_db_tables") or []

        source_lines = [
            self._format_source_status(
                source_name="GitHub",
                connected=bool(settings.github_token),
                accessible_tools=len(tools_by_source["github"]),
                access_scope="all repositories" if role == "admin" else self._format_scope_list(allowed_repos),
            ),
            self._format_source_status(
                source_name="Slack",
                connected=bool(settings.slack_bot_token),
                accessible_tools=len(tools_by_source["slack"]),
                access_scope="all channels" if role == "admin" else self._format_scope_list(allowed_channels),
            ),
            self._format_source_status(
                source_name="PostgreSQL",
                connected=bool(settings.database_url),
                accessible_tools=len(tools_by_source["postgres"]),
                access_scope="all tables" if role == "admin" else self._format_scope_list(allowed_tables),
            ),
        ]

        if tools:
            tool_lines = [self._format_tool_line(tool) for tool in tools]
        else:
            tool_lines = ["- No external tools are available to this user in the current chat context."]

        return "\n\n".join([
            build_system_prompt(),
            "\n".join([
                "Current app/user context:",
                f"- User role: {role}",
                *source_lines,
            ]),
            "\n".join(["Accessible tools in this chat:"] + tool_lines),
        ])

    @staticmethod
    def _format_source_status(
        source_name: str,
        connected: bool,
        accessible_tools: int,
        access_scope: str,
    ) -> str:
        if not connected:
            return (
                f"- {source_name}: not configured in this deployment; "
                f"assigned access scope: {access_scope}."
            )
        return (
            f"- {source_name}: connected with {accessible_tools} accessible tool(s); "
            f"access scope: {access_scope}."
        )

    @staticmethod
    def _format_scope_list(items: list[str]) -> str:
        return ", ".join(items) if items else "none assigned"

    def _format_tool_line(self, tool: MCPTool) -> str:
        properties = tool.parameters.get("properties", {})
        required = set(tool.parameters.get("required", []))
        if not properties:
            signature = "()"
        else:
            params = []
            for name, meta in properties.items():
                param_type = meta.get("type", "any")
                label = f"{name}: {param_type}"
                if name in required:
                    label += " [required]"
                elif "default" in meta:
                    label += f" = {json.dumps(meta['default'])}"
                params.append(label)
            signature = f"({', '.join(params)})"

        return f"- {tool.name} {signature} [{tool.server_name}] - {tool.description}"

    def _track_context_source(
        self,
        context_sources: list[dict],
        seen_keys: set[tuple[str, str]],
        tool_name: str,
        tool_args: dict,
    ) -> None:
        if not self._mcp:
            return

        server = self._mcp.get_server_for_tool(tool_name)
        if not server:
            return

        detail = ""
        for key in ("repo", "org", "channel", "table", "path"):
            if tool_args.get(key):
                detail = str(tool_args[key])
                break
        if not detail:
            detail = tool_name

        marker = (server, detail)
        if marker in seen_keys:
            return

        seen_keys.add(marker)
        context_sources.append({"type": server, "detail": detail})

    @staticmethod
    def _build_assistant_tool_message(content: str, tool_events: list[ChatEvent]) -> Message:
        tool_calls = []
        for event in tool_events:
            tool_calls.append({
                "id": event.tool_call_id or f"call_{event.tool_name}",
                "type": "function",
                "function": {
                    "name": event.tool_name,
                    "arguments": json.dumps(event.tool_args),
                },
            })
        return Message(role="assistant", content=content, tool_calls=tool_calls)

    @staticmethod
    def _tool_result_is_error(result: str) -> bool:
        lowered = result.lower()
        return lowered.startswith("error") or '"error"' in lowered

    @staticmethod
    def _build_turn_metrics(
        model_id: str,
        request_started_at: float,
        ttft_ms: int | None,
        tool_calls: list[dict],
        provider_metrics: dict[str, Any],
        final_content: str,
    ) -> dict:
        total_time_ms = int((time.monotonic() - request_started_at) * 1000)
        tool_time_ms = sum(int(tool.get("duration_ms", 0) or 0) for tool in tool_calls)
        return {
            "model_id": model_id,
            "ttft_ms": ttft_ms,
            "total_time_ms": total_time_ms,
            "tool_time_ms": tool_time_ms,
            "tool_call_count": len(tool_calls),
            "input_tokens": provider_metrics.get("input_tokens"),
            "output_tokens": provider_metrics.get("output_tokens"),
            "cost_usd": provider_metrics.get("cost_usd"),
            "provider_model": provider_metrics.get("provider_model", ""),
            "response_chars": len(final_content),
        }

    async def _complete_turn(
        self,
        user: dict,
        conversation_id: str,
        user_message: Message,
        assistant_text: str,
        model_id: str,
        request_started_at: float,
        ttft_ms: int | None,
        tool_calls: list[dict],
        provider_metrics: dict[str, Any],
        context_sources: list[dict],
    ) -> dict:
        turn_metrics = self._build_turn_metrics(
            model_id=model_id,
            request_started_at=request_started_at,
            ttft_ms=ttft_ms,
            tool_calls=tool_calls,
            provider_metrics=provider_metrics,
            final_content=assistant_text,
        )
        self._store_conversation_turn(
            conversation_id=conversation_id,
            user_message=user_message,
            assistant_text=assistant_text,
        )
        await self._persist_turn_metrics(
            user=user,
            conversation_id=conversation_id,
            metrics=turn_metrics,
            tool_calls=tool_calls,
            context_sources=context_sources,
        )
        return {
            "content": assistant_text,
            "tool_calls": tool_calls,
            "context_sources": context_sources,
            "model_id": model_id,
            "metrics": turn_metrics,
            "summary": None,
        }

    async def _persist_turn_metrics(
        self,
        user: dict,
        conversation_id: str,
        metrics: dict[str, Any],
        tool_calls: list[dict],
        context_sources: list[dict],
    ) -> None:
        if not self._user_service:
            return

        user_id = str(user.get("id", "") or "").strip()
        if not user_id:
            return

        try:
            await self._user_service.record_chat_metric(
                user_id=user_id,
                conversation_id=conversation_id,
                metrics=metrics,
                tool_calls=tool_calls,
                context_sources=context_sources,
            )
        except Exception as exc:
            log.warning(
                "chat_metric_persist_failed",
                user_id=user_id,
                conversation_id=conversation_id,
                error=str(exc),
            )

    async def _try_kimi_grounded_override(
        self,
        model_id: str,
        message: str,
        user: dict,
        final_content: str,
        context_sources: list[dict],
        context_source_keys: set[tuple[str, str]],
        tool_calls: list[dict],
    ) -> str | None:
        if not self._is_kimi_model(model_id):
            return None

        commit_override = self._format_kimi_commit_count_answer(message, tool_calls)
        if commit_override:
            return commit_override

        workflow_override = self._format_kimi_workflow_name_answer(message, tool_calls)
        if workflow_override:
            return workflow_override

        table_override = await self._format_kimi_table_listing_answer(
            message=message,
            user=user,
            context_sources=context_sources,
            context_source_keys=context_source_keys,
            tool_calls=tool_calls,
        )
        if table_override:
            return table_override

        mention_override = await self._format_kimi_repo_mention_answer(
            message=message,
            user=user,
            context_sources=context_sources,
            context_source_keys=context_source_keys,
            tool_calls=tool_calls,
        )
        if mention_override:
            return mention_override

        return None

    async def _format_kimi_table_listing_answer(
        self,
        message: str,
        user: dict,
        context_sources: list[dict],
        context_source_keys: set[tuple[str, str]],
        tool_calls: list[dict],
    ) -> str | None:
        if not re.search(r"\btables?\b", message, re.IGNORECASE):
            return None
        if not re.search(r"\b(postgres(?:ql)?|database|sql)\b", message, re.IGNORECASE):
            return None
        if not re.search(r"\b(list|show|available|how many|count)\b", message, re.IGNORECASE):
            return None

        payload: list[dict] | None = None
        for tool in reversed(tool_calls):
            if tool.get("name") != "db_list_tables" or tool.get("status") != "success":
                continue
            try:
                parsed = json.loads(str(tool.get("result", "")))
            except Exception:
                continue
            if isinstance(parsed, list):
                payload = parsed
                break

        if payload is None:
            result = await self._execute_fallback_tool(
                tool_name="db_list_tables",
                tool_args={},
                user=user,
                context_sources=context_sources,
                context_source_keys=context_source_keys,
                tool_calls=tool_calls,
            )
            try:
                parsed = json.loads(result)
            except Exception:
                return None
            if isinstance(parsed, list):
                payload = parsed

        if not payload:
            return None

        if re.search(r"\b(how many|count|total)\b", message, re.IGNORECASE):
            return (
                f"There are **{len(payload)} PostgreSQL tables** available.\n\n"
                f"Sources: PostgreSQL ({payload[0]['schema']} schema - table list)"
            )

        rows = [f"- `{row['schema']}.{row['table']}` ({row['columns']} columns)" for row in payload]
        return "Here are the available PostgreSQL tables:\n" + "\n".join(rows) + "\n\nSources: PostgreSQL (public schema - table list)"

    async def _format_kimi_repo_mention_answer(
        self,
        message: str,
        user: dict,
        context_sources: list[dict],
        context_source_keys: set[tuple[str, str]],
        tool_calls: list[dict],
    ) -> str | None:
        if not re.search(r"\b(find|where)\b", message, re.IGNORECASE):
            return None
        if "mentioned" not in message.lower():
            return None

        keyword = self._extract_repo_search_term(message)
        if not keyword:
            return None

        for tool in reversed(tool_calls):
            if tool.get("name") != "github_search_code" or tool.get("status") != "success":
                continue

            args = tool.get("args", {})
            repo = str(args.get("repo", "")).strip()
            try:
                search_payload = json.loads(str(tool.get("result", "")))
            except Exception:
                continue

            if isinstance(search_payload, list) and search_payload:
                first = search_payload[0]
                path = str(first.get("path", "") or first.get("name", "") or "")
                repo_name = str(first.get("repository", "") or repo)
                if path:
                    return (
                        f"I found **{keyword}** in `{repo_name}` at `{path}`.\n\n"
                        f"Sources: GitHub ({repo_name} - code search)"
                    )

            if not repo:
                continue

            readme_content = self._get_successful_readme(tool_calls, repo, "")
            if readme_content is None:
                readme_content = await self._execute_fallback_tool(
                    tool_name="github_read_file",
                    tool_args={"repo": repo, "path": "README.md", "ref": ""},
                    user=user,
                    context_sources=context_sources,
                    context_source_keys=context_source_keys,
                    tool_calls=tool_calls,
                )

            if self._tool_result_is_error(readme_content):
                continue

            for line in str(readme_content).splitlines():
                if keyword.lower() in line.lower():
                    snippet = line.strip().strip("- ").strip()
                    return (
                        f"I found **{keyword}** mentioned in `{repo}` inside `README.md`.\n\n"
                        f"`{snippet}`\n\n"
                        f"Sources: GitHub ({repo} - README.md)"
                    )

        return None

    @staticmethod
    def _format_kimi_commit_count_answer(message: str, tool_calls: list[dict]) -> str | None:
        if not re.search(r"\bcommits?\b", message, re.IGNORECASE):
            return None

        for tool in reversed(tool_calls):
            if tool.get("name") != "github_count_commits" or tool.get("status") != "success":
                continue
            try:
                payload = json.loads(str(tool.get("result", "")))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue

            repo = str(payload.get("repo", "the repository"))
            author = str(payload.get("author", "") or "")
            count = payload.get("commit_count", "?")
            is_self_prompt = bool(
                re.search(
                    r"\bmy\s+commits?\b|\bcommits?\s+i\s+made\b|\bi\s+(?:made|authored|committed)\b|\bdid\s+i\b",
                    message,
                    re.IGNORECASE,
                )
            )
            if is_self_prompt and author:
                return (
                    f"You've made **{count} commits** in `{repo}`.\n\n"
                    f"Sources: GitHub ({repo} - commit count)"
                )
            return (
                f"There are **{count} commits** in `{repo}`.\n\n"
                f"Sources: GitHub ({repo} - commit count)"
            )

        return None

    @staticmethod
    def _format_kimi_workflow_name_answer(message: str, tool_calls: list[dict]) -> str | None:
        if "workflow" not in message.lower():
            return None
        if not re.search(r"\b(name|named|called)\b", message, re.IGNORECASE):
            return None

        for tool in reversed(tool_calls):
            if tool.get("name") != "github_read_file" or tool.get("status") != "success":
                continue
            args = tool.get("args", {})
            path = str(args.get("path", "")).strip()
            if not path.startswith(".github/workflows/"):
                continue
            content = str(tool.get("result", ""))
            match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
            if not match:
                continue
            repo = str(args.get("repo", "the repository"))
            workflow_name = match.group(1).strip()
            return (
                f'The deployment workflow in `{repo}` is called **"{workflow_name}"**.\n\n'
                f"Sources: GitHub ({repo} - workflow file)"
            )
        return None

    @staticmethod
    def _normalize_kimi_tool_args(tool_name: str, tool_args: dict, user_message: str) -> dict:
        normalized_args = dict(tool_args)
        if tool_name not in {"github_count_commits", "github_get_commit_history"}:
            return normalized_args

        author = str(normalized_args.get("author", "") or "").strip().lower()
        if not author:
            return normalized_args

        reserved_words = {
            "github",
            "git",
            "slack",
            "postgres",
            "postgresql",
            "database",
            "db",
            "repo",
            "repository",
        }
        if author in reserved_words:
            normalized_args.pop("author", None)
        return normalized_args

    @staticmethod
    def _extract_repo_search_term(message: str) -> str:
        patterns = [
            r"\bfind where\s+(.+?)\s+is mentioned\b",
            r"\bfind\s+(.+?)\s+in\s+[\w./-]+\s+repo\b",
            r"\bwhere is\s+(.+?)\s+mentioned\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if not match:
                continue
            keyword = match.group(1).strip().strip('\"\'`')
            if keyword:
                return keyword
        return ""

    @staticmethod
    def _is_kimi_model(model_id: str) -> bool:
        return model_id == "nvidia/kimi-k2"

    @staticmethod
    def _is_kimi_db_identifier_request(message: str) -> bool:
        if not re.search(r"\b[a-z]+_[a-z0-9_]+\b", message):
            return False
        return bool(
            re.search(
                r"\b(avg|average|highest|lowest|top|count|how many|rows?|service|status|usage|cpu|schema|column|table|database)\b",
                message,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _finalize_response_content(
        final_content: str,
        tool_calls: list[dict],
        context_sources: list[dict],
    ) -> str:
        if final_content.strip() and not ChatService._looks_like_tool_plan(final_content):
            return final_content

        for tool in reversed(tool_calls):
            if tool.get("status") != "success":
                continue

            if tool.get("name") == "github_get_repo_metrics":
                try:
                    payload = json.loads(str(tool.get("result", "")))
                except Exception:
                    continue
                repo = payload.get("repo", "the repository")
                commits = payload.get("commit_count", "?")
                prs = payload.get("pull_request_count", "?")
                deployments = payload.get("deployment_workflow_count", "?")
                workflows = payload.get("workflow_count", "?")
                answer = (
                    f"In {repo}, there are {commits} commits, {prs} pull requests, "
                    f"and {deployments} deployment workflow"
                    f"{'' if deployments == 1 else 's'} ({workflows} workflow"
                    f"{'' if workflows == 1 else 's'} total)."
                )
                source_line = "Sources: GitHub ({repo} - repo metrics)".format(repo=repo)
                return f"{answer}\n\n{source_line}"
            if tool.get("name") == "github_count_commits":
                try:
                    payload = json.loads(str(tool.get("result", "")))
                except Exception:
                    continue
                repo = payload.get("repo", "the repository")
                author = payload.get("author", "")
                commit_count = payload.get("commit_count", "?")
                branch = payload.get("branch", "")
                qualifier = f" by {author}" if author else ""
                branch_note = f" on branch `{branch}`" if branch else ""
                answer = f"I found {commit_count} commit"
                if commit_count != 1:
                    answer += "s"
                answer += f"{qualifier} in {repo}{branch_note}."
                source_line = "Sources: GitHub ({repo} - commit count)".format(repo=repo)
                return f"{answer}\n\n{source_line}"
            if tool.get("name") == "github_get_commit_history":
                try:
                    payload = json.loads(str(tool.get("result", "")))
                except Exception:
                    continue
                if not isinstance(payload, list):
                    continue
                repo = tool.get("args", {}).get("repo", "the repository")
                author = tool.get("args", {}).get("author", "")
                commit_count = len(payload)
                qualifier = f" by {author}" if author else ""
                answer = f"I found {commit_count} retrieved commit"
                if commit_count != 1:
                    answer += "s"
                answer += f"{qualifier} in {repo}."
                if commit_count >= int(tool.get("args", {}).get("count", 0) or 0):
                    answer += " This may be truncated because the model used commit history sampling instead of the exact count tool."
                source_line = "Sources: GitHub ({repo} - commit history)".format(repo=repo)
                return f"{answer}\n\n{source_line}"

        if context_sources:
            source_chunks = [f"{item['type'].title()} ({item['detail']})" for item in context_sources]
            return (
                "I retrieved the requested data, but the model did not return a final summary.\n\n"
                f"Sources: {' · '.join(source_chunks)}"
            )

        return final_content

    @staticmethod
    def _looks_like_tool_plan(text: str) -> bool:
        lowered = text.strip().lower()
        plan_markers = (
            "let's start",
            "let's first",
            "i will first",
            "we need to use",
            "to get the",
            "i'll first check",
            "using the `github_",
            "using the github_",
            "using the `db_",
            "using the db_",
            "using the `slack_",
            "using the slack_",
        )
        return any(marker in lowered for marker in plan_markers)

    async def _try_live_data_tool_fallback(
        self,
        message: str,
        user: dict,
        context_sources: list[dict],
        context_source_keys: set[tuple[str, str]],
        tool_calls: list[dict],
    ) -> dict[str, str] | None:
        if not self._mcp:
            return None

        lowered = message.lower()
        if "github" not in lowered and "repo" not in lowered and "repository" not in lowered:
            return None

        repo = self._infer_repo_from_message(message)
        if not repo:
            return None

        asks_commits = bool(re.search(r"\bcommits?\b", message, re.IGNORECASE))
        asks_prs = bool(re.search(r"\b(pr|prs|pull request|pull requests)\b", message, re.IGNORECASE))
        asks_workflows = bool(re.search(r"\b(workflows?|deployment)\b", message, re.IGNORECASE))
        asks_how_many = bool(re.search(r"\b(how many|count|total)\b", message, re.IGNORECASE))
        if not asks_how_many or not (asks_commits or asks_prs or asks_workflows):
            return None

        if asks_prs or asks_workflows:
            args, resolution_error = await self._normalize_tool_args("github_get_repo_metrics", {"repo": repo})
            args = self._infer_user_tool_args("github_get_repo_metrics", args, user, message)
            if resolution_error:
                return {"content": resolution_error}
            validate_tool_call(user, "github_get_repo_metrics", args)
            result = await self._execute_fallback_tool(
                tool_name="github_get_repo_metrics",
                tool_args=args,
                user=user,
                context_sources=context_sources,
                context_source_keys=context_source_keys,
                tool_calls=tool_calls,
            )
            return {"content": self._finalize_response_content("", tool_calls, context_sources)} if result else None

        if asks_commits:
            args, resolution_error = await self._normalize_tool_args("github_count_commits", {"repo": repo})
            args = self._infer_user_tool_args("github_count_commits", args, user, message)
            if resolution_error:
                return {"content": resolution_error}
            validate_tool_call(user, "github_count_commits", args)
            result = await self._execute_fallback_tool(
                tool_name="github_count_commits",
                tool_args=args,
                user=user,
                context_sources=context_sources,
                context_source_keys=context_source_keys,
                tool_calls=tool_calls,
            )
            return {"content": self._finalize_response_content("", tool_calls, context_sources)} if result else None

        return None

    async def _execute_fallback_tool(
        self,
        tool_name: str,
        tool_args: dict,
        user: dict,
        context_sources: list[dict],
        context_source_keys: set[tuple[str, str]],
        tool_calls: list[dict],
    ) -> str:
        result = await self._mcp.execute_tool(tool_name, tool_args)
        result = filter_tool_result_for_user(user, tool_name, result)
        result = self._sanitize_text(
            result,
            user=user,
            model_id="fallback",
            tool_name=tool_name,
            source="tool_result",
        )
        tool_calls.append({
            "name": tool_name,
            "args": tool_args,
            "result": result,
            "duration_ms": 0,
            "status": "error" if self._tool_result_is_error(result) else "success",
        })
        self._track_context_source(
            context_sources=context_sources,
            seen_keys=context_source_keys,
            tool_name=tool_name,
            tool_args=tool_args,
        )
        return result

    async def _try_repo_model_usage_fallback(
        self,
        message: str,
        user: dict,
        final_content: str,
        context_sources: list[dict],
        context_source_keys: set[tuple[str, str]],
        tool_calls: list[dict],
    ) -> str | None:
        if not self._mcp:
            return None

        lowered_message = message.lower()
        if "model" not in lowered_message:
            return None
        if not re.search(r"\b(stt|speech[- ]to[- ]text|ptt|push[- ]to[- ]talk)\b", lowered_message):
            return None

        lowered_final = final_content.lower()
        weak_response = (
            "tool call limit reached" in lowered_final
            or "no results were found" in lowered_final
            or "no results found" in lowered_final
            or "there are no stt" in lowered_final
            or "there are no ptt" in lowered_final
            or "no stt or ptt models" in lowered_final
        )
        if not weak_response:
            return None

        repo = self._infer_repo_from_message(message)
        if not repo:
            return None

        try:
            repo_info_args, resolution_error = await self._normalize_tool_args("github_get_repo_info", {"repo": repo})
            if resolution_error:
                return None
            validate_tool_call(user, "github_get_repo_info", repo_info_args)
        except AuthorizationError:
            return None

        repo_info_payload = self._get_successful_tool_payload(tool_calls, "github_get_repo_info")
        if repo_info_payload is None:
            repo_info_result = await self._execute_fallback_tool(
                tool_name="github_get_repo_info",
                tool_args=repo_info_args,
                user=user,
                context_sources=context_sources,
                context_source_keys=context_source_keys,
                tool_calls=tool_calls,
            )
            try:
                repo_info_payload = json.loads(repo_info_result)
            except Exception:
                return None

        if not isinstance(repo_info_payload, dict):
            return None

        target_repo = str(repo_info_payload.get("name") or repo_info_args.get("repo") or repo)
        default_branch = str(repo_info_payload.get("default_branch", "") or "")
        readme_args = {"repo": target_repo, "path": "README.md", "ref": default_branch}

        try:
            validate_tool_call(user, "github_read_file", readme_args)
        except AuthorizationError:
            return None

        readme_content = self._get_successful_readme(tool_calls, target_repo, default_branch)
        if readme_content is None:
            readme_content = await self._execute_fallback_tool(
                tool_name="github_read_file",
                tool_args=readme_args,
                user=user,
                context_sources=context_sources,
                context_source_keys=context_source_keys,
                tool_calls=tool_calls,
            )

        if self._tool_result_is_error(readme_content):
            return None

        return self._summarize_repo_model_usage_from_readme(target_repo, readme_content)

    @staticmethod
    def _get_successful_tool_payload(tool_calls: list[dict], tool_name: str) -> dict | None:
        for tool in reversed(tool_calls):
            if tool.get("name") != tool_name or tool.get("status") != "success":
                continue
            try:
                payload = json.loads(str(tool.get("result", "")))
            except Exception:
                continue
            if isinstance(payload, dict):
                return payload
        return None

    @staticmethod
    def _get_successful_readme(tool_calls: list[dict], repo: str, ref: str) -> str | None:
        for tool in reversed(tool_calls):
            if tool.get("name") != "github_read_file" or tool.get("status") != "success":
                continue
            args = tool.get("args", {})
            if str(args.get("repo", "")) != repo:
                continue
            if str(args.get("path", "")).lower() != "readme.md":
                continue
            if ref and str(args.get("ref", "")) not in {"", ref}:
                continue
            return str(tool.get("result", ""))
        return None

    @staticmethod
    def _summarize_repo_model_usage_from_readme(repo: str, readme_content: str) -> str | None:
        stt_summary = ""
        ptt_summary = ""

        stt_match = re.search(r"Live STT.*?with ([^\n]+)", readme_content, re.IGNORECASE)
        if stt_match:
            stt_summary = stt_match.group(1).strip().rstrip(".")
        else:
            stt_arch_match = re.search(r"STT proxy \(([^)]+)\)", readme_content, re.IGNORECASE)
            if stt_arch_match:
                stt_summary = stt_arch_match.group(1).strip()

        if re.search(r"Push-to-Talk|PTT transcription", readme_content, re.IGNORECASE):
            if stt_summary:
                ptt_summary = (
                    "The README describes push-to-talk transcription but does not name a separate PTT-specific model, "
                    "so it appears to use the same transcription pipeline."
                )
            else:
                ptt_summary = "The README describes push-to-talk transcription, but it does not name a dedicated PTT-specific model."

        if not stt_summary and not ptt_summary:
            return None

        parts = [f"In `{repo}`, the README indicates:"]
        if stt_summary:
            parts.append(f"- STT uses {stt_summary}.")
        if ptt_summary:
            parts.append(f"- PTT: {ptt_summary}")
        parts.append(f"\nSources: GitHub ({repo} - README.md)")
        return "\n".join(parts)

    @staticmethod
    def _infer_repo_from_message(message: str) -> str:
        owner_repo = REPO_OR_PATH_REGEX.search(message)
        if owner_repo:
            return owner_repo.group(0)

        patterns = [
            r"\bin\s+([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)\s+repo\b",
            r"\b(?:repo|repository)\s+([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)\b",
            r"\bfor\s+([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)\b",
        ]
        invalid_tokens = {"for", "and", "the", "this", "that", "my", "your", "a", "an"}
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                candidate = match.group(1)
                if candidate.lower() in invalid_tokens:
                    continue
                return candidate
        return ""

    @staticmethod
    def _infer_user_tool_args(tool_name: str, tool_args: dict, user: dict, user_message: str) -> dict:
        normalized_args = dict(tool_args)
        if not tool_name.startswith("github_"):
            return normalized_args

        if tool_name in {"github_get_commit_history", "github_count_commits"}:
            author = str(normalized_args.get("author", "") or "").strip()
            prompt_mentions_self = bool(
                re.search(
                    r"\bmy\s+commits?\b|\bcommits?\s+i\s+made\b|\bi\s+(?:made|authored|committed)\b|\bdid\s+i\b",
                    user_message,
                    re.IGNORECASE,
                )
            )
            explicit_named_author = re.search(
                r"\b(?:author|user|username|by|from|as)\s+([A-Za-z0-9_.-]+)\b",
                user_message,
                re.IGNORECASE,
            )
            if explicit_named_author is not None:
                normalized_args["author"] = explicit_named_author.group(1)
            elif prompt_mentions_self and user.get("username"):
                normalized_args["author"] = str(user["username"])
            elif author:
                normalized_args.pop("author", None)

            if tool_name == "github_get_commit_history" and re.search(r"\bhow many\b", user_message, re.IGNORECASE):
                normalized_args["count"] = max(int(normalized_args.get("count", 30) or 30), 200)

        return normalized_args

    @staticmethod
    def _normalize_user_message(message: str) -> str:
        normalized = message.strip()
        if not normalized:
            raise ValidationError("message cannot be empty")
        if len(normalized) > settings.max_message_length:
            raise ValidationError(
                f"message exceeds the {settings.max_message_length} character limit"
            )
        return normalized

    @staticmethod
    def _sanitize_text(
        text: str,
        user: dict,
        model_id: str,
        source: str,
        tool_name: str = "",
    ) -> str:
        if not text:
            return text

        text = ChatService._normalize_model_text_artifacts(text)
        sanitized, redactions = pii_filter.scan_and_redact(text)
        if redactions:
            summary = ", ".join(f"{item['type']} x{item['count']}" for item in redactions)
            audit_logger.log_event(
                "security_content_redacted",
                user_id=user.get("id", ""),
                username=user.get("username", ""),
                model_id=model_id,
                tool_name=tool_name,
                result_summary=sanitized[:500],
                details=f"{source}: {summary}",
            )
        return sanitized

    @staticmethod
    async def _normalize_tool_args(tool_name: str, tool_args: dict) -> tuple[dict, str | None]:
        normalized_args = dict(tool_args)
        repo = normalized_args.get("repo")
        if not tool_name.startswith("github_") or not isinstance(repo, str) or not repo.strip():
            return normalized_args, None

        from app.mcp_layer.servers.github_server import resolve_accessible_repo

        resolved_repo, resolution_error = await resolve_accessible_repo(repo)
        if resolution_error:
            return normalized_args, resolution_error
        if resolved_repo:
            normalized_args["repo"] = resolved_repo
        return normalized_args, None

    @staticmethod
    def _normalize_model_text_artifacts(text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            block = match.group(0)
            if "type" not in block or "text" not in block:
                return block

            parsed: Any | None = None
            for loader in (json.loads, ast.literal_eval):
                try:
                    parsed = loader(block)
                    break
                except Exception:
                    continue

            extracted = ChatService._extract_text_from_block(parsed)
            return f" {extracted} " if extracted else block

        normalized = SERIALIZED_TEXT_BLOCK_REGEX.sub(replace, text)
        normalized = re.sub(r"[ \t]+\n", "\n", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    @staticmethod
    def _extract_implicit_tool_call(text: str) -> ChatEvent | None:
        stripped = text.strip()
        if not stripped or not stripped.startswith("{") or not stripped.endswith("}"):
            return None

        parsed: Any | None = None
        for loader in (json.loads, ast.literal_eval):
            try:
                parsed = loader(stripped)
                break
            except Exception:
                continue

        if not isinstance(parsed, dict):
            return None

        if isinstance(parsed.get("function"), dict):
            function = parsed["function"]
            name = function.get("name")
            raw_args = function.get("arguments") or function.get("parameters") or {}
        elif isinstance(parsed.get("name"), str):
            name = parsed.get("name")
            raw_args = (
                parsed.get("parameters")
                or parsed.get("arguments")
                or parsed.get("args")
                or {}
            )
        else:
            tool_type = str(parsed.get("type", "")).lower()
            if tool_type not in {"function", "tool", "tool_call"}:
                return None
            name = parsed.get("name")
            raw_args = parsed.get("parameters") or parsed.get("arguments") or {}

        if not isinstance(name, str) or not name.strip():
            return None

        if isinstance(raw_args, str):
            for loader in (json.loads, ast.literal_eval):
                try:
                    raw_args = loader(raw_args)
                    break
                except Exception:
                    continue

        tool_args = raw_args if isinstance(raw_args, dict) else {}
        return ChatEvent(
            type=ChatEventType.TOOL_CALL,
            tool_name=name.strip(),
            tool_args=tool_args,
            tool_call_id=f"implicit_{name.strip()}",
        )

    @staticmethod
    def _extract_text_from_block(value: Any) -> str:
        if isinstance(value, dict):
            if value.get("type") == "text" and isinstance(value.get("text"), str):
                return value["text"]
            return ""

        if isinstance(value, list):
            parts = [ChatService._extract_text_from_block(item).strip() for item in value]
            return "\n".join(part for part in parts if part)

        return ""

    @classmethod
    def _is_relevant_request(cls, message: str, history: list[Message]) -> bool:
        if DIRECT_RELEVANCE_REGEX.search(message):
            return True
        if REPO_OR_PATH_REGEX.search(message) or SQL_QUERY_REGEX.search(message):
            return True
        if history and cls._history_contains_relevant_context(history):
            return bool(FOLLOW_UP_RELEVANCE_REGEX.search(message))
        return False

    @classmethod
    def _history_contains_relevant_context(cls, history: list[Message]) -> bool:
        for prior in reversed(history[-6:]):
            if prior.content == OUT_OF_SCOPE_RESPONSE:
                continue
            if DIRECT_RELEVANCE_REGEX.search(prior.content):
                return True
            if REPO_OR_PATH_REGEX.search(prior.content) or SQL_QUERY_REGEX.search(prior.content):
                return True
        return False

    @classmethod
    def _get_conversation_history(cls, conversation_id: str) -> list[Message]:
        if not conversation_id:
            return []
        history = cls._conversation_history.get(conversation_id, [])
        return [cls._clone_message(message) for message in history]

    @classmethod
    def _store_conversation_turn(
        cls,
        conversation_id: str,
        user_message: Message,
        assistant_text: str,
    ) -> None:
        if not conversation_id:
            return

        history = cls._conversation_history.setdefault(conversation_id, [])
        history.append(cls._clone_message(user_message))
        history.append(cls._clone_message(Message(role="assistant", content=assistant_text)))

        if len(history) > MAX_HISTORY_MESSAGES:
            cls._conversation_history[conversation_id] = history[-MAX_HISTORY_MESSAGES:]

    @staticmethod
    def _clone_message(message: Message) -> Message:
        return Message(
            role=message.role,
            content=message.content,
            tool_call_id=message.tool_call_id,
            tool_name=message.tool_name,
            tool_calls=[dict(tool_call) for tool_call in message.tool_calls],
        )
