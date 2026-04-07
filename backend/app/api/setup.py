"""Instance info endpoint — returns mode and setup status."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.utils.logging import get_logger

router = APIRouter(tags=["setup"])
log = get_logger("api.setup")


@router.get("/api/setup/info")
async def get_instance_info() -> dict:
    """Public endpoint — frontend uses this to show correct signup form."""
    return {
        "mode": settings.instance_mode,
        "has_team_code": bool(settings.team_code),
    }
