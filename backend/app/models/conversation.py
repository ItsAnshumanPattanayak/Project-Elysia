from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.character import Character
    from app.models.memory import Memory
    from app.models.message import Message
    from app.models.relationship_event import RelationshipEvent
    from app.models.relationship_state import RelationshipState
    from app.models.roleplay_profile import RoleplayProfile


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    roleplay_profile_id: Mapped[int] = mapped_column(
        ForeignKey("roleplay_profiles.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(250))
    summary: Mapped[str] = mapped_column(Text, default="")
    current_scene: Mapped[str] = mapped_column(Text, default="")
    relationship_stage: Mapped[str] = mapped_column(String(100), default="committed")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    character: Mapped["Character"] = relationship(back_populates="conversations")
    roleplay_profile: Mapped["RoleplayProfile"] = relationship(
        back_populates="conversations"
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    relationship_state: Mapped["RelationshipState | None"] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", uselist=False
    )
    memories: Mapped[list["Memory"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    relationship_events: Mapped[list["RelationshipEvent"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
