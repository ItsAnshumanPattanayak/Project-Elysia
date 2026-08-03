import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.ai.exceptions import AIError, GenerationCancelledError
from app.ai.schemas import (
    AIModelInfo,
    AIProviderStatus,
    GenerationRequest,
    GenerationResult,
)
from app.api.errors import error_payload
from app.services.ai_service import AIService, get_ai_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status", response_model=AIProviderStatus)
async def ai_status(
    service: Annotated[AIService, Depends(get_ai_service)],
    refresh: bool = Query(default=False),
) -> AIProviderStatus:
    return await service.status(force_refresh=refresh)


@router.get("/models", response_model=list[AIModelInfo])
async def ai_models(
    service: Annotated[AIService, Depends(get_ai_service)],
    refresh: bool = Query(default=False),
) -> list[AIModelInfo]:
    return await service.models(force_refresh=refresh)


@router.post("/generate", response_model=GenerationResult)
async def generate(
    request: GenerationRequest,
    service: Annotated[AIService, Depends(get_ai_service)],
) -> GenerationResult:
    return await service.generate(request)


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/generate/stream")
async def stream_generate(
    payload: GenerationRequest,
    request: Request,
    service: Annotated[AIService, Depends(get_ai_service)],
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        try:
            async for item in service.stream(payload):
                if await request.is_disconnected():
                    raise GenerationCancelledError("Generation was cancelled.")
                yield _sse(item.event, item.data)
        except AIError as exc:
            yield _sse(
                "error",
                error_payload(exc.code, exc.message, exc.retryable, exc.details)[
                    "error"
                ],
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
