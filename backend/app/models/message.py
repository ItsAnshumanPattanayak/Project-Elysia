from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.memory import Memory


class MessageSender(str, Enum):
    USER = "user"
    CHARACTER = "character"
    SYSTEM = "system"


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "sequence_number", name="uq_message_sequence"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    sender: Mapped[MessageSender] = mapped_column(
        SQLEnum(MessageSender, native_enum=False)
    )
    raw_content: Mapped[str] = mapped_column(Text)
    narration: Mapped[str | None] = mapped_column(Text)
    dialogue: Mapped[str | None] = mapped_column(Text)
    emotion: Mapped[str | None] = mapped_column(String(100))
    message_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict
    )
    sequence_number: Mapped[int] = mapped_column(Integer)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    edited_at: Mapped[datetime | None]

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    user_sourced_memories: Mapped[list["Memory"]] = relationship(
        foreign_keys="Memory.source_user_message_id",
        back_populates="source_user_message",
    )
    character_sourced_memories: Mapped[list["Memory"]] = relationship(
        foreign_keys="Memory.source_character_message_id",
        back_populates="source_character_message",
    )
