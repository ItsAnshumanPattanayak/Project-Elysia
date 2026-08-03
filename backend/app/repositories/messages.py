from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Message, MessageSender


class MessageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, message_id: int) -> Message | None:
        return self.session.get(Message, message_id)

    def add(self, message: Message) -> None:
        self.session.add(message)

    def next_sequence(self, conversation_id: int) -> int:
        current = self.session.scalar(
            select(func.max(Message.sequence_number)).where(
                Message.conversation_id == conversation_id
            )
        )
        return int(current or 0) + 1

    def page(
        self, conversation_id: int, *, limit: int, offset: int
    ) -> tuple[list[Message], int]:
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.conversation_id == conversation_id)
            )
            or 0
        )
        items = list(
            self.session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.sequence_number, Message.id)
                .offset(offset)
                .limit(limit)
            )
        )
        return items, total

    def recent(self, conversation_id: int, limit: int) -> list[Message]:
        descending = list(
            self.session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.sequence_number.desc())
                .limit(limit)
            )
        )
        return list(reversed(descending))

    def latest(self, conversation_id: int) -> Message | None:
        return self.session.scalar(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_number.desc())
            .limit(1)
        )

    def by_sequence(self, conversation_id: int, sequence: int) -> Message | None:
        return self.session.scalar(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.sequence_number == sequence,
            )
        )

    def find_client_message(
        self, conversation_id: int, client_message_id: str
    ) -> Message | None:
        messages = self.session.scalars(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.sender == MessageSender.USER,
            )
        )
        return next(
            (
                item
                for item in messages
                if item.message_metadata.get("client_message_id") == client_message_id
            ),
            None,
        )

    def delete_from(self, conversation_id: int, sequence: int) -> None:
        self.session.execute(
            delete(Message).where(
                Message.conversation_id == conversation_id,
                Message.sequence_number >= sequence,
            )
        )

    def completed_turn_count(self, conversation_id: int) -> int:
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.sender == MessageSender.CHARACTER,
                )
            )
            or 0
        )
