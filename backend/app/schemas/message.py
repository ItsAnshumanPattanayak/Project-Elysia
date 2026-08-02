from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.message import MessageSender


class MessageBase(BaseModel):
    conversation_id: int
    sender: MessageSender
    raw_content: str = Field(min_length=1)
    narration: str | None = None
    dialogue: str | None = None
    emotion: str | None = None
    message_metadata: dict[str, Any] = Field(default_factory=dict)
    sequence_number: int = Field(ge=0)


class MessageCreate(MessageBase):
    pass


class MessageUpdate(BaseModel):
    raw_content: str | None = Field(default=None, min_length=1)
    narration: str | None = None
    dialogue: str | None = None
    emotion: str | None = None


class MessageRead(MessageBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_edited: bool
    created_at: datetime
    edited_at: datetime | None
