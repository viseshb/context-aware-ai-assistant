"""Chat endpoints — WebSocket for streaming, REST for fallback."""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.dependencies import get_current_user, get_llm_registry
from app.schemas.chat import ChatRequest
from app.security.jwt_auth import decode_access_token
from app.services.chat_service import ChatService
from app.utils.logging import get_logger

router = APIRouter(tags=["chat"])
log = get_logger("api.chat")


@router.post("/api/chat")
async def rest_chat(
    body: ChatRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Non-streaming chat endpoint (fallback)."""
    registry = get_llm_registry()
    service = ChatService(registry)
    return await service.handle_rest_chat(
        model_id=body.model_id,
        message=body.message,
        user=user,
    )


@router.websocket("/api/ws/chat")
async def websocket_chat(ws: WebSocket) -> None:
    """WebSocket chat endpoint with JWT auth on connect."""
    await ws.accept()

    # Auth: first message must include token
    session_id = str(uuid.uuid4())
    user = None

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
                from app.dependencies import get_user_service
                user_svc = await get_user_service()
                user = await user_svc.get_by_id(payload["sub"])
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
                model_id = data.get("model_id", "")
                message = data.get("message", "")
                conversation_id = data.get("conversation_id", str(uuid.uuid4()))

                if not model_id or not message:
                    await ws.send_json({
                        "type": "error",
                        "message": "model_id and message are required",
                        "code": "VALIDATION_ERROR",
                    })
                    continue

                from app.dependencies import get_mcp_manager
                registry = get_llm_registry()
                mcp_mgr = await get_mcp_manager()
                service = ChatService(registry, mcp_mgr)
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
