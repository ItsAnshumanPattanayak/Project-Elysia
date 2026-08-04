from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.settings_api import (
    SettingsMutationResponse,
    SettingsResetRequest,
    SettingsResponse,
    SettingsSchemaResponse,
    SettingsUpdateRequest,
)
from app.services.ai_service import AIService, get_ai_service
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SettingsService:
    return SettingsService(session, settings)


Service = Annotated[SettingsService, Depends(get_service)]


@router.get("", response_model=SettingsResponse)
def get_safe_settings(service: Service) -> SettingsResponse:
    return service.get()


@router.get("/schema", response_model=SettingsSchemaResponse)
def get_safe_settings_schema(service: Service) -> SettingsSchemaResponse:
    return service.schema()


@router.patch("", response_model=SettingsMutationResponse)
async def update_safe_settings(
    payload: SettingsUpdateRequest,
    service: Service,
    ai: Annotated[AIService, Depends(get_ai_service)],
) -> SettingsMutationResponse:
    keys = set(payload.values)
    installed = None
    if "selected_model" in keys:
        installed = {item.name for item in await ai.models(force_refresh=True)}
    return service.update(payload, installed)


@router.post("/reset", response_model=SettingsMutationResponse)
def reset_safe_settings(
    payload: SettingsResetRequest, service: Service
) -> SettingsMutationResponse:
    return service.reset(payload)
