from __future__ import annotations

import asyncio
import json
import importlib

import pytest

from app.mcp_layer.servers import github_server, slack_server


def test_github_headers_use_settings_token(monkeypatch):
    monkeypatch.setattr("app.mcp_layer.servers.github_server.settings.github_token", "test-token")
    headers = github_server._headers()
    assert headers["Authorization"] == "Bearer test-token"


def test_github_list_repos_can_use_authenticated_user_repo_access(monkeypatch):
    monkeypatch.setattr("app.mcp_layer.servers.github_server.settings.github_token", "test-token")

    async def fake_github_get(path: str, params: dict | None = None):
        if path == "/user/repos":
            return [
                {
                    "full_name": "acme/private-repo",
                    "description": "private",
                    "stargazers_count": 1,
                    "language": "Python",
                    "private": True,
                    "owner": {"login": "acme"},
                },
                {
                    "full_name": "other/public-repo",
                    "description": "public",
                    "stargazers_count": 2,
                    "language": "TypeScript",
                    "private": False,
                    "owner": {"login": "other"},
                },
            ]
        raise AssertionError(f"Unexpected path: {path}")

    monkeypatch.setattr(github_server, "_github_get", fake_github_get)

    payload = asyncio.run(github_server.github_list_repos("acme"))
    repos = json.loads(payload)

    assert repos == [
        {
            "name": "acme/private-repo",
            "description": "private",
            "stars": 1,
            "language": "Python",
            "private": True,
        }
    ]


def test_github_list_repos_can_omit_org_and_return_accessible_repos(monkeypatch):
    monkeypatch.setattr("app.mcp_layer.servers.github_server.settings.github_token", "test-token")

    async def fake_github_get(path: str, params: dict | None = None):
        assert path == "/user/repos"
        return [
            {
                "full_name": "acme/interview-helper",
                "description": "assistant repo",
                "stargazers_count": 7,
                "language": "TypeScript",
                "private": True,
                "owner": {"login": "acme"},
            }
        ]

    monkeypatch.setattr(github_server, "_github_get", fake_github_get)

    payload = asyncio.run(github_server.github_list_repos())
    repos = json.loads(payload)

    assert repos == [
        {
            "name": "acme/interview-helper",
            "description": "assistant repo",
            "stars": 7,
            "language": "TypeScript",
            "private": True,
        }
    ]


def test_resolve_accessible_repo_accepts_unique_short_name(monkeypatch):
    monkeypatch.setattr("app.mcp_layer.servers.github_server.settings.github_token", "test-token")

    async def fake_github_get(path: str, params: dict | None = None):
        assert path == "/user/repos"
        return [
            {
                "full_name": "viseshb/Interview-Helper",
                "name": "Interview-Helper",
                "owner": {"login": "viseshb"},
            },
            {
                "full_name": "viseshb/context-ai",
                "name": "context-ai",
                "owner": {"login": "viseshb"},
            },
        ]

    monkeypatch.setattr(github_server, "_github_get", fake_github_get)

    resolved, error = asyncio.run(github_server.resolve_accessible_repo("Interview-Helper repo"))

    assert error is None
    assert resolved == "viseshb/Interview-Helper"


def test_github_get_commit_history_supports_author_and_date_filters(monkeypatch):
    monkeypatch.setattr("app.mcp_layer.servers.github_server.settings.github_token", "test-token")

    async def fake_github_get(path: str, params: dict | None = None):
        assert path == "/repos/viseshb/Interview-Helper/commits"
        assert params == {
            "per_page": 5,
            "author": "viseshb",
            "since": "2026-01-01T00:00:00Z",
            "until": "2026-04-01T00:00:00Z",
            "sha": "main",
            "page": 1,
        }
        return [
            {
                "sha": "abcdef123456",
                "commit": {
                    "message": "Add deployment workflow\n\nMore details",
                    "author": {"name": "Visesh", "date": "2026-03-20T10:00:00Z"},
                },
            }
        ]

    async def fake_resolve(repo: str):
        assert repo == "Interview-Helper"
        return "viseshb/Interview-Helper", None

    monkeypatch.setattr(github_server, "_github_get", fake_github_get)
    monkeypatch.setattr(github_server, "resolve_accessible_repo", fake_resolve)

    payload = asyncio.run(github_server.github_get_commit_history(
        repo="Interview-Helper",
        count=5,
        author="viseshb",
        since="2026-01-01T00:00:00Z",
        until="2026-04-01T00:00:00Z",
        branch="main",
    ))
    commits = json.loads(payload)

    assert commits == [
        {
            "sha": "abcdef1",
            "message": "Add deployment workflow",
            "author": "Visesh",
            "date": "2026-03-20T10:00:00Z",
        }
    ]


def test_github_get_repo_metrics_counts_commits_prs_and_deployments(monkeypatch):
    monkeypatch.setattr("app.mcp_layer.servers.github_server.settings.github_token", "test-token")

    async def fake_resolve(repo: str):
        assert repo == "Interview-Helper"
        return "viseshb/Interview-Helper", None

    async def fake_github_get(path: str, params: dict | None = None):
        if path == "/repos/viseshb/Interview-Helper":
            return {"default_branch": "master"}
        if path == "/repos/viseshb/Interview-Helper/commits":
            if params == {"sha": "master", "page": 1, "per_page": 100}:
                return [{"sha": f"c{i}"} for i in range(100)]
            if params == {"sha": "master", "page": 2, "per_page": 100}:
                return [{"sha": f"c{i}"} for i in range(37)]
        if path == "/repos/viseshb/Interview-Helper/pulls":
            if params == {"state": "all", "page": 1, "per_page": 100}:
                return [{"number": i} for i in range(8)]
        if path == "/repos/viseshb/Interview-Helper/actions/workflows":
            return {
                "workflows": [
                    {"name": "Deploy Backend + Frontend", "path": ".github/workflows/deploy.yml", "state": "active"},
                    {"name": "Dependabot Updates", "path": "dynamic/dependabot/dependabot-updates", "state": "active"},
                ]
            }
        raise AssertionError(f"Unexpected path/params: {path} {params}")

    monkeypatch.setattr(github_server, "resolve_accessible_repo", fake_resolve)
    monkeypatch.setattr(github_server, "_github_get", fake_github_get)

    payload = asyncio.run(github_server.github_get_repo_metrics("Interview-Helper"))
    metrics = json.loads(payload)

    assert metrics["repo"] == "viseshb/Interview-Helper"
    assert metrics["default_branch"] == "master"
    assert metrics["commit_count"] == 137
    assert metrics["pull_request_count"] == 8
    assert metrics["workflow_count"] == 2
    assert metrics["deployment_workflow_count"] == 1
    assert metrics["deployment_workflows"] == [
        {
            "name": "Deploy Backend + Frontend",
            "path": ".github/workflows/deploy.yml",
            "state": "active",
        }
    ]


def test_github_count_commits_supports_author_filters(monkeypatch):
    monkeypatch.setattr("app.mcp_layer.servers.github_server.settings.github_token", "test-token")

    async def fake_resolve(repo: str):
        assert repo == "Interview-Helper"
        return "viseshb/Interview-Helper", None

    async def fake_github_get(path: str, params: dict | None = None):
        assert path == "/repos/viseshb/Interview-Helper/commits"
        if params == {"author": "viseshb", "page": 1, "per_page": 100}:
            return [{"sha": f"c{i}"} for i in range(100)]
        if params == {"author": "viseshb", "page": 2, "per_page": 100}:
            return [{"sha": f"c{i}"} for i in range(17)]
        raise AssertionError(f"Unexpected path/params: {path} {params}")

    monkeypatch.setattr(github_server, "resolve_accessible_repo", fake_resolve)
    monkeypatch.setattr(github_server, "_github_get", fake_github_get)

    payload = asyncio.run(github_server.github_count_commits("Interview-Helper", author="viseshb"))
    metrics = json.loads(payload)

    assert metrics == {
        "repo": "viseshb/Interview-Helper",
        "author": "viseshb",
        "branch": "",
        "path": "",
        "since": "",
        "until": "",
        "commit_count": 117,
    }


def test_github_read_file_uses_default_branch_when_ref_omitted(monkeypatch):
    monkeypatch.setattr("app.mcp_layer.servers.github_server.settings.github_token", "test-token")

    async def fake_resolve(repo: str):
        assert repo == "Interview-Helper"
        return "viseshb/Interview-Helper", None

    async def fake_github_get(path: str, params: dict | None = None):
        assert path == "/repos/viseshb/Interview-Helper"
        return {"default_branch": "master"}

    class FakeResponse:
        status_code = 200
        text = "# Interview Mate"

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, headers: dict | None = None, params: dict | None = None):
            assert url.endswith("/repos/viseshb/Interview-Helper/contents/README.md")
            assert params == {"ref": "master"}
            return FakeResponse()

    monkeypatch.setattr(github_server, "resolve_accessible_repo", fake_resolve)
    monkeypatch.setattr(github_server, "_github_get", fake_github_get)
    monkeypatch.setattr("app.mcp_layer.servers.github_server.httpx.AsyncClient", FakeClient)

    payload = asyncio.run(github_server.github_read_file("Interview-Helper", "README.md"))

    assert payload == "# Interview Mate"


def test_slack_headers_use_settings_token(monkeypatch):
    monkeypatch.setattr("app.mcp_layer.servers.slack_server.settings.slack_bot_token", "xoxb-test")
    headers = slack_server._headers()
    assert headers["Authorization"] == "Bearer xoxb-test"


def test_postgres_pool_uses_settings_database_url(monkeypatch):
    pytest.importorskip("asyncpg")
    postgres_server = importlib.import_module("app.mcp_layer.servers.postgres_server")

    postgres_server._pool = None
    postgres_server._pool_dsn = None

    captured: dict[str, str] = {}

    async def fake_create_pool(dsn: str, min_size: int, max_size: int):
        captured["dsn"] = dsn
        return object()

    monkeypatch.setattr("app.mcp_layer.servers.postgres_server.settings.database_url", "postgresql://db")
    monkeypatch.setattr("app.mcp_layer.servers.postgres_server.asyncpg.create_pool", fake_create_pool)

    pool = asyncio.run(postgres_server._get_pool())

    assert pool is not None
    assert captured["dsn"] == "postgresql://db"
