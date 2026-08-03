from enum import Enum


class MemoryType(str, Enum):
    USER_FACT = "user_fact"
    USER_PREFERENCE = "user_preference"
    USER_DISLIKE = "user_dislike"
    USER_GOAL = "user_goal"
    USER_HABIT = "user_habit"
    USER_BOUNDARY = "user_boundary"
    USER_RELATIONSHIP_FACT = "user_relationship_fact"
    SHARED_EXPERIENCE = "shared_experience"
    PROMISE = "promise"
    COMMITMENT = "commitment"
    CONFLICT = "conflict"
    RECONCILIATION = "reconciliation"
    EMOTIONAL_MOMENT = "emotional_moment"
    CHARACTER_FACT = "character_fact"
    SCENE_FACT = "scene_fact"
    STORY_FACT = "story_fact"
    IMPORTANT_QUOTE = "important_quote"
    RECURRING_TOPIC = "recurring_topic"
    PRIVATE_NOTE = "private_note"


class MemorySource(str, Enum):
    MODEL_CANDIDATE = "model_candidate"
    DETERMINISTIC_USER_FACT = "deterministic_user_fact"
    MANUAL = "manual"
    CONSOLIDATION = "consolidation"
    SYSTEM_REBUILD = "system_rebuild"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"
    REVERTED = "reverted"
