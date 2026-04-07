"""LLM provider registry — register, list, and look up providers."""
from __future__ import annotations

from dataclasses import dataclass

from app.llm.base import LLMProvider
from app.utils.errors import NotFoundError
from app.utils.logging import get_logger

log = get_logger("llm.registry")


@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str
    tier: str
    available: bool
    supports_tools: bool
    supports_streaming: bool


class LLMRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        self._providers[provider.model_id] = provider
        log.info("registered_model", model_id=provider.model_id, provider=provider.provider_name)

    def get(self, model_id: str) -> LLMProvider:
        provider = self._providers.get(model_id)
        if not provider:
            raise NotFoundError(f"Model '{model_id}' not found. Available: {list(self._providers.keys())}")
        return provider

    def list_available(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id=p.model_id,
                name=p.display_name,
                provider=p.provider_name,
                tier=p.tier,
                available=True,
                supports_tools=p.supports_tools,
                supports_streaming=p.supports_streaming,
            )
            for p in self._providers.values()
        ]

    async def health_check_all(self) -> dict[str, bool]:
        results = {}
        for model_id, provider in self._providers.items():
            try:
                results[model_id] = await provider.health_check()
            except Exception:
                results[model_id] = False
        return results
