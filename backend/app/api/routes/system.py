from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.constants import AI_STATUS, DATABASE_TYPE
from app.schemas.health import SystemInfoResponse

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/info", response_model=SystemInfoResponse)
def system_info(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SystemInfoResponse:
    return SystemInfoResponse(
        application=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        database_type=DATABASE_TYPE,
        local_first=True,
        ai_integration=AI_STATUS,
        documentation={
            "swagger": "/docs",
            "openapi": "/openapi.json",
            "redoc": "/redoc",
        },
    )
