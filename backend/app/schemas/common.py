"""
Shared response schemas used across multiple routes.

Keeping these in one place means every endpoint returns errors and health
data in the exact same shape, which is what makes the API predictable for
frontend developers and for the auto-generated Swagger docs.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error envelope returned by every failed request."""

    error_code: str = Field(..., examples=["not_found"])
    message: str = Field(..., examples=["Requested resource was not found."])
    details: Optional[Dict[str, Any]] = Field(default=None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "error_code": "not_found",
                "message": "Requested resource was not found.",
                "details": None,
            }
        }
    }


class ServiceStatus(BaseModel):
    """Health status of a single dependency (e.g. postgres, redis)."""

    name: str
    healthy: bool
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Overall API health, including each dependency's status."""

    status: str = Field(..., examples=["ok", "degraded"])
    version: str
    environment: str
    services: list[ServiceStatus]
