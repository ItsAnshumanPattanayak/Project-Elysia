from typing import Any


class AIError(Exception):
    code = "ollama_generation_failed"
    retryable = False

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class OllamaUnavailableError(AIError):
    code = "ollama_unavailable"
    retryable = True


class OllamaTimeoutError(AIError):
    code = "ollama_timeout"
    retryable = True


class OllamaInvalidResponseError(AIError):
    code = "ollama_invalid_response"


class OllamaModelNotConfiguredError(AIError):
    code = "ollama_model_not_configured"


class OllamaModelNotInstalledError(AIError):
    code = "ollama_model_not_installed"


class OllamaModelLoadError(AIError):
    code = "ollama_model_load_failed"


class OllamaGenerationError(AIError):
    code = "ollama_generation_failed"


class OllamaStreamInterruptedError(AIError):
    code = "ollama_stream_interrupted"
    retryable = True


class GenerationCancelledError(AIError):
    code = "generation_cancelled"


class ResponseParseError(AIError):
    code = "response_parse_failed"
