"""GET /api/models — list available LLM providers."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.utils.logging import get_logger

router = APIRouter(tags=["models"])
log = get_logger("api.models")


@router.get("/api/models")
async def list_models(user: dict = Depends(get_current_user)) -> dict:
    from app.dependencies import get_llm_registry

    try:
        registry = get_llm_registry()
        models = registry.list_available()
    except Exception as e:
        log.error("list_models_failed", error=str(e), user_id=user["id"])
        raise

    log.info("models_listed", count=len(models), user_id=user["id"])
    return {
        "models": [
            {
                "id": m.id, "name": m.name, "provider": m.provider,
                "tier": m.tier, "available": m.available,
                "supports_tools": m.supports_tools, "supports_streaming": m.supports_streaming,
            }
            for m in models
        ]
    }
