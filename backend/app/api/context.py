"""Context sources status — shows what data sources are connected."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import settings
from app.dependencies import get_current_user, get_mcp_manager
from app.security.rbac import get_user_tool_names
from app.utils.logging import get_logger

router = APIRouter(tags=["context"])
log = get_logger("api.context")


@router.get("/api/context/sources")
async def get_context_sources(user: dict = Depends(get_current_user)) -> dict:
    """Return connected data sources and user's access level."""
    mcp = await get_mcp_manager()
    all_tools = mcp.get_all_tools()
    user_tools = get_user_tool_names(user)

    sources = []

    # GitHub
    github_connected = bool(settings.github_token)
    github_tools = [t for t in all_tools if t.server_name == "github"]
    github_user_tools = [t.name for t in github_tools if t.name in user_tools]
    sources.append({
        "type": "github",
        "label": "GitHub",
        "connected": github_connected,
        "total_tools": len(github_tools),
        "user_tools": len(github_user_tools),
        "status": "connected" if github_connected else "not configured",
        "detail": f"{len(github_user_tools)}/{len(github_tools)} tools accessible" if github_connected else "Add GITHUB_TOKEN to .env",
    })

    # Slack
    slack_connected = bool(settings.slack_bot_token)
    slack_tools = [t for t in all_tools if t.server_name == "slack"]
    slack_user_tools = [t.name for t in slack_tools if t.name in user_tools]
    sources.append({
        "type": "slack",
        "label": "Slack",
        "connected": slack_connected,
        "total_tools": len(slack_tools),
        "user_tools": len(slack_user_tools),
        "status": "connected" if slack_connected else "not configured",
        "detail": f"{len(slack_user_tools)}/{len(slack_tools)} tools accessible" if slack_connected else "Add SLACK_BOT_TOKEN to .env",
    })

    # PostgreSQL
    db_connected = bool(settings.database_url)
    db_tools = [t for t in all_tools if t.server_name == "postgres"]
    db_user_tools = [t.name for t in db_tools if t.name in user_tools]
    sources.append({
        "type": "postgres",
        "label": "PostgreSQL",
        "connected": db_connected,
        "total_tools": len(db_tools),
        "user_tools": len(db_user_tools),
        "status": "connected" if db_connected else "not configured",
        "detail": f"{len(db_user_tools)}/{len(db_tools)} tools accessible" if db_connected else "Add DATABASE_URL to .env",
    })

    role_message = ""
    if user["role"] == "viewer":
        role_message = "Your role is Viewer — you can chat but cannot access data sources. Ask an admin to upgrade your role to Member."
    elif user["role"] == "member" and not user.get("allowed_repos") and not user.get("allowed_channels") and not user.get("allowed_db_tables"):
        role_message = "Your role is Member but no resources are assigned yet. Ask an admin to assign repos/channels/tables."

    return {
        "sources": sources,
        "role": user["role"],
        "role_message": role_message,
        "total_tools": len(all_tools),
        "user_accessible_tools": len(user_tools),
    }
