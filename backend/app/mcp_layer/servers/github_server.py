"""GitHub MCP server with read-only tools and settings-backed auth."""
from __future__ import annotations

from difflib import SequenceMatcher
import json
import logging
import re

import httpx
from mcp.server.fastmcp import FastMCP

from app.config import settings

mcp = FastMCP("github")
logger = logging.getLogger("mcp.github")

GITHUB_API = "https://api.github.com"
DEPLOYMENT_WORKFLOW_HINTS = (
    "deploy",
    "deployment",
    "release",
    "publish",
    "rollout",
    "production",
    "staging",
)
SENSITIVE_PATH_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(^|/)\.env(?:\.(?!example$|sample$|template$)[^/]+)?$", re.IGNORECASE), "environment secrets file"),
    (re.compile(r"(^|/)\.envrc$", re.IGNORECASE), "environment loader file"),
    (re.compile(r"(^|/)\.npmrc$", re.IGNORECASE), "package registry credentials file"),
    (re.compile(r"(^|/)\.pypirc$", re.IGNORECASE), "package registry credentials file"),
    (re.compile(r"(^|/)\.netrc$", re.IGNORECASE), "network credentials file"),
    (re.compile(r"(^|/)\.git-credentials$", re.IGNORECASE), "git credentials file"),
    (re.compile(r"(^|/)\.dockercfg$", re.IGNORECASE), "docker credentials file"),
    (re.compile(r"(^|/)\.docker/config\.json$", re.IGNORECASE), "docker credentials file"),
    (re.compile(r"(^|/)\.aws/credentials$", re.IGNORECASE), "AWS credentials file"),
    (re.compile(r"(^|/)\.ssh/(?:id_rsa|id_dsa|id_ecdsa|id_ed25519)$", re.IGNORECASE), "SSH private key"),
    (re.compile(r"(^|/)(?:id_rsa|id_dsa|id_ecdsa|id_ed25519)$", re.IGNORECASE), "SSH private key"),
    (re.compile(r"\.(?:pem|key|p12|pfx|jks|keystore)$", re.IGNORECASE), "private key or keystore"),
    (re.compile(r"(^|/)(?:service-account|firebase-adminsdk|credentials)[^/]*\.json$", re.IGNORECASE), "credential file"),
]


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def _extract_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json() if response.content else {}
    except Exception:
        payload = {}
    if isinstance(payload, dict) and payload.get("message"):
        return str(payload["message"])
    fallback = response.text.strip()
    return fallback[:200] if fallback else "Unknown GitHub error"


async def _github_get(path: str, params: dict | None = None) -> dict | list:
    """Shared GET helper with clearer error handling."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{GITHUB_API}{path}", headers=_headers(), params=params)
        error_message = _extract_error_message(response)

        if response.status_code == 404:
            logger.warning("github_not_found path=%s", path)
            return {"error": f"Not found or not accessible: {path}. GitHub said: {error_message}"}
        if response.status_code == 403:
            logger.error("github_forbidden path=%s message=%s", path, error_message)
            return {"error": f"GitHub access forbidden: {error_message}"}
        if response.status_code == 401:
            logger.error("github_auth_failed path=%s message=%s", path, error_message)
            return {"error": f"GitHub authentication failed - check GITHUB_TOKEN. GitHub said: {error_message}"}
        if response.status_code >= 400:
            logger.error(
                "github_api_error",
                extra={"path": path, "status_code": response.status_code, "message": error_message},
            )
            return {"error": f"GitHub API error {response.status_code}: {error_message}"}

        return response.json()


def _serialize_repo(repo: dict) -> dict:
    return {
        "name": repo["full_name"],
        "description": repo.get("description", ""),
        "stars": repo["stargazers_count"],
        "language": repo.get("language", ""),
        "private": bool(repo.get("private", False)),
    }


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip().lstrip("/")


def _normalize_repo_input(repo: str) -> str:
    normalized = _normalize_path(repo).strip()
    normalized = re.sub(r"\b(?:repo|repository)\b", "", normalized, flags=re.IGNORECASE).strip()
    return normalized.strip("/")


def _compact_repo_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _sensitive_path_reason(path: str) -> str | None:
    normalized = _normalize_path(path)
    for pattern, reason in SENSITIVE_PATH_RULES:
        if pattern.search(normalized):
            return reason
    return None


def _is_deployment_workflow(workflow: dict) -> bool:
    name = str(workflow.get("name", "")).lower()
    path = str(workflow.get("path", "")).lower()
    text = f"{name} {path}"
    return any(hint in text for hint in DEPLOYMENT_WORKFLOW_HINTS)


async def _count_paginated_collection(
    path: str,
    params: dict | None = None,
    *,
    max_pages: int = 50,
) -> tuple[int | None, str | None]:
    request_params = dict(params or {})
    per_page = max(1, min(int(request_params.pop("per_page", 100)), 100))
    total = 0

    for page in range(1, max_pages + 1):
        data = await _github_get(path, {**request_params, "page": page, "per_page": per_page})
        if isinstance(data, dict) and "error" in data:
            return None, str(data["error"])
        if not isinstance(data, list):
            return None, f"Unexpected GitHub response while counting results for {path}"
        total += len(data)
        if len(data) < per_page:
            return total, None

    return total, None


async def _list_accessible_repos(max_pages: int = 5) -> list[dict]:
    if not settings.github_token:
        return []

    repos: list[dict] = []
    seen: set[str] = set()

    for page in range(1, max_pages + 1):
        data = await _github_get(
            "/user/repos",
            {
                "page": page,
                "per_page": 100,
                "sort": "updated",
                "affiliation": "owner,collaborator,organization_member",
            },
        )
        if not isinstance(data, list):
            break

        for repo in data:
            full_name = repo.get("full_name")
            if not full_name or full_name in seen:
                continue
            repos.append(repo)
            seen.add(full_name)

        if len(data) < 100:
            break

    return repos


def _repo_match_score(query: str, repo: dict) -> float:
    full_name = str(repo.get("full_name", "")).lower()
    short_name = str(repo.get("name") or full_name.rsplit("/", 1)[-1]).lower()
    query_lower = query.lower()
    query_compact = _compact_repo_token(query_lower)
    full_compact = _compact_repo_token(full_name)
    short_compact = _compact_repo_token(short_name)

    if query_lower == full_name:
        return 1.0
    if query_lower == short_name:
        return 0.99
    if query_compact and query_compact == short_compact:
        return 0.97
    if query_compact and query_compact == full_compact:
        return 0.96
    if query_lower in short_name or (query_compact and query_compact in short_compact):
        return 0.92
    if query_lower in full_name or (query_compact and query_compact in full_compact):
        return 0.9

    return max(
        SequenceMatcher(None, query_lower, short_name).ratio(),
        SequenceMatcher(None, query_lower, full_name).ratio() * 0.97,
    )


async def resolve_accessible_repo(repo: str) -> tuple[str | None, str | None]:
    normalized = _normalize_repo_input(repo)
    if not normalized:
        return None, "Repository name was empty."

    if re.fullmatch(r"[\w.-]+/[\w.-]+", normalized):
        return normalized, None

    repos = await _list_accessible_repos()
    if not repos:
        return normalized, None

    ranked = sorted(
        (
            (_repo_match_score(normalized, candidate), candidate["full_name"])
            for candidate in repos
            if candidate.get("full_name")
        ),
        key=lambda item: item[0],
        reverse=True,
    )

    if not ranked or ranked[0][0] < 0.72:
        suggestions = ", ".join(full_name for _, full_name in ranked[:5]) or "no accessible repositories matched"
        return None, (
            f"Repository '{repo}' could not be matched to an accessible GitHub repository. "
            f"Try a full owner/repo path or one of: {suggestions}."
        )

    best_score, best_full_name = ranked[0]
    second_score = ranked[1][0] if len(ranked) > 1 else 0.0

    if best_score >= 0.96 or best_score - second_score >= 0.08:
        logger.info("github_repo_resolved repo=%s resolved=%s score=%.3f", repo, best_full_name, best_score)
        return best_full_name, None

    suggestions = ", ".join(full_name for _, full_name in ranked[:5])
    return None, (
        f"Repository '{repo}' matched multiple accessible GitHub repositories. "
        f"Try one of: {suggestions}."
    )


@mcp.tool()
async def github_list_repos(org: str = "", page: int = 1) -> str:
    """List repositories for an org/user, or all accessible repos when org is omitted."""
    logger.info("github_list_repos org=%s page=%d", org or "[accessible]", page)
    try:
        data: dict | list = {"error": "No repository source returned data"}

        if settings.github_token:
            accessible = await _github_get(
                "/user/repos",
                {
                    "page": page,
                    "per_page": 100,
                    "sort": "updated",
                    "affiliation": "owner,collaborator,organization_member",
                },
            )
            if isinstance(accessible, list):
                if not org:
                    data = accessible
                else:
                    filtered = [
                        repo for repo in accessible
                        if repo.get("owner", {}).get("login", "").lower() == org.lower()
                    ]
                    if filtered:
                        data = filtered

        if org and isinstance(data, dict) and "error" in data:
            data = await _github_get(
                f"/orgs/{org}/repos",
                {"page": page, "per_page": 30, "sort": "updated", "type": "all"},
            )

        if org and isinstance(data, dict) and "error" in data:
            data = await _github_get(
                f"/users/{org}/repos",
                {"page": page, "per_page": 30, "sort": "updated", "type": "owner"},
            )

        if isinstance(data, dict) and "error" in data:
            return json.dumps(data)

        repos = [_serialize_repo(repo) for repo in data]
        logger.info("github_list_repos_result org=%s count=%d", org, len(repos))
        return json.dumps(repos, indent=2)
    except Exception as e:
        logger.error("github_list_repos_error org=%s error=%s", org, str(e))
        return json.dumps({"error": f"Failed to list repos: {e}"})


@mcp.tool()
async def github_search_code(query: str, repo: str) -> str:
    """Search for code in a GitHub repository."""
    logger.info("github_search_code repo=%s query=%s", repo, query[:50])
    try:
        resolved_repo, resolution_error = await resolve_accessible_repo(repo)
        if resolution_error:
            return json.dumps({"error": resolution_error})
        repo = resolved_repo or repo
        data = await _github_get("/search/code", {"q": f"{query} repo:{repo}"})
        if isinstance(data, dict) and "error" in data:
            return json.dumps(data)
        items = []
        filtered_sensitive = 0
        for item in data.get("items", []):
            if _sensitive_path_reason(item["path"]):
                filtered_sensitive += 1
                continue
            items.append({"path": item["path"], "name": item["name"], "url": item["html_url"]})
            if len(items) >= 10:
                break
        if filtered_sensitive:
            logger.warning(
                "github_search_code_filtered_sensitive_paths repo=%s count=%d",
                repo,
                filtered_sensitive,
            )
        return json.dumps(items, indent=2)
    except Exception as e:
        logger.error("github_search_code_error repo=%s error=%s", repo, str(e))
        return json.dumps({"error": f"Code search failed: {e}"})


@mcp.tool()
async def github_get_issues(repo: str, state: str = "open", labels: str = "", page: int = 1) -> str:
    """Get issues from a GitHub repository."""
    logger.info("github_get_issues repo=%s state=%s", repo, state)
    try:
        resolved_repo, resolution_error = await resolve_accessible_repo(repo)
        if resolution_error:
            return json.dumps({"error": resolution_error})
        repo = resolved_repo or repo
        params: dict = {"state": state, "page": page, "per_page": 20}
        if labels:
            params["labels"] = labels
        data = await _github_get(f"/repos/{repo}/issues", params)
        if isinstance(data, dict) and "error" in data:
            return json.dumps(data)
        issues = [
            {
                "number": issue["number"],
                "title": issue["title"],
                "state": issue["state"],
                "labels": [label["name"] for label in issue.get("labels", [])],
                "author": issue["user"]["login"],
                "created_at": issue["created_at"],
            }
            for issue in data
            if "pull_request" not in issue
        ]
        logger.info("github_get_issues_result repo=%s count=%d", repo, len(issues))
        return json.dumps(issues, indent=2)
    except Exception as e:
        logger.error("github_get_issues_error repo=%s error=%s", repo, str(e))
        return json.dumps({"error": f"Failed to get issues: {e}"})


@mcp.tool()
async def github_get_pull_requests(repo: str, state: str = "open", page: int = 1) -> str:
    """Get pull requests from a GitHub repository."""
    logger.info("github_get_prs repo=%s state=%s", repo, state)
    try:
        resolved_repo, resolution_error = await resolve_accessible_repo(repo)
        if resolution_error:
            return json.dumps({"error": resolution_error})
        repo = resolved_repo or repo
        data = await _github_get(f"/repos/{repo}/pulls", {"state": state, "page": page, "per_page": 20})
        if isinstance(data, dict) and "error" in data:
            return json.dumps(data)
        prs = [
            {
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "author": pr["user"]["login"],
                "created_at": pr["created_at"],
                "draft": pr.get("draft", False),
            }
            for pr in data
        ]
        return json.dumps(prs, indent=2)
    except Exception as e:
        logger.error("github_get_prs_error repo=%s error=%s", repo, str(e))
        return json.dumps({"error": f"Failed to get PRs: {e}"})


@mcp.tool()
async def github_read_file(repo: str, path: str, ref: str = "") -> str:
    """Read a file from a GitHub repository."""
    logger.info("github_read_file repo=%s path=%s ref=%s", repo, path, ref)
    blocked_reason = _sensitive_path_reason(path)
    if blocked_reason:
        logger.warning("github_read_file_blocked repo=%s path=%s reason=%s", repo, path, blocked_reason)
        return json.dumps({
            "error": f"Access to sensitive file '{path}' is blocked ({blocked_reason}).",
        })
    try:
        resolved_repo, resolution_error = await resolve_accessible_repo(repo)
        if resolution_error:
            return json.dumps({"error": resolution_error})
        repo = resolved_repo or repo
        target_ref = ref
        if not target_ref:
            repo_info = await _github_get(f"/repos/{repo}")
            if isinstance(repo_info, dict) and "error" not in repo_info:
                target_ref = str(repo_info.get("default_branch", "") or "")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{GITHUB_API}/repos/{repo}/contents/{path}",
                headers={**_headers(), "Accept": "application/vnd.github.v3.raw"},
                params={"ref": target_ref} if target_ref else None,
            )
            if response.status_code == 404:
                return json.dumps(
                    {"error": f"File not found or not accessible: {path}. GitHub said: {_extract_error_message(response)}"}
                )
            response.raise_for_status()
            content = response.text
            if len(content) > 10000:
                content = content[:10000] + "\n... (truncated)"
            return content
    except Exception as e:
        logger.error("github_read_file_error repo=%s path=%s error=%s", repo, path, str(e))
        return json.dumps({"error": f"Failed to read file: {e}"})


@mcp.tool()
async def github_get_repo_info(repo: str) -> str:
    """Get metadata about a GitHub repository."""
    logger.info("github_get_repo_info repo=%s", repo)
    try:
        resolved_repo, resolution_error = await resolve_accessible_repo(repo)
        if resolution_error:
            return json.dumps({"error": resolution_error})
        repo = resolved_repo or repo
        data = await _github_get(f"/repos/{repo}")
        if isinstance(data, dict) and "error" in data:
            return json.dumps(data)
        return json.dumps(
            {
                "name": data["full_name"],
                "description": data.get("description", ""),
                "stars": data["stargazers_count"],
                "forks": data["forks_count"],
                "language": data.get("language", ""),
                "open_issues": data["open_issues_count"],
                "private": bool(data.get("private", False)),
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
                "default_branch": data["default_branch"],
            },
            indent=2,
        )
    except Exception as e:
        logger.error("github_get_repo_info_error repo=%s error=%s", repo, str(e))
        return json.dumps({"error": f"Failed to get repo info: {e}"})


@mcp.tool()
async def github_get_repo_metrics(repo: str, branch: str = "") -> str:
    """Get repository-level counts for commits, pull requests, and workflows."""
    logger.info("github_get_repo_metrics repo=%s branch=%s", repo, branch or "[default]")
    try:
        resolved_repo, resolution_error = await resolve_accessible_repo(repo)
        if resolution_error:
            return json.dumps({"error": resolution_error})
        repo = resolved_repo or repo

        repo_info = await _github_get(f"/repos/{repo}")
        if isinstance(repo_info, dict) and "error" in repo_info:
            return json.dumps(repo_info)

        target_branch = branch or repo_info.get("default_branch", "")

        commit_count, commit_error = await _count_paginated_collection(
            f"/repos/{repo}/commits",
            {"sha": target_branch, "per_page": 100} if target_branch else {"per_page": 100},
        )
        pr_count, pr_error = await _count_paginated_collection(
            f"/repos/{repo}/pulls",
            {"state": "all", "per_page": 100},
        )

        workflows_payload = await _github_get(f"/repos/{repo}/actions/workflows")
        workflow_error = ""
        workflows: list[dict] = []
        if isinstance(workflows_payload, dict) and "error" in workflows_payload:
            workflow_error = str(workflows_payload["error"])
        elif isinstance(workflows_payload, dict):
            workflows = list(workflows_payload.get("workflows", []))

        deployment_workflows = [
            {
                "name": workflow.get("name", ""),
                "path": workflow.get("path", ""),
                "state": workflow.get("state", ""),
            }
            for workflow in workflows
            if _is_deployment_workflow(workflow)
        ]

        return json.dumps(
            {
                "repo": repo,
                "default_branch": repo_info.get("default_branch", ""),
                "counted_branch": target_branch,
                "commit_count": commit_count,
                "pull_request_count": pr_count,
                "workflow_count": len(workflows),
                "deployment_workflow_count": len(deployment_workflows),
                "deployment_workflows": deployment_workflows,
                "warnings": {
                    "commits": commit_error or "",
                    "pull_requests": pr_error or "",
                    "workflows": workflow_error,
                },
            },
            indent=2,
        )
    except Exception as e:
        logger.error("github_get_repo_metrics_error repo=%s error=%s", repo, str(e))
        return json.dumps({"error": f"Failed to get repository metrics: {e}"})


@mcp.tool()
async def github_count_commits(
    repo: str,
    author: str = "",
    since: str = "",
    until: str = "",
    branch: str = "",
    path: str = "",
) -> str:
    """Count commits in a repository with optional author, date, branch, and path filters."""
    logger.info(
        "github_count_commits repo=%s author=%s since=%s until=%s branch=%s path=%s",
        repo,
        author,
        since,
        until,
        branch,
        path,
    )
    if path:
        blocked_reason = _sensitive_path_reason(path)
        if blocked_reason:
            logger.warning("github_count_commits_blocked repo=%s path=%s reason=%s", repo, path, blocked_reason)
            return json.dumps({
                "error": f"Access to commit count for sensitive path '{path}' is blocked ({blocked_reason}).",
            })
    try:
        resolved_repo, resolution_error = await resolve_accessible_repo(repo)
        if resolution_error:
            return json.dumps({"error": resolution_error})
        repo = resolved_repo or repo

        params: dict[str, str | int] = {"per_page": 100}
        if author:
            params["author"] = author
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if branch:
            params["sha"] = branch
        if path:
            params["path"] = path

        total, error = await _count_paginated_collection(f"/repos/{repo}/commits", params)
        if error:
            return json.dumps({"error": error})

        return json.dumps(
            {
                "repo": repo,
                "author": author,
                "branch": branch,
                "path": path,
                "since": since,
                "until": until,
                "commit_count": total or 0,
            },
            indent=2,
        )
    except Exception as e:
        logger.error("github_count_commits_error repo=%s error=%s", repo, str(e))
        return json.dumps({"error": f"Failed to count commits: {e}"})


@mcp.tool()
async def github_get_commit_history(
    repo: str,
    path: str = "",
    count: int = 30,
    author: str = "",
    since: str = "",
    until: str = "",
    branch: str = "",
) -> str:
    """Get recent commit history for a repository or file."""
    logger.info(
        "github_get_commits repo=%s path=%s count=%d author=%s since=%s until=%s branch=%s",
        repo,
        path,
        count,
        author,
        since,
        until,
        branch,
    )
    if path:
        blocked_reason = _sensitive_path_reason(path)
        if blocked_reason:
            logger.warning("github_get_commits_blocked repo=%s path=%s reason=%s", repo, path, blocked_reason)
            return json.dumps({
                "error": f"Access to commit history for sensitive path '{path}' is blocked ({blocked_reason}).",
            })
    try:
        resolved_repo, resolution_error = await resolve_accessible_repo(repo)
        if resolution_error:
            return json.dumps({"error": resolution_error})
        repo = resolved_repo or repo
        max_commits = max(1, min(count, 200))
        params: dict = {"per_page": min(max_commits, 100)}
        if path:
            params["path"] = path
        if author:
            params["author"] = author
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if branch:
            params["sha"] = branch

        commits_raw: list[dict] = []
        page = 1
        while len(commits_raw) < max_commits:
            page_params = {**params, "page": page}
            data = await _github_get(f"/repos/{repo}/commits", page_params)
            if isinstance(data, dict) and "error" in data:
                return json.dumps(data)
            if not isinstance(data, list) or not data:
                break
            commits_raw.extend(data)
            if len(data) < page_params["per_page"]:
                break
            page += 1

        commits = [
            {
                "sha": commit["sha"][:7],
                "message": commit["commit"]["message"].split("\n")[0],
                "author": commit["commit"]["author"]["name"],
                "date": commit["commit"]["author"]["date"],
            }
            for commit in commits_raw[:max_commits]
        ]
        return json.dumps(commits, indent=2)
    except Exception as e:
        logger.error("github_get_commits_error repo=%s error=%s", repo, str(e))
        return json.dumps({"error": f"Failed to get commits: {e}"})


if __name__ == "__main__":
    mcp.run(transport="stdio")
