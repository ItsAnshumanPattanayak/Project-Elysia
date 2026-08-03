from collections.abc import AsyncIterator
from functools import lru_cache

from app.ai.base import AIProvider
from app.ai.factory import create_ai_provider
from app.ai.schemas import (
    AIModelInfo,
    AIProviderStatus,
    GenerationRequest,
    GenerationResult,
    PromptPreview,
    StreamEvent,
)
from app.character_engine.loader import CharacterLoader
from app.character_engine.prompt_builder import PromptBuilder
from app.character_engine.schemas import GenerationOptions, PromptContext, PromptPackage
from app.core.config import Settings, get_settings


class AIService:
    def __init__(
        self,
        settings: Settings,
        provider: AIProvider | None = None,
        loader: CharacterLoader | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self.settings = settings
        self.provider = provider or create_ai_provider(settings)
        self.loader = loader or CharacterLoader()
        self.prompt_builder = prompt_builder or PromptBuilder()

    async def aclose(self) -> None:
        await self.provider.aclose()

    async def status(self, force_refresh: bool = False) -> AIProviderStatus:
        return await self.provider.status(force_refresh)

    async def models(self, force_refresh: bool = False) -> list[AIModelInfo]:
        return await self.provider.list_models(force_refresh)

    def build_prompt(
        self, context: PromptContext, options: GenerationOptions | None = None
    ) -> PromptPackage:
        character = self.loader.load_character(context.character_slug)
        roleplay_user = self.loader.load_roleplay_user(context.roleplay_user_slug)
        return self.prompt_builder.build(character, roleplay_user, context, options)

    def preview(self, context: PromptContext) -> PromptPreview:
        package = self.build_prompt(context, self._default_options())
        return PromptPreview(
            character_slug=package.character_slug,
            roleplay_user_slug=package.roleplay_user_slug,
            system_prompt=package.system_prompt,
            conversation_messages=[
                {"role": item.role.value, "content": item.content}
                for item in package.conversation_messages
            ],
            generation_options=package.generation_options.model_dump(),
            applied_behaviour_hint=package.applied_behaviour_hint,
            warnings=[
                "Preview content is not persisted.",
                "Messages, memories, scenes, and summaries are treated as untrusted "
                "narrative data.",
            ],
        )

    def _default_options(self) -> GenerationOptions:
        return GenerationOptions(
            temperature=self.settings.ollama_temperature,
            top_p=self.settings.ollama_top_p,
            top_k=self.settings.ollama_top_k,
            repeat_penalty=self.settings.ollama_repeat_penalty,
            max_output_tokens=self.settings.ollama_max_output_tokens,
            context_size=self.settings.ollama_context_size,
        )

    def _options(self, request: GenerationRequest) -> GenerationOptions:
        defaults = self._default_options().model_dump()
        overrides = request.model_dump(
            include={
                "temperature",
                "top_p",
                "top_k",
                "repeat_penalty",
                "max_output_tokens",
                "context_size",
                "seed",
            },
            exclude_none=True,
        )
        return GenerationOptions.model_validate({**defaults, **overrides})

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        package = self.build_prompt(request.context, self._options(request))
        return await self.provider.generate(package, request.model)

    async def stream(self, request: GenerationRequest) -> AsyncIterator[StreamEvent]:
        package = self.build_prompt(request.context, self._options(request))
        async for event in self.provider.stream_generate(package, request.model):
            yield event


@lru_cache
def get_ai_service() -> AIService:
    return AIService(get_settings())
