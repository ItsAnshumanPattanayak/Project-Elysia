from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.ai.schemas import MemoryCandidate, StructuredRoleplayResponse
from app.core.config import Settings
from app.db.seed import seed_database
from app.memory.extraction import MemoryExtractionService, is_secret_like
from app.memory.normalization import normalize_content, normalize_tags
from app.memory.retrieval import MemoryRetrievalService
from app.memory.service import MemoryApplicationService, MemoryLifecycleService
from app.memory.types import MemoryType
from app.models import Conversation, Memory, Message, MessageSender
from app.repositories.memories import MemoryRepository


def settings(**values: object) -> Settings:
    return Settings(_env_file=None, database_url="sqlite:///:memory:", **values)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("  MY   Favourite Food is Biryani!!! ", "my favourite food is biryani"),
        ("Ｃａｆé", "café"),
        ("Hello, world.", "hello world"),
    ],
)
def test_normalization(source: str, expected: str) -> None:
    assert normalize_content(source) == expected


def test_tag_normalization_is_bounded() -> None:
    assert normalize_tags([" Food ", "food", "Travel"], limit=2) == [
        "food",
        "travel",
    ]


@pytest.mark.parametrize(
    ("text", "memory_type"),
    [
        ("My favourite food is biryani.", MemoryType.USER_PREFERENCE),
        ("I like short explanations.", MemoryType.USER_PREFERENCE),
        ("I dislike crowded places.", MemoryType.USER_DISLIKE),
        ("I am allergic to peanuts.", MemoryType.USER_BOUNDARY),
        ("My goal is to become a software engineer.", MemoryType.USER_GOAL),
        ("I always take an evening walk.", MemoryType.USER_HABIT),
        ("My boundary is no shouting.", MemoryType.USER_BOUNDARY),
        ("Please remember that I prefer tea.", MemoryType.USER_FACT),
        ("I promised to visit Delhi.", MemoryType.PROMISE),
        ("We decided to call on Sunday.", MemoryType.COMMITMENT),
    ],
)
def test_explicit_fact_extraction(text: str, memory_type: MemoryType) -> None:
    result = MemoryExtractionService(settings()).deterministic(text)
    assert len(result) == 1
    assert result[0].memory_type == memory_type
    assert result[0].confidence == 0.95


@pytest.mark.parametrize(
    "text",
    [
        "Hello",
        "Okay",
        "What are you doing?",
        "Maybe I will travel someday.",
        '"I like pizza."',
        "Pretend my favourite food is pizza.",
        "Zara walks across the room.",
    ],
)
def test_trivial_hypothetical_question_and_narration_rejected(text: str) -> None:
    assert MemoryExtractionService(settings()).deterministic(text) == []


@pytest.mark.parametrize(
    "text",
    [
        "password=hunter2",
        "API key: sk-example",
        "access_token=abc123",
    ],
)
def test_secret_detection(text: str) -> None:
    assert is_secret_like(text)


def test_structured_candidate_needs_user_evidence() -> None:
    extractor = MemoryExtractionService(settings())
    supported = MemoryCandidate(
        content="I prefer concise technical explanations",
        memory_type="preference",
        importance=80,
        confidence=0.9,
        tags=["explanations"],
    )
    assert extractor.structured([supported], "I prefer concise technical explanations.")
    assert not extractor.structured([supported], "The weather is pleasant today.")


def test_unknown_structured_type_and_path_are_rejected() -> None:
    extractor = MemoryExtractionService(settings())
    unknown = MemoryCandidate(
        content="I prefer concise explanations",
        memory_type="arbitrary_type",
        importance=80,
        confidence=0.9,
    )
    path = MemoryCandidate(
        content=r"My file is C:\Users\person\secret.txt",
        memory_type="user_fact",
        importance=80,
        confidence=0.9,
    )
    assert extractor.structured([unknown, path], unknown.content) == []


def seeded_exchange(session: Session) -> tuple[Conversation, Message, Message]:
    seed_database(session)
    conversation = session.query(Conversation).one()
    user = Message(
        conversation_id=conversation.id,
        sender=MessageSender.USER,
        raw_content="My favourite food is biryani.",
        sequence_number=1,
        message_metadata={},
    )
    character = Message(
        conversation_id=conversation.id,
        sender=MessageSender.CHARACTER,
        raw_content="I will remember that.",
        sequence_number=2,
        message_metadata={"regeneration_count": 0},
    )
    session.add_all([user, character])
    session.commit()
    return conversation, user, character


def test_application_is_idempotent_and_conflict_is_auditable(
    db_session: Session,
) -> None:
    conversation, user, character = seeded_exchange(db_session)
    service = MemoryApplicationService(db_session, settings())
    response = StructuredRoleplayResponse()
    first = service.apply_exchange(conversation, user, character, response)
    second = service.apply_exchange(conversation, user, character, response)
    assert first.created == 1
    assert second.already_applied == 1
    old = db_session.get(Memory, first.memory_ids[0])
    assert old is not None and old.status == "active"

    user2 = Message(
        conversation_id=conversation.id,
        sender=MessageSender.USER,
        raw_content="My favourite food is dosa.",
        sequence_number=3,
        message_metadata={},
    )
    character2 = Message(
        conversation_id=conversation.id,
        sender=MessageSender.CHARACTER,
        raw_content="Noted.",
        sequence_number=4,
        message_metadata={},
    )
    db_session.add_all([user2, character2])
    db_session.commit()
    changed = service.apply_exchange(conversation, user2, character2, response)
    assert changed.superseded == 1
    assert old.status == "superseded"
    assert old.superseded_by_memory_id == changed.memory_ids[0]


def memory(
    conversation_id: int,
    key: str,
    content: str,
    *,
    status: str = "active",
    importance: int = 60,
    confidence: float = 0.8,
    pinned: bool = False,
    created_at: datetime | None = None,
) -> Memory:
    return Memory(
        conversation_id=conversation_id,
        memory_type="user_preference",
        content=content,
        normalized_content=normalize_content(content),
        importance=importance,
        confidence=confidence,
        tags=[],
        entities=[],
        source="manual",
        application_key=key,
        status=status,
        is_sensitive=False,
        is_pinned=pinned,
        is_locked=False,
        usage_count=0,
        memory_metadata={},
        created_at=created_at or datetime.now(UTC),
        updated_at=created_at or datetime.now(UTC),
    )


def test_retrieval_ranks_filters_and_bounds(db_session: Session) -> None:
    seed_database(db_session)
    conversation = db_session.query(Conversation).one()
    other = Conversation(
        character_id=conversation.character_id,
        roleplay_profile_id=conversation.roleplay_profile_id,
        title="Other",
    )
    db_session.add(other)
    db_session.flush()
    db_session.add_all(
        [
            memory(conversation.id, "a", "I prefer biryani for dinner"),
            memory(
                conversation.id,
                "b",
                "I collect antique clocks",
                importance=100,
            ),
            memory(conversation.id, "c", "Biryani was archived", status="archived"),
            memory(other.id, "d", "Biryani in another conversation"),
            memory(
                conversation.id,
                "e",
                "I like biryani",
                created_at=datetime.now(UTC) - timedelta(days=365),
                pinned=True,
            ),
        ]
    )
    db_session.commit()
    retrieval = MemoryRetrievalService(MemoryRepository(db_session), settings())
    result = retrieval.retrieve(
        conversation.id, "What biryani dinner do I prefer?", limit=2
    )
    assert len(result.items) == 2
    assert "biryani" in result.items[0].content.casefold()
    assert all("archived" not in item.content for item in result.items)
    assert all("another conversation" not in item.content for item in result.items)
    assert result.items[0].score.final_score >= result.items[1].score.final_score


def test_lifecycle_preserves_manual_and_locked(db_session: Session) -> None:
    conversation, user, character = seeded_exchange(db_session)
    automatic = memory(conversation.id, "auto", "Automatic fact")
    automatic.source = "model_candidate"
    automatic.source_character_message_id = character.id
    manual = memory(conversation.id, "manual", "Manual fact")
    locked = memory(conversation.id, "locked", "Locked fact")
    locked.source = "model_candidate"
    locked.source_character_message_id = character.id
    locked.is_locked = True
    db_session.add_all([automatic, manual, locked])
    db_session.commit()
    count = MemoryLifecycleService(db_session, settings()).invalidate_for_messages(
        conversation.id, [character.id], commit=True
    )
    assert count == 1
    assert automatic.status == "reverted"
    assert manual.status == locked.status == "active"
