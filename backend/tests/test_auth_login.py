from __future__ import annotations

import asyncio

from app.services.user_service import UserService


def test_authenticate_uses_username_case_insensitively(tmp_path):
    db_path = tmp_path / "users.db"
    service = UserService(str(db_path))
    asyncio.run(service.initialize())

    try:
        created = asyncio.run(service.create_user(
            username="ViseshAdmin",
            email="visesh66@gmail.com",
            password="StrongPass1",
            role="admin",
        ))

        authenticated = asyncio.run(service.authenticate("viseshadmin", "StrongPass1"))

        assert authenticated is not None
        assert authenticated["id"] == created["id"]
        assert authenticated["username"] == "ViseshAdmin"
    finally:
        asyncio.run(service.close())


def test_chat_metrics_are_persisted_in_sqlite(tmp_path):
    db_path = tmp_path / "users.db"
    service = UserService(str(db_path))
    asyncio.run(service.initialize())

    try:
        created = asyncio.run(service.create_user(
            username="metrics-admin",
            email="admin@example.com",
            password="StrongPass1",
            role="admin",
        ))

        asyncio.run(service.record_chat_metric(
            user_id=created["id"],
            conversation_id="conv-metrics-1",
            metrics={
                "model_id": "gemini-3.1-flash-lite",
                "provider_model": "gemini-3.1-flash-lite",
                "ttft_ms": 420,
                "total_time_ms": 2100,
                "tool_time_ms": 380,
                "tool_call_count": 2,
                "input_tokens": 123,
                "output_tokens": 456,
                "cost_usd": 0.0123,
                "response_chars": 789,
            },
            tool_calls=[
                {"name": "github_get_repo_info", "status": "success", "duration_ms": 120},
                {"name": "github_read_file", "status": "success", "duration_ms": 260},
            ],
            context_sources=[{"type": "github", "detail": "viseshb/Interview-Helper"}],
        ))

        rows = asyncio.run(service.list_chat_metrics(created["id"]))
        summary = asyncio.run(service.get_chat_metrics_summary(created["id"]))

        assert len(rows) == 1
        assert rows[0]["conversation_id"] == "conv-metrics-1"
        assert rows[0]["tool_calls"][0]["name"] == "github_get_repo_info"
        assert rows[0]["input_tokens"] == 123
        assert summary["total_turns"] == 1
        assert summary["avg_ttft_ms"] == 420
        assert summary["total_input_tokens"] == 123
        assert summary["total_output_tokens"] == 456
        assert summary["total_cost_usd"] == 0.0123
    finally:
        asyncio.run(service.close())
