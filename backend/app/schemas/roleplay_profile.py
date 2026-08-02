from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ReadSchema


class RoleplayProfileBase(BaseModel):
    roleplay_name: str = Field(min_length=1, max_length=200)
    age: int | None = Field(default=None, ge=18)
    profession: str | None = None
    personality: dict[str, Any] = Field(default_factory=dict)
    relationship_description: str = ""
    preferred_address: list[str] = Field(default_factory=list)
    background: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class RoleplayProfileCreate(RoleplayProfileBase):
    pass


class RoleplayProfileUpdate(BaseModel):
    roleplay_name: str | None = Field(default=None, min_length=1)
    age: int | None = Field(default=None, ge=18)
    profession: str | None = None
    personality: dict[str, Any] | None = None
    is_active: bool | None = None


class RoleplayProfileRead(RoleplayProfileBase, ReadSchema):
    pass
