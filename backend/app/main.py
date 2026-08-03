import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.ai.exceptions import AIError
from app.api.errors import (
    CHARACTER_ERRORS,
    ai_error_handler,
    character_error_handler,
    conversation_error_handler,
    validation_error_handler,
)
from app.api.router import api_router
from app.core.config import get_settings
from app.core.constants import APP_DESCRIPTION
from app.core.logging import configure_logging
from app.db.session import engine
from app.services.ai_service import get_ai_service
from app.services.conversation_errors import ConversationError

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting %s %s", settings.app_name, settings.app_version)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database connectivity check failed during startup")
        raise
    yield
    if get_ai_service.cache_info().currsize:
        await get_ai_service().aclose()
        get_ai_service.cache_clear()
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    application = FastAPI(
        title=f"{settings.app_name} API",
        version=settings.app_version,
        description=APP_DESCRIPTION,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    application.include_router(api_router)
    application.add_exception_handler(AIError, ai_error_handler)
    application.add_exception_handler(ConversationError, conversation_error_handler)
    for error_type in CHARACTER_ERRORS:
        application.add_exception_handler(error_type, character_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    return application


app = create_app()
