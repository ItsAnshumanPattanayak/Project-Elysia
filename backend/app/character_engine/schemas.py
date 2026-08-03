from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
]
Slug = Annotated[
    str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
]


class Identity(BaseModel):
    name: ShortText
    display_name: ShortText
    adult: Literal[True]
    age: int = Field(ge=18, le=120)
    pronouns: ShortText
    profession: ShortText
    company: ShortText
    archetype: ShortText
    fictional_status: Literal[True]
    short_description: Text
    backstory: Text


class Appearance(BaseModel):
    summary: Text
    hair: ShortText
    eyes: ShortText
    clothing_style: Text
    distinguishing_features: Text
    avatar_path: str | None = Field(default=None, max_length=300)


class Personality(BaseModel):
    core_traits: list[ShortText] = Field(min_length=3, max_length=16)
    positive_traits: list[ShortText] = Field(min_length=1, max_length=16)
    flaws: list[ShortText] = Field(min_length=1, max_length=12)
    values: list[ShortText] = Field(min_length=1, max_length=16)
    likes: list[ShortText] = Field(min_length=1, max_length=20)
    dislikes: list[ShortText] = Field(min_length=1, max_length=20)
    fears: list[ShortText] = Field(min_length=1, max_length=12)
    ambitions: list[ShortText] = Field(min_length=1, max_length=12)
    emotional_tendencies: list[ShortText] = Field(min_length=1, max_length=16)


class SpeakingStyle(BaseModel):
    primary_language: ShortText
    secondary_language: ShortText
    language_mode: ShortText
    tone: Text
    business_tone: Text
    private_tone: Text
    vocabulary: list[ShortText] = Field(min_length=1, max_length=20)
    uses_narration: bool
    narration_perspective: ShortText
    dialogue_prefix: ShortText
    preferred_response_length: Literal["concise", "balanced", "detailed"]
    hinglish_rules: list[Text] = Field(min_length=1, max_length=12)
    forbidden_phrases: list[ShortText] = Field(min_length=1, max_length=20)


class RelationshipContext(BaseModel):
    relationship_type: ShortText
    relationship_stage: ShortText
    established_history: list[Text] = Field(min_length=1, max_length=12)
    preferred_forms_of_address: list[ShortText] = Field(min_length=1, max_length=12)
    emotional_baseline: Text
    boundaries: list[Text] = Field(min_length=1, max_length=20)


class BehaviourRule(BaseModel):
    trigger_description: Text
    desired_tone: Text
    instructions: list[Text] = Field(min_length=1, max_length=12)
    prohibited_reactions: list[Text] = Field(min_length=1, max_length=12)


class ResponsePreferences(BaseModel):
    narration_enabled: bool = True
    dialogue_enabled: bool = True
    default_length: Literal["concise", "balanced", "detailed"] = "balanced"
    max_paragraphs: int = Field(default=5, ge=1, le=12)


class CharacterDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    slug: Slug
    identity: Identity
    appearance: Appearance
    personality: Personality
    speaking_style: SpeakingStyle
    relationship: RelationshipContext
    behaviour_rules: dict[str, BehaviourRule] = Field(min_length=3, max_length=20)
    consistency_rules: list[Text] = Field(min_length=6, max_length=24)
    safety_rules: list[Text] = Field(min_length=4, max_length=24)
    response_preferences: ResponsePreferences

    @model_validator(mode="after")
    def ensure_character_requirements(self) -> "CharacterDefinition":
        required = {"normal", "romantic", "professional", "concern", "anger"}
        if not required.issubset(self.behaviour_rules):
            raise ValueError("required behaviour rules are missing")
        return self


class RoleplayUserIdentity(BaseModel):
    roleplay_name: ShortText
    adult: Literal[True]
    age: int = Field(ge=18, le=120)
    fictional_status: Literal[True]
    authentication_data: Literal[False]
    profession: Text
    pronouns: ShortText


class RoleplayUserPersonality(BaseModel):
    traits: list[Text] = Field(min_length=1, max_length=16)
    communication_style: Text


class RoleplayUserRelationship(BaseModel):
    relationship_to_character: Text
    preferred_forms_of_address: list[ShortText] = Field(min_length=1, max_length=12)
    shared_history: list[Text] = Field(min_length=1, max_length=20)
    boundaries: list[Text] = Field(min_length=1, max_length=20)


class RoleplayUserPreferences(BaseModel):
    language_mode: ShortText
    response_length: Literal["concise", "balanced", "detailed"]
    narration: bool
    notes: list[Text] = Field(default_factory=list, max_length=20)


class RoleplayUserDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    slug: Slug
    identity: RoleplayUserIdentity
    personality: RoleplayUserPersonality
    relationship_context: RoleplayUserRelationship
    preferences: RoleplayUserPreferences
    editable_facts: dict[str, Text] = Field(default_factory=dict, max_length=30)


class MessageRole(str, Enum):
    USER = "user"
    CHARACTER = "character"
    SYSTEM = "system"


class PromptMessage(BaseModel):
    role: MessageRole
    content: str = Field(min_length=1, max_length=4000)


class MemoryContext(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    memory_type: str = Field(min_length=1, max_length=80)
    importance: int = Field(ge=1, le=5)


class RelationshipValues(BaseModel):
    attraction: int | None = Field(default=None, ge=0, le=100)
    trust: int | None = Field(default=None, ge=0, le=100)
    affection: int | None = Field(default=None, ge=0, le=100)
    respect: int | None = Field(default=None, ge=0, le=100)
    comfort: int | None = Field(default=None, ge=0, le=100)
    jealousy: int | None = Field(default=None, ge=0, le=100)
    anger: int | None = Field(default=None, ge=0, le=100)


class PromptContext(BaseModel):
    character_slug: Slug = "zara-mirza"
    roleplay_user_slug: Slug = "anshuman"
    conversation_id: int | None = Field(default=None, ge=1)
    current_scene: str | None = Field(default=None, max_length=2000)
    relationship_stage: str | None = Field(default=None, max_length=100)
    relationship_values: RelationshipValues | None = None
    recent_messages: list[PromptMessage] = Field(default_factory=list, max_length=30)
    relevant_memories: list[MemoryContext] = Field(default_factory=list, max_length=10)
    conversation_summary: str | None = Field(default=None, max_length=3000)
    behaviour_hint: str | None = Field(default=None, max_length=80)
    response_length: Literal["concise", "balanced", "detailed"] | None = None
    language_mode: str | None = Field(default=None, max_length=80)


class GenerationOptions(BaseModel):
    temperature: float = Field(default=0.8, ge=0, le=2)
    top_p: float = Field(default=0.9, gt=0, le=1)
    top_k: int = Field(default=40, ge=1, le=200)
    repeat_penalty: float = Field(default=1.1, ge=0.5, le=2)
    max_output_tokens: int = Field(default=700, ge=32, le=4096)
    context_size: int = Field(default=4096, ge=512, le=131072)
    seed: int | None = Field(default=None, ge=0)


class PromptPackage(BaseModel):
    system_prompt: str
    conversation_messages: list[PromptMessage]
    generation_options: GenerationOptions
    character_slug: str
    roleplay_user_slug: str
    applied_behaviour_hint: str
    metadata: dict[str, Any]
