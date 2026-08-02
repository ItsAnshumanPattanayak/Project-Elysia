from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ReadSchema


class CharacterBase(BaseModel):
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)
    age: int | None = Field(default=None, ge=18)
    profession: str | None = None
    archetype: str | None = None
    description: str = ""
    backstory: str = ""
    personality: dict[str, Any] = Field(default_factory=dict)
    speaking_style: dict[str, Any] = Field(default_factory=dict)
    behaviour_rules: dict[str, Any] = Field(default_factory=dict)
    preferred_language: str = "Hinglish"
    avatar_path: str | None = None
    greeting_message: str = ""
    system_prompt_template: str = ""
    is_active: bool = True


class CharacterCreate(CharacterBase):
    pass


class CharacterUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    age: int | None = Field(default=None, ge=18)
    profession: str | None = None
    description: str | None = None
    is_active: bool | None = None


class CharacterRead(CharacterBase, ReadSchema):
    pass
