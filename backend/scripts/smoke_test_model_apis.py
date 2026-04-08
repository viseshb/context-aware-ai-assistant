from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test auth/models/chat API endpoints for all models.")
    parser.add_argument("--base-url", default=os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--username", default=os.getenv("SMOKE_USERNAME", ""))
    parser.add_argument("--password", default=os.getenv("SMOKE_PASSWORD", ""))
    parser.add_argument(
        "--prompt",
        default=(
            "This is a health check for this assistant. Reply with exactly E2E_OK. "
            "Do not use tools."
        ),
    )
    parser.add_argument(
        "--tool-prompt",
        default="",
        help="Optional second prompt to run per model for tool-calling verification.",
    )
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument(
        "--skip-model",
        action="append",
        default=[],
        help="Model id to skip. Can be provided multiple times.",
    )
    return parser.parse_args()


async def login(client: httpx.AsyncClient, username: str, password: str) -> str:
    resp = await client.post("/api/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    payload = resp.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Login succeeded but no access token was returned.")
    return token


async def main() -> int:
    args = parse_args()
    if not args.username or not args.password:
        print("SMOKE_USERNAME and SMOKE_PASSWORD are required.", file=sys.stderr)
        return 2

    async with httpx.AsyncClient(base_url=args.base_url, timeout=args.timeout) as client:
        token = await login(client, args.username, args.password)
        headers = {"Authorization": f"Bearer {token}"}

        models_resp = await client.get("/api/models", headers=headers)
        models_resp.raise_for_status()
        models = models_resp.json().get("models", [])

        results: list[dict] = []
        skipped = set(args.skip_model)
        for model in models:
            if model["id"] in skipped:
                results.append({"model_id": model["id"], "skipped": True})
                continue
            entry = {"model_id": model["id"], "ok": False, "tool_ok": None, "error": "", "tool_error": ""}
            try:
                chat_resp = await client.post(
                    "/api/chat",
                    headers=headers,
                    json={
                        "model_id": model["id"],
                        "message": args.prompt,
                        "conversation_id": f"smoke-{model['id']}-plain",
                    },
                )
                chat_resp.raise_for_status()
                content = chat_resp.json().get("content", "")
                entry["ok"] = "E2E_OK" in content
                if not entry["ok"]:
                    entry["error"] = content[:300]
            except Exception as e:
                entry["error"] = str(e)

            if args.tool_prompt:
                try:
                    tool_resp = await client.post(
                        "/api/chat",
                        headers=headers,
                        json={
                            "model_id": model["id"],
                            "message": args.tool_prompt,
                            "conversation_id": f"smoke-{model['id']}-tool",
                        },
                    )
                    tool_resp.raise_for_status()
                    tool_payload = tool_resp.json()
                    tool_calls = tool_payload.get("tool_calls", [])
                    entry["tool_ok"] = bool(tool_calls) and not any(tc.get("status") == "error" for tc in tool_calls)
                    if not entry["tool_ok"]:
                        entry["tool_error"] = tool_payload.get("content", "")[:300]
                except Exception as e:
                    entry["tool_ok"] = False
                    entry["tool_error"] = str(e)

            results.append(entry)

        print(json.dumps({"base_url": args.base_url, "results": results}, indent=2))
        return 0 if all(
            r.get("skipped") or (r["ok"] and (r["tool_ok"] in (None, True)))
            for r in results
        ) else 1


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "backend"))
    import asyncio

    raise SystemExit(asyncio.run(main()))
