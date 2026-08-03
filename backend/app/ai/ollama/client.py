import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.ai.exceptions import (
    GenerationCancelledError,
    OllamaGenerationError,
    OllamaInvalidResponseError,
    OllamaModelLoadError,
    OllamaStreamInterruptedError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        connect_timeout: float,
        read_timeout: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(
                connect=connect_timeout,
                read=read_timeout,
                write=connect_timeout,
                pool=connect_timeout,
            ),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def _raise_http(response: httpx.Response) -> None:
        if response.is_success:
            return
        message = "Ollama request failed."
        try:
            error = response.json().get("error")
            if isinstance(error, str):
                message = error
        except (json.JSONDecodeError, AttributeError):
            pass
        lowered = message.lower()
        if "not found" in lowered or "load model" in lowered:
            raise OllamaModelLoadError(
                "The configured Ollama model could not be loaded."
            )
        raise OllamaGenerationError(
            "The local Ollama request failed.", {"status_code": response.status_code}
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await self._client.request(method, path, **kwargs)
            self._raise_http(response)
            return response
        except httpx.ConnectError as exc:
            raise OllamaUnavailableError(
                "The local Ollama service is not available."
            ) from exc
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError("The local Ollama request timed out.") from exc

    async def version(self) -> str:
        response = await self._request("GET", "/api/version")
        try:
            version = response.json()["version"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise OllamaInvalidResponseError(
                "Ollama returned an invalid version response."
            ) from exc
        if not isinstance(version, str) or not version:
            raise OllamaInvalidResponseError(
                "Ollama returned an invalid version response."
            )
        return version

    async def tags(self) -> list[dict[str, Any]]:
        response = await self._request("GET", "/api/tags")
        try:
            models = response.json()["models"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise OllamaInvalidResponseError(
                "Ollama returned an invalid model list."
            ) from exc
        if not isinstance(models, list) or not all(
            isinstance(item, dict) for item in models
        ):
            raise OllamaInvalidResponseError("Ollama returned an invalid model list.")
        return models

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("POST", "/api/chat", json=payload)
        try:
            value = response.json()
        except json.JSONDecodeError as exc:
            raise OllamaInvalidResponseError(
                "Ollama returned invalid generation JSON."
            ) from exc
        if not isinstance(value, dict):
            raise OllamaInvalidResponseError(
                "Ollama returned an invalid generation response."
            )
        content = value.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaInvalidResponseError("Ollama returned an empty generation.")
        return value

    async def stream_chat(
        self, payload: dict[str, Any], max_characters: int
    ) -> AsyncIterator[dict[str, Any]]:
        received = 0
        try:
            async with self._client.stream(
                "POST", "/api/chat", json=payload
            ) as response:
                self._raise_http(response)
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise OllamaInvalidResponseError(
                            "Ollama returned invalid streaming JSON."
                        ) from exc
                    if not isinstance(item, dict):
                        raise OllamaInvalidResponseError(
                            "Ollama returned an invalid stream event."
                        )
                    content = item.get("message", {}).get("content", "")
                    if not isinstance(content, str):
                        raise OllamaInvalidResponseError(
                            "Ollama returned an invalid stream token."
                        )
                    received += len(content)
                    if received > max_characters:
                        raise OllamaGenerationError(
                            "Ollama output exceeded the configured safety limit."
                        )
                    yield item
        except httpx.ConnectError as exc:
            raise OllamaUnavailableError(
                "The local Ollama service is not available."
            ) from exc
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError("The local Ollama stream timed out.") from exc
        except httpx.HTTPError as exc:
            raise OllamaStreamInterruptedError(
                "The Ollama stream was interrupted."
            ) from exc
        except asyncio.CancelledError as exc:
            raise GenerationCancelledError("Generation was cancelled.") from exc
