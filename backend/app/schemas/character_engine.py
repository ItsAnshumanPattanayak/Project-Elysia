from pydantic import BaseModel

from app.character_engine.schemas import PromptContext


class CharacterSummary(BaseModel):
    slug: str
    name: str
    display_name: str
    adult: bool
    profession: str
    archetype: str
    description: str


class CharacterProfile(CharacterSummary):
    personality_summary: list[str]
    speaking_style_summary: str
    preferred_language: str
    avatar_path: str | None
    relationship_summary: str


class PromptPreviewRequest(PromptContext):
    pass
