from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


def create_database_engine(database_url: str) -> Engine:
    args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine_args: dict[str, Any] = {"connect_args": args}
    if database_url in {"sqlite://", "sqlite:///:memory:"}:
        engine_args["poolclass"] = StaticPool
    database_engine = create_engine(database_url, **engine_args)
    if database_url.startswith("sqlite"):

        @event.listens_for(database_engine, "connect")
        def enable_foreign_keys(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return database_engine


engine = create_database_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
