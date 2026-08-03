from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.ai.exceptions import AIError
from app.character_engine.exceptions import (
    CharacterConfigurationError,
    CharacterNotFoundError,
    RoleplayProfileNotFoundError,
    UnsafeCharacterPathError,
    UnsupportedCharacterSchemaVersionError,
)


def error_payload(
    code: str,
    message: str,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "retryable": retryable,
        }
    }


async def ai_error_handler(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AIError):
        raise exc
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else 400,
        content=error_payload(exc.code, exc.message, exc.retryable, exc.details),
    )


async def character_error_handler(_: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, CharacterNotFoundError):
        return JSONResponse(
            status_code=404, content=error_payload("character_not_found", str(exc))
        )
    if isinstance(exc, RoleplayProfileNotFoundError):
        return JSONResponse(
            status_code=404, content=error_payload("invalid_roleplay_profile", str(exc))
        )
    if isinstance(exc, UnsupportedCharacterSchemaVersionError):
        code = "unsupported_character_schema"
    elif isinstance(exc, UnsafeCharacterPathError):
        code = "unsafe_character_path"
    else:
        code = "invalid_character_configuration"
    return JSONResponse(status_code=400, content=error_payload(code, str(exc)))


async def validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    details = {
        "fields": [
            {"location": [str(part) for part in item["loc"]], "message": item["msg"]}
            for item in exc.errors()
        ]
    }
    return JSONResponse(
        status_code=422,
        content=error_payload(
            "invalid_generation_request",
            "The request failed validation.",
            False,
            details,
        ),
    )


CHARACTER_ERRORS = (
    CharacterNotFoundError,
    RoleplayProfileNotFoundError,
    CharacterConfigurationError,
    UnsupportedCharacterSchemaVersionError,
    UnsafeCharacterPathError,
)
