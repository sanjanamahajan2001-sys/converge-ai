"""Liveness and readiness health status endpoints."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from app.core.config import Settings, get_settings
from app.db.session import db_manager

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Liveness response schema."""

    status: str = Field(
        default="healthy",
        description="Liveness status of the running FastAPI process",
        examples=["healthy"],
    )
    service: str = Field(
        default="converge-ai",
        description="Application identifier",
        examples=["converge-ai"],
    )
    environment: str = Field(
        description="Runtime environment name",
        examples=["development"],
    )


class ReadinessResponse(BaseModel):
    """Readiness response schema reflecting real infrastructure dependencies."""

    status: str = Field(
        description="Readiness status (ready or not_ready)",
        examples=["ready"],
    )
    database: str = Field(
        description="Database connectivity status (connected, disconnected, or unconfigured)",
        examples=["connected"],
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Process Liveness Probe",
    description=(
        "Returns the process liveness state. Indicates application server is running."
    ),
)
async def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return application liveness status."""
    return HealthResponse(
        status="healthy",
        service="converge-ai",
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Infrastructure Readiness Probe",
    description="Truthful readiness check verifying actual database connectivity.",
    responses={
        200: {"description": "Service is ready to handle traffic"},
        503: {"description": "Service dependencies are not ready"},
    },
)
async def get_readiness(settings: Settings = Depends(get_settings)) -> JSONResponse:
    """Check database connectivity and return readiness status."""
    if not settings.DATABASE_URL:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "database": "unconfigured",
            },
        )

    is_connected = await db_manager.check_connectivity(timeout_seconds=2.0)
    if is_connected:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "database": "connected",
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "database": "disconnected",
            },
        )
