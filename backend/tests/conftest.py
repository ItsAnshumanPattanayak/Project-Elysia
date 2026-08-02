import os
from collections.abc import Generator

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app import models  # noqa: F401
from app.db.base import Base
from app.db.session import create_database_engine, get_db
from app.main import create_app


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    test_engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    with factory() as session:
        yield session
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    application = create_app()

    def override_db() -> Generator[Session, None, None]:
        yield db_session

    application.dependency_overrides[get_db] = override_db
    with TestClient(application) as test_client:
        yield test_client
