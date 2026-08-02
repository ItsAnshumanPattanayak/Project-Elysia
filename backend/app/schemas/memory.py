from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ReadSchema


class MemoryBase(BaseModel):
    conversation_id: int
    memory_type: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    importance: int = Field(default=3, ge=1, le=5)
    emotional_value: int = Field(default=0, ge=-100, le=100)
    tags: list[str] = Field(default_factory=list)
    source_message_id: int | None = None
    is_permanent: bool = False
    is_active: bool = True
    last_recalled_at: datetime | None = None


class MemoryCreate(MemoryBase):
    pass


class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    importance: int | None = Field(default=None, ge=1, le=5)
    emotional_value: int | None = Field(default=None, ge=-100, le=100)
    tags: list[str] | None = None
    is_permanent: bool | None = None
    is_active: bool | None = None


class MemoryRead(MemoryBase, ReadSchema):
    pass
