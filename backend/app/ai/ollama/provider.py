import asyncio
import time
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Protocol

from app.ai.exceptions import (
    AIError,
    OllamaInvalidResponseError,
    OllamaModelNotConfiguredError,
    OllamaModelNotInstalledError,
)
from app.ai.ollama.client import OllamaClient
from app.ai.parser import parse_roleplay_response
from app.ai.schemas import (
    AIModelDetails,
    AIModelInfo,
    AIProviderStatus,
    GenerationResult,
    StreamEvent,
)
from app.character_engine.schemas import MessageRole, PromptPackage
from app.core.config import Settings


class OllamaClientProtocol(Protocol):
    async def aclose(self) -> None: ...
    async def version(self) -> str: ...
    async def tags(self) -> list[dict[str, Any]]: ...
    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def stream_chat(
        self, payload: dict[str, Any], max_characters: int
    ) -> AsyncIterator[dict[str, Any]]: ...


class OllamaProvider:
    def __init__(
        self, settings: Settings, client: OllamaClientProtocol | None = None
    ) -> None:
        self.settings = settings
        self.client = client or OllamaClient(
            str(settings.ollama_base_url),
            settings.ollama_connect_timeout_seconds,
            settings.ollama_read_timeout_seconds,
        )
        self._cache_lock = asyncio.Lock()
        self._cached_status: tuple[float, AIProviderStatus] | None = None
        self._cached_models: tuple[float, list[AIModelInfo]] | None = None

    async def aclose(self) -> None:
        await self.client.aclose()

    @property
    def safe_base_url(self) -> str:
        url = self.settings.ollama_base_url
        return f"{url.scheme}://{url.host}:{url.port or 80}"

    def _fresh(self, timestamp: float) -> bool:
        return (
            time.monotonic() - timestamp < self.settings.ollama_status_cache_ttl_seconds
        )

    async def list_models(self, force_refresh: bool = False) -> list[AIModelInfo]:
        if (
            not force_refresh
            and self._cached_models
            and self._fresh(self._cached_models[0])
        ):
            return [item.model_copy(deep=True) for item in self._cached_models[1]]
        async with self._cache_lock:
            if (
                not force_refresh
                and self._cached_models
                and self._fresh(self._cached_models[0])
            ):
                return [item.model_copy(deep=True) for item in self._cached_models[1]]
            raw_models = await self.client.tags()
            models: list[AIModelInfo] = []
            for item in raw_models:
                raw_details = item.get("details")
                details: dict[str, Any] = (
                    raw_details if isinstance(raw_details, dict) else {}
                )
                modified = item.get("modified_at")
                models.append(
                    AIModelInfo(
                        name=str(item.get("name") or item.get("model") or ""),
                        modified_at=(
                            datetime.fromisoformat(modified)
                            if isinstance(modified, str)
                            else None
                        ),
                        size=int(item.get("size") or 0),
                        digest=str(item.get("digest") or ""),
                        details=AIModelDetails(
                            family=details.get("family"),
                            parameter_size=details.get("parameter_size"),
                            quantization_level=details.get("quantization_level"),
                            format=details.get("format"),
                            context_length=details.get("context_length"),
                        ),
                        is_configured=item.get("name") == self.settings.ollama_model,
                    )
                )
            self._cached_models = (time.monotonic(), models)
            return [item.model_copy(deep=True) for item in models]

    async def status(self, force_refresh: bool = False) -> AIProviderStatus:
        if (
            not force_refresh
            and self._cached_status
            and self._fresh(self._cached_status[0])
        ):
            return self._cached_status[1].model_copy(deep=True)
        try:
            version = await self.client.version()
            models = await self.list_models(force_refresh=force_refresh)
            configured = self.settings.ollama_model.strip()
            if not configured:
                status = AIProviderStatus(
                    provider="ollama",
                    available=True,
                    state="model_not_configured",
                    version=version,
                    configured_model=None,
                    model_ready=False,
                    base_url=self.safe_base_url,
                    error_code="ollama_model_not_configured",
                    message="Ollama is available, but no model is configured.",
                )
            elif not any(model.name == configured for model in models):
                status = AIProviderStatus(
                    provider="ollama",
                    available=True,
                    state="model_not_installed",
                    version=version,
                    configured_model=configured,
                    model_ready=False,
                    base_url=self.safe_base_url,
                    error_code="ollama_model_not_installed",
                    message="The configured model is not installed locally.",
                )
            else:
                status = AIProviderStatus(
                    provider="ollama",
                    available=True,
                    state="ready",
                    version=version,
                    configured_model=configured,
                    model_ready=True,
                    base_url=self.safe_base_url,
                    message="Ollama and the configured model are ready.",
                )
        except AIError as exc:
            status = AIProviderStatus(
                provider="ollama",
                available=False,
                state="unavailable",
                configured_model=self.settings.ollama_model or None,
                model_ready=False,
                base_url=self.safe_base_url,
                error_code=exc.code,
                message=exc.message,
            )
        async with self._cache_lock:
            self._cached_status = (time.monotonic(), status)
        return status.model_copy(deep=True)

    def _model(self, requested: str | None) -> str:
        model = (requested or self.settings.ollama_model).strip()
        if not model:
            raise OllamaModelNotConfiguredError("No Ollama model is configured.")
        return model

    async def _ensure_model(self, model: str) -> None:
        if not any(item.name == model for item in await self.list_models()):
            raise OllamaModelNotInstalledError(
                "The configured Ollama model is not installed locally."
            )

    def _payload(
        self, prompt: PromptPackage, model: str, stream: bool
    ) -> dict[str, Any]:
        role_map = {
            MessageRole.USER: "user",
            MessageRole.CHARACTER: "assistant",
            MessageRole.SYSTEM: "system",
        }
        messages = [{"role": "system", "content": prompt.system_prompt}]
        messages.extend(
            {"role": role_map[item.role], "content": item.content}
            for item in prompt.conversation_messages
        )
        options = prompt.generation_options
        return {
            "model": model,
            "messages": messages,
            "stream": stream,
            "keep_alive": self.settings.ollama_keep_alive,
            "format": "json",
            "options": {
                "temperature": options.temperature,
                "top_p": options.top_p,
                "top_k": options.top_k,
                "repeat_penalty": options.repeat_penalty,
                "num_ctx": options.context_size,
                "num_predict": options.max_output_tokens,
                **({"seed": options.seed} if options.seed is not None else {}),
            },
        }

    async def generate(
        self, prompt: PromptPackage, model: str | None = None
    ) -> GenerationResult:
        selected = self._model(model)
        await self._ensure_model(selected)
        raw = await self.client.chat(self._payload(prompt, selected, False))
        text = raw["message"]["content"]
        parsed, parse_status = parse_roleplay_response(text)
        metadata = {
            key: raw[key]
            for key in (
                "total_duration",
                "load_duration",
                "prompt_eval_count",
                "eval_count",
            )
            if key in raw
        }
        return GenerationResult(
            provider="ollama",
            model=selected,
            text=text,
            parsed_response=parsed,
            parse_status=parse_status,
            done=bool(raw.get("done", True)),
            finish_reason=raw.get("done_reason"),
            metadata=metadata,
        )

    async def stream_generate(
        self, prompt: PromptPackage, model: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        selected = self._model(model)
        await self._ensure_model(selected)
        yield StreamEvent(event="start", data={"provider": "ollama", "model": selected})
        combined: list[str] = []
        final: dict[str, Any] = {}
        async for item in self.client.stream_chat(
            self._payload(prompt, selected, True),
            max_characters=prompt.generation_options.max_output_tokens * 12,
        ):
            content = item.get("message", {}).get("content", "")
            if content:
                combined.append(content)
                yield StreamEvent(event="token", data={"text": content})
            if item.get("done"):
                final = item
        if not combined:
            raise OllamaInvalidResponseError(
                "Ollama returned an empty generation stream."
            )
        text = "".join(combined)
        parsed, parse_status = parse_roleplay_response(text)
        metadata = {
            key: final[key]
            for key in (
                "total_duration",
                "load_duration",
                "prompt_eval_count",
                "eval_count",
                "done_reason",
            )
            if key in final
        }
        yield StreamEvent(
            event="metadata", data={"parse_status": parse_status, **metadata}
        )
        yield StreamEvent(
            event="completed",
            data={
                "text": text,
                "parsed_response": parsed.model_dump(mode="json"),
                "parse_status": parse_status,
            },
        )
