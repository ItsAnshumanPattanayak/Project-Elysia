from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    character_slug: str = Field(
        default="zara-mirza", pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    roleplay_user_slug: str = Field(
        default="anshuman", pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    title: str | None = Field(default=None, min_length=1, max_length=250)
    current_scene: str = Field(default="", max_length=2000)
    relationship_stage: str = Field(default="committed", min_length=1, max_length=100)


class ConversationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=250)
    current_scene: str | None = Field(default=None, max_length=2000)
    relationship_stage: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None
    is_archived: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> "ConversationUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("at least one update field is required")
        return self


class CharacterReference(BaseModel):
    id: int
    slug: str
    display_name: str


class RoleplayProfileReference(BaseModel):
    id: int
    roleplay_name: str


class RelationshipSnapshot(BaseModel):
    attraction: int
    trust: int
    affection: int
    respect: int
    comfort: int
    jealousy: int
    anger: int
    mood: str
    relationship_stage: str
    turn_count: int


class MessagePreview(BaseModel):
    id: int
    sender: Literal["user", "character", "system"]
    raw_content: str
    sequence_number: int
    created_at: datetime


class ConversationSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    character: CharacterReference
    roleplay_user: RoleplayProfileReference
    current_scene: str
    relationship_stage: str
    is_active: bool
    is_archived: bool
    message_count: int
    turn_count: int
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None


class ConversationDetailResponse(ConversationSummaryResponse):
    relationship_state: RelationshipSnapshot
    recent_messages: list[MessagePreview] = Field(default_factory=list)


class ConversationListResponse(BaseModel):
    items: list[ConversationSummaryResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
