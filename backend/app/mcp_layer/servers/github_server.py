"""GitHub MCP Server — 7 read-only tools with error logging."""
from __future__ import annotations

import json
import logging
import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("github")
logger = logging.getLogger("mcp.github")

GITHUB_API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github.v3+json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


async def _github_get(path: str, params: dict | None = None) -> dict | list:
    """Shared GET helper with error handling."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{GITHUB_API}{path}", headers=_headers(), params=params)
        if r.status_code == 404:
            logger.warning("github_not_found path=%s", path)
            return {"error": f"Not found: {path}"}
        if r.status_code == 403:
            logger.error("github_rate_limited path=%s", path)
            return {"error": "GitHub API rate limit exceeded"}
        if r.status_code == 401:
            logger.error("github_auth_failed path=%s", path)
            return {"error": "GitHub authentication failed — check GITHUB_TOKEN"}
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def github_list_repos(org: str, page: int = 1) -> str:
    """List repositories in a GitHub organization."""
    logger.info("github_list_repos org=%s page=%d", org, page)
    try:
        data = await _github_get(f"/orgs/{org}/repos", {"page": page, "per_page": 30, "sort": "updated"})
        if isinstance(data, dict) and "error" in data:
            # Try as user
            data = await _github_get(f"/users/{org}/repos", {"page": page, "per_page": 30, "sort": "updated"})
        if isinstance(data, dict) and "error" in data:
            return json.dumps(data)
        repos = [
            {"name": r["full_name"], "description": r.get("description", ""), "stars": r["stargazers_count"], "language": r.get("language", "")}
            for r in data
        ]
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
        data = await _github_get("/search/code", {"q": f"{query} repo:{repo}"})
        if isinstance(data, dict) and "error" in data:
            return json.dumps(data)
        items = [
            {"path": item["path"], "name": item["name"], "url": item["html_url"]}
            for item in data.get("items", [])[:10]
        ]
        return json.dumps(items, indent=2)
    except Exception as e:
        logger.error("github_search_code_error repo=%s error=%s", repo, str(e))
        return json.dumps({"error": f"Code search failed: {e}"})


@mcp.tool()
async def github_get_issues(repo: str, state: str = "open", labels: str = "", page: int = 1) -> str:
    """Get issues from a GitHub repository."""
    logger.info("github_get_issues repo=%s state=%s", repo, state)
    try:
        params: dict = {"state": state, "page": page, "per_page": 20}
        if labels:
            params["labels"] = labels
        data = await _github_get(f"/repos/{repo}/issues", params)
        if isinstance(data, dict) and "error" in data:
            return json.dumps(data)
        issues = [
            {"number": i["number"], "title": i["title"], "state": i["state"],
             "labels": [l["name"] for l in i.get("labels", [])],
             "author": i["user"]["login"], "created_at": i["created_at"]}
            for i in data if "pull_request" not in i
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
        data = await _github_get(f"/repos/{repo}/pulls", {"state": state, "page": page, "per_page": 20})
        if isinstance(data, dict) and "error" in data:
            return json.dumps(data)
        prs = [
            {"number": pr["number"], "title": pr["title"], "state": pr["state"],
             "author": pr["user"]["login"], "created_at": pr["created_at"], "draft": pr.get("draft", False)}
            for pr in data
        ]
        return json.dumps(prs, indent=2)
    except Exception as e:
        logger.error("github_get_prs_error repo=%s error=%s", repo, str(e))
        return json.dumps({"error": f"Failed to get PRs: {e}"})


@mcp.tool()
async def github_read_file(repo: str, path: str, ref: str = "main") -> str:
    """Read a file from a GitHub repository."""
    logger.info("github_read_file repo=%s path=%s ref=%s", repo, path, ref)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{GITHUB_API}/repos/{repo}/contents/{path}",
                headers={**_headers(), "Accept": "application/vnd.github.v3.raw"},
                params={"ref": ref},
            )
            if r.status_code == 404:
                return json.dumps({"error": f"File not found: {path}"})
            r.raise_for_status()
            content = r.text
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
        data = await _github_get(f"/repos/{repo}")
        if isinstance(data, dict) and "error" in data:
            return json.dumps(data)
        return json.dumps({
            "name": data["full_name"], "description": data.get("description", ""),
            "stars": data["stargazers_count"], "forks": data["forks_count"],
            "language": data.get("language", ""), "open_issues": data["open_issues_count"],
            "created_at": data["created_at"], "updated_at": data["updated_at"],
            "default_branch": data["default_branch"],
        }, indent=2)
    except Exception as e:
        logger.error("github_get_repo_info_error repo=%s error=%s", repo, str(e))
        return json.dumps({"error": f"Failed to get repo info: {e}"})


@mcp.tool()
async def github_get_commit_history(repo: str, path: str = "", count: int = 10) -> str:
    """Get recent commit history for a repository or file."""
    logger.info("github_get_commits repo=%s path=%s count=%d", repo, path, count)
    try:
        params: dict = {"per_page": min(count, 30)}
        if path:
            params["path"] = path
        data = await _github_get(f"/repos/{repo}/commits", params)
        if isinstance(data, dict) and "error" in data:
            return json.dumps(data)
        commits = [
            {"sha": c["sha"][:7], "message": c["commit"]["message"].split("\n")[0],
             "author": c["commit"]["author"]["name"], "date": c["commit"]["author"]["date"]}
            for c in data
        ]
        return json.dumps(commits, indent=2)
    except Exception as e:
        logger.error("github_get_commits_error repo=%s error=%s", repo, str(e))
        return json.dumps({"error": f"Failed to get commits: {e}"})


if __name__ == "__main__":
    mcp.run(transport="stdio")
