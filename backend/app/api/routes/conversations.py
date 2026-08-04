import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.exceptions import AIError, GenerationCancelledError
from app.api.errors import error_payload
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.relationship.schemas import (
    EventSource,
    ManualRelationshipUpdate,
    RelationshipApplicationResult,
    RelationshipEventListResponse,
    RelationshipEventType,
    RelationshipRecalculationResponse,
    RelationshipStateResponse,
)
from app.schemas.conversation_api import (
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationUpdateRequest,
)
from app.schemas.message_api import (
    EditMessageRequest,
    MessageListResponse,
    MessageResponse,
    RegenerateRequest,
    RegenerateResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.ai_service import AIService, get_ai_service
from app.services.conversation_errors import ConversationError, InvalidPaginationError
from app.services.conversation_lock_service import (
    ConversationLockService,
    conversation_lock_service,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def get_lock_service() -> ConversationLockService:
    return conversation_lock_service


def get_conversation_service(
    session: Annotated[Session, Depends(get_db)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    locks: Annotated[ConversationLockService, Depends(get_lock_service)],
) -> ConversationService:
    return ConversationService(session, settings, ai_service, locks)


Service = Annotated[ConversationService, Depends(get_conversation_service)]


def _bounded_limit(value: int | None, default: int, maximum: int) -> int:
    result = default if value is None else value
    if result < 1 or result > maximum:
        raise InvalidPaginationError(
            f"Pagination limit must be between 1 and {maximum}."
        )
    return result


@router.post("", response_model=ConversationDetailResponse, status_code=201)
def create_conversation(
    payload: ConversationCreateRequest, service: Service
) -> ConversationDetailResponse:
    return service.create(payload)


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    service: Service,
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    archived: bool | None = Query(default=None),
    active: bool | None = Query(default=None),
    character_slug: str | None = Query(default=None, max_length=80),
) -> ConversationListResponse:
    return service.list(
        limit=_bounded_limit(
            limit,
            settings.conversation_list_default_limit,
            settings.conversation_list_max_limit,
        ),
        offset=offset,
        archived=archived,
        active=active,
        character_slug=character_slug,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: int, service: Service
) -> ConversationDetailResponse:
    return service.detail(conversation_id)


@router.get("/{conversation_id}/relationship", response_model=RelationshipStateResponse)
def get_relationship(
    conversation_id: int, service: Service
) -> RelationshipStateResponse:
    return service.relationship_state(conversation_id)


@router.get(
    "/{conversation_id}/relationship/events",
    response_model=RelationshipEventListResponse,
)
def get_relationship_events(
    conversation_id: int,
    service: Service,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    event_type: RelationshipEventType | None = None,
    source: EventSource | None = None,
    reverted: bool | None = None,
    oldest_first: bool = False,
) -> RelationshipEventListResponse:
    return service.relationship_history(
        conversation_id,
        limit=limit,
        offset=offset,
        event_type=event_type.value if event_type else None,
        source=source.value if source else None,
        reverted=reverted,
        oldest_first=oldest_first,
    )


@router.patch(
    "/{conversation_id}/relationship", response_model=RelationshipApplicationResult
)
async def update_relationship(
    conversation_id: int,
    payload: ManualRelationshipUpdate,
    service: Service,
) -> RelationshipApplicationResult:
    return await service.manual_relationship_update(conversation_id, payload)


@router.post(
    "/{conversation_id}/relationship/recalculate",
    response_model=RelationshipRecalculationResponse,
)
async def recalculate_relationship(
    conversation_id: int, service: Service
) -> RelationshipRecalculationResponse:
    return await service.recalculate_relationship(conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationDetailResponse)
def update_conversation(
    conversation_id: int,
    payload: ConversationUpdateRequest,
    service: Service,
) -> ConversationDetailResponse:
    return service.update(conversation_id, payload)


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, service: Service) -> Response:
    service.delete(conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
def list_messages(
    conversation_id: int,
    service: Service,
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
) -> MessageListResponse:
    return service.list_messages(
        conversation_id,
        limit=_bounded_limit(
            limit,
            settings.message_list_default_limit,
            settings.message_list_max_limit,
        ),
        offset=offset,
    )


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message(
    conversation_id: int, payload: SendMessageRequest, service: Service
) -> SendMessageResponse:
    return await service.send(conversation_id, payload)


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: int,
    payload: SendMessageRequest,
    request: Request,
    service: Service,
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        try:
            async for item in service.stream_send(conversation_id, payload):
                if await request.is_disconnected():
                    raise GenerationCancelledError("Generation was cancelled.")
                yield _sse(item.event, item.data)
        except GenerationCancelledError as exc:
            yield _sse("cancelled", {"code": exc.code, "message": exc.message})
        except (AIError, ConversationError) as exc:
            yield _sse(
                "error",
                error_payload(exc.code, exc.message, exc.retryable, exc.details)[
                    "error"
                ],
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/{conversation_id}/messages/regenerate", response_model=RegenerateResponse
)
async def regenerate_message(
    conversation_id: int, payload: RegenerateRequest, service: Service
) -> RegenerateResponse:
    return await service.regenerate(conversation_id, payload)


@router.patch(
    "/{conversation_id}/messages/{message_id}", response_model=MessageResponse
)
def edit_message(
    conversation_id: int,
    message_id: int,
    payload: EditMessageRequest,
    service: Service,
) -> MessageResponse:
    return service.edit_message(conversation_id, message_id, payload)


@router.delete("/{conversation_id}/messages/{message_id}", status_code=204)
def delete_message(
    conversation_id: int,
    message_id: int,
    service: Service,
    confirm_truncate_following_messages: bool = Query(default=False),
) -> Response:
    service.delete_message(
        conversation_id,
        message_id,
        confirm_truncate=confirm_truncate_following_messages,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
