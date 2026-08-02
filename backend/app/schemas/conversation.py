from pydantic import BaseModel, Field

from app.schemas.common import ReadSchema


class ConversationBase(BaseModel):
    character_id: int
    roleplay_profile_id: int
    title: str = Field(min_length=1, max_length=250)
    summary: str = ""
    current_scene: str = ""
    relationship_stage: str = "committed"
    is_active: bool = True
    is_archived: bool = False


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=250)
    summary: str | None = None
    current_scene: str | None = None
    relationship_stage: str | None = None
    is_active: bool | None = None
    is_archived: bool | None = None


class ConversationRead(ConversationBase, ReadSchema):
    pass
