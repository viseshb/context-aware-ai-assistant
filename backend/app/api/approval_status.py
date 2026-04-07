"""SSE endpoint for pending users to listen for approval status changes."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from app.security.jwt_auth import decode_access_token
from app.utils.logging import get_logger

router = APIRouter(tags=["approval"])
log = get_logger("api.approval_status")

MAX_POLL_SECONDS = 600  # 10 minutes
POLL_INTERVAL = 3


@router.get("/api/auth/approval-status")
async def approval_status_stream(
    authorization: str = Header(...),
) -> StreamingResponse:
    """SSE stream — pushes status updates for pending users."""
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)

    if not payload or payload.get("purpose") != "pending_check":
        return StreamingResponse(
            iter([f"data: {json.dumps({'error': 'Invalid pending token'})}\n\n"]),
            media_type="text/event-stream",
        )

    user_id = payload["sub"]
    log.info("approval_sse_connected", user_id=user_id)

    async def event_stream():
        from app.dependencies import get_user_service
        user_svc = await get_user_service()

        elapsed = 0
        while elapsed < MAX_POLL_SECONDS:
            user = await user_svc.get_by_id(user_id)
            if not user:
                yield f"data: {json.dumps({'status': 'error', 'message': 'User not found'})}\n\n"
                return

            status = user.get("status", "pending")
            if status != "pending":
                log.info("approval_status_changed", user_id=user_id, status=status)
                yield f"data: {json.dumps({'status': status, 'role': user.get('role', '')})}\n\n"
                return

            yield f"data: {json.dumps({'status': 'pending'})}\n\n"
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

        yield f"data: {json.dumps({'status': 'timeout'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
