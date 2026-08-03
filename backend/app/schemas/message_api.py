from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.ai.schemas import GenerationResult
from app.relationship.schemas import RelationshipApplicationResult
from app.schemas.conversation_api import ConversationSummaryResponse

MessageContent = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)
]
ClientMessageId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]


class GenerationOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, gt=0, le=1)
    top_k: int | None = Field(default=None, ge=1, le=200)
    repeat_penalty: float | None = Field(default=None, ge=0.5, le=2)
    max_output_tokens: int | None = Field(default=None, ge=32, le=4096)
    context_size: int | None = Field(default=None, ge=512, le=131072)
    seed: int | None = Field(default=None, ge=0)


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: MessageContent
    client_message_id: ClientMessageId | None = None
    behaviour_hint: str | None = Field(default=None, max_length=80)
    response_length: Literal["concise", "balanced", "detailed"] | None = None
    language_mode: str | None = Field(default=None, max_length=80)
    generation_overrides: GenerationOverrides = Field(
        default_factory=GenerationOverrides
    )


class RegenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    behaviour_hint: str | None = Field(default=None, max_length=80)
    response_length: Literal["concise", "balanced", "detailed"] | None = None
    language_mode: str | None = Field(default=None, max_length=80)
    generation_overrides: GenerationOverrides = Field(
        default_factory=GenerationOverrides
    )


class EditMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: MessageContent
    confirm_truncate_following_messages: bool = False
    behaviour_hint: str | None = Field(default=None, max_length=80)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender: Literal["user", "character", "system"]
    raw_content: str
    narration: str | None
    dialogue: str | None
    emotion: str | None
    message_metadata: dict[str, Any]
    sequence_number: int
    is_edited: bool
    created_at: datetime
    edited_at: datetime | None


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class SendMessageResponse(BaseModel):
    conversation: ConversationSummaryResponse
    user_message: MessageResponse
    character_message: MessageResponse
    generation: GenerationResult
    relationship: RelationshipApplicationResult | None = None
    warnings: list[str] = Field(default_factory=list)


class RegenerateResponse(BaseModel):
    character_message: MessageResponse
    generation: GenerationResult
    turn_count: int
    relationship: RelationshipApplicationResult | None = None
    warnings: list[str] = Field(default_factory=list)
