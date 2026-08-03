import httpx
import pytest

from app.ai.exceptions import (
    OllamaInvalidResponseError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)
from app.ai.ollama.client import OllamaClient


def client_for(handler: httpx.MockTransport) -> OllamaClient:
    return OllamaClient(
        "http://127.0.0.1:11434",
        1,
        1,
        httpx.AsyncClient(transport=handler, base_url="http://127.0.0.1:11434"),
    )


@pytest.mark.asyncio
async def test_version_models_and_generation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.test"})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "chat:test"}]})
        return httpx.Response(
            200,
            json={"message": {"content": "hello"}, "done": True},
        )

    client = client_for(httpx.MockTransport(handler))
    assert await client.version() == "0.test"
    assert await client.tags() == [{"name": "chat:test"}]
    assert (await client.chat({"model": "chat:test"}))["done"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["connect", "timeout"])
async def test_transport_errors(kind: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if kind == "connect":
            raise httpx.ConnectError("offline", request=request)
        raise httpx.ReadTimeout("slow", request=request)

    client = client_for(httpx.MockTransport(handler))
    expected = OllamaUnavailableError if kind == "connect" else OllamaTimeoutError
    with pytest.raises(expected):
        await client.version()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "body"),
    [("/api/version", b"bad"), ("/api/tags", b"{}"), ("/api/chat", b"bad")],
)
async def test_invalid_json_and_shapes(path: str, body: bytes) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    client = client_for(httpx.MockTransport(handler))
    with pytest.raises(OllamaInvalidResponseError):
        if path == "/api/version":
            await client.version()
        elif path == "/api/tags":
            await client.tags()
        else:
            await client.chat({})


@pytest.mark.asyncio
async def test_stream_preserves_token_order() -> None:
    content = (
        b'{"message":{"content":"one "},"done":false}\n'
        b'{"message":{"content":"two"},"done":true}\n'
    )
    client = client_for(
        httpx.MockTransport(lambda _: httpx.Response(200, content=content))
    )
    items = [item async for item in client.stream_chat({}, 100)]
    assert [item["message"]["content"] for item in items] == ["one ", "two"]


@pytest.mark.asyncio
async def test_invalid_and_empty_stream() -> None:
    client = client_for(
        httpx.MockTransport(lambda _: httpx.Response(200, content=b"not-json\n"))
    )
    with pytest.raises(OllamaInvalidResponseError):
        _ = [item async for item in client.stream_chat({}, 100)]
