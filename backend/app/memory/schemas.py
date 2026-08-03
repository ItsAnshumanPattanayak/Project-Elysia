from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.memory.types import MemorySource, MemoryType


class NormalizedCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    normalized_content: str
    memory_type: MemoryType
    importance: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    tags: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    source: MemorySource
    canonical_fact_key: str | None = None
    is_sensitive: bool = False
    reason: str | None = None


class MemoryProcessingResult(BaseModel):
    created: int = 0
    consolidated: int = 0
    superseded: int = 0
    rejected: int = 0
    already_applied: int = 0
    memory_ids: list[int] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MemoryScoreBreakdown(BaseModel):
    lexical: float
    importance: float
    confidence: float
    recency: float
    tag_entity: float
    pinned_type: float
    final_score: float


class RankedMemory(BaseModel):
    id: int
    content: str
    memory_type: MemoryType
    importance: int
    score: MemoryScoreBreakdown
    created_at: datetime


class MemorySelectionResult(BaseModel):
    items: list[RankedMemory]
    selected_ids: list[int]
    total_characters: int
