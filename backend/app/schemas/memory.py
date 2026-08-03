from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.memory.types import MemorySource, MemoryStatus, MemoryType
from app.schemas.common import ReadSchema


class MemoryBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: int
    memory_type: MemoryType
    content: str = Field(min_length=4, max_length=1000)
    importance: int = Field(default=50, ge=0, le=100)
    confidence: float = Field(default=1.0, ge=0, le=1)
    tags: list[str] = Field(default_factory=list, max_length=10)
    entities: list[str] = Field(default_factory=list, max_length=10)
    source_user_message_id: int | None = None
    source_character_message_id: int | None = None
    source: MemorySource = MemorySource.MANUAL
    status: MemoryStatus = MemoryStatus.ACTIVE
    is_sensitive: bool = False
    is_pinned: bool = False
    is_locked: bool = False
    usage_count: int = Field(default=0, ge=0)
    last_used_at: datetime | None = None


class MemoryCreate(MemoryBase):
    pass


class MemoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str | None = Field(default=None, min_length=4, max_length=1000)
    memory_type: MemoryType | None = None
    importance: int | None = Field(default=None, ge=0, le=100)
    tags: list[str] | None = Field(default=None, max_length=10)
    is_sensitive: bool | None = None
    is_pinned: bool | None = None
    is_locked: bool | None = None
    status: MemoryStatus | None = None


class MemoryRead(MemoryBase, ReadSchema):
    application_key: str
    last_confirmed_at: datetime | None
    supersedes_memory_id: int | None
    superseded_by_memory_id: int | None
