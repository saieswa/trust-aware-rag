"""
FastAPI application entrypoint.

This file's only job is to assemble the app: configuration, logging,
middleware, exception handlers, routers, and lifespan (startup/shutdown)
events. It intentionally contains no business logic — that lives in
app/services/, app/api/routes/, and (in later steps) the agents/ package.

Run locally with:
    uvicorn app.main:app --reload --port 8000

Docker runs the same command (see deployment/docker/Dockerfile.backend).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.middleware.logging_middleware import RequestLoggingMiddleware
from database.postgres.session import check_database_connection, engine
from database.redis.client import check_redis_connection

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---------- Startup ----------
    configure_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} ({settings.APP_ENV})")

    db_ok = await check_database_connection()
    redis_ok = await check_redis_connection()
    logger.info(f"Startup dependency check — postgresql={db_ok} redis={redis_ok}")
    if not db_ok:
        logger.warning("PostgreSQL is not reachable at startup. Check DATABASE_URL / container status.")
    if not redis_ok:
        logger.warning("Redis is not reachable at startup. Check REDIS_URL / container status.")

    yield

    # ---------- Shutdown ----------
    logger.info("Shutting down — disposing database engine connections.")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Backend API for the Trust-Aware Multi-Agent Retrieval and "
        "Verification Framework. This build implements the core API "
        "scaffold — configuration, routing, logging, error handling, and "
        "database/cache connectivity. RAG and agent endpoints are added "
        "in later steps."
    ),
    docs_url="/docs",          # Swagger UI
    redoc_url="/redoc",        # ReDoc alternative UI
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ---------- Middleware ----------
# Order matters: middleware added last runs first on the way in.
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Exception handlers ----------
register_exception_handlers(app)

# ---------- Routers ----------
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
