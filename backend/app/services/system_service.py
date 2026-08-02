from sqlalchemy import text
from sqlalchemy.orm import Session


def database_is_connected(session: Session) -> bool:
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        return False
    return True
