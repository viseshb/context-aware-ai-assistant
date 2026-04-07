from __future__ import annotations

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.contact import router as contact_router
from app.api.models import router as models_router
from app.api.chat import router as chat_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(contact_router)
api_router.include_router(models_router)
api_router.include_router(chat_router)
