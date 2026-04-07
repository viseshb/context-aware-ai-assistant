from __future__ import annotations

import time

from fastapi import APIRouter

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/api/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "uptime_seconds": int(time.time() - _start_time),
    }
