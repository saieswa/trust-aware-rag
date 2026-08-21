"""
Health check route.

`/api/v1/health` is the single most important endpoint at this stage of the
project: it proves the FastAPI app, PostgreSQL, and Redis are all wired up
correctly, before any RAG/agent logic is added. Docker healthchecks,
load balancers, and uptime monitors all point here in production.
"""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import HealthResponse, ServiceStatus
from database.postgres.session import check_database_connection
from database.redis.client import check_redis_connection

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API and dependency health",
    description=(
        "Returns overall API status along with the health of each critical "
        "dependency (PostgreSQL, Redis). Used by Docker, load balancers, "
        "and monitoring tools to confirm the service is ready to serve traffic."
    ),
)
async def health_check() -> HealthResponse:
    settings = get_settings()

    db_healthy = await check_database_connection()
    redis_healthy = await check_redis_connection()

    services = [
        ServiceStatus(
            name="postgresql",
            healthy=db_healthy,
            detail=None if db_healthy else "Could not connect to PostgreSQL.",
        ),
        ServiceStatus(
            name="redis",
            healthy=redis_healthy,
            detail=None if redis_healthy else "Could not connect to Redis.",
        ),
    ]

    overall_status = "ok" if all(s.healthy for s in services) else "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        services=services,
    )


@router.get(
    "/",
    summary="API root",
    description="Basic liveness probe — confirms the API process is running at all.",
)
async def root() -> dict:
    return {"message": "Trust-Aware Multi-Agent RAG API is running.", "docs": "/docs"}
