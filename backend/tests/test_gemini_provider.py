from __future__ import annotations

import asyncio

from app import llm
from app.llm.base import ChatEventType, Message
from app.llm.providers import gemini


def test_gemini_health_check_requires_sdk_and_key(monkeypatch):
    monkeypatch.setattr("app.llm.providers.gemini.settings.google_api_key", "test-key")
    monkeypatch.setattr(gemini, "gemini_sdk_available", lambda: False)

    provider = gemini.GeminiProvider("gemini-2.5-flash-lite")

    assert provider is not None
    assert provider.supports_tools is True

    import asyncio

    assert asyncio.run(provider.health_check()) is False


def test_registry_skips_gemini_when_sdk_missing(monkeypatch):
    monkeypatch.setattr("app.llm.settings.google_api_key", "test-key")
    monkeypatch.setattr("app.llm.providers.gemini.gemini_sdk_available", lambda: False)
    monkeypatch.setattr("app.llm.settings.nvidia_api_key", "")
    monkeypatch.setattr("app.llm.settings.anthropic_api_key", "")
    monkeypatch.setattr("app.llm.settings.openai_api_key", "")

    registry = llm.create_registry()

    assert all(not model.id.startswith("gemini-") for model in registry.list_available())


def test_gemini_streaming_chat_accepts_sync_sdk_iterator(monkeypatch):
    class FakePart:
        text = "E2E_OK"

    class FakeContent:
        parts = [FakePart()]

    class FakeCandidate:
        content = FakeContent()

    class FakeChunk:
        candidates = [FakeCandidate()]

    class FakeModels:
        def generate_content_stream(self, **kwargs):
            return [FakeChunk()]

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    class FakeGenaiModule:
        Client = FakeClient

    async def collect_events():
        provider = gemini.GeminiProvider("gemini-3.1-flash-lite")
        events = []
        async for event in provider.chat(
            [Message(role="user", content="health check")],
            stream=True,
        ):
            events.append(event)
        return events

    monkeypatch.setattr("app.llm.providers.gemini.settings.google_api_key", "test-key")
    monkeypatch.setattr(gemini, "_load_genai_module", lambda: FakeGenaiModule())

    events = asyncio.run(collect_events())

    assert [event.type for event in events] == [ChatEventType.TEXT_CHUNK, ChatEventType.DONE]
    assert events[0].content == "E2E_OK"
