from fastapi import APIRouter

from app.api.routes import (
    ai,
    characters,
    conversations,
    health,
    memories,
    settings,
    system,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(system.router)
api_router.include_router(characters.router)
api_router.include_router(ai.router)
api_router.include_router(conversations.router)
api_router.include_router(memories.router)
api_router.include_router(settings.router)
