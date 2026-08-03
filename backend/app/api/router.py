from fastapi import APIRouter

from app.api.routes import ai, characters, health, system

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(system.router)
api_router.include_router(characters.router)
api_router.include_router(ai.router)
