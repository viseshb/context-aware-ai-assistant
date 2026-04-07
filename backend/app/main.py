from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.utils.errors import AppError, app_error_handler, unhandled_exception_handler
from app.utils.logging import setup_logging, get_logger


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    log = get_logger("startup")
    log.info("Starting Context-Aware AI Assistant", log_level=settings.log_level)

    # Initialize user database
    from app.dependencies import get_user_service, get_llm_registry
    user_svc = await get_user_service()
    log.info("User database initialized", db_path=settings.users_db_path)

    # Initialize LLM registry
    registry = get_llm_registry()
    log.info("LLM registry initialized", models=len(registry.list_available()))

    # Initialize MCP manager
    from app.dependencies import get_mcp_manager
    mcp = await get_mcp_manager()
    log.info("MCP manager initialized", tools=len(mcp.get_all_tools()))

    yield

    await user_svc.close()
    log.info("Shutting down")


app = FastAPI(
    title="Context-Aware AI Assistant",
    description="AI assistant with MCP integration for GitHub, Slack, and PostgreSQL",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
from app.security.rate_limiter import setup_rate_limiting
setup_rate_limiting(app)

# Error handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Routes
app.include_router(api_router)
