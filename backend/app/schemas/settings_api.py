from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

SettingValue = str | int | float | bool | None


class SettingDefinition(BaseModel):
    key: str
    label: str
    category: str
    value_type: Literal["string", "integer", "number", "boolean", "enum", "model"]
    default: SettingValue
    minimum: float | None = None
    maximum: float | None = None
    allowed_values: list[str] | None = None
    restart_required: bool = False
    description: str


class SafeSetting(BaseModel):
    key: str
    value: SettingValue
    category: str
    is_default: bool
    restart_required: bool


class SettingsResponse(BaseModel):
    items: list[SafeSetting]
    schema_version: Literal[1] = 1


class SettingsSchemaResponse(BaseModel):
    items: list[SettingDefinition]
    schema_version: Literal[1] = 1


class SettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: dict[str, SettingValue] = Field(min_length=1, max_length=20)


class SettingsResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keys: list[str] | None = Field(default=None, max_length=20)
    category: Annotated[str | None, Field(max_length=50)] = None
    all: bool = False


class SettingsMutationResponse(SettingsResponse):
    changed: list[str]
    restart_required: list[str]
