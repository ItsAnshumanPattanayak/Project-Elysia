from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RelationshipEventType(str, Enum):
    SUPPORTIVE = "supportive"
    AFFECTIONATE = "affectionate"
    ROMANTIC = "romantic"
    RESPECTFUL = "respectful"
    PROTECTIVE = "protective"
    HONEST = "honest"
    VULNERABLE = "vulnerable"
    APOLOGETIC = "apologetic"
    REASSURING = "reassuring"
    HUMOROUS = "humorous"
    THOUGHTFUL = "thoughtful"
    PROMISE_KEPT = "promise_kept"
    CONFLICT_RESOLVED = "conflict_resolved"
    NEUTRAL = "neutral"
    INFORMATIONAL = "informational"
    BUSINESS = "business"
    PLAYFUL = "playful"
    TEASING = "teasing"
    CONCERNED = "concerned"
    BOUNDARY_SETTING = "boundary_setting"
    CLARIFICATION = "clarification"
    RUDE = "rude"
    DISMISSIVE = "dismissive"
    DISHONEST = "dishonest"
    MANIPULATIVE = "manipulative"
    JEALOUS = "jealous"
    INSENSITIVE = "insensitive"
    THREATENING = "threatening"
    PROMISE_BROKEN = "promise_broken"
    DISRESPECTFUL = "disrespectful"
    TRUST_BREACH = "trust_breach"
    CONFLICT_ESCALATED = "conflict_escalated"
    EMOTIONALLY_DISTANT = "emotionally_distant"


class EventSource(str, Enum):
    DETERMINISTIC = "deterministic"
    MODEL_SUGGESTED_VALIDATED = "model_suggested_validated"
    MANUAL = "manual"
    SYSTEM_RECALCULATION = "system_recalculation"


class EventIntensity(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class Mood(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    AFFECTIONATE = "affectionate"
    ROMANTIC = "romantic"
    PLAYFUL = "playful"
    CONCERNED = "concerned"
    PROTECTIVE = "protective"
    JEALOUS = "jealous"
    ANGRY = "angry"
    HURT = "hurt"
    SUSPICIOUS = "suspicious"
    COLD = "cold"
    EXCITED = "excited"
    EMBARRASSED = "embarrassed"
    RELIEVED = "relieved"


class RelationshipStage(str, Enum):
    STRANGERS = "strangers"
    ACQUAINTANCES = "acquaintances"
    FRIENDS = "friends"
    CLOSE_FRIENDS = "close_friends"
    INTERESTED = "interested"
    DATING = "dating"
    COMMITTED = "committed"
    DEEPLY_BONDED = "deeply_bonded"
    STRAINED = "strained"
    SEPARATED = "separated"


SCORE_FIELDS = (
    "attraction",
    "trust",
    "affection",
    "respect",
    "comfort",
    "jealousy",
    "anger",
)
LOCKABLE_FIELDS = (*SCORE_FIELDS, "mood", "relationship_stage")


class EventEvidence(BaseModel):
    kind: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=300)


class ResolvedRelationshipEvent(BaseModel):
    event_type: RelationshipEventType
    source: EventSource
    confidence: float = Field(ge=0, le=1)
    evidence: list[EventEvidence] = Field(default_factory=list, max_length=10)
    intensity: EventIntensity = EventIntensity.NORMAL
    model_suggestion: str | None = Field(default=None, max_length=100)
    resolver_version: str = "1.0"


class RelationshipValues(BaseModel):
    attraction: int = Field(ge=0, le=100)
    trust: int = Field(ge=0, le=100)
    affection: int = Field(ge=0, le=100)
    respect: int = Field(ge=0, le=100)
    comfort: int = Field(ge=0, le=100)
    jealousy: int = Field(ge=0, le=100)
    anger: int = Field(ge=0, le=100)


class RelationshipApplicationResult(BaseModel):
    event_id: int
    event_type: RelationshipEventType
    source: EventSource
    confidence: float
    score_deltas: dict[str, int]
    suppressed_by_locks: list[str]
    values_before: RelationshipValues
    values_after: RelationshipValues
    mood_before: Mood
    mood_after: Mood
    stage_before: RelationshipStage
    stage_after: RelationshipStage
    application_key: str
    already_applied: bool = False


class RelationshipStateResponse(RelationshipValues):
    conversation_id: int
    mood: Mood
    relationship_stage: RelationshipStage
    turn_count: int
    locked_values: dict[str, bool]
    baseline_values: dict[str, Any]


class RelationshipEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    source_user_message_id: int | None
    source_character_message_id: int | None
    event_type: RelationshipEventType
    source: EventSource
    confidence: float
    evidence: list[dict[str, Any]]
    score_deltas: dict[str, int]
    values_before: dict[str, Any]
    values_after: dict[str, Any]
    mood_before: Mood
    mood_after: Mood
    stage_before: RelationshipStage
    stage_after: RelationshipStage
    application_key: str
    is_reverted: bool
    reverted_at: datetime | None
    created_at: datetime


class RelationshipEventListResponse(BaseModel):
    items: list[RelationshipEventResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class ManualRelationshipUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attraction: int | None = Field(default=None, ge=0, le=100)
    trust: int | None = Field(default=None, ge=0, le=100)
    affection: int | None = Field(default=None, ge=0, le=100)
    respect: int | None = Field(default=None, ge=0, le=100)
    comfort: int | None = Field(default=None, ge=0, le=100)
    jealousy: int | None = Field(default=None, ge=0, le=100)
    anger: int | None = Field(default=None, ge=0, le=100)
    mood: Mood | None = None
    relationship_stage: RelationshipStage | None = None
    locked_values: dict[
        Literal[
            "attraction",
            "trust",
            "affection",
            "respect",
            "comfort",
            "jealousy",
            "anger",
            "mood",
            "relationship_stage",
        ],
        bool,
    ] = Field(default_factory=dict)
    force: bool = False
    reason: str = Field(min_length=1, max_length=500)
