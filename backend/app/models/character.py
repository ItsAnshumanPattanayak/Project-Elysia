from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Character(TimestampMixin, Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    display_name: Mapped[str] = mapped_column(String(200))
    age: Mapped[int | None]
    profession: Mapped[str | None] = mapped_column(String(250))
    archetype: Mapped[str | None] = mapped_column(String(250))
    description: Mapped[str] = mapped_column(Text, default="")
    backstory: Mapped[str] = mapped_column(Text, default="")
    personality: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    speaking_style: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    behaviour_rules: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    preferred_language: Mapped[str] = mapped_column(String(50), default="Hinglish")
    avatar_path: Mapped[str | None] = mapped_column(String(500))
    greeting_message: Mapped[str] = mapped_column(Text, default="")
    system_prompt_template: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="character"
    )
