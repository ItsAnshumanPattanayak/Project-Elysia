from typing import Literal

from sqlalchemy.orm import Session

from app.character_engine.schemas import (
    MessageRole,
    PromptContext,
    PromptMessage,
    RelationshipValues,
)
from app.core.config import Settings
from app.models import Conversation, MessageSender
from app.repositories.messages import MessageRepository


class ConversationContextBuilder:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.messages = MessageRepository(session)
        self.settings = settings

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
        return PromptContext(
            character_slug=conversation.character.slug,
            roleplay_user_slug=roleplay_slug,
            conversation_id=conversation.id,
            current_scene=conversation.current_scene or None,
            relationship_stage=conversation.relationship_stage,
            relationship_values=relationship_values,
            recent_messages=[
                PromptMessage(role=role_map[item.sender], content=item.raw_content)
                for item in recent
            ],
            relevant_memories=[],
            conversation_summary=conversation.summary or None,
            behaviour_hint=behaviour_hint,
            response_length=response_length,
            language_mode=language_mode,
        )
