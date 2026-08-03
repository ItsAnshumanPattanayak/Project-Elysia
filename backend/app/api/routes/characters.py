from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai.schemas import PromptPreview
from app.character_engine.loader import CharacterLoader
from app.schemas.character_engine import (
    CharacterProfile,
    CharacterSummary,
    PromptPreviewRequest,
)
from app.services.ai_service import AIService, get_ai_service

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.get("", response_model=list[CharacterSummary])
def list_characters() -> list[CharacterSummary]:
    return [
        CharacterSummary(
            slug=item.slug,
            name=item.identity.name,
            display_name=item.identity.display_name,
            adult=item.identity.adult,
            profession=item.identity.profession,
            archetype=item.identity.archetype,
            description=item.identity.short_description,
        )
        for item in CharacterLoader().list_characters()
    ]


@router.get("/{slug}", response_model=CharacterProfile)
def character_profile(slug: str) -> CharacterProfile:
    item = CharacterLoader().load_character(slug)
    return CharacterProfile(
        slug=item.slug,
        name=item.identity.name,
        display_name=item.identity.display_name,
        adult=item.identity.adult,
        profession=item.identity.profession,
        archetype=item.identity.archetype,
        description=item.identity.short_description,
        personality_summary=item.personality.core_traits,
        speaking_style_summary=item.speaking_style.language_mode,
        preferred_language=item.speaking_style.primary_language,
        avatar_path=item.appearance.avatar_path,
        relationship_summary=item.relationship.emotional_baseline,
    )


@router.post("/{slug}/prompt-preview", response_model=PromptPreview)
def prompt_preview(
    slug: str,
    request: PromptPreviewRequest,
    service: Annotated[AIService, Depends(get_ai_service)],
) -> PromptPreview:
    context = request.model_copy(update={"character_slug": slug})
    return service.preview(context)
