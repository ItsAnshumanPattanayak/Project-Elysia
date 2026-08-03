from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import utc_now
from app.memory.exceptions import (
    InvalidMemoryContentError,
    MemoryConversationMismatchError,
    MemoryDuplicateError,
    MemoryLockedError,
    MemoryNotFoundError,
    MemoryRebuildConfirmationError,
    SecretLikeMemoryRejectedError,
)
from app.memory.extraction import is_secret_like, is_sensitive
from app.memory.normalization import (
    application_hash,
    display_content,
    normalize_content,
    normalize_tags,
)
from app.memory.retrieval import MemoryRetrievalService
from app.memory.service import MemoryLifecycleService
from app.memory.types import MemorySource
from app.models import Conversation, Memory
from app.repositories.conversations import ConversationRepository
from app.repositories.memories import MemoryRepository
from app.schemas.memory_api import (
    ManualMemoryCreate,
    MemoryDetailResponse,
    MemoryListResponse,
    MemoryRebuildResponse,
    MemoryResponse,
    MemorySearchPreviewRequest,
    MemorySearchPreviewResponse,
    MemoryUpdate,
)


class MemoryService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.conversations = ConversationRepository(session)
        self.memories = MemoryRepository(session)
        self.lifecycle = MemoryLifecycleService(session, settings)
        self.retrieval = MemoryRetrievalService(self.memories, settings)

    def _conversation(self, conversation_id: int) -> Conversation:
        item = self.conversations.get(conversation_id)
        if item is None:
            raise MemoryNotFoundError("The conversation was not found.")
        return item

    def _memory(self, conversation_id: int, memory_id: int) -> Memory:
        self._conversation(conversation_id)
        item = self.memories.get(memory_id)
        if item is None:
            raise MemoryNotFoundError("The memory was not found.")
        if item.conversation_id != conversation_id:
            raise MemoryConversationMismatchError(
                "The memory does not belong to this conversation."
            )
        return item

    def list(
        self,
        conversation_id: int,
        *,
        limit: int,
        offset: int,
        status: str | None,
        memory_type: str | None,
        source: str | None,
        pinned: bool | None,
        sensitive: bool | None,
        query: str | None,
    ) -> MemoryListResponse:
        self._conversation(conversation_id)
        items, total = self.memories.page(
            conversation_id,
            limit=limit,
            offset=offset,
            status=status,
            memory_type=memory_type,
            source=source,
            pinned=pinned,
            sensitive=sensitive,
            query=query,
        )
        return MemoryListResponse(
            items=[MemoryResponse.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )

    def detail(self, conversation_id: int, memory_id: int) -> MemoryDetailResponse:
        return MemoryDetailResponse.model_validate(
            self._memory(conversation_id, memory_id)
        )

    def create(
        self, conversation_id: int, payload: ManualMemoryCreate
    ) -> MemoryDetailResponse:
        self._conversation(conversation_id)
        content = display_content(payload.content)
        if is_secret_like(content):
            raise SecretLikeMemoryRejectedError(
                "Secret-like content cannot be stored as memory."
            )
        sensitive = payload.sensitive or is_sensitive(content)
        if sensitive and not payload.confirm_sensitive:
            raise InvalidMemoryContentError(
                "Sensitive memory creation requires explicit confirmation."
            )
        normalized = normalize_content(content)
        if self.memories.exact(conversation_id, normalized, payload.memory_type.value):
            raise MemoryDuplicateError("An active equivalent memory already exists.")
        now = utc_now()
        item = Memory(
            conversation_id=conversation_id,
            memory_type=payload.memory_type.value,
            content=content,
            normalized_content=normalized,
            importance=payload.importance,
            confidence=1.0,
            tags=normalize_tags(
                payload.tags,
                limit=self.settings.memory_max_tags,
                max_length=self.settings.memory_max_tag_length,
            ),
            entities=[],
            source=MemorySource.MANUAL.value,
            application_key=(
                f"manual:{conversation_id}:"
                f"{application_hash(normalized, now.isoformat())}"
            ),
            status="active",
            is_sensitive=sensitive,
            is_pinned=payload.pinned,
            is_locked=payload.locked,
            usage_count=0,
            last_confirmed_at=now,
            memory_metadata={"note": payload.note, "created_manually": True},
        )
        self.memories.add(item)
        self.session.commit()
        return MemoryDetailResponse.model_validate(item)

    def update(
        self, conversation_id: int, memory_id: int, payload: MemoryUpdate
    ) -> MemoryDetailResponse:
        item = self._memory(conversation_id, memory_id)
        changes = payload.model_dump(exclude_unset=True)
        destructive = any(
            key in changes for key in ("content", "memory_type", "archived")
        )
        if item.is_locked and destructive and not payload.force:
            raise MemoryLockedError(
                "This memory is locked; set force=true for this explicit change."
            )
        if payload.content is not None:
            content = display_content(payload.content)
            if is_secret_like(content):
                raise SecretLikeMemoryRejectedError(
                    "Secret-like content cannot be stored as memory."
                )
            item.content = content
            item.normalized_content = normalize_content(content)
        if payload.memory_type is not None:
            item.memory_type = payload.memory_type.value
        if payload.importance is not None:
            item.importance = payload.importance
        if payload.tags is not None:
            item.tags = normalize_tags(
                payload.tags,
                limit=self.settings.memory_max_tags,
                max_length=self.settings.memory_max_tag_length,
            )
        if payload.sensitive is not None:
            if payload.sensitive and not payload.confirm_sensitive:
                raise InvalidMemoryContentError(
                    "Sensitive memory changes require explicit confirmation."
                )
            item.is_sensitive = payload.sensitive
        if payload.pinned is not None:
            item.is_pinned = payload.pinned
        if payload.locked is not None:
            item.is_locked = payload.locked
        if payload.archived is not None:
            item.status = "archived" if payload.archived else "active"
        metadata = dict(item.memory_metadata)
        audit = list(metadata.get("manual_edits", []))
        audit.append(
            {
                "at": utc_now().isoformat(),
                "reason": payload.reason,
                "fields": sorted(changes),
            }
        )
        metadata["manual_edits"] = audit[-20:]
        item.memory_metadata = metadata
        self.session.commit()
        return MemoryDetailResponse.model_validate(item)

    def archive(self, conversation_id: int, memory_id: int) -> None:
        item = self._memory(conversation_id, memory_id)
        if item.is_locked:
            raise MemoryLockedError("Unlock the memory before archiving it.")
        item.status = "archived"
        self.session.commit()

    def preview(
        self, conversation_id: int, payload: MemorySearchPreviewRequest
    ) -> MemorySearchPreviewResponse:
        self._conversation(conversation_id)
        types = (
            {item.value for item in payload.memory_types}
            if payload.memory_types
            else None
        )
        selection = self.retrieval.retrieve(
            conversation_id, payload.query, limit=payload.limit, memory_types=types
        )
        return MemorySearchPreviewResponse(
            items=selection.items, total_characters=selection.total_characters
        )

    def rebuild(self, conversation_id: int, confirm: bool) -> MemoryRebuildResponse:
        if not confirm:
            raise MemoryRebuildConfirmationError(
                "Memory rebuild requires confirm=true."
            )
        before, after, warnings = self.lifecycle.rebuild(
            self._conversation(conversation_id)
        )
        return MemoryRebuildResponse(before=before, after=after, warnings=warnings)
