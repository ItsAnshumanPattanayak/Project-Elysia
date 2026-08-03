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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.message import Message


class RelationshipEvent(Base):
    __tablename__ = "relationship_events"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_relationship_event_confidence",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    source_user_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), index=True
    )
    source_character_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    score_deltas: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    values_before: Mapped[dict[str, Any]] = mapped_column(JSON)
    values_after: Mapped[dict[str, Any]] = mapped_column(JSON)
    mood_before: Mapped[str] = mapped_column(String(100))
    mood_after: Mapped[str] = mapped_column(String(100))
    stage_before: Mapped[str] = mapped_column(String(100))
    stage_after: Mapped[str] = mapped_column(String(100))
    application_key: Mapped[str] = mapped_column(String(250), unique=True, index=True)
    is_reverted: Mapped[bool] = mapped_column(Boolean, default=False)
    reverted_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    conversation: Mapped["Conversation"] = relationship(
        back_populates="relationship_events"
    )
    source_user_message: Mapped["Message | None"] = relationship(
        foreign_keys=[source_user_message_id]
    )
    source_character_message: Mapped["Message | None"] = relationship(
        foreign_keys=[source_character_message_id]
    )
