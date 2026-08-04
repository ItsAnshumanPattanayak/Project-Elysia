import pytest
from conftest import FakeProvider
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.exceptions import OllamaTimeoutError
from app.db.seed import seed_database
from app.models import (
    Conversation,
    Memory,
    Message,
    RelationshipEvent,
    RelationshipState,
)
from app.services.conversation_errors import RelationshipProcessingError
from app.services.relationship_service import RelationshipService


def seeded_conversation(session: Session) -> int:
    seed_database(session)
    conversation_id = session.scalar(select(Conversation.id))
    assert conversation_id is not None
    return conversation_id


def send(
    client: TestClient, conversation_id: int, content: str = "Hard day"
) -> dict[str, object]:
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": content},
    )
    assert response.status_code == 200, response.text
    return response.json()


def state(session: Session) -> RelationshipState:
    session.expire_all()
    value = session.scalar(select(RelationshipState))
    assert value is not None
    return value


def events(session: Session) -> list[RelationshipEvent]:
    session.expire_all()
    return list(
        session.scalars(select(RelationshipEvent).order_by(RelationshipEvent.id))
    )


def test_completed_send_applies_exactly_once_and_duplicate_retry_is_idempotent(
    client: TestClient, db_session: Session, fake_provider: FakeProvider
) -> None:
    conversation_id = seeded_conversation(db_session)
    request = {"content": "Hard day", "client_message_id": "rel-idempotent"}
    first = client.post(f"/api/conversations/{conversation_id}/messages", json=request)
    second = client.post(f"/api/conversations/{conversation_id}/messages", json=request)
    assert first.status_code == second.status_code == 200
    assert first.json()["relationship"]["event_type"] == "supportive"
    assert fake_provider.generate_calls == 1
    assert len(events(db_session)) == 1
    current = state(db_session)
    assert (current.trust, current.affection, current.comfort) == (77, 73, 72)


def test_repeated_positive_event_has_diminishing_returns(
    client: TestClient, db_session: Session
) -> None:
    conversation_id = seeded_conversation(db_session)
    first = send(client, conversation_id)
    second = send(client, conversation_id)
    assert first["relationship"]["score_deltas"]["trust"] == 2
    assert second["relationship"]["score_deltas"]["trust"] == 1
    assert state(db_session).trust == 78


def test_failed_generation_creates_no_relationship_event(
    client: TestClient, db_session: Session, fake_provider: FakeProvider
) -> None:
    conversation_id = seeded_conversation(db_session)
    fake_provider.generate_error = OllamaTimeoutError("timeout")
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "Keep only user"},
    )
    assert response.status_code == 503
    assert events(db_session) == []
    current = state(db_session)
    assert (current.trust, current.affection, current.turn_count) == (75, 72, 0)


def test_relationship_history_filters_and_recalculation_snapshot(
    client: TestClient, db_session: Session
) -> None:
    conversation_id = seeded_conversation(db_session)
    send(client, conversation_id)
    manual = client.patch(
        f"/api/conversations/{conversation_id}/relationship",
        json={"trust": 81, "reason": "Local dashboard verification."},
    )
    assert manual.status_code == 200
    filtered = client.get(
        f"/api/conversations/{conversation_id}/relationship/events",
        params={"source": "manual", "reverted": False, "oldest_first": True},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["source"] == "manual"

    recalculated = client.post(
        f"/api/conversations/{conversation_id}/relationship/recalculate"
    )
    assert recalculated.status_code == 200
    result = recalculated.json()
    assert result["before"]["turn_count"] == result["after"]["turn_count"]
    assert result["after"]["trust"] == 81
    assert "No AI model was called." in result["warnings"]


def test_relationship_failure_is_non_fatal_after_completed_chat(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation_id = seeded_conversation(db_session)

    def fail_relationship(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise RelationshipProcessingError("test relationship failure")

    monkeypatch.setattr(RelationshipService, "apply_exchange", fail_relationship)
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "Chat still completes"},
    )
    assert response.status_code == 200
    assert response.json()["relationship"] is None
    assert response.json()["warnings"]
    assert db_session.scalar(select(func.count()).select_from(Message)) == 2
    assert events(db_session) == []
    assert state(db_session).turn_count == 1


def test_stream_success_applies_relationship_and_stream_failure_does_not(
    client: TestClient, db_session: Session, fake_provider: FakeProvider
) -> None:
    conversation_id = seeded_conversation(db_session)
    success = client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Stream"},
    )
    assert "event: metadata" in success.text
    assert '"relationship"' in success.text
    assert len(events(db_session)) == 1
    fake_provider.stream_error = True
    failed = client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Fail"},
    )
    assert "event: error" in failed.text
    assert len(events(db_session)) == 1


def test_regeneration_reverts_prior_event_and_replays_from_baseline(
    client: TestClient, db_session: Session, fake_provider: FakeProvider
) -> None:
    conversation_id = seeded_conversation(db_session)
    sent = send(client, conversation_id)
    assert state(db_session).trust == 77
    character_id = sent["character_message"]["id"]
    fake_provider.plain_text = True
    regenerated = client.post(
        f"/api/conversations/{conversation_id}/messages/regenerate", json={}
    )
    assert regenerated.status_code == 200, regenerated.text
    history = events(db_session)
    assert len(history) == 2
    assert history[0].is_reverted is True
    assert history[0].source_character_message_id == character_id
    assert history[1].event_type == "supportive"
    assert history[1].is_reverted is False
    current = state(db_session)
    assert current.trust == 77
    assert current.turn_count == 1


def test_failed_regeneration_preserves_event_and_state(
    client: TestClient, db_session: Session, fake_provider: FakeProvider
) -> None:
    conversation_id = seeded_conversation(db_session)
    send(client, conversation_id)
    fake_provider.generate_error = OllamaTimeoutError("failed replacement")
    response = client.post(
        f"/api/conversations/{conversation_id}/messages/regenerate", json={}
    )
    assert response.status_code == 503
    history = events(db_session)
    assert len(history) == 1 and history[0].is_reverted is False
    assert state(db_session).trust == 77


def test_delete_latest_character_reverts_event_and_restores_baseline(
    client: TestClient, db_session: Session
) -> None:
    conversation_id = seeded_conversation(db_session)
    sent = send(client, conversation_id)
    character_id = sent["character_message"]["id"]
    assert (
        client.delete(
            f"/api/conversations/{conversation_id}/messages/{character_id}"
        ).status_code
        == 204
    )
    history = events(db_session)
    assert len(history) == 1 and history[0].is_reverted is True
    assert history[0].source_character_message_id is None
    current = state(db_session)
    assert (current.trust, current.affection, current.comfort, current.turn_count) == (
        75,
        72,
        70,
        0,
    )


def test_edit_with_truncation_reverts_all_removed_exchange_events(
    client: TestClient, db_session: Session
) -> None:
    conversation_id = seeded_conversation(db_session)
    first = send(client, conversation_id, "First")
    send(client, conversation_id, "Second")
    user_id = first["user_message"]["id"]
    response = client.patch(
        f"/api/conversations/{conversation_id}/messages/{user_id}",
        json={"content": "Changed", "confirm_truncate_following_messages": True},
    )
    assert response.status_code == 200
    assert all(item.is_reverted for item in events(db_session))
    current = state(db_session)
    assert (current.trust, current.turn_count) == (75, 0)


def test_relationship_state_history_and_manual_control_api(
    client: TestClient, db_session: Session
) -> None:
    conversation_id = seeded_conversation(db_session)
    initial = client.get(f"/api/conversations/{conversation_id}/relationship")
    assert initial.status_code == 200
    assert initial.json()["baseline_values"]["trust"] == 75
    manual = client.patch(
        f"/api/conversations/{conversation_id}/relationship",
        json={
            "trust": 90,
            "mood": "happy",
            "locked_values": {"trust": True, "mood": True},
            "reason": "Personal control test",
        },
    )
    assert manual.status_code == 200, manual.text
    assert manual.json()["source"] == "manual"
    locked = client.patch(
        f"/api/conversations/{conversation_id}/relationship",
        json={"trust": 91, "reason": "Should be rejected"},
    )
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "relationship_value_locked"
    forced = client.patch(
        f"/api/conversations/{conversation_id}/relationship",
        json={"trust": 91, "force": True, "reason": "Explicit override"},
    )
    assert forced.status_code == 200
    listing = client.get(
        f"/api/conversations/{conversation_id}/relationship/events?limit=1"
    ).json()
    assert listing["total"] == 2
    assert listing["has_more"] is True


def test_automatic_processing_respects_score_mood_and_stage_locks(
    client: TestClient, db_session: Session
) -> None:
    conversation_id = seeded_conversation(db_session)
    client.patch(
        f"/api/conversations/{conversation_id}/relationship",
        json={
            "locked_values": {
                "trust": True,
                "mood": True,
                "relationship_stage": True,
            },
            "reason": "Lock automatic fields",
        },
    )
    result = send(client, conversation_id)
    relationship = result["relationship"]
    assert relationship["score_deltas"]["trust"] == 0
    assert "trust" in relationship["suppressed_by_locks"]
    current = state(db_session)
    assert current.trust == 75
    assert current.mood == "affectionate"
    assert current.relationship_stage == "committed"


def test_memory_candidates_remain_metadata_only(
    client: TestClient, db_session: Session
) -> None:
    conversation_id = seeded_conversation(db_session)
    send(client, conversation_id)
    assert db_session.scalar(select(func.count()).select_from(Memory)) == 0
    character = db_session.scalar(
        select(Message).order_by(Message.sequence_number.desc()).limit(1)
    )
    assert character is not None
    generation = character.message_metadata["generation"]
    assert "memory_candidates" in generation["parsed_response"]


def test_relationship_history_missing_conversation_is_safe(
    client: TestClient,
) -> None:
    response = client.get("/api/conversations/99999/relationship/events")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"
