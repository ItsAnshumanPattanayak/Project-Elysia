from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.character_engine.schemas import PromptContext, PromptPackage
from app.relationship.schemas import Mood, RelationshipEventType

BoundedBlock = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]


class MemoryCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=1000)
    memory_type: str = Field(default="candidate", min_length=1, max_length=80)
    importance: int = Field(default=50, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    tags: list[Annotated[str, StringConstraints(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=12
    )
    entities: list[Annotated[str, StringConstraints(min_length=1, max_length=80)]] = (
        Field(default_factory=list, max_length=12)
    )
    reason: str | None = Field(default=None, max_length=250)
    is_sensitive: bool = False
    permanence: Literal["temporary", "long_term", "permanent"] | None = None


class StructuredRoleplayResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    narration_blocks: list[BoundedBlock] = Field(default_factory=list, max_length=12)
    dialogue_blocks: list[BoundedBlock] = Field(default_factory=list, max_length=12)
    emotion: Mood | None = None
    original_emotion: str | None = Field(default=None, max_length=80)
    relationship_event: RelationshipEventType | None = None
    model_relationship_suggestion: str | None = Field(default=None, max_length=100)
    memory_candidates: list[MemoryCandidate] = Field(default_factory=list, max_length=8)
    raw_text: str = Field(default="", max_length=20000)


class ParserDiagnostics(BaseModel):
    parse_status: Literal["structured", "repaired", "plain_text_fallback"]
    parser_version: str = "2.0"
    repair_attempted: bool = False
    repair_actions: list[str] = Field(default_factory=list, max_length=10)
    schema_valid: bool = False
    fallback_used: bool = False
    warnings: list[str] = Field(default_factory=list, max_length=10)


class AIModelDetails(BaseModel):
    family: str | None = None
    parameter_size: str | None = None
    quantization_level: str | None = None
    format: str | None = None
    context_length: int | None = None


class AIModelInfo(BaseModel):
    name: str
    modified_at: datetime | None = None
    size: int = Field(ge=0)
    digest: str = ""
    details: AIModelDetails = Field(default_factory=AIModelDetails)
    is_configured: bool = False


AIState = Literal["ready", "unavailable", "model_not_configured", "model_not_installed"]


class AIProviderStatus(BaseModel):
    provider: str
    available: bool
    state: AIState
    version: str | None = None
    configured_model: str | None = None
    model_ready: bool
    base_url: str
    error_code: str | None = None
    message: str


class GenerationRequest(BaseModel):
    context: PromptContext
    model: str | None = Field(default=None, max_length=200)
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, gt=0, le=1)
    top_k: int | None = Field(default=None, ge=1, le=200)
    repeat_penalty: float | None = Field(default=None, ge=0.5, le=2)
    max_output_tokens: int | None = Field(default=None, ge=32, le=4096)
    context_size: int | None = Field(default=None, ge=512, le=131072)
    seed: int | None = Field(default=None, ge=0)


class GenerationResult(BaseModel):
    provider: str
    model: str
    text: str
    parsed_response: StructuredRoleplayResponse
    parse_status: Literal["structured", "repaired", "plain_text_fallback"]
    parser_diagnostics: ParserDiagnostics | None = None
    done: bool
    finish_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StreamEvent(BaseModel):
    event: Literal[
        "accepted",
        "user_message",
        "start",
        "token",
        "metadata",
        "completed",
        "error",
        "cancelled",
    ]
    data: dict[str, Any]


class PromptPreview(BaseModel):
    character_slug: str
    roleplay_user_slug: str
    system_prompt: str
    conversation_messages: list[dict[str, str]]
    generation_options: dict[str, Any]
    applied_behaviour_hint: str
    warnings: list[str]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False


class ErrorResponse(BaseModel):
    error: ErrorBody


class ProviderGenerationInput(BaseModel):
    prompt_package: PromptPackage
    model: str
