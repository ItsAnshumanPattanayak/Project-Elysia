from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class RelationshipState(TimestampMixin, Base):
    __tablename__ = "relationship_states"
    __table_args__ = (
        UniqueConstraint("conversation_id"),
        CheckConstraint(
            "attraction BETWEEN 0 AND 100", name="ck_relationship_attraction"
        ),
        CheckConstraint("trust BETWEEN 0 AND 100", name="ck_relationship_trust"),
        CheckConstraint(
            "affection BETWEEN 0 AND 100", name="ck_relationship_affection"
        ),
        CheckConstraint("respect BETWEEN 0 AND 100", name="ck_relationship_respect"),
        CheckConstraint("comfort BETWEEN 0 AND 100", name="ck_relationship_comfort"),
        CheckConstraint("jealousy BETWEEN 0 AND 100", name="ck_relationship_jealousy"),
        CheckConstraint("anger BETWEEN 0 AND 100", name="ck_relationship_anger"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    attraction: Mapped[int] = mapped_column(Integer, default=50)
    trust: Mapped[int] = mapped_column(Integer, default=50)
    affection: Mapped[int] = mapped_column(Integer, default=50)
    respect: Mapped[int] = mapped_column(Integer, default=50)
    comfort: Mapped[int] = mapped_column(Integer, default=50)
    jealousy: Mapped[int] = mapped_column(Integer, default=0)
    anger: Mapped[int] = mapped_column(Integer, default=0)
    mood: Mapped[str] = mapped_column(String(100), default="neutral")
    relationship_stage: Mapped[str] = mapped_column(String(100), default="committed")
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    conversation: Mapped["Conversation"] = relationship(
        back_populates="relationship_state"
    )
