from app.ai.base import AIProvider
from app.ai.ollama.provider import OllamaProvider
from app.core.config import Settings


def create_ai_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider != "ollama":
        raise ValueError("Only the local Ollama provider is supported.")
    return OllamaProvider(settings)
