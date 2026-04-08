"""Initialize and register all LLM providers."""
from __future__ import annotations

from app.config import settings
from app.llm.registry import LLMRegistry
from app.utils.logging import get_logger

log = get_logger("llm")


def create_registry() -> LLMRegistry:
    """Create registry and register all configured providers."""
    registry = LLMRegistry()

    # Gemini models (Google)
    if settings.google_api_key:
        from app.llm.providers.gemini import GeminiProvider, gemini_sdk_available
        if gemini_sdk_available():
            for model_id in [
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-3.1-flash-lite",
                "gemini-3-flash",
            ]:
                registry.register(GeminiProvider(model_id))
        else:
            log.warning("google_sdk_missing", msg="Gemini SDK not installed; Gemini models not available")
    else:
        log.warning("google_api_key_missing", msg="Gemini models not available")

    # NVIDIA NIM models
    if settings.nvidia_api_key:
        from app.llm.providers.nvidia import NvidiaProvider, NVIDIA_MODELS
        for model_id in NVIDIA_MODELS:
            registry.register(NvidiaProvider(model_id))
    else:
        log.warning("nvidia_api_key_missing", msg="NVIDIA models not available")

    # Claude CLI (always registered — health check verifies availability)
    from app.llm.providers.claude_cli import ClaudeCLIProvider
    registry.register(ClaudeCLIProvider())

    # Claude API
    if settings.anthropic_api_key:
        from app.llm.providers.claude_api import ClaudeAPIProvider, anthropic_sdk_available
        if anthropic_sdk_available():
            registry.register(ClaudeAPIProvider())
        else:
            log.warning("anthropic_sdk_missing", msg="Anthropic SDK not installed; Claude API not available")
    else:
        log.warning("anthropic_api_key_missing", msg="Claude API not available")

    # OpenAI
    if settings.openai_api_key:
        from app.llm.providers.openai_provider import OpenAIProvider
        registry.register(OpenAIProvider())
    else:
        log.warning("openai_api_key_missing", msg="OpenAI not available")

    log.info("registry_ready", models=len(registry.list_available()))
    return registry
