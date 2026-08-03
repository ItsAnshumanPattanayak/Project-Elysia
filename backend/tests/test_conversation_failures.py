import asyncio

import pytest
from conftest import FakeProvider
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.seed import seed_database
from app.models import Conversation, Message, MessageSender, RelationshipState
from app.schemas.message_api import SendMessageRequest
from app.services.ai_service import AIService
from app.services.conversation_errors import (
    ConversationBusyError,
    ResponsePersistenceError,
    StreamOutputLimitError,
)
from app.services.conversation_lock_service import ConversationLockService
from app.services.conversation_service import ConversationService


def service_setup(
    session: Session,
    ai_service: AIService,
    **settings_overrides: object,
) -> tuple[int, ConversationService, ConversationLockService]:
    seed_database(session)
    conversation_id = session.scalar(select(Conversation.id))
    assert conversation_id is not None
    settings = Settings(
        _env_file=None,
        database_url="sqlite:///:memory:",
        environment="test",
        ollama_model="test-model",
        **settings_overrides,
    )
    locks = ConversationLockService()
    return (
        conversation_id,
        ConversationService(session, settings, ai_service, locks),
        locks,
    )


def rows(session: Session, conversation_id: int) -> list[Message]:
    return list(
        session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_number)
        )
    )


@pytest.mark.asyncio
async def test_user_persistence_failure_prevents_provider_call(
    db_session: Session,
    ai_service: AIService,
    fake_provider: FakeProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation_id, service, _ = service_setup(db_session, ai_service)

    def fail_commit() -> None:
        raise SQLAlchemyError("test failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(ResponsePersistenceError):
        await service.send(conversation_id, SendMessageRequest(content="Do not call"))
    assert fake_provider.generate_calls == 0
    assert rows(db_session, conversation_id) == []


@pytest.mark.asyncio
async def test_character_persistence_failure_keeps_user_and_turn_zero(
    db_session: Session,
    ai_service: AIService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation_id, service, _ = service_setup(db_session, ai_service)
    original_commit = db_session.commit
    commit_calls = 0

    def fail_second_commit() -> None:
        nonlocal commit_calls
        commit_calls += 1
        if commit_calls == 2:
            raise SQLAlchemyError("test character persistence failure")
        original_commit()

    monkeypatch.setattr(db_session, "commit", fail_second_commit)
    with pytest.raises(ResponsePersistenceError):
        await service.send(conversation_id, SendMessageRequest(content="Keep me"))
    assert [item.sender for item in rows(db_session, conversation_id)] == [
        MessageSender.USER
    ]
    state = db_session.scalar(select(RelationshipState))
    assert state is not None and state.turn_count == 0


@pytest.mark.asyncio
async def test_busy_lock_times_out_then_registry_cleans_up(
    db_session: Session, ai_service: AIService
) -> None:
    conversation_id, service, locks = service_setup(
        db_session, ai_service, conversation_lock_timeout_seconds=0.01
    )
    async with locks.acquire(conversation_id, 1):
        with pytest.raises(ConversationBusyError):
            await service.send(conversation_id, SendMessageRequest(content="Busy"))
        assert locks.registry_size == 1
    assert locks.registry_size == 0
    assert rows(db_session, conversation_id) == []


@pytest.mark.asyncio
async def test_stream_size_limit_keeps_user_and_releases_lock(
    db_session: Session,
    ai_service: AIService,
    fake_provider: FakeProvider,
) -> None:
    conversation_id, service, locks = service_setup(
        db_session, ai_service, stream_max_accumulated_characters=1000
    )
    fake_provider.stream_tokens = ["x" * 1001]
    with pytest.raises(StreamOutputLimitError):
        _ = [
            event
            async for event in service.stream_send(
                conversation_id, SendMessageRequest(content="Bound this")
            )
        ]
    assert [item.sender for item in rows(db_session, conversation_id)] == [
        MessageSender.USER
    ]
    assert locks.registry_size == 0
    assert db_session.scalar(select(RelationshipState.turn_count)) == 0


@pytest.mark.asyncio
async def test_stream_cancellation_keeps_user_and_releases_lock(
    db_session: Session,
    ai_service: AIService,
    fake_provider: FakeProvider,
) -> None:
    conversation_id, service, locks = service_setup(db_session, ai_service)
    fake_provider.delay_seconds = 1
    stream = service.stream_send(
        conversation_id, SendMessageRequest(content="Cancel this")
    )
    assert (await anext(stream)).event == "accepted"
    assert (await anext(stream)).event == "user_message"
    assert (await anext(stream)).event == "start"
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    await stream.aclose()
    assert [item.sender for item in rows(db_session, conversation_id)] == [
        MessageSender.USER
    ]
    assert db_session.scalar(select(RelationshipState.turn_count)) == 0
    assert locks.registry_size == 0


def test_context_recent_limit_and_chronological_order(
    db_session: Session, ai_service: AIService
) -> None:
    conversation_id, service, _ = service_setup(
        db_session, ai_service, conversation_recent_message_limit=20
    )
    db_session.add_all(
        [
            Message(
                conversation_id=conversation_id,
                sender=MessageSender.USER,
                raw_content=f"message-{number}",
                sequence_number=number,
            )
            for number in range(1, 26)
        ]
    )
    db_session.commit()
    conversation = service.conversations.get(conversation_id)
    assert conversation is not None
    context = service.context_builder.build(conversation)
    assert len(context.recent_messages) == 20
    assert context.recent_messages[0].content == "message-6"
    assert context.recent_messages[-1].content == "message-25"


def test_confirmed_earlier_delete_truncates_and_recalculates(
    db_session: Session, ai_service: AIService
) -> None:
    conversation_id, service, _ = service_setup(db_session, ai_service)
    db_session.add_all(
        [
            Message(
                conversation_id=conversation_id,
                sender=sender,
                raw_content=f"message-{sequence}",
                sequence_number=sequence,
            )
            for sequence, sender in (
                (1, MessageSender.USER),
                (2, MessageSender.CHARACTER),
                (3, MessageSender.USER),
                (4, MessageSender.CHARACTER),
            )
        ]
    )
    state = db_session.scalar(select(RelationshipState))
    assert state is not None
    state.turn_count = 2
    db_session.commit()
    first_character = rows(db_session, conversation_id)[1]
    service.delete_message(
        conversation_id,
        first_character.id,
        confirm_truncate=True,
    )
    assert [
        (item.sequence_number, item.sender)
        for item in rows(db_session, conversation_id)
    ] == [(1, MessageSender.USER)]
    assert state.turn_count == 0
