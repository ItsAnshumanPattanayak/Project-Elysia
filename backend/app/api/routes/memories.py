from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.memory.types import MemorySource, MemoryStatus, MemoryType
from app.schemas.memory_api import (
    ManualMemoryCreate,
    MemoryDetailResponse,
    MemoryListResponse,
    MemoryRebuildRequest,
    MemoryRebuildResponse,
    MemorySearchPreviewRequest,
    MemorySearchPreviewResponse,
    MemoryUpdate,
)
from app.services.conversation_errors import InvalidPaginationError
from app.services.memory_service import MemoryService

router = APIRouter(
    prefix="/api/conversations/{conversation_id}/memories", tags=["memories"]
)


def get_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MemoryService:
    return MemoryService(session, settings)


Service = Annotated[MemoryService, Depends(get_service)]


@router.get("", response_model=MemoryListResponse)
def list_memories(
    conversation_id: int,
    service: Service,
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    memory_status: Annotated[MemoryStatus | None, Query(alias="status")] = None,
    memory_type: MemoryType | None = None,
    source: MemorySource | None = None,
    pinned: bool | None = None,
    locked: bool | None = None,
    sensitive: bool | None = None,
    query: str | None = Query(default=None, max_length=2000),
) -> MemoryListResponse:
    actual_limit = settings.memory_default_list_limit if limit is None else limit
    if actual_limit < 1 or actual_limit > settings.memory_max_list_limit:
        raise InvalidPaginationError(
            f"Pagination limit must be between 1 and "
            f"{settings.memory_max_list_limit}."
        )
    return service.list(
        conversation_id,
        limit=actual_limit,
        offset=offset,
        status=memory_status.value if memory_status else None,
        memory_type=memory_type.value if memory_type else None,
        source=source.value if source else None,
        pinned=pinned,
        locked=locked,
        sensitive=sensitive,
        query=query,
    )


@router.get("/{memory_id}", response_model=MemoryDetailResponse)
def get_memory(
    conversation_id: int, memory_id: int, service: Service
) -> MemoryDetailResponse:
    return service.detail(conversation_id, memory_id)


@router.post("", response_model=MemoryDetailResponse, status_code=201)
def create_memory(
    conversation_id: int, payload: ManualMemoryCreate, service: Service
) -> MemoryDetailResponse:
    return service.create(conversation_id, payload)


@router.patch("/{memory_id}", response_model=MemoryDetailResponse)
def update_memory(
    conversation_id: int, memory_id: int, payload: MemoryUpdate, service: Service
) -> MemoryDetailResponse:
    return service.update(conversation_id, memory_id, payload)


@router.delete("/{memory_id}", status_code=204)
def delete_memory(conversation_id: int, memory_id: int, service: Service) -> Response:
    service.archive(conversation_id, memory_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/search-preview", response_model=MemorySearchPreviewResponse)
def preview(
    conversation_id: int, payload: MemorySearchPreviewRequest, service: Service
) -> MemorySearchPreviewResponse:
    return service.preview(conversation_id, payload)


@router.post("/rebuild", response_model=MemoryRebuildResponse)
def rebuild(
    conversation_id: int, payload: MemoryRebuildRequest, service: Service
) -> MemoryRebuildResponse:
    return service.rebuild(conversation_id, payload.confirm)
