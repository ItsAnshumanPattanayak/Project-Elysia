from conftest import FakeProvider
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.seed import seed_database
from app.models import Conversation, Memory, Message, RelationshipState


def request_body() -> dict[str, object]:
    return {
        "context": {
            "character_slug": "zara-mirza",
            "roleplay_user_slug": "anshuman",
            "current_scene": "Zara's office after business hours.",
            "behaviour_hint": "concern",
            "recent_messages": [
                {"role": "user", "content": "Aaj ka din bahut tiring tha."}
            ],
        }
    }


def database_snapshot(session: Session) -> tuple[int, int, int, list[tuple[int, str]]]:
    return (
        session.scalar(select(func.count()).select_from(Message)) or 0,
        session.scalar(select(func.count()).select_from(Memory)) or 0,
        session.scalar(select(func.count()).select_from(RelationshipState)) or 0,
        list(session.execute(select(Conversation.id, Conversation.summary)).all()),
    )


def test_character_list_detail_missing_and_unsafe(client: TestClient) -> None:
    listing = client.get("/api/characters")
    assert listing.status_code == 200
    assert listing.json()[0]["slug"] == "zara-mirza"
    detail = client.get("/api/characters/zara-mirza")
    assert detail.status_code == 200
    assert detail.json()["adult"] is True
    assert "consistency_rules" not in detail.json()
    missing = client.get("/api/characters/missing")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "character_not_found"
    unsafe = client.get("/api/characters/Zara")
    assert unsafe.status_code == 400
    assert unsafe.json()["error"]["code"] == "unsafe_character_path"


def test_prompt_preview_and_validation(client: TestClient) -> None:
    response = client.post(
        "/api/characters/zara-mirza/prompt-preview",
        json=request_body()["context"],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["applied_behaviour_hint"] == "concern"
    assert "## Character identity" in payload["system_prompt"]
    invalid = client.post(
        "/api/characters/zara-mirza/prompt-preview",
        json={"current_scene": "x" * 2001},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_generation_request"


def test_ai_status_variants_and_models(
    client: TestClient, fake_provider: FakeProvider
) -> None:
    for state in (
        "ready",
        "unavailable",
        "model_not_configured",
        "model_not_installed",
    ):
        fake_provider.state = state
        payload = client.get("/api/ai/status?refresh=true").json()
        assert payload["state"] == state
    models = client.get("/api/ai/models")
    assert models.status_code == 200
    assert models.json()[0]["name"] == "test-model"


def test_generate_does_not_mutate_database(
    client: TestClient, db_session: Session, fake_provider: FakeProvider
) -> None:
    seed_database(db_session)
    before = database_snapshot(db_session)
    response = client.post("/api/ai/generate", json=request_body())
    assert response.status_code == 200
    assert response.json()["parse_status"] == "structured"
    assert fake_provider.generate_calls == 1
    assert database_snapshot(db_session) == before


def test_stream_event_order_and_nonmutation(
    client: TestClient, db_session: Session
) -> None:
    seed_database(db_session)
    before = database_snapshot(db_session)
    response = client.post("/api/ai/generate/stream", json=request_body())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [
        line.removeprefix("event: ")
        for line in response.text.splitlines()
        if line.startswith("event: ")
    ]
    assert events == ["start", "token", "token", "metadata", "completed"]
    assert database_snapshot(db_session) == before


def test_stream_safe_error_event(
    client: TestClient, fake_provider: FakeProvider
) -> None:
    fake_provider.stream_error = True
    response = client.post("/api/ai/generate/stream", json=request_body())
    assert "event: error" in response.text
    assert "ollama_stream_interrupted" in response.text
    assert "Traceback" not in response.text


def test_responses_do_not_leak_paths_or_secrets(client: TestClient) -> None:
    for path in ("/api/ai/status", "/api/ai/models", "/api/characters/zara-mirza"):
        rendered = client.get(path).text.lower()
        assert "e:\\project-elysia" not in rendered
        assert "c:\\users" not in rendered
        assert "database_url" not in rendered
