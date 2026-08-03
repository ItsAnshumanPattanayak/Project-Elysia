import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Character,
    Conversation,
    Memory,
    Message,
    RelationshipEvent,
    RelationshipState,
    RoleplayProfile,
)
from app.models.message import MessageSender
from app.schemas.character import CharacterCreate
from app.schemas.memory import MemoryCreate
from app.schemas.relationship_state import RelationshipStateCreate
from app.schemas.roleplay_profile import RoleplayProfileCreate


def create_context(session: Session) -> Conversation:
    character = Character(slug="test", name="Test", display_name="Test", age=20)
    profile = RoleplayProfile(roleplay_name="Player", age=20)
    conversation = Conversation(
        character=character, roleplay_profile=profile, title="Test"
    )
    session.add(conversation)
    session.commit()
    return conversation


def test_all_tables_are_created(db_session: Session) -> None:
    names = set(db_session.bind.dialect.get_table_names(db_session.connection()))
    assert {
        "characters",
        "roleplay_profiles",
        "conversations",
        "messages",
        "relationship_states",
        "memories",
        "application_settings",
        "relationship_events",
    } <= names


def test_character_profile_and_relationships(db_session: Session) -> None:
    conversation = create_context(db_session)
    state = RelationshipState(conversation=conversation, attraction=70)
    db_session.add(state)
    db_session.commit()
    db_session.refresh(conversation)
    assert conversation.character.name == "Test"
    assert conversation.roleplay_profile.roleplay_name == "Player"
    assert conversation.relationship_state is state


def test_message_sequence_is_unique(db_session: Session) -> None:
    conversation = create_context(db_session)
    db_session.add_all(
        [
            Message(
                conversation=conversation,
                sender=MessageSender.USER,
                raw_content="One",
                sequence_number=1,
            ),
            Message(
                conversation=conversation,
                sender=MessageSender.CHARACTER,
                raw_content="Two",
                sequence_number=1,
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_database_constraints(db_session: Session) -> None:
    conversation = create_context(db_session)
    db_session.add(RelationshipState(conversation=conversation, attraction=101))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_relationship_event_confidence_and_application_key_constraints(
    db_session: Session,
) -> None:
    conversation = create_context(db_session)
    event = RelationshipEvent(
        conversation=conversation,
        event_type="neutral",
        source="deterministic",
        confidence=1.1,
        evidence=[],
        score_deltas={},
        values_before={},
        values_after={},
        mood_before="neutral",
        mood_after="neutral",
        stage_before="friends",
        stage_after="friends",
        application_key="invalid-confidence",
    )
    db_session.add(event)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_relationship_event_application_key_is_unique(db_session: Session) -> None:
    conversation = create_context(db_session)

    def make_event() -> RelationshipEvent:
        return RelationshipEvent(
            conversation=conversation,
            event_type="neutral",
            source="deterministic",
            confidence=0.5,
            evidence=[],
            score_deltas={},
            values_before={},
            values_after={},
            mood_before="neutral",
            mood_after="neutral",
            stage_before="friends",
            stage_after="friends",
            application_key="same-application-key",
        )

    db_session.add_all([make_event(), make_event()])
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    db_session.add(
        Memory(conversation=conversation, memory_type="fact", content="x", importance=0)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize(
    ("schema", "kwargs"),
    [
        (
            CharacterCreate,
            {"slug": "minor", "name": "Minor", "display_name": "Minor", "age": 17},
        ),
        (RoleplayProfileCreate, {"roleplay_name": "Minor", "age": 17}),
        (RelationshipStateCreate, {"conversation_id": 1, "trust": 101}),
        (
            MemoryCreate,
            {
                "conversation_id": 1,
                "memory_type": "fact",
                "content": "x",
                "importance": 6,
            },
        ),
    ],
)
def test_schema_validation_rejects_invalid_values(
    schema: type, kwargs: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        schema(**kwargs)
