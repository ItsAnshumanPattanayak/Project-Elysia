from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.ai.exceptions import (
    OllamaInvalidResponseError,
    OllamaModelNotConfiguredError,
    OllamaModelNotInstalledError,
    OllamaUnavailableError,
)
from app.ai.ollama.provider import OllamaProvider
from app.ai.parser import parse_roleplay_response
from app.character_engine.loader import CharacterLoader
from app.character_engine.prompt_builder import PromptBuilder
from app.character_engine.schemas import PromptContext, PromptPackage
from app.core.config import Settings


class StubClient:
    def __init__(self) -> None:
        self.version_calls = 0
        self.tags_calls = 0
        self.installed = True
        self.unavailable = False
        self.empty_stream = False

    async def aclose(self) -> None:
        return None

    async def version(self) -> str:
        self.version_calls += 1
        if self.unavailable:
            raise OllamaUnavailableError("offline")
        return "0.test"

    async def tags(self) -> list[dict[str, Any]]:
        self.tags_calls += 1
        if not self.installed:
            return []
        return [
            {
                "name": "test-model",
                "size": 100,
                "digest": "digest",
                "details": {
                    "family": "llama",
                    "parameter_size": "1B",
                    "quantization_level": "Q4",
                },
            }
        ]

    async def chat(self, _: dict[str, Any]) -> dict[str, Any]:
        return {
            "message": {
                "content": (
                    '{"narration_blocks":[],"dialogue_blocks":["Hello"],'
                    '"emotion":"warm","relationship_event":null,'
                    '"memory_candidates":[],"raw_text":"Hello"}'
                )
            },
            "done": True,
            "eval_count": 4,
        }

    async def stream_chat(
        self, _: dict[str, Any], max_characters: int
    ) -> AsyncIterator[dict[str, Any]]:
        del max_characters
        if self.empty_stream:
            return
        yield {"message": {"content": "Hello "}, "done": False}
        yield {"message": {"content": "there"}, "done": True, "eval_count": 2}


def settings(model: str = "test-model", ttl: float = 10) -> Settings:
    return Settings(
        _env_file=None,
        database_url="sqlite:///:memory:",
        ollama_model=model,
        ollama_status_cache_ttl_seconds=ttl,
    )


def prompt() -> PromptPackage:
    loader = CharacterLoader()
    return PromptBuilder().build(
        loader.load_character("zara-mirza"),
        loader.load_roleplay_user("anshuman"),
        PromptContext(recent_messages=[{"role": "user", "content": "private"}]),
    )


@pytest.mark.asyncio
async def test_ready_status_models_and_cache() -> None:
    client = StubClient()
    provider = OllamaProvider(settings(), client=client)
    first = await provider.status()
    second = await provider.status()
    assert first.state == second.state == "ready"
    assert client.version_calls == 1
    assert (await provider.list_models())[0].is_configured is True
    await provider.status(force_refresh=True)
    assert client.version_calls == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "installed", "state"),
    [("", True, "model_not_configured"), ("missing", False, "model_not_installed")],
)
async def test_not_ready_states(model: str, installed: bool, state: str) -> None:
    client = StubClient()
    client.installed = installed
    provider = OllamaProvider(settings(model), client=client)
    assert (await provider.status(force_refresh=True)).state == state


@pytest.mark.asyncio
async def test_unavailable_state() -> None:
    client = StubClient()
    client.unavailable = True
    provider = OllamaProvider(settings(), client=client)
    status = await provider.status()
    assert status.state == "unavailable"
    assert status.error_code == "ollama_unavailable"


@pytest.mark.asyncio
async def test_generation_and_stream() -> None:
    client = StubClient()
    provider = OllamaProvider(settings(), client=client)
    result = await provider.generate(prompt())
    assert result.parse_status == "structured"
    assert result.parsed_response.dialogue_blocks == ["Hello"]
    events = [item async for item in provider.stream_generate(prompt())]
    assert [item.event for item in events] == [
        "start",
        "token",
        "token",
        "metadata",
        "completed",
    ]
    assert events[-1].data["text"] == "Hello there"


@pytest.mark.asyncio
async def test_missing_and_empty_model_errors() -> None:
    empty = OllamaProvider(settings(""), client=StubClient())
    with pytest.raises(OllamaModelNotConfiguredError):
        await empty.generate(prompt())
    client = StubClient()
    client.installed = False
    missing = OllamaProvider(settings("missing"), client=client)
    with pytest.raises(OllamaModelNotInstalledError):
        await missing.generate(prompt())


@pytest.mark.asyncio
async def test_empty_stream_error() -> None:
    client = StubClient()
    client.empty_stream = True
    provider = OllamaProvider(settings(), client=client)
    with pytest.raises(OllamaInvalidResponseError):
        _ = [event async for event in provider.stream_generate(prompt())]


def test_structured_and_plain_text_parser() -> None:
    structured, status = parse_roleplay_response(
        '{"narration_blocks":[],"dialogue_blocks":["Hi"],"emotion":null,"relationship_event":null,"memory_candidates":[],"raw_text":"Hi"}'
    )
    assert status == "structured"
    assert structured.dialogue_blocks == ["Hi"]
    fallback, status = parse_roleplay_response('*Zara smiles.*\nZara: "Hi"')
    assert status == "plain_text_fallback"
    assert fallback.narration_blocks == ["Zara smiles."]
    assert fallback.dialogue_blocks == ["Hi"]


@pytest.mark.asyncio
async def test_private_prompt_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    provider = OllamaProvider(settings(), client=StubClient())
    await provider.generate(prompt())
    assert "private" not in caplog.text
