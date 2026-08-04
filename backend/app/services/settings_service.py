from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import ApplicationSetting
from app.schemas.settings_api import (
    SafeSetting,
    SettingDefinition,
    SettingsMutationResponse,
    SettingsResetRequest,
    SettingsResponse,
    SettingsSchemaResponse,
    SettingsUpdateRequest,
    SettingValue,
)


class SettingsApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class Definition:
    label: str
    category: str
    value_type: Literal["string", "integer", "number", "boolean", "enum", "model"]
    default_attr: str | None
    fallback: SettingValue
    description: str
    minimum: float | None = None
    maximum: float | None = None
    allowed_values: tuple[str, ...] | None = None
    restart_required: bool = False


DEFINITIONS: dict[str, Definition] = {
    "selected_model": Definition(
        "Installed model",
        "ai",
        "model",
        "ollama_model",
        None,
        "The installed local Ollama model used for chat.",
    ),
    "temperature": Definition(
        "Temperature",
        "ai",
        "number",
        "ollama_temperature",
        0.8,
        "Controls response variation.",
        0,
        2,
    ),
    "top_p": Definition(
        "Top-p",
        "ai",
        "number",
        "ollama_top_p",
        0.9,
        "Limits nucleus sampling.",
        0.01,
        1,
    ),
    "top_k": Definition(
        "Top-k", "ai", "integer", "ollama_top_k", 40, "Limits token candidates.", 1, 200
    ),
    "repeat_penalty": Definition(
        "Repeat penalty",
        "ai",
        "number",
        "ollama_repeat_penalty",
        1.1,
        "Discourages repeated text.",
        0.5,
        2,
    ),
    "context_size": Definition(
        "Context size",
        "ai",
        "integer",
        "ollama_context_size",
        4096,
        "Maximum local context window.",
        512,
        131072,
    ),
    "max_output_tokens": Definition(
        "Output token limit",
        "ai",
        "integer",
        "ollama_max_output_tokens",
        700,
        "Maximum generated tokens.",
        32,
        4096,
    ),
    "response_length": Definition(
        "Response length",
        "chat",
        "enum",
        None,
        "balanced",
        "Default response length preference.",
        allowed_values=("concise", "balanced", "detailed"),
    ),
    "relationship_engine_enabled": Definition(
        "Relationship processing",
        "relationship",
        "boolean",
        None,
        True,
        "Enable deterministic relationship processing.",
    ),
    "auto_memory_enabled": Definition(
        "Automatic memories",
        "memory",
        "boolean",
        None,
        True,
        "Enable automatic long-term memory extraction.",
    ),
}


class SettingsService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def _default(self, key: str) -> SettingValue:
        definition = DEFINITIONS[key]
        value = (
            getattr(self.settings, definition.default_attr)
            if definition.default_attr
            else definition.fallback
        )
        if key == "selected_model" and value == "":
            return None
        return value

    def _rows(self) -> dict[str, ApplicationSetting]:
        rows = self.session.scalars(
            select(ApplicationSetting).where(ApplicationSetting.key.in_(DEFINITIONS))
        )
        return {row.key: row for row in rows}

    def _validate(
        self, key: str, value: SettingValue, installed_models: set[str] | None
    ) -> SettingValue:
        definition = DEFINITIONS.get(key)
        if definition is None:
            raise SettingsApiError(
                "unsafe_setting_key", f"Setting '{key}' is not editable."
            )
        if definition.value_type == "boolean":
            if type(value) is not bool:
                raise SettingsApiError(
                    "invalid_setting_value", f"Setting '{key}' must be a boolean."
                )
        elif definition.value_type == "integer":
            if type(value) is not int:
                raise SettingsApiError(
                    "invalid_setting_value", f"Setting '{key}' must be an integer."
                )
        elif definition.value_type == "number":
            if not isinstance(value, int | float) or isinstance(value, bool):
                raise SettingsApiError(
                    "invalid_setting_value", f"Setting '{key}' must be numeric."
                )
            value = float(value)
        elif definition.value_type == "enum":
            if not isinstance(value, str) or value not in (
                definition.allowed_values or ()
            ):
                raise SettingsApiError(
                    "invalid_setting_value",
                    f"Setting '{key}' has an unsupported value.",
                )
        elif definition.value_type == "model":
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise SettingsApiError(
                    "invalid_setting_value",
                    "The selected model must be an installed model name or null.",
                )
            if (
                value is not None
                and installed_models is not None
                and value not in installed_models
            ):
                raise SettingsApiError(
                    "model_not_installed",
                    "Only a model reported by local Ollama can be selected.",
                )
        if isinstance(value, int | float) and type(value) is not bool:
            if definition.minimum is not None and value < definition.minimum:
                raise SettingsApiError(
                    "invalid_setting_value",
                    f"Setting '{key}' is below its safe minimum.",
                )
            if definition.maximum is not None and value > definition.maximum:
                raise SettingsApiError(
                    "invalid_setting_value",
                    f"Setting '{key}' exceeds its safe maximum.",
                )
        return value

    def schema(self) -> SettingsSchemaResponse:
        return SettingsSchemaResponse(
            items=[
                SettingDefinition(
                    key=key,
                    label=item.label,
                    category=item.category,
                    value_type=item.value_type,
                    default=self._default(key),
                    minimum=item.minimum,
                    maximum=item.maximum,
                    allowed_values=(
                        list(item.allowed_values) if item.allowed_values else None
                    ),
                    restart_required=item.restart_required,
                    description=item.description,
                )
                for key, item in DEFINITIONS.items()
            ]
        )

    def get(self) -> SettingsResponse:
        rows = self._rows()
        return SettingsResponse(
            items=[
                SafeSetting(
                    key=key,
                    value=rows[key].value if key in rows else self._default(key),
                    category=definition.category,
                    is_default=key not in rows or rows[key].value == self._default(key),
                    restart_required=definition.restart_required,
                )
                for key, definition in DEFINITIONS.items()
            ]
        )

    def update(
        self, payload: SettingsUpdateRequest, installed_models: set[str] | None = None
    ) -> SettingsMutationResponse:
        rows = self._rows()
        changed: list[str] = []
        for key, incoming in payload.values.items():
            value = self._validate(key, incoming, installed_models)
            row = rows.get(key)
            if row is None:
                definition = DEFINITIONS[key]
                row = ApplicationSetting(
                    key=key,
                    value=value,
                    category=definition.category,
                    description=definition.description,
                )
                self.session.add(row)
                rows[key] = row
            else:
                row.value = value
            changed.append(key)
        self.session.commit()
        current = self.get()
        return SettingsMutationResponse(
            **current.model_dump(),
            changed=changed,
            restart_required=[
                key for key in changed if DEFINITIONS[key].restart_required
            ],
        )

    def reset(self, payload: SettingsResetRequest) -> SettingsMutationResponse:
        selectors = sum(
            (payload.keys is not None, payload.category is not None, payload.all)
        )
        if selectors != 1:
            raise SettingsApiError(
                "invalid_reset_request",
                "Choose keys, one category, or all safe settings.",
            )
        if payload.keys is not None:
            unknown = sorted(set(payload.keys) - DEFINITIONS.keys())
            if unknown:
                raise SettingsApiError(
                    "unsafe_setting_key", f"Setting '{unknown[0]}' is not resettable."
                )
            selected = set(payload.keys)
        elif payload.category is not None:
            selected = {
                key
                for key, item in DEFINITIONS.items()
                if item.category == payload.category
            }
            if not selected:
                raise SettingsApiError(
                    "invalid_setting_category",
                    "The settings category is not resettable.",
                )
        else:
            selected = set(DEFINITIONS)
        rows = self._rows()
        for key in selected:
            row = rows.get(key)
            if row is not None:
                self.session.delete(row)
        self.session.commit()
        current = self.get()
        return SettingsMutationResponse(
            **current.model_dump(),
            changed=sorted(selected),
            restart_required=[
                key for key in sorted(selected) if DEFINITIONS[key].restart_required
            ],
        )

    def generation_overrides(self) -> dict[str, SettingValue]:
        current = {item.key: item.value for item in self.get().items}
        return {
            key: current[key]
            for key in (
                "temperature",
                "top_p",
                "top_k",
                "repeat_penalty",
                "context_size",
                "max_output_tokens",
            )
        }
