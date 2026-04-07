"""MCPManager — manages MCP server subprocesses and tool routing."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from app.config import settings
from app.utils.logging import get_logger

log = get_logger("mcp.manager")

SERVER_DIR = Path(__file__).parent / "servers"


class MCPTool:
    """Represents a tool exposed by an MCP server."""
    def __init__(self, name: str, description: str, parameters: dict, server_name: str):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.server_name = server_name


class MCPManager:
    """Manages lifecycle of MCP servers and routes tool calls."""

    def __init__(self):
        self._tools: dict[str, MCPTool] = {}
        self._servers: dict[str, dict] = {}  # server_name -> {process, reader, writer}
        self._initialized = False

    async def start_all(self) -> None:
        """Register tools from configured servers (lazy — no subprocesses yet)."""
        if self._initialized:
            return

        # GitHub tools
        if settings.github_token:
            self._register_github_tools()
            log.info("mcp_server_ready", server="github", tools=7)

        # Slack tools
        if settings.slack_bot_token:
            self._register_slack_tools()
            log.info("mcp_server_ready", server="slack", tools=5)

        # Postgres tools
        if settings.database_url:
            self._register_postgres_tools()
            log.info("mcp_server_ready", server="postgres", tools=4)

        self._initialized = True
        log.info("mcp_manager_ready", total_tools=len(self._tools))

    def _register_github_tools(self) -> None:
        tools = [
            ("github_list_repos", "List repositories in a GitHub organization", {"type": "object", "properties": {"org": {"type": "string", "description": "GitHub org or user"}, "page": {"type": "integer", "default": 1}}, "required": ["org"]}),
            ("github_search_code", "Search for code in a GitHub repository", {"type": "object", "properties": {"query": {"type": "string"}, "repo": {"type": "string", "description": "owner/repo"}}, "required": ["query", "repo"]}),
            ("github_get_issues", "Get issues from a repository", {"type": "object", "properties": {"repo": {"type": "string"}, "state": {"type": "string", "default": "open"}, "labels": {"type": "string", "default": ""}, "page": {"type": "integer", "default": 1}}, "required": ["repo"]}),
            ("github_get_pull_requests", "Get pull requests from a repository", {"type": "object", "properties": {"repo": {"type": "string"}, "state": {"type": "string", "default": "open"}, "page": {"type": "integer", "default": 1}}, "required": ["repo"]}),
            ("github_read_file", "Read a file from a repository", {"type": "object", "properties": {"repo": {"type": "string"}, "path": {"type": "string"}, "ref": {"type": "string", "default": "main"}}, "required": ["repo", "path"]}),
            ("github_get_repo_info", "Get repository metadata", {"type": "object", "properties": {"repo": {"type": "string"}}, "required": ["repo"]}),
            ("github_get_commit_history", "Get recent commits", {"type": "object", "properties": {"repo": {"type": "string"}, "path": {"type": "string", "default": ""}, "count": {"type": "integer", "default": 10}}, "required": ["repo"]}),
        ]
        for name, desc, params in tools:
            self._tools[name] = MCPTool(name, desc, params, "github")

    def _register_slack_tools(self) -> None:
        tools = [
            ("slack_search_messages", "Search messages in Slack", {"type": "object", "properties": {"query": {"type": "string"}, "channel": {"type": "string", "default": ""}, "count": {"type": "integer", "default": 20}}, "required": ["query"]}),
            ("slack_list_channels", "List joined Slack channels", {"type": "object", "properties": {"limit": {"type": "integer", "default": 100}}, "required": []}),
            ("slack_get_thread", "Get replies in a thread", {"type": "object", "properties": {"channel": {"type": "string"}, "thread_ts": {"type": "string"}}, "required": ["channel", "thread_ts"]}),
            ("slack_get_channel_history", "Get recent channel messages", {"type": "object", "properties": {"channel": {"type": "string"}, "limit": {"type": "integer", "default": 50}}, "required": ["channel"]}),
            ("slack_get_user_info", "Get Slack user info", {"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]}),
        ]
        for name, desc, params in tools:
            self._tools[name] = MCPTool(name, desc, params, "slack")

    def _register_postgres_tools(self) -> None:
        tools = [
            ("db_list_tables", "List all database tables", {"type": "object", "properties": {}, "required": []}),
            ("db_get_schema", "Get table schema", {"type": "object", "properties": {"table": {"type": "string"}}, "required": ["table"]}),
            ("db_query", "Execute read-only SQL query", {"type": "object", "properties": {"sql": {"type": "string"}, "params": {"type": "string", "default": "[]"}}, "required": ["sql"]}),
            ("db_explain_query", "Get query execution plan", {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]}),
        ]
        for name, desc, params in tools:
            self._tools[name] = MCPTool(name, desc, params, "postgres")

    def get_all_tools(self) -> list[MCPTool]:
        return list(self._tools.values())

    def get_server_for_tool(self, tool_name: str) -> str | None:
        tool = self._tools.get(tool_name)
        return tool.server_name if tool else None

    async def execute_tool(self, tool_name: str, args: dict) -> str:
        """Execute a tool by importing and calling the server function directly."""
        tool = self._tools.get(tool_name)
        if not tool:
            return f"Error: Unknown tool '{tool_name}'"

        try:
            if tool.server_name == "github":
                from app.mcp_layer.servers import github_server
                fn = getattr(github_server, tool_name)
                return await fn(**args)
            elif tool.server_name == "slack":
                from app.mcp_layer.servers import slack_server
                fn = getattr(slack_server, tool_name)
                return await fn(**args)
            elif tool.server_name == "postgres":
                from app.mcp_layer.servers import postgres_server
                fn = getattr(postgres_server, tool_name)
                return await fn(**args)
            else:
                return f"Error: Unknown server '{tool.server_name}'"
        except Exception as e:
            log.error("tool_execution_error", tool=tool_name, error=str(e))
            return f"Error executing {tool_name}: {str(e)}"

    async def stop_all(self) -> None:
        self._initialized = False
        self._tools.clear()
