from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ReadSchema


class RelationshipStateBase(BaseModel):
    conversation_id: int
    attraction: int = Field(default=50, ge=0, le=100)
    trust: int = Field(default=50, ge=0, le=100)
    affection: int = Field(default=50, ge=0, le=100)
    respect: int = Field(default=50, ge=0, le=100)
    comfort: int = Field(default=50, ge=0, le=100)
    jealousy: int = Field(default=0, ge=0, le=100)
    anger: int = Field(default=0, ge=0, le=100)
    mood: str = "neutral"
    relationship_stage: str = "committed"
    turn_count: int = Field(default=0, ge=0)
    locked_values: dict[str, Any] = Field(default_factory=dict)


class RelationshipStateCreate(RelationshipStateBase):
    pass


class RelationshipStateUpdate(BaseModel):
    attraction: int | None = Field(default=None, ge=0, le=100)
    trust: int | None = Field(default=None, ge=0, le=100)
    affection: int | None = Field(default=None, ge=0, le=100)
    respect: int | None = Field(default=None, ge=0, le=100)
    comfort: int | None = Field(default=None, ge=0, le=100)
    jealousy: int | None = Field(default=None, ge=0, le=100)
    anger: int | None = Field(default=None, ge=0, le=100)
    mood: str | None = None
    turn_count: int | None = Field(default=None, ge=0)


class RelationshipStateRead(RelationshipStateBase, ReadSchema):
    pass
