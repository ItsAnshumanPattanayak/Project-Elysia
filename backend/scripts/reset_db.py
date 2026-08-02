import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402


def resolve_safe_database() -> Path:
    url = get_settings().database_url
    parsed = urlparse(url)
    if parsed.scheme != "sqlite" or not parsed.path:
        raise ValueError("Reset is supported only for a local SQLite database")
    path = Path(unquote(parsed.path.lstrip("/") if parsed.netloc else parsed.path))
    if not path.is_absolute():
        path = (BACKEND_DIR / path).resolve()
    allowed_dir = (BACKEND_DIR / "data").resolve()
    if path.parent.resolve() != allowed_dir or path.suffix != ".db":
        raise ValueError(
            "Refusing to delete a database outside backend/data or without .db"
        )
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset the development database")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive reset")
    args = parser.parse_args()
    if not args.yes:
        print("Refusing reset. Re-run with --yes after reviewing the configured path.")
        return 2
    if get_settings().environment.lower() not in {"development", "test"}:
        print("Refusing reset outside development or test.", file=sys.stderr)
        return 2
    try:
        database = resolve_safe_database()
        print(f"WARNING: deleting local development database {database}")
        database.unlink(missing_ok=True)
        return subprocess.run(
            [sys.executable, str(BACKEND_DIR / "scripts" / "init_db.py")]
        ).returncode
    except Exception as exc:
        print(f"Database reset failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
