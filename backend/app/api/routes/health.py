from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.health import HealthResponse, RootResponse
from app.services.system_service import database_is_connected

router = APIRouter()


@router.get("/", response_model=RootResponse)
def root(settings: Annotated[Settings, Depends(get_settings)]) -> RootResponse:
    return RootResponse(
        name=f"{settings.app_name} API", version=settings.app_version, status="running"
    )


@router.get("/health", response_model=HealthResponse)
def health(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    if not database_is_connected(session):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        )
    return HealthResponse(
        status="healthy",
        application=settings.app_name,
        version=settings.app_version,
        database="connected",
        environment=settings.environment,
    )
