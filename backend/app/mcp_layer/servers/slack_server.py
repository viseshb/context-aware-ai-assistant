"""Slack MCP Server — 5 read-only tools with error logging."""
from __future__ import annotations

import json
import logging
import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("slack")
logger = logging.getLogger("mcp.slack")

SLACK_API = "https://slack.com/api"
TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


async def _slack_get(method: str, params: dict | None = None) -> dict:
    """Shared GET helper with error handling."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{SLACK_API}/{method}", headers=_headers(), params=params)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            error = data.get("error", "unknown_error")
            logger.error("slack_api_error method=%s error=%s", method, error)
            return {"error": f"Slack API error: {error}"}
        return data


@mcp.tool()
async def slack_search_messages(query: str, channel: str = "", count: int = 20) -> str:
    """Search for messages in Slack."""
    search_query = f"{query} in:#{channel}" if channel else query
    logger.info("slack_search query=%s channel=%s", query[:50], channel)
    try:
        data = await _slack_get("search.messages", {"query": search_query, "count": min(count, 100)})
        if "error" in data:
            return json.dumps(data)
        matches = [
            {"text": m["text"][:300], "user": m.get("username", "unknown"),
             "channel": m.get("channel", {}).get("name", ""), "ts": m.get("ts", "")}
            for m in data.get("messages", {}).get("matches", [])[:count]
        ]
        logger.info("slack_search_result count=%d", len(matches))
        return json.dumps(matches, indent=2)
    except Exception as e:
        logger.error("slack_search_error error=%s", str(e))
        return json.dumps({"error": f"Slack search failed: {e}"})


@mcp.tool()
async def slack_list_channels(limit: int = 100) -> str:
    """List joined Slack channels."""
    logger.info("slack_list_channels limit=%d", limit)
    try:
        data = await _slack_get("conversations.list", {"limit": min(limit, 200), "types": "public_channel,private_channel"})
        if "error" in data:
            return json.dumps(data)
        channels = [
            {"name": ch["name"], "id": ch["id"], "topic": ch.get("topic", {}).get("value", ""),
             "member_count": ch.get("num_members", 0)}
            for ch in data.get("channels", [])
        ]
        logger.info("slack_list_channels_result count=%d", len(channels))
        return json.dumps(channels, indent=2)
    except Exception as e:
        logger.error("slack_list_channels_error error=%s", str(e))
        return json.dumps({"error": f"Failed to list channels: {e}"})


@mcp.tool()
async def slack_get_thread(channel: str, thread_ts: str) -> str:
    """Get all replies in a Slack thread."""
    logger.info("slack_get_thread channel=%s ts=%s", channel, thread_ts)
    try:
        data = await _slack_get("conversations.replies", {"channel": channel, "ts": thread_ts, "limit": 50})
        if "error" in data:
            return json.dumps(data)
        messages = [
            {"text": m["text"][:500], "user": m.get("user", "unknown"), "ts": m["ts"]}
            for m in data.get("messages", [])
        ]
        return json.dumps(messages, indent=2)
    except Exception as e:
        logger.error("slack_get_thread_error channel=%s error=%s", channel, str(e))
        return json.dumps({"error": f"Failed to get thread: {e}"})


@mcp.tool()
async def slack_get_channel_history(channel: str, limit: int = 50) -> str:
    """Get recent messages from a Slack channel."""
    logger.info("slack_get_history channel=%s limit=%d", channel, limit)
    try:
        data = await _slack_get("conversations.history", {"channel": channel, "limit": min(limit, 100)})
        if "error" in data:
            return json.dumps(data)
        messages = [
            {"text": m["text"][:500], "user": m.get("user", "unknown"),
             "ts": m["ts"], "thread_ts": m.get("thread_ts")}
            for m in data.get("messages", [])
        ]
        return json.dumps(messages, indent=2)
    except Exception as e:
        logger.error("slack_get_history_error channel=%s error=%s", channel, str(e))
        return json.dumps({"error": f"Failed to get history: {e}"})


@mcp.tool()
async def slack_get_user_info(user_id: str) -> str:
    """Get information about a Slack user."""
    logger.info("slack_get_user user_id=%s", user_id)
    try:
        data = await _slack_get("users.info", {"user": user_id})
        if "error" in data:
            return json.dumps(data)
        user = data.get("user", {})
        profile = user.get("profile", {})
        return json.dumps({
            "name": user.get("real_name", ""), "display_name": profile.get("display_name", ""),
            "title": profile.get("title", ""), "status": profile.get("status_text", ""),
        }, indent=2)
    except Exception as e:
        logger.error("slack_get_user_error user_id=%s error=%s", user_id, str(e))
        return json.dumps({"error": f"Failed to get user info: {e}"})


if __name__ == "__main__":
    mcp.run(transport="stdio")
