from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Character,
    Conversation,
    Message,
    RelationshipState,
    RoleplayProfile,
)


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, conversation_id: int) -> Conversation | None:
        return self.session.scalar(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                joinedload(Conversation.character),
                joinedload(Conversation.roleplay_profile),
                joinedload(Conversation.relationship_state),
            )
        )

    def get_character(self, slug: str) -> Character | None:
        return self.session.scalar(select(Character).where(Character.slug == slug))

    def get_profile(self, roleplay_name: str) -> RoleplayProfile | None:
        return self.session.scalar(
            select(RoleplayProfile).where(
                func.lower(RoleplayProfile.roleplay_name) == roleplay_name.lower()
            )
        )

    def add(self, conversation: Conversation) -> None:
        self.session.add(conversation)

    def delete(self, conversation: Conversation) -> None:
        self.session.delete(conversation)

    def page(
        self,
        *,
        limit: int,
        offset: int,
        archived: bool | None,
        active: bool | None,
        character_slug: str | None,
    ) -> tuple[list[Conversation], int]:
        filters = []
        if archived is not None:
            filters.append(Conversation.is_archived == archived)
        if active is not None:
            filters.append(Conversation.is_active == active)
        if character_slug is not None:
            filters.append(Character.slug == character_slug)
        base = select(Conversation).join(Conversation.character).where(*filters)
        total = (
            self.session.scalar(select(func.count()).select_from(base.subquery())) or 0
        )
        items = list(
            self.session.scalars(
                base.options(
                    joinedload(Conversation.character),
                    joinedload(Conversation.roleplay_profile),
                    joinedload(Conversation.relationship_state),
                )
                .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return items, total

    def message_stats(self, conversation_id: int) -> tuple[int, object | None]:
        row = self.session.execute(
            select(func.count(Message.id), func.max(Message.created_at)).where(
                Message.conversation_id == conversation_id
            )
        ).one()
        return int(row[0]), row[1]

    def ensure_relationship(self, conversation: Conversation) -> RelationshipState:
        state = conversation.relationship_state
        if state is None:
            state = RelationshipState(
                conversation=conversation,
                relationship_stage=conversation.relationship_stage,
            )
            self.session.add(state)
        return state
