from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.message import Message


class Memory(TimestampMixin, Base):
    __tablename__ = "memories"
    __table_args__ = (
        CheckConstraint("importance BETWEEN 0 AND 100", name="ck_memory_importance"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_memory_confidence"),
        CheckConstraint(
            "status IN ('active','archived','superseded','reverted')",
            name="ck_memory_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    source_user_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), index=True
    )
    source_character_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), index=True
    )
    memory_type: Mapped[str] = mapped_column(String(50), index=True)
    content: Mapped[str] = mapped_column(Text)
    normalized_content: Mapped[str] = mapped_column(Text)
    canonical_fact_key: Mapped[str | None] = mapped_column(String(250), index=True)
    importance: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    entities: Mapped[list[str]] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(40), index=True)
    application_key: Mapped[str] = mapped_column(String(250), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    supersedes_memory_id: Mapped[int | None] = mapped_column(
        ForeignKey("memories.id", ondelete="SET NULL")
    )
    superseded_by_memory_id: Mapped[int | None] = mapped_column(
        ForeignKey("memories.id", ondelete="SET NULL")
    )
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None]
    last_confirmed_at: Mapped[datetime | None]
    reverted_at: Mapped[datetime | None]
    memory_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="memories")
    source_user_message: Mapped["Message | None"] = relationship(
        foreign_keys=[source_user_message_id], back_populates="user_sourced_memories"
    )
    source_character_message: Mapped["Message | None"] = relationship(
        foreign_keys=[source_character_message_id],
        back_populates="character_sourced_memories",
    )
