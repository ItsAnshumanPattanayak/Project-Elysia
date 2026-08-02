from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class RoleplayProfile(TimestampMixin, Base):
    __tablename__ = "roleplay_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roleplay_name: Mapped[str] = mapped_column(String(200), index=True)
    age: Mapped[int | None]
    profession: Mapped[str | None] = mapped_column(String(250))
    personality: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    relationship_description: Mapped[str] = mapped_column(Text, default="")
    preferred_address: Mapped[list[str]] = mapped_column(JSON, default=list)
    background: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="roleplay_profile"
    )
