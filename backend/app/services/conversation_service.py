import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.parser import process_roleplay_response
from app.ai.schemas import GenerationRequest, GenerationResult, StreamEvent
from app.character_engine.exceptions import (
    CharacterNotFoundError,
    RoleplayProfileNotFoundError,
)
from app.core.config import Settings
from app.db.base import utc_now
from app.memory.schemas import MemoryProcessingResult
from app.memory.service import MemoryApplicationService, MemoryLifecycleService
from app.models import Conversation, Message, MessageSender, RelationshipState
from app.relationship.schemas import (
    ManualRelationshipUpdate,
    RelationshipApplicationResult,
    RelationshipEventListResponse,
    RelationshipStateResponse,
)
from app.repositories.conversations import ConversationRepository
from app.repositories.memories import MemoryRepository
from app.repositories.messages import MessageRepository
from app.schemas.conversation_api import (
    CharacterReference,
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummaryResponse,
    ConversationUpdateRequest,
    MessagePreview,
    RelationshipSnapshot,
    RoleplayProfileReference,
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
from app.services.ai_service import AIService
from app.services.conversation_context_service import ConversationContextBuilder
from app.services.conversation_errors import (
    ConversationArchivedError,
    ConversationInactiveError,
    ConversationNotFoundError,
    DuplicateClientMessageError,
    InvalidMessageSenderError,
    MessageConversationMismatchError,
    MessageDeleteRequiresTruncationError,
    MessageEditRequiresTruncationError,
    MessageNotFoundError,
    NoCharacterResponseToRegenerateError,
    RegenerateNotAllowedError,
    ResponsePersistenceError,
    StreamOutputLimitError,
)
from app.services.conversation_lock_service import ConversationLockService
from app.services.relationship_service import RelationshipService


class ConversationService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        ai_service: AIService,
        lock_service: ConversationLockService,
    ) -> None:
        self.session = session
        self.settings = settings
        self.ai = ai_service
        self.locks = lock_service
        self.conversations = ConversationRepository(session)
        self.messages = MessageRepository(session)
        self.context_builder = ConversationContextBuilder(session, settings)
        self.relationships = RelationshipService(session)
        self.memory_application = MemoryApplicationService(session, settings)
        self.memory_lifecycle = MemoryLifecycleService(session, settings)
        self.memory_repository = MemoryRepository(session)

    def _record_memory_usage(self, character: Message) -> None:
        selected = self.context_builder.last_selected_memory_ids
        character.message_metadata = {
            **character.message_metadata,
            "selected_memory_ids": selected,
        }
        if selected:
            self.memory_repository.record_usage(selected, utc_now())

    def _apply_memory(
        self,
        conversation: Conversation,
        user: Message,
        character: Message,
        result: GenerationResult,
    ) -> MemoryProcessingResult:
        processing = self.memory_application.apply_exchange(
            conversation,
            user,
            character,
            result.parsed_response,
            commit=False,
        )
        character.message_metadata = {
            **character.message_metadata,
            "memory_processing": processing.model_dump(mode="json"),
        }
        self.session.commit()
        return processing

    def _get(self, conversation_id: int) -> Conversation:
        conversation = self.conversations.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError("The conversation was not found.")
        return conversation

    @staticmethod
    def _ensure_writable(conversation: Conversation) -> None:
        if conversation.is_archived:
            raise ConversationArchivedError("Archived conversations are read-only.")
        if not conversation.is_active:
            raise ConversationInactiveError("Inactive conversations are read-only.")

    def _summary(self, conversation: Conversation) -> ConversationSummaryResponse:
        count, last_at = self.conversations.message_stats(conversation.id)
        state = self.conversations.ensure_relationship(conversation)
        return ConversationSummaryResponse(
            id=conversation.id,
            title=conversation.title,
            character=CharacterReference(
                id=conversation.character.id,
                slug=conversation.character.slug,
                display_name=conversation.character.display_name,
            ),
            roleplay_user=RoleplayProfileReference(
                id=conversation.roleplay_profile.id,
                roleplay_name=conversation.roleplay_profile.roleplay_name,
            ),
            current_scene=conversation.current_scene,
            relationship_stage=conversation.relationship_stage,
            is_active=conversation.is_active,
            is_archived=conversation.is_archived,
            message_count=count,
            turn_count=state.turn_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            last_message_at=last_at if isinstance(last_at, datetime) else None,
        )

    def _detail(self, conversation: Conversation) -> ConversationDetailResponse:
        summary = self._summary(conversation)
        state = self.conversations.ensure_relationship(conversation)
        recent = self.messages.recent(conversation.id, 10)
        return ConversationDetailResponse(
            **summary.model_dump(),
            relationship_state=RelationshipSnapshot.model_validate(
                state, from_attributes=True
            ),
            recent_messages=[
                MessagePreview(
                    id=item.id,
                    sender=item.sender.value,
                    raw_content=item.raw_content,
                    sequence_number=item.sequence_number,
                    created_at=item.created_at,
                )
                for item in recent
            ],
        )

    def create(self, payload: ConversationCreateRequest) -> ConversationDetailResponse:
        character_config = self.ai.loader.load_character(payload.character_slug)
        profile_config = self.ai.loader.load_roleplay_user(payload.roleplay_user_slug)
        character = self.conversations.get_character(character_config.slug)
        if character is None:
            raise CharacterNotFoundError(
                f"Character '{payload.character_slug}' was not found."
            )
        profile = self.conversations.get_profile(profile_config.identity.roleplay_name)
        if profile is None:
            raise RoleplayProfileNotFoundError(
                f"Roleplay profile '{payload.roleplay_user_slug}' was not found."
            )
        conversation = Conversation(
            character=character,
            roleplay_profile=profile,
            title=payload.title or f"Conversation with {character.display_name}",
            current_scene=payload.current_scene,
            relationship_stage=payload.relationship_stage,
        )
        conversation.relationship_state = RelationshipState(
            relationship_stage=payload.relationship_stage,
            baseline_values={
                "attraction": 50,
                "trust": 50,
                "affection": 50,
                "respect": 50,
                "comfort": 50,
                "jealousy": 0,
                "anger": 0,
                "mood": "neutral",
                "relationship_stage": payload.relationship_stage,
            },
        )
        self.conversations.add(conversation)
        self.session.commit()
        return self._detail(conversation)

    def list(
        self,
        *,
        limit: int,
        offset: int,
        archived: bool | None,
        active: bool | None,
        character_slug: str | None,
    ) -> ConversationListResponse:
        items, total = self.conversations.page(
            limit=limit,
            offset=offset,
            archived=archived,
            active=active,
            character_slug=character_slug,
        )
        return ConversationListResponse(
            items=[self._summary(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )

    def detail(self, conversation_id: int) -> ConversationDetailResponse:
        return self._detail(self._get(conversation_id))

    def update(
        self, conversation_id: int, payload: ConversationUpdateRequest
    ) -> ConversationDetailResponse:
        conversation = self._get(conversation_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(conversation, field, value)
        if payload.relationship_stage is not None:
            self.conversations.ensure_relationship(conversation).relationship_stage = (
                payload.relationship_stage
            )
        conversation.updated_at = utc_now()
        self.session.commit()
        return self._detail(conversation)

    def delete(self, conversation_id: int) -> None:
        conversation = self._get(conversation_id)
        self.conversations.delete(conversation)
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def list_messages(
        self, conversation_id: int, *, limit: int, offset: int
    ) -> MessageListResponse:
        self._get(conversation_id)
        items, total = self.messages.page(conversation_id, limit=limit, offset=offset)
        return MessageListResponse(
            items=[MessageResponse.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )

    def _generation_request(
        self,
        conversation: Conversation,
        payload: SendMessageRequest | RegenerateRequest,
        *,
        exclude_sequence: int | None = None,
    ) -> GenerationRequest:
        context = self.context_builder.build(
            conversation,
            behaviour_hint=payload.behaviour_hint,
            response_length=payload.response_length,
            language_mode=payload.language_mode,
            exclude_sequence=exclude_sequence,
        )
        return GenerationRequest(
            context=context,
            **payload.generation_overrides.model_dump(exclude_none=True),
        )

    @staticmethod
    def _character_message(
        conversation_id: int,
        sequence_number: int,
        result: GenerationResult,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        parsed = result.parsed_response
        generation_metadata = {
            "provider": result.provider,
            "model": result.model,
            "parse_status": result.parse_status,
            "finish_reason": result.finish_reason,
            "generation": result.model_dump(mode="json"),
            **(metadata or {}),
        }
        return Message(
            conversation_id=conversation_id,
            sender=MessageSender.CHARACTER,
            raw_content=parsed.raw_text or result.text,
            narration="\n\n".join(parsed.narration_blocks) or None,
            dialogue="\n\n".join(parsed.dialogue_blocks) or None,
            emotion=parsed.emotion,
            message_metadata=generation_metadata,
            sequence_number=sequence_number,
        )

    def _recalculate_turns(self, conversation: Conversation) -> int:
        self.session.flush()
        count = self.messages.completed_turn_count(conversation.id)
        self.conversations.ensure_relationship(conversation).turn_count = count
        return count

    def _existing_send(
        self, conversation: Conversation, client_message_id: str
    ) -> SendMessageResponse | None:
        user = self.messages.find_client_message(conversation.id, client_message_id)
        if user is None:
            return None
        character = self.messages.by_sequence(conversation.id, user.sequence_number + 1)
        if character is None or character.sender != MessageSender.CHARACTER:
            raise DuplicateClientMessageError(
                "This client message was already accepted and has no completed "
                "reply yet."
            )
        raw_generation = character.message_metadata.get("generation")
        if not isinstance(raw_generation, dict):
            raise DuplicateClientMessageError(
                "This client message was already completed."
            )
        return SendMessageResponse(
            conversation=self._summary(conversation),
            user_message=MessageResponse.model_validate(user),
            character_message=MessageResponse.model_validate(character),
            generation=GenerationResult.model_validate(raw_generation),
            warnings=[
                "Returned the persisted result for a duplicate client_message_id."
            ],
        )

    async def send(
        self, conversation_id: int, payload: SendMessageRequest
    ) -> SendMessageResponse:
        self._ensure_writable(self._get(conversation_id))
        async with self.locks.acquire(
            conversation_id, self.settings.conversation_lock_timeout_seconds
        ):
            conversation = self._get(conversation_id)
            self._ensure_writable(conversation)
            if payload.client_message_id:
                existing = self._existing_send(conversation, payload.client_message_id)
                if existing is not None:
                    return existing
            user = Message(
                conversation_id=conversation.id,
                sender=MessageSender.USER,
                raw_content=payload.content,
                sequence_number=self.messages.next_sequence(conversation.id),
                message_metadata={
                    **(
                        {"client_message_id": payload.client_message_id}
                        if payload.client_message_id
                        else {}
                    ),
                    **(
                        {"behaviour_hint": payload.behaviour_hint}
                        if payload.behaviour_hint
                        else {}
                    ),
                },
            )
            self.messages.add(user)
            conversation.updated_at = utc_now()
            try:
                self.session.commit()
            except SQLAlchemyError as exc:
                self.session.rollback()
                raise ResponsePersistenceError(
                    "The user message could not be persisted."
                ) from exc
            request = self._generation_request(conversation, payload)
            result = await self.ai.generate(request)
            character = self._character_message(
                conversation.id, user.sequence_number + 1, result
            )
            self._record_memory_usage(character)
            self.messages.add(character)
            conversation.updated_at = utc_now()
            try:
                self._recalculate_turns(conversation)
                self.session.commit()
            except SQLAlchemyError as exc:
                self.session.rollback()
                raise ResponsePersistenceError(
                    "The generated response could not be persisted."
                ) from exc
            warnings: list[str] = []
            relationship: RelationshipApplicationResult | None = None
            memory: MemoryProcessingResult | None = None
            try:
                relationship = self.relationships.apply_exchange(
                    conversation, user, character, result.parsed_response
                )
            except Exception:
                self.session.rollback()
                warnings.append(
                    "The exchange was saved, but relationship processing failed and "
                    "can be recalculated."
                )
            try:
                memory = self._apply_memory(conversation, user, character, result)
            except Exception:
                self.session.rollback()
                warnings.append(
                    "The exchange was saved, but memory processing failed and can "
                    "be rebuilt."
                )
            return SendMessageResponse(
                conversation=self._summary(conversation),
                user_message=MessageResponse.model_validate(user),
                character_message=MessageResponse.model_validate(character),
                generation=result,
                relationship=relationship,
                memory=memory,
                warnings=warnings,
            )

    async def stream_send(
        self, conversation_id: int, payload: SendMessageRequest
    ) -> AsyncIterator[StreamEvent]:
        self._ensure_writable(self._get(conversation_id))
        async with self.locks.acquire(
            conversation_id, self.settings.conversation_lock_timeout_seconds
        ):
            conversation = self._get(conversation_id)
            self._ensure_writable(conversation)
            if payload.client_message_id:
                if self.messages.find_client_message(
                    conversation.id, payload.client_message_id
                ):
                    raise DuplicateClientMessageError(
                        "This client message was already accepted."
                    )
            user = Message(
                conversation_id=conversation.id,
                sender=MessageSender.USER,
                raw_content=payload.content,
                sequence_number=self.messages.next_sequence(conversation.id),
                message_metadata=(
                    {"client_message_id": payload.client_message_id}
                    if payload.client_message_id
                    else {}
                ),
            )
            self.messages.add(user)
            conversation.updated_at = utc_now()
            try:
                self.session.commit()
            except SQLAlchemyError as exc:
                self.session.rollback()
                raise ResponsePersistenceError(
                    "The user message could not be persisted."
                ) from exc
            yield StreamEvent(
                event="accepted", data={"conversation_id": conversation.id}
            )
            yield StreamEvent(
                event="user_message",
                data=MessageResponse.model_validate(user).model_dump(mode="json"),
            )
            request = self._generation_request(conversation, payload)
            chunks: list[str] = []
            provider = "ollama"
            model = self.settings.ollama_model
            provider_metadata: dict[str, Any] = {}
            try:
                async for event in self.ai.stream(request):
                    if event.event == "start":
                        provider = str(event.data.get("provider", provider))
                        model = str(event.data.get("model", model))
                        yield event
                    elif event.event == "token":
                        token = str(event.data.get("text", ""))
                        chunks.append(token)
                        if (
                            sum(map(len, chunks))
                            > self.settings.stream_max_accumulated_characters
                        ):
                            raise StreamOutputLimitError(
                                "The generated stream exceeded the configured output "
                                "limit."
                            )
                        yield event
                    elif event.event == "metadata":
                        provider_metadata.update(event.data)
                    elif event.event == "completed":
                        text = str(event.data.get("text", "")) or "".join(chunks)
                        processed = process_roleplay_response(text)
                        result = GenerationResult(
                            provider=provider,
                            model=model,
                            text=text,
                            parsed_response=processed.response,
                            parse_status=processed.parse_status,
                            parser_diagnostics=processed.diagnostics,
                            done=True,
                            finish_reason=(
                                str(provider_metadata["done_reason"])
                                if "done_reason" in provider_metadata
                                else None
                            ),
                            metadata=provider_metadata,
                        )
                        character = self._character_message(
                            conversation.id, user.sequence_number + 1, result
                        )
                        self._record_memory_usage(character)
                        self.messages.add(character)
                        conversation.updated_at = utc_now()
                        try:
                            self._recalculate_turns(conversation)
                            self.session.commit()
                        except SQLAlchemyError as exc:
                            self.session.rollback()
                            raise ResponsePersistenceError(
                                "The streamed response could not be persisted."
                            ) from exc
                        relationship = None
                        relationship_warning = None
                        try:
                            relationship = self.relationships.apply_exchange(
                                conversation,
                                user,
                                character,
                                result.parsed_response,
                            )
                        except Exception:
                            self.session.rollback()
                            relationship_warning = (
                                "The exchange was saved, but relationship processing "
                                "failed and can be recalculated."
                            )
                        memory = None
                        memory_warning = None
                        try:
                            memory = self._apply_memory(
                                conversation, user, character, result
                            )
                        except Exception:
                            self.session.rollback()
                            memory_warning = (
                                "The exchange was saved, but memory processing failed "
                                "and can be rebuilt."
                            )
                        yield StreamEvent(
                            event="metadata",
                            data={
                                "parse_status": processed.parse_status,
                                "parser_diagnostics": processed.diagnostics.model_dump(
                                    mode="json"
                                ),
                                "relationship": (
                                    relationship.model_dump(mode="json")
                                    if relationship
                                    else None
                                ),
                                "memory": (
                                    memory.model_dump(mode="json") if memory else None
                                ),
                                "warnings": [
                                    warning
                                    for warning in (
                                        relationship_warning,
                                        memory_warning,
                                    )
                                    if warning
                                ],
                                **provider_metadata,
                            },
                        )
                        yield StreamEvent(
                            event="completed",
                            data={
                                "character_message": MessageResponse.model_validate(
                                    character
                                ).model_dump(mode="json"),
                                "turn_count": self.conversations.ensure_relationship(
                                    conversation
                                ).turn_count,
                            },
                        )
            except asyncio.CancelledError:
                self.session.rollback()
                raise

    async def regenerate(
        self, conversation_id: int, payload: RegenerateRequest
    ) -> RegenerateResponse:
        self._ensure_writable(self._get(conversation_id))
        async with self.locks.acquire(
            conversation_id, self.settings.conversation_lock_timeout_seconds
        ):
            conversation = self._get(conversation_id)
            self._ensure_writable(conversation)
            latest = self.messages.latest(conversation.id)
            if latest is None:
                raise NoCharacterResponseToRegenerateError(
                    "There is no character response to regenerate."
                )
            if latest.sender == MessageSender.USER:
                request = self._generation_request(conversation, payload)
                result = await self.ai.generate(request)
                character = self._character_message(
                    conversation.id, latest.sequence_number + 1, result
                )
                self._record_memory_usage(character)
                self.messages.add(character)
                conversation.updated_at = utc_now()
                try:
                    turn_count = self._recalculate_turns(conversation)
                    self.session.commit()
                except SQLAlchemyError as exc:
                    self.session.rollback()
                    raise ResponsePersistenceError(
                        "The regenerated response could not be persisted."
                    ) from exc
                warnings: list[str] = []
                relationship = None
                memory = None
                try:
                    relationship = self.relationships.apply_exchange(
                        conversation, latest, character, result.parsed_response
                    )
                except Exception:
                    self.session.rollback()
                    warnings.append(
                        "The response was saved, but relationship processing failed."
                    )
                try:
                    memory = self._apply_memory(conversation, latest, character, result)
                except Exception:
                    self.session.rollback()
                    warnings.append(
                        "The response was saved, but memory processing failed."
                    )
                return RegenerateResponse(
                    character_message=MessageResponse.model_validate(character),
                    generation=result,
                    turn_count=turn_count,
                    relationship=relationship,
                    memory=memory,
                    warnings=warnings,
                )
            character = latest
            if character.sender != MessageSender.CHARACTER:
                raise RegenerateNotAllowedError(
                    "Only a latest user or character message can be regenerated."
                )
            user = self.messages.by_sequence(
                conversation.id, character.sequence_number - 1
            )
            if user is None or user.sender != MessageSender.USER:
                raise RegenerateNotAllowedError(
                    "The character response has no directly preceding user message."
                )
            request = self._generation_request(
                conversation, payload, exclude_sequence=character.sequence_number
            )
            result = await self.ai.generate(request)
            self.memory_lifecycle.invalidate_for_messages(
                conversation.id,
                [character.id],
                preserve_deterministic_user_ids={user.id},
            )
            replacement = self._character_message(
                conversation.id,
                character.sequence_number,
                result,
                {
                    "regeneration_count": int(
                        character.message_metadata.get("regeneration_count", 0)
                    )
                    + 1
                },
            )
            character.raw_content = replacement.raw_content
            character.narration = replacement.narration
            character.dialogue = replacement.dialogue
            character.emotion = replacement.emotion
            character.message_metadata = replacement.message_metadata
            self._record_memory_usage(character)
            character.is_edited = True
            character.edited_at = utc_now()
            conversation.updated_at = utc_now()
            self.session.commit()
            warnings = []
            relationship = None
            memory = None
            try:
                relationship = self.relationships.supersede_and_apply(
                    conversation, user, character, result.parsed_response
                )
            except Exception:
                self.session.rollback()
                warnings.append(
                    "The regenerated response was saved, but relationship processing "
                    "failed. The previous audit event remains recoverable."
                )
            try:
                memory = self._apply_memory(conversation, user, character, result)
            except Exception:
                self.session.rollback()
                warnings.append(
                    "The regenerated response was saved, but memory processing failed."
                )
            return RegenerateResponse(
                character_message=MessageResponse.model_validate(character),
                generation=result,
                turn_count=self.conversations.ensure_relationship(
                    conversation
                ).turn_count,
                relationship=relationship,
                memory=memory,
                warnings=warnings,
            )

    def edit_message(
        self,
        conversation_id: int,
        message_id: int,
        payload: EditMessageRequest,
    ) -> MessageResponse:
        conversation = self._get(conversation_id)
        self._ensure_writable(conversation)
        message = self.messages.get(message_id)
        if message is None:
            raise MessageNotFoundError("The message was not found.")
        if message.conversation_id != conversation_id:
            raise MessageConversationMismatchError(
                "The message does not belong to this conversation."
            )
        if message.sender != MessageSender.USER:
            raise InvalidMessageSenderError("Only user messages can be edited.")
        latest = self.messages.latest(conversation_id)
        if (
            latest is not None
            and latest.sequence_number > message.sequence_number
            and not payload.confirm_truncate_following_messages
        ):
            raise MessageEditRequiresTruncationError(
                "Editing this message requires truncating all later messages."
            )
        if latest is not None and latest.sequence_number > message.sequence_number:
            removed = self.messages.from_sequence(
                conversation_id, message.sequence_number + 1
            )
            self.relationships.revert_for_messages(
                conversation,
                [item.id for item in removed],
                recalculate=False,
            )
            self.memory_lifecycle.invalidate_for_messages(
                conversation_id, [message.id, *(item.id for item in removed)]
            )
            self.messages.delete_from(conversation_id, message.sequence_number + 1)
        else:
            removed = []
            self.memory_lifecycle.invalidate_for_messages(conversation_id, [message.id])
        message.raw_content = payload.content
        message.is_edited = True
        message.edited_at = utc_now()
        if payload.behaviour_hint:
            message.message_metadata = {
                **message.message_metadata,
                "behaviour_hint": payload.behaviour_hint,
            }
        conversation.updated_at = utc_now()
        self._recalculate_turns(conversation)
        if removed:
            self.relationships.recalculate(conversation)
        self.session.commit()
        return MessageResponse.model_validate(message)

    def delete_message(
        self,
        conversation_id: int,
        message_id: int,
        *,
        confirm_truncate: bool,
    ) -> None:
        conversation = self._get(conversation_id)
        self._ensure_writable(conversation)
        message = self.messages.get(message_id)
        if message is None:
            raise MessageNotFoundError("The message was not found.")
        if message.conversation_id != conversation_id:
            raise MessageConversationMismatchError(
                "The message does not belong to this conversation."
            )
        latest = self.messages.latest(conversation_id)
        if (
            latest is not None
            and latest.sequence_number > message.sequence_number
            and not confirm_truncate
        ):
            raise MessageDeleteRequiresTruncationError(
                "Deleting this message requires truncating all later messages."
            )
        removed = self.messages.from_sequence(conversation_id, message.sequence_number)
        self.relationships.revert_for_messages(
            conversation,
            [item.id for item in removed],
            recalculate=False,
        )
        self.memory_lifecycle.invalidate_for_messages(
            conversation_id, [item.id for item in removed]
        )
        self.messages.delete_from(conversation_id, message.sequence_number)
        conversation.updated_at = utc_now()
        self._recalculate_turns(conversation)
        self.relationships.recalculate(conversation)
        self.session.commit()

    def relationship_state(self, conversation_id: int) -> RelationshipStateResponse:
        return self.relationships.state(self._get(conversation_id))

    def relationship_history(
        self, conversation_id: int, *, limit: int, offset: int
    ) -> RelationshipEventListResponse:
        self._get(conversation_id)
        return self.relationships.history(conversation_id, limit=limit, offset=offset)

    async def manual_relationship_update(
        self, conversation_id: int, payload: ManualRelationshipUpdate
    ) -> RelationshipApplicationResult:
        async with self.locks.acquire(
            conversation_id, self.settings.conversation_lock_timeout_seconds
        ):
            conversation = self._get(conversation_id)
            return self.relationships.manual_update(conversation, payload)
