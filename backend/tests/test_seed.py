from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.seed import DEFAULT_SETTINGS, seed_database
from app.models import (
    ApplicationSetting,
    Character,
    Conversation,
    RelationshipState,
    RoleplayProfile,
)


def counts(session: Session) -> tuple[int, ...]:
    return tuple(
        session.scalar(select(func.count()).select_from(model)) or 0
        for model in (
            Character,
            RoleplayProfile,
            Conversation,
            RelationshipState,
            ApplicationSetting,
        )
    )


def test_seed_is_complete_and_idempotent(db_session: Session) -> None:
    seed_database(db_session)
    first = counts(db_session)
    seed_database(db_session)
    assert counts(db_session) == first == (1, 1, 1, 1, len(DEFAULT_SETTINGS))
    conversation = db_session.scalar(select(Conversation))
    assert conversation is not None
    assert conversation.relationship_state is not None
    keys = set(db_session.scalars(select(ApplicationSetting.key)))
    assert keys == set(DEFAULT_SETTINGS)
