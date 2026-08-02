from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.message import Message


class Memory(TimestampMixin, Base):
    __tablename__ = "memories"
    __table_args__ = (
        CheckConstraint("importance BETWEEN 1 AND 5", name="ck_memory_importance"),
        CheckConstraint(
            "emotional_value BETWEEN -100 AND 100", name="ck_memory_emotional_value"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    memory_type: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[int] = mapped_column(Integer, default=3)
    emotional_value: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), index=True
    )
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_recalled_at: Mapped[datetime | None]

    conversation: Mapped["Conversation"] = relationship(back_populates="memories")
    source_message: Mapped["Message | None"] = relationship(
        back_populates="sourced_memories"
    )
