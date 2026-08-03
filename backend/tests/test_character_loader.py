import json
from pathlib import Path
from typing import Any

import pytest

from app.character_engine.exceptions import (
    CharacterConfigurationError,
    CharacterNotFoundError,
    UnsafeCharacterPathError,
    UnsupportedCharacterSchemaVersionError,
)
from app.character_engine.loader import CharacterLoader
from app.core.config import BACKEND_DIR


def source_json(name: str) -> dict[str, Any]:
    return json.loads((BACKEND_DIR / "characters" / name).read_text(encoding="utf-8"))


def write_config(directory: Path, name: str, value: object) -> None:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_valid_character_and_roleplay_user_load() -> None:
    loader = CharacterLoader()
    assert loader.load_character("zara-mirza").identity.name == "Zara Mirza"
    profile = loader.load_roleplay_user("anshuman")
    assert profile.identity.fictional_status is True
    assert profile.identity.authentication_data is False


@pytest.mark.parametrize("slug", ["../zara", "zara_mirza", "Zara", "zara/mirza", ".."])
def test_unsafe_slug_and_traversal_rejected(slug: str) -> None:
    with pytest.raises(UnsafeCharacterPathError):
        CharacterLoader().load_character(slug)


def test_missing_character() -> None:
    with pytest.raises(CharacterNotFoundError):
        CharacterLoader().load_character("missing")


def test_unsupported_schema_version(tmp_path: Path) -> None:
    value = source_json("zara_mirza.json")
    value["schema_version"] = "99.0"
    write_config(tmp_path, "zara_mirza.json", value)
    with pytest.raises(UnsupportedCharacterSchemaVersionError):
        CharacterLoader(tmp_path).load_character("zara-mirza")


@pytest.mark.parametrize(
    ("filename", "path", "value"),
    [
        ("zara_mirza.json", ("identity", "age"), 17),
        ("zara_mirza.json", ("identity", "name"), ""),
        ("roleplay_users/anshuman.json", ("identity", "age"), 17),
    ],
)
def test_invalid_identity_values(
    tmp_path: Path, filename: str, path: tuple[str, str], value: object
) -> None:
    source_name = (
        "zara_mirza.json" if "zara" in filename else "roleplay_users/anshuman.json"
    )
    data = source_json(source_name)
    section = data[path[0]]
    assert isinstance(section, dict)
    section[path[1]] = value
    write_config(tmp_path, filename, data)
    loader = CharacterLoader(tmp_path)
    with pytest.raises(CharacterConfigurationError):
        if "roleplay_users" in filename:
            loader.load_roleplay_user("anshuman")
        else:
            loader.load_character("zara-mirza")


def test_invalid_json_and_listing_excludes_it(tmp_path: Path) -> None:
    write_config(tmp_path, "zara_mirza.json", source_json("zara_mirza.json"))
    (tmp_path / "broken.json").write_text("{broken", encoding="utf-8")
    assert [item.slug for item in CharacterLoader(tmp_path).list_characters()] == [
        "zara-mirza"
    ]
    with pytest.raises(CharacterConfigurationError):
        CharacterLoader(tmp_path).load_character("broken")


def test_loading_is_shell_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(BACKEND_DIR / "tests")
    assert CharacterLoader().load_character("zara-mirza").slug == "zara-mirza"
