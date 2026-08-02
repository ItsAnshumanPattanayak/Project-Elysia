from pathlib import Path

import pytest

from app.core.config import DEFAULT_DATABASE_PATH, Settings


def test_default_database_path_is_independent_of_working_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = Path.cwd()
    try:
        monkeypatch.delenv("DATABASE_URL")
        monkeypatch.chdir(Path(__file__).resolve().parent)
        settings = Settings(_env_file=None)
        assert str(DEFAULT_DATABASE_PATH.as_posix()) in settings.database_url
    finally:
        monkeypatch.chdir(original)
