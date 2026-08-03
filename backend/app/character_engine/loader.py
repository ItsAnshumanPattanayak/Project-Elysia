import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.character_engine.exceptions import (
    CharacterConfigurationError,
    CharacterNotFoundError,
    RoleplayProfileNotFoundError,
    UnsafeCharacterPathError,
    UnsupportedCharacterSchemaVersionError,
)
from app.character_engine.schemas import CharacterDefinition, RoleplayUserDefinition
from app.core.config import BACKEND_DIR

SAFE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SUPPORTED_SCHEMA_VERSION = "1.0"


class CharacterLoader:
    def __init__(self, character_dir: Path | None = None) -> None:
        self.character_dir = (character_dir or BACKEND_DIR / "characters").resolve()
        self.roleplay_user_dir = (self.character_dir / "roleplay_users").resolve()

    @staticmethod
    def _validate_slug(slug: str) -> None:
        if not SAFE_SLUG.fullmatch(slug):
            raise UnsafeCharacterPathError("The supplied slug is not safe.")

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CharacterConfigurationError(
                "The local configuration is invalid."
            ) from exc
        if not isinstance(value, dict):
            raise CharacterConfigurationError(
                "The local configuration must be an object."
            )
        if value.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
            raise UnsupportedCharacterSchemaVersionError(
                "The local configuration schema version is unsupported."
            )
        return value

    def _safe_path(self, directory: Path, slug: str) -> Path:
        self._validate_slug(slug)
        path = (directory / f"{slug.replace('-', '_')}.json").resolve()
        if path.parent != directory:
            raise UnsafeCharacterPathError(
                "The supplied slug leaves the approved directory."
            )
        return path

    def load_character(self, slug: str) -> CharacterDefinition:
        path = self._safe_path(self.character_dir, slug)
        if not path.is_file():
            raise CharacterNotFoundError(f"Character '{slug}' was not found.")
        try:
            return CharacterDefinition.model_validate(self._read_json(path))
        except ValidationError as exc:
            raise CharacterConfigurationError(
                "The local character configuration failed validation."
            ) from exc

    def load_roleplay_user(self, slug: str) -> RoleplayUserDefinition:
        path = self._safe_path(self.roleplay_user_dir, slug)
        if not path.is_file():
            raise RoleplayProfileNotFoundError(
                f"Roleplay profile '{slug}' was not found."
            )
        try:
            return RoleplayUserDefinition.model_validate(self._read_json(path))
        except ValidationError as exc:
            raise CharacterConfigurationError(
                "The local roleplay profile failed validation."
            ) from exc

    def list_characters(self) -> list[CharacterDefinition]:
        valid: list[CharacterDefinition] = []
        for path in sorted(self.character_dir.glob("*.json")):
            slug = path.stem.replace("_", "-")
            try:
                valid.append(self.load_character(slug))
            except CharacterConfigurationError:
                continue
        return valid
