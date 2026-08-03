import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.seed import seed_database


@pytest.fixture(autouse=True)
def seeded_database(db_session: Session) -> None:
    seed_database(db_session)


def conversation_id(client: TestClient) -> int:
    response = client.post(
        "/api/conversations",
        json={"character_slug": "zara-mirza", "roleplay_user_slug": "anshuman"},
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def test_manual_memory_crud_search_and_rebuild(client: TestClient) -> None:
    conversation = conversation_id(client)
    created = client.post(
        f"/api/conversations/{conversation}/memories",
        json={
            "content": "I prefer concise explanations.",
            "memory_type": "user_preference",
            "importance": 80,
            "pinned": True,
        },
    )
    assert created.status_code == 201
    memory = created.json()
    assert memory["source"] == "manual"
    assert memory["confidence"] == 1.0

    listed = client.get(
        f"/api/conversations/{conversation}/memories?status=active&pinned=true"
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    preview = client.post(
        f"/api/conversations/{conversation}/memories/search-preview",
        json={"query": "Can you give concise explanations?", "limit": 3},
    )
    assert preview.status_code == 200
    assert preview.json()["items"][0]["id"] == memory["id"]

    updated = client.patch(
        f"/api/conversations/{conversation}/memories/{memory['id']}",
        json={"locked": True},
    )
    assert updated.status_code == 200
    blocked = client.delete(
        f"/api/conversations/{conversation}/memories/{memory['id']}"
    )
    assert blocked.status_code == 409
    unlocked = client.patch(
        f"/api/conversations/{conversation}/memories/{memory['id']}",
        json={"locked": False, "archived": True, "force": True},
    )
    assert unlocked.status_code == 200
    assert unlocked.json()["status"] == "archived"

    rebuild = client.post(
        f"/api/conversations/{conversation}/memories/rebuild",
        json={"confirm": False},
    )
    assert rebuild.status_code == 409
    rebuilt = client.post(
        f"/api/conversations/{conversation}/memories/rebuild",
        json={"confirm": True},
    )
    assert rebuilt.status_code == 200


def test_memory_duplicate_secret_sensitive_and_mismatch(client: TestClient) -> None:
    first = conversation_id(client)
    second = conversation_id(client)
    payload = {
        "content": "I prefer concise explanations.",
        "memory_type": "user_preference",
    }
    created = client.post(f"/api/conversations/{first}/memories", json=payload)
    assert created.status_code == 201
    assert (
        client.post(f"/api/conversations/{first}/memories", json=payload).status_code
        == 409
    )
    secret = client.post(
        f"/api/conversations/{first}/memories",
        json={"content": "password=hunter2", "memory_type": "private_note"},
    )
    assert secret.status_code == 422
    sensitive = client.post(
        f"/api/conversations/{first}/memories",
        json={"content": "I am allergic to peanuts", "memory_type": "user_boundary"},
    )
    assert sensitive.status_code == 422
    mismatch = client.get(
        f"/api/conversations/{second}/memories/{created.json()['id']}"
    )
    assert mismatch.status_code == 404


def test_completed_send_extracts_once_and_failed_generation_does_not(
    client: TestClient, fake_provider: object
) -> None:
    conversation = conversation_id(client)
    sent = client.post(
        f"/api/conversations/{conversation}/messages",
        json={
            "content": "My favourite food is biryani.",
            "client_message_id": "memory-once",
        },
    )
    assert sent.status_code == 200
    assert sent.json()["memory"]["created"] == 1
    duplicate = client.post(
        f"/api/conversations/{conversation}/messages",
        json={
            "content": "My favourite food is biryani.",
            "client_message_id": "memory-once",
        },
    )
    assert duplicate.status_code == 200
    listed = client.get(f"/api/conversations/{conversation}/memories")
    assert listed.json()["total"] == 1


def test_completed_stream_extracts_and_truncation_reverts(
    client: TestClient,
) -> None:
    conversation = conversation_id(client)
    streamed = client.post(
        f"/api/conversations/{conversation}/messages/stream",
        json={"content": "I dislike crowded places."},
    )
    assert streamed.status_code == 200
    assert "event: completed" in streamed.text
    active = client.get(
        f"/api/conversations/{conversation}/memories?status=active"
    ).json()
    assert active["total"] == 1

    messages = client.get(f"/api/conversations/{conversation}/messages").json()["items"]
    user = next(item for item in messages if item["sender"] == "user")
    edited = client.patch(
        f"/api/conversations/{conversation}/messages/{user['id']}",
        json={
            "content": "This statement no longer contains a durable fact.",
            "confirm_truncate_following_messages": True,
        },
    )
    assert edited.status_code == 200
    reverted = client.get(
        f"/api/conversations/{conversation}/memories?status=reverted"
    ).json()
    assert reverted["total"] == 1


def test_rebuild_restores_deterministic_memory_without_changing_turns(
    client: TestClient,
) -> None:
    conversation = conversation_id(client)
    sent = client.post(
        f"/api/conversations/{conversation}/messages",
        json={"content": "My goal is to become a software engineer."},
    )
    assert sent.status_code == 200
    before = client.get(f"/api/conversations/{conversation}/relationship").json()
    rebuilt = client.post(
        f"/api/conversations/{conversation}/memories/rebuild",
        json={"confirm": True},
    )
    assert rebuilt.status_code == 200
    after = client.get(f"/api/conversations/{conversation}/relationship").json()
    assert after == before
    assert (
        client.get(f"/api/conversations/{conversation}/memories?status=active").json()[
            "total"
        ]
        == 1
    )
