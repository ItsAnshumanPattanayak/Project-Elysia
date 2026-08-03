import os
from collections.abc import AsyncIterator, Generator

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app import models  # noqa: F401
from app.ai.exceptions import OllamaStreamInterruptedError
from app.ai.parser import parse_roleplay_response
from app.ai.schemas import (
    AIModelDetails,
    AIModelInfo,
    AIProviderStatus,
    AIState,
    GenerationResult,
    StreamEvent,
)
from app.character_engine.schemas import PromptPackage
from app.core.config import Settings
from app.db.base import Base
from app.db.session import create_database_engine, get_db
from app.main import create_app
from app.services.ai_service import AIService, get_ai_service


class FakeProvider:
    def __init__(self) -> None:
        self.state: AIState = "ready"
        self.generate_calls = 0
        self.stream_error = False

    async def aclose(self) -> None:
        return None

    async def status(self, force_refresh: bool = False) -> AIProviderStatus:
        del force_refresh
        ready = self.state == "ready"
        return AIProviderStatus(
            provider="ollama",
            available=self.state != "unavailable",
            state=self.state,
            version="0.test" if self.state != "unavailable" else None,
            configured_model=(
                "test-model" if self.state != "model_not_configured" else None
            ),
            model_ready=ready,
            base_url="http://127.0.0.1:11434",
            error_code=None if ready else f"ollama_{self.state}",
            message="Ready for tests." if ready else "Not ready for tests.",
        )

    async def list_models(self, force_refresh: bool = False) -> list[AIModelInfo]:
        del force_refresh
        return [
            AIModelInfo(
                name="test-model",
                size=100,
                digest="test-digest",
                details=AIModelDetails(
                    family="llama", parameter_size="1B", quantization_level="Q4"
                ),
                is_configured=True,
            )
        ]

    async def generate(
        self, prompt: PromptPackage, model: str | None = None
    ) -> GenerationResult:
        del prompt
        self.generate_calls += 1
        text = (
            '{"narration_blocks":["Zara looks up."],'
            '"dialogue_blocks":["Tum theek ho?"],"emotion":"concerned",'
            '"relationship_event":"supportive","memory_candidates":[],'
            '"raw_text":"*Zara looks up.*"}'
        )
        parsed, status = parse_roleplay_response(text)
        return GenerationResult(
            provider="ollama",
            model=model or "test-model",
            text=text,
            parsed_response=parsed,
            parse_status=status,
            done=True,
        )

    async def stream_generate(
        self, prompt: PromptPackage, model: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        del prompt
        if self.stream_error:
            raise OllamaStreamInterruptedError("Stream failed in test.")
        yield StreamEvent(event="start", data={"model": model or "test-model"})
        yield StreamEvent(event="token", data={"text": "Tum "})
        yield StreamEvent(event="token", data={"text": "theek ho?"})
        yield StreamEvent(
            event="metadata", data={"parse_status": "plain_text_fallback"}
        )
        yield StreamEvent(event="completed", data={"text": "Tum theek ho?"})


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
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def ai_service(fake_provider: FakeProvider) -> AIService:
    settings = Settings(
        _env_file=None,
        database_url="sqlite:///:memory:",
        environment="test",
        ollama_model="test-model",
    )
    return AIService(settings, provider=fake_provider)


@pytest.fixture
def client(
    db_session: Session, ai_service: AIService
) -> Generator[TestClient, None, None]:
    application = create_app()

    def override_db() -> Generator[Session, None, None]:
        yield db_session

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_ai_service] = lambda: ai_service
    with TestClient(application) as test_client:
        yield test_client
