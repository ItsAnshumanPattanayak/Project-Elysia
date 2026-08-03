from typing import Literal

from sqlalchemy.orm import Session

from app.character_engine.schemas import (
    MemoryContext,
    MessageRole,
    PromptContext,
    PromptMessage,
    RelationshipValues,
)
from app.core.config import Settings
from app.memory.retrieval import MemoryRetrievalService
from app.models import Conversation, MessageSender
from app.repositories.memories import MemoryRepository
from app.repositories.messages import MessageRepository


class ConversationContextBuilder:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.messages = MessageRepository(session)
        self.settings = settings
        self.memory_retrieval = MemoryRetrievalService(
            MemoryRepository(session), settings
        )
        self.last_selected_memory_ids: list[int] = []

    def build(
        self,
        conversation: Conversation,
        *,
        behaviour_hint: str | None = None,
        response_length: Literal["concise", "balanced", "detailed"] | None = None,
        language_mode: str | None = None,
        exclude_sequence: int | None = None,
    ) -> PromptContext:
        recent = self.messages.recent(
            conversation.id, self.settings.conversation_recent_message_limit + 1
        )
        if exclude_sequence is not None:
            recent = [
                item for item in recent if item.sequence_number != exclude_sequence
            ]
        recent = recent[-self.settings.conversation_recent_message_limit :]
        role_map = {
            MessageSender.USER: MessageRole.USER,
            MessageSender.CHARACTER: MessageRole.CHARACTER,
            MessageSender.SYSTEM: MessageRole.SYSTEM,
        }
        state = conversation.relationship_state
        relationship_values = None
        if state is not None:
            relationship_values = RelationshipValues(
                attraction=state.attraction,
                trust=state.trust,
                affection=state.affection,
                respect=state.respect,
                comfort=state.comfort,
                jealousy=state.jealousy,
                anger=state.anger,
            )
        roleplay_slug = conversation.roleplay_profile.roleplay_name.strip().lower()
        query_parts = [
            conversation.current_scene,
            conversation.relationship_stage,
            *(item.raw_content for item in recent[-4:]),
        ]
        selection = self.memory_retrieval.retrieve(
            conversation.id, "\n".join(part for part in query_parts if part)
        )
        self.last_selected_memory_ids = selection.selected_ids
        return PromptContext(
            character_slug=conversation.character.slug,
            roleplay_user_slug=roleplay_slug,
            conversation_id=conversation.id,
            current_scene=conversation.current_scene or None,
            relationship_stage=conversation.relationship_stage,
            current_mood=state.mood if state is not None else None,
            relationship_values=relationship_values,
            recent_messages=[
                PromptMessage(role=role_map[item.sender], content=item.raw_content)
                for item in recent
            ],
            relevant_memories=[
                MemoryContext(
                    content=item.content,
                    memory_type=item.memory_type.value,
                    importance=item.importance,
                )
                for item in selection.items
            ],
            conversation_summary=conversation.summary or None,
            behaviour_hint=behaviour_hint,
            response_length=response_length,
            language_mode=language_mode,
        )
