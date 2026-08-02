from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ReadSchema


class ApplicationSettingBase(BaseModel):
    key: str = Field(min_length=1, max_length=150)
    value: Any
    category: str = "general"
    description: str = ""


class ApplicationSettingCreate(ApplicationSettingBase):
    pass


class ApplicationSettingUpdate(BaseModel):
    value: Any | None = None
    category: str | None = None
    description: str | None = None


class ApplicationSettingRead(ApplicationSettingBase, ReadSchema):
    pass
