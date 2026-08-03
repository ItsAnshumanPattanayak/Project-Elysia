from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.constants import DATABASE_TYPE
from app.schemas.health import SystemInfoResponse
from app.services.ai_service import AIService, get_ai_service

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/info", response_model=SystemInfoResponse)
async def system_info(
    settings: Annotated[Settings, Depends(get_settings)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> SystemInfoResponse:
    ai_status = await ai_service.status()
    return SystemInfoResponse(
        application=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        database_type=DATABASE_TYPE,
        local_first=True,
        ai_integration=ai_status.state,
        documentation={
            "swagger": "/docs",
            "openapi": "/openapi.json",
            "redoc": "/redoc",
        },
    )
