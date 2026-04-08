"""Role-Based Access Control — filter tools and validate per-user permissions."""
from __future__ import annotations

import fnmatch
import json

from app.utils.errors import AuthorizationError


# ─── Role hierarchy ─────────────────────────────────────────────────

ROLES = {"admin", "member", "viewer"}

TOOL_CATEGORIES = {
    "github": [
        "github_list_repos",
        "github_get_repo_metrics",
        "github_count_commits",
        "github_search_code",
        "github_get_issues",
        "github_get_pull_requests",
        "github_read_file",
        "github_get_repo_info",
        "github_get_commit_history",
    ],
    "slack": [
        "slack_search_messages",
        "slack_list_channels",
        "slack_get_thread",
        "slack_get_channel_history",
        "slack_get_user_info",
    ],
    "db": [
        "db_list_tables",
        "db_get_schema",
        "db_query",
        "db_explain_query",
    ],
}


def _category_for_tool(tool_name: str) -> str | None:
    for cat, tools in TOOL_CATEGORIES.items():
        if tool_name in tools:
            return cat
    return None


def get_user_tool_names(user: dict) -> set[str]:
    """Return the set of tool names this user is allowed to call."""
    role = user.get("role", "viewer")

    if role == "admin":
        # Admin gets all tools
        return {t for tools in TOOL_CATEGORIES.values() for t in tools}

    if role == "viewer":
        # Viewer gets no tools — chat only
        return set()

    # Member: gets tools for categories where they have at least one resource
    allowed: set[str] = set()
    if user.get("allowed_repos"):
        allowed.update(TOOL_CATEGORIES["github"])
    if user.get("allowed_channels"):
        allowed.update(TOOL_CATEGORIES["slack"])
    if user.get("allowed_db_tables"):
        allowed.update(TOOL_CATEGORIES["db"])
    return allowed


def validate_tool_call(user: dict, tool_name: str, args: dict) -> None:
    """Raise AuthorizationError if the user cannot call this tool with these args."""
    role = user.get("role", "viewer")

    if role == "admin":
        return  # admin can do anything

    if role == "viewer":
        raise AuthorizationError(
            f"Viewers cannot use tools. Your role is 'viewer'. Contact an admin for access."
        )

    # Member — check specific resource access
    category = _category_for_tool(tool_name)
    if category is None:
        raise AuthorizationError(f"Unknown tool: {tool_name}")

    if category == "github":
        repo = args.get("repo", "")
        org = args.get("org", "")
        allowed_repos = user.get("allowed_repos", [])
        if tool_name == "github_list_repos":
            if not allowed_repos:
                raise AuthorizationError("You have no GitHub repository access.")
            if org and not _allow_org_listing(org, allowed_repos):
                raise AuthorizationError(
                    f"You don't have access to list repositories for '{org}'. "
                    f"Your allowed repos: {allowed_repos}"
                )
            return
        repo = repo or org
        if not _matches_allowlist(repo, allowed_repos):
            raise AuthorizationError(
                f"You don't have access to repository '{repo}'. "
                f"Your allowed repos: {allowed_repos}"
            )

    elif category == "slack":
        channel = args.get("channel", "")
        allowed_channels = user.get("allowed_channels", [])
        # Channel listing doesn't require specific channel
        if tool_name == "slack_list_channels":
            if not allowed_channels:
                raise AuthorizationError("You have no Slack channel access.")
            return
        if channel and not _matches_allowlist(channel, allowed_channels):
            raise AuthorizationError(
                f"You don't have access to channel '{channel}'. "
                f"Your allowed channels: {allowed_channels}"
            )

    elif category == "db":
        table = args.get("table", "")
        allowed_tables = user.get("allowed_db_tables", [])
        # Table listing is always allowed if user has any db access
        if tool_name == "db_list_tables":
            if not allowed_tables:
                raise AuthorizationError("You have no database access.")
            return
        if table and not _matches_allowlist(table, allowed_tables):
            raise AuthorizationError(
                f"You don't have access to table '{table}'. "
                f"Your allowed tables: {allowed_tables}"
            )


def _matches_allowlist(resource: str, allowed: list[str]) -> bool:
    """Check if resource matches any pattern in the allowlist. Supports wildcards."""
    if not allowed:
        return False
    if "*" in allowed:
        return True
    return any(fnmatch.fnmatch(resource, pattern) for pattern in allowed)


def _allow_org_listing(org: str, allowed_repos: list[str]) -> bool:
    if not allowed_repos:
        return False
    if "*" in allowed_repos:
        return True

    normalized_org = org.lower()
    for pattern in allowed_repos:
        if "/" in pattern:
            owner = pattern.split("/", 1)[0].lower()
            if owner == normalized_org or fnmatch.fnmatch(f"{normalized_org}/placeholder", pattern.lower()):
                return True
        elif fnmatch.fnmatch(normalized_org, pattern.lower()):
            return True
    return False


def filter_tool_result_for_user(user: dict, tool_name: str, result: str) -> str:
    """Filter list-style tool results to match the user's allowlists."""
    if user.get("role") == "admin":
        return result

    try:
        payload = json.loads(result)
    except Exception:
        return result

    if not isinstance(payload, list):
        return result

    if tool_name == "github_list_repos":
        allowed_repos = user.get("allowed_repos", [])
        filtered = [
            repo for repo in payload
            if isinstance(repo, dict) and _matches_allowlist(str(repo.get("name", "")), allowed_repos)
        ]
        return json.dumps(filtered, indent=2)

    if tool_name == "slack_list_channels":
        allowed_channels = user.get("allowed_channels", [])
        filtered = [
            channel for channel in payload
            if isinstance(channel, dict)
            and (
                _matches_allowlist(str(channel.get("name", "")), allowed_channels)
                or _matches_allowlist(str(channel.get("id", "")), allowed_channels)
            )
        ]
        return json.dumps(filtered, indent=2)

    if tool_name == "db_list_tables":
        allowed_tables = user.get("allowed_db_tables", [])
        filtered = []
        for table in payload:
            if not isinstance(table, dict):
                continue
            table_name = str(table.get("table", ""))
            schema = str(table.get("schema", ""))
            qualified = f"{schema}.{table_name}" if schema else table_name
            if _matches_allowlist(qualified, allowed_tables) or _matches_allowlist(table_name, allowed_tables):
                filtered.append(table)
        return json.dumps(filtered, indent=2)

    return result
