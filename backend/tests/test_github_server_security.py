from __future__ import annotations

import asyncio
import json

from app.mcp_layer.servers import github_server


def test_github_read_file_blocks_sensitive_paths():
    result = asyncio.run(github_server.github_read_file("acme/api", ".env"))
    payload = json.loads(result)

    assert "error" in payload
    assert "blocked" in payload["error"].lower()
    assert ".env" in payload["error"]


def test_github_commit_history_blocks_sensitive_paths():
    result = asyncio.run(github_server.github_get_commit_history("acme/api", ".aws/credentials"))
    payload = json.loads(result)

    assert "error" in payload
    assert "blocked" in payload["error"].lower()
    assert ".aws/credentials" in payload["error"]


def test_github_search_filters_sensitive_paths(monkeypatch):
    async def fake_github_get(path: str, params: dict | None = None) -> dict:
        assert path == "/search/code"
        return {
            "items": [
                {"path": ".env", "name": ".env", "html_url": "https://example.com/env"},
                {"path": "src/app.py", "name": "app.py", "html_url": "https://example.com/app"},
                {"path": ".aws/credentials", "name": "credentials", "html_url": "https://example.com/creds"},
            ]
        }

    monkeypatch.setattr(github_server, "_github_get", fake_github_get)

    result = asyncio.run(github_server.github_search_code("token", "acme/api"))
    payload = json.loads(result)

    assert payload == [
        {"path": "src/app.py", "name": "app.py", "url": "https://example.com/app"}
    ]
