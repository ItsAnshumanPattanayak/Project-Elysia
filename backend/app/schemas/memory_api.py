from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.memory.schemas import RankedMemory
from app.memory.types import MemorySource, MemoryStatus, MemoryType

Tag = str


class ManualMemoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=4, max_length=1000)
    memory_type: MemoryType
    importance: int = Field(default=70, ge=0, le=100)
    tags: list[Tag] = Field(default_factory=list, max_length=10)
    sensitive: bool = False
    confirm_sensitive: bool = False
    pinned: bool = False
    locked: bool = False
    note: str | None = Field(default=None, max_length=500)


class MemoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str | None = Field(default=None, min_length=4, max_length=1000)
    memory_type: MemoryType | None = None
    importance: int | None = Field(default=None, ge=0, le=100)
    tags: list[Tag] | None = Field(default=None, max_length=10)
    sensitive: bool | None = None
    confirm_sensitive: bool = False
    pinned: bool | None = None
    locked: bool | None = None
    archived: bool | None = None
    force: bool = False
    reason: str | None = Field(default=None, max_length=500)


class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conversation_id: int
    content: str
    memory_type: MemoryType
    importance: int
    confidence: float
    tags: list[str]
    entities: list[str]
    source: MemorySource
    source_user_message_id: int | None
    source_character_message_id: int | None
    status: MemoryStatus
    is_sensitive: bool
    is_pinned: bool
    is_locked: bool
    usage_count: int
    last_used_at: datetime | None
    last_confirmed_at: datetime | None
    supersedes_memory_id: int | None
    superseded_by_memory_id: int | None
    created_at: datetime
    updated_at: datetime


class MemoryDetailResponse(MemoryResponse):
    memory_metadata: dict[str, object]


class MemoryListResponse(BaseModel):
    items: list[MemoryResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class MemorySearchPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    memory_types: list[MemoryType] | None = Field(default=None, max_length=20)
    limit: int = Field(default=8, ge=1, le=30)


class MemorySearchPreviewResponse(BaseModel):
    items: list[RankedMemory]
    total_characters: int


class MemoryRebuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm: bool


class MemoryRebuildResponse(BaseModel):
    before: dict[str, int]
    after: dict[str, int]
    warnings: list[str]
