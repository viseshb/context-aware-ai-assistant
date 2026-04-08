"""Chat endpoints — WebSocket for streaming, REST for fallback."""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.config import settings
from app.dependencies import get_current_user, get_llm_registry, get_user_service
from app.schemas.chat import ChatRequest
from app.security.jwt_auth import decode_access_token
from app.services.chat_service import ChatService
from app.services.user_service import UserService
from app.utils.logging import get_logger

router = APIRouter(tags=["chat"])
log = get_logger("api.chat")


@router.post("/api/chat")
async def rest_chat(
    body: ChatRequest,
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    """Non-streaming chat endpoint (fallback)."""
    from app.dependencies import get_mcp_manager

    registry = get_llm_registry()
    mcp_mgr = await get_mcp_manager()
    service = ChatService(registry, mcp_mgr, user_service)
    return await service.handle_rest_chat(
        model_id=body.model_id,
        message=body.message,
        user=user,
        conversation_id=body.conversation_id,
    )


@router.get("/api/chat/metrics")
async def get_chat_metrics(
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    """Return persisted chat metrics for the signed-in user."""
    rows = await user_service.list_chat_metrics(user["id"], limit=limit)
    summary = await user_service.get_chat_metrics_summary(user["id"])
    return {"rows": rows, "summary": summary}


@router.websocket("/api/ws/chat")
async def websocket_chat(ws: WebSocket) -> None:
    """WebSocket chat endpoint with JWT auth on connect."""
    await ws.accept()

    # Auth: first message must include token
    session_id = str(uuid.uuid4())
    user = None
    user_service: UserService | None = None

    try:
        # Send connected event
        await ws.send_json({"type": "connected", "session_id": session_id})

        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")

            # Handle auth message
            if msg_type == "auth":
                token = data.get("token", "")
                payload = decode_access_token(token)
                if not payload:
                    await ws.send_json({
                        "type": "error",
                        "message": "Invalid or expired token",
                        "code": "AUTH_REQUIRED",
                    })
                    continue

                # Load user
                user_service = await get_user_service()
                user = await user_service.get_by_id(payload["sub"])
                if not user or not user["is_active"]:
                    await ws.send_json({
                        "type": "error",
                        "message": "User not found",
                        "code": "AUTH_REQUIRED",
                    })
                    continue

                await ws.send_json({
                    "type": "authenticated",
                    "user": {
                        "id": user["id"],
                        "username": user["username"],
                        "role": user["role"],
                    },
                })
                continue

            # Require auth for chat messages
            if not user:
                await ws.send_json({
                    "type": "error",
                    "message": "Send auth message first: {\"type\": \"auth\", \"token\": \"...\"}",
                    "code": "AUTH_REQUIRED",
                })
                continue

            # Handle chat message
            if msg_type == "chat_message":
                model_id = str(data.get("model_id", "")).strip()
                message = str(data.get("message", "")).strip()
                conversation_id = str(data.get("conversation_id", str(uuid.uuid4()))).strip()

                if not model_id or not message:
                    await ws.send_json({
                        "type": "error",
                        "message": "model_id and message are required",
                        "code": "VALIDATION_ERROR",
                    })
                    continue

                if len(message) > settings.max_message_length:
                    await ws.send_json({
                        "type": "error",
                        "message": f"message exceeds the {settings.max_message_length} character limit",
                        "code": "VALIDATION_ERROR",
                    })
                    continue

                from app.dependencies import get_mcp_manager
                registry = get_llm_registry()
                mcp_mgr = await get_mcp_manager()
                service = ChatService(registry, mcp_mgr, user_service)
                await service.handle_ws_chat(
                    ws=ws,
                    model_id=model_id,
                    message=message,
                    conversation_id=conversation_id,
                    user=user,
                )

            elif msg_type == "cancel":
                # TODO: implement cancellation in Phase 5
                pass

    except WebSocketDisconnect:
        log.info("ws_disconnected", session_id=session_id)
    except Exception as e:
        log.error("ws_error", session_id=session_id, error=str(e))
        try:
            await ws.send_json({
                "type": "error",
                "message": str(e),
                "code": "INTERNAL_ERROR",
            })
        except Exception:
            pass
