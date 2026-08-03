from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import RelationshipEvent


class RelationshipEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_application_key(self, key: str) -> RelationshipEvent | None:
        return self.session.scalar(
            select(RelationshipEvent).where(RelationshipEvent.application_key == key)
        )

    def add(self, event: RelationshipEvent) -> None:
        self.session.add(event)

    def active(self, conversation_id: int) -> list[RelationshipEvent]:
        return list(
            self.session.scalars(
                select(RelationshipEvent)
                .where(
                    RelationshipEvent.conversation_id == conversation_id,
                    RelationshipEvent.is_reverted.is_(False),
                )
                .order_by(RelationshipEvent.created_at, RelationshipEvent.id)
            )
        )

    def recent(self, conversation_id: int, limit: int = 10) -> list[RelationshipEvent]:
        items = list(
            self.session.scalars(
                select(RelationshipEvent)
                .where(
                    RelationshipEvent.conversation_id == conversation_id,
                    RelationshipEvent.is_reverted.is_(False),
                )
                .order_by(
                    RelationshipEvent.created_at.desc(), RelationshipEvent.id.desc()
                )
                .limit(limit)
            )
        )
        return list(reversed(items))

    def page(
        self, conversation_id: int, *, limit: int, offset: int
    ) -> tuple[list[RelationshipEvent], int]:
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(RelationshipEvent)
                .where(RelationshipEvent.conversation_id == conversation_id)
            )
            or 0
        )
        items = list(
            self.session.scalars(
                select(RelationshipEvent)
                .where(RelationshipEvent.conversation_id == conversation_id)
                .order_by(
                    RelationshipEvent.created_at.desc(), RelationshipEvent.id.desc()
                )
                .offset(offset)
                .limit(limit)
            )
        )
        return items, int(total)

    def for_character_message(self, message_id: int) -> list[RelationshipEvent]:
        return list(
            self.session.scalars(
                select(RelationshipEvent).where(
                    RelationshipEvent.source_character_message_id == message_id,
                    RelationshipEvent.is_reverted.is_(False),
                )
            )
        )

    def for_message_ids(self, message_ids: list[int]) -> list[RelationshipEvent]:
        if not message_ids:
            return []
        return list(
            self.session.scalars(
                select(RelationshipEvent).where(
                    RelationshipEvent.is_reverted.is_(False),
                    (
                        RelationshipEvent.source_user_message_id.in_(message_ids)
                        | RelationshipEvent.source_character_message_id.in_(message_ids)
                    ),
                )
            )
        )
