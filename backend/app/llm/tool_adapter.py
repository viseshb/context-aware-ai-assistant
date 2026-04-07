"""Convert MCP tools to LLM provider-native formats."""
from __future__ import annotations

from app.llm.base import ToolDefinition
from app.mcp_layer.manager import MCPTool


def mcp_to_tool_definitions(mcp_tools: list[MCPTool]) -> list[ToolDefinition]:
    """Convert MCPTool list to our generic ToolDefinition format."""
    return [
        ToolDefinition(
            name=t.name,
            description=t.description,
            parameters=t.parameters,
        )
        for t in mcp_tools
    ]


def filter_tools_for_user(all_tools: list[MCPTool], user: dict) -> list[MCPTool]:
    """Filter MCP tools based on user's RBAC permissions."""
    from app.security.rbac import get_user_tool_names

    allowed_names = get_user_tool_names(user)
    return [t for t in all_tools if t.name in allowed_names]
