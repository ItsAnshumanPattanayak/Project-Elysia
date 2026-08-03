from collections.abc import AsyncIterator
from typing import Protocol

from app.ai.schemas import AIModelInfo, AIProviderStatus, GenerationResult, StreamEvent
from app.character_engine.schemas import PromptPackage


class AIProvider(Protocol):
    async def status(self, force_refresh: bool = False) -> AIProviderStatus: ...

    async def list_models(self, force_refresh: bool = False) -> list[AIModelInfo]: ...

    async def generate(
        self, prompt: PromptPackage, model: str | None = None
    ) -> GenerationResult: ...

    def stream_generate(
        self, prompt: PromptPackage, model: str | None = None
    ) -> AsyncIterator[StreamEvent]: ...

    async def aclose(self) -> None: ...
