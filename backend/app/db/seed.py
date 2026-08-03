from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ApplicationSetting,
    Character,
    Conversation,
    RelationshipState,
    RoleplayProfile,
)

DEFAULT_SETTINGS: dict[str, object] = {
    "selected_model": None,
    "response_length": "balanced",
    "temperature": 0.8,
    "theme": "dark",
    "narration_enabled": True,
    "visible_relationship_stats": ["attraction", "mood", "turn_count"],
    "auto_memory_enabled": True,
    "relationship_engine_enabled": True,
}


def seed_database(session: Session) -> dict[str, int]:
    character = session.scalar(select(Character).where(Character.slug == "zara-mirza"))
    if character is None:
        character = Character(
            slug="zara-mirza",
            name="Zara Mirza",
            display_name="Zara",
            age=32,
            profession="Founder and CEO of Mirza Global Technologies",
            archetype="Billionaire technology CEO and established romantic partner",
            description="A confident, composed, affectionate fictional character.",
            backstory=(
                "Zara built Mirza Global Technologies through ambition and discipline."
            ),
            personality={"traits": ["confident", "intelligent", "protective", "witty"]},
            speaking_style={"primary": "Hinglish", "business": "English"},
            behaviour_rules={"fictional": True, "explicit_content": False},
            greeting_message="Tum aa gaye. I was waiting for you.",
            system_prompt_template="Reserved for a future local AI integration.",
        )
        session.add(character)
        session.flush()

    profile = session.scalar(
        select(RoleplayProfile).where(RoleplayProfile.roleplay_name == "Anshuman")
    )
    if profile is None:
        profile = RoleplayProfile(
            roleplay_name="Anshuman",
            age=25,
            profession="[Editable profession]",
            personality={"notes": "[Editable fictional personality]"},
            relationship_description="Established romantic relationship with Zara",
            preferred_address=["Anshuman", "[Editable nickname]"],
            background={"shared_history": "[Editable fictional history]"},
            preferences={"notes": "[Editable roleplay preferences]"},
        )
        session.add(profile)
        session.flush()

    conversation = session.scalar(
        select(Conversation).where(
            Conversation.character_id == character.id,
            Conversation.roleplay_profile_id == profile.id,
            Conversation.title == "A Quiet Evening",
        )
    )
    if conversation is None:
        conversation = Conversation(
            character=character,
            roleplay_profile=profile,
            title="A Quiet Evening",
            current_scene="[Ready for a future roleplay scene]",
            relationship_stage="committed",
        )
        session.add(conversation)
        session.flush()

    if conversation.relationship_state is None:
        session.add(
            RelationshipState(
                conversation=conversation,
                attraction=70,
                trust=75,
                affection=72,
                respect=80,
                comfort=70,
                jealousy=20,
                anger=0,
                mood="affectionate",
                relationship_stage="committed",
                turn_count=0,
                baseline_values={
                    "attraction": 70,
                    "trust": 75,
                    "affection": 72,
                    "respect": 80,
                    "comfort": 70,
                    "jealousy": 20,
                    "anger": 0,
                    "mood": "affectionate",
                    "relationship_stage": "committed",
                },
            )
        )

    existing = set(session.scalars(select(ApplicationSetting.key)))
    for key, value in DEFAULT_SETTINGS.items():
        if key not in existing:
            session.add(
                ApplicationSetting(
                    key=key,
                    value=value,
                    category="experience",
                    description=f"Default local setting for {key.replace('_', ' ')}.",
                )
            )
    session.commit()
    return {
        "characters": 1,
        "profiles": 1,
        "conversations": 1,
        "settings": len(DEFAULT_SETTINGS),
    }
