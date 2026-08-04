from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApplicationSetting


def values(response: dict[str, object]) -> dict[str, object]:
    items = response["items"]
    assert isinstance(items, list)
    return {str(item["key"]): item["value"] for item in items if isinstance(item, dict)}


def test_get_settings_returns_only_safe_allow_list(client: TestClient) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    payload = values(response.json())
    assert set(payload) == {
        "selected_model",
        "temperature",
        "top_p",
        "top_k",
        "repeat_penalty",
        "context_size",
        "max_output_tokens",
        "response_length",
        "relationship_engine_enabled",
        "auto_memory_enabled",
    }
    serialized = response.text.casefold()
    assert "base_url" not in serialized
    assert "password" not in serialized
    assert "system_prompt" not in serialized


def test_schema_contains_bounds_and_no_sensitive_fields(client: TestClient) -> None:
    response = client.get("/api/settings/schema")
    assert response.status_code == 200
    items = {item["key"]: item for item in response.json()["items"]}
    assert items["temperature"]["minimum"] == 0
    assert items["temperature"]["maximum"] == 2
    assert items["response_length"]["allowed_values"] == [
        "concise",
        "balanced",
        "detailed",
    ]
    assert all("sensitive" not in item for item in items.values())


def test_valid_settings_update_persists(
    client: TestClient, db_session: Session
) -> None:
    response = client.patch(
        "/api/settings",
        json={"values": {"temperature": 1.2, "top_k": 55}},
    )
    assert response.status_code == 200
    assert values(response.json())["temperature"] == 1.2
    row = db_session.scalar(
        select(ApplicationSetting).where(ApplicationSetting.key == "top_k")
    )
    assert row is not None
    assert row.value == 55


def test_invalid_or_unsafe_keys_are_rejected(client: TestClient) -> None:
    for key in ("ollama_base_url", "api_key", "system_prompt", "character_path"):
        response = client.patch("/api/settings", json={"values": {key: "unsafe"}})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "unsafe_setting_key"


def test_types_bounds_and_enums_are_strict(client: TestClient) -> None:
    cases = [
        {"temperature": 2.1},
        {"top_p": 0},
        {"top_k": 1.5},
        {"context_size": 100},
        {"max_output_tokens": 5000},
        {"response_length": "unbounded"},
        {"auto_memory_enabled": "yes"},
    ]
    for payload in cases:
        response = client.patch("/api/settings", json={"values": payload})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_setting_value"


def test_model_selection_requires_installed_model(client: TestClient) -> None:
    invalid = client.patch(
        "/api/settings", json={"values": {"selected_model": "remote-model"}}
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "model_not_installed"
    valid = client.patch(
        "/api/settings", json={"values": {"selected_model": "test-model"}}
    )
    assert valid.status_code == 200
    assert values(valid.json())["selected_model"] == "test-model"


def test_reset_key_category_and_all(client: TestClient) -> None:
    client.patch(
        "/api/settings",
        json={
            "values": {
                "temperature": 1.4,
                "response_length": "detailed",
                "auto_memory_enabled": False,
            }
        },
    )
    one = client.post("/api/settings/reset", json={"keys": ["temperature"]})
    assert one.status_code == 200
    assert values(one.json())["temperature"] == 0.8
    category = client.post("/api/settings/reset", json={"category": "chat"})
    assert category.status_code == 200
    assert values(category.json())["response_length"] == "balanced"
    reset_all = client.post("/api/settings/reset", json={"all": True})
    assert reset_all.status_code == 200
    assert values(reset_all.json())["auto_memory_enabled"] is True


def test_reset_requires_exactly_one_selector(client: TestClient) -> None:
    missing = client.post("/api/settings/reset", json={})
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "invalid_reset_request"
    conflicting = client.post(
        "/api/settings/reset", json={"keys": ["temperature"], "all": True}
    )
    assert conflicting.status_code == 400


def test_settings_api_does_not_mutate_env_file(
    client: TestClient, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OLLAMA_BASE_URL=http://127.0.0.1:11434\n", encoding="utf-8")
    before = env_file.read_bytes()
    response = client.patch("/api/settings", json={"values": {"temperature": 0.7}})
    assert response.status_code == 200
    assert env_file.read_bytes() == before
