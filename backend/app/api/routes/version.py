"""Application version endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.config import Settings, get_settings

router = APIRouter(tags=["Version"])


class VersionResponse(BaseModel):
    """Application version schema."""

    version: str = Field(
        description="Application semantic version",
        examples=["0.1.0"],
    )
    project_name: str = Field(
        description="Public project name",
        examples=["Converge AI — Conference Agent Network"],
    )
    api_prefix: str = Field(
        description="Active API router gateway prefix",
        examples=["/converge-api/v1"],
    )


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="Application Version",
    description="Returns verified semantic application version and API metadata.",
)
async def get_version(settings: Settings = Depends(get_settings)) -> VersionResponse:
    """Return packaged application version metadata."""
    return VersionResponse(
        version=settings.VERSION,
        project_name=settings.PROJECT_NAME,
        api_prefix=settings.API_V1_PREFIX,
    )
