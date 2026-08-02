import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.seed import seed_database  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def main() -> int:
    try:
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            check=True,
        )
        with SessionLocal() as session:
            result = seed_database(session)
        print(f"Database ready: {result}")
    except Exception as exc:
        print(f"Database initialization failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
