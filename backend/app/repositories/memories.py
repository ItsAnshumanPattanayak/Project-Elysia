from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Memory


class MemoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, memory_id: int) -> Memory | None:
        return self.session.get(Memory, memory_id)

    def by_application_key(self, key: str) -> Memory | None:
        return self.session.scalar(select(Memory).where(Memory.application_key == key))

    def exact(
        self, conversation_id: int, normalized: str, memory_type: str
    ) -> Memory | None:
        return self.session.scalar(
            select(Memory).where(
                Memory.conversation_id == conversation_id,
                Memory.normalized_content == normalized,
                Memory.memory_type == memory_type,
                Memory.status == "active",
            )
        )

    def fact(self, conversation_id: int, key: str) -> Memory | None:
        return self.session.scalar(
            select(Memory)
            .where(
                Memory.conversation_id == conversation_id,
                Memory.canonical_fact_key == key,
                Memory.status == "active",
            )
            .order_by(Memory.created_at.desc())
        )

    def active(self, conversation_id: int) -> list[Memory]:
        return list(
            self.session.scalars(
                select(Memory)
                .where(
                    Memory.conversation_id == conversation_id, Memory.status == "active"
                )
                .order_by(Memory.created_at.desc())
            )
        )

    def page(
        self,
        conversation_id: int,
        *,
        limit: int,
        offset: int,
        status: str | None = None,
        memory_type: str | None = None,
        source: str | None = None,
        pinned: bool | None = None,
        locked: bool | None = None,
        sensitive: bool | None = None,
        query: str | None = None,
    ) -> tuple[list[Memory], int]:
        filters = [Memory.conversation_id == conversation_id]
        if status is not None:
            filters.append(Memory.status == status)
        if memory_type is not None:
            filters.append(Memory.memory_type == memory_type)
        if source is not None:
            filters.append(Memory.source == source)
        if pinned is not None:
            filters.append(Memory.is_pinned == pinned)
        if locked is not None:
            filters.append(Memory.is_locked == locked)
        if sensitive is not None:
            filters.append(Memory.is_sensitive == sensitive)
        if query:
            escaped = query.replace("%", "\\%").replace("_", "\\_")
            filters.append(
                or_(
                    Memory.content.ilike(f"%{escaped}%", escape="\\"),
                    Memory.normalized_content.ilike(f"%{escaped}%", escape="\\"),
                )
            )
        total = int(
            self.session.scalar(select(func.count(Memory.id)).where(*filters)) or 0
        )
        items = list(
            self.session.scalars(
                select(Memory)
                .where(*filters)
                .order_by(
                    Memory.is_pinned.desc(), Memory.updated_at.desc(), Memory.id.desc()
                )
                .offset(offset)
                .limit(limit)
            )
        )
        return items, total

    def source_linked(
        self, conversation_id: int, message_ids: list[int]
    ) -> list[Memory]:
        if not message_ids:
            return []
        return list(
            self.session.scalars(
                select(Memory).where(
                    Memory.conversation_id == conversation_id,
                    or_(
                        Memory.source_user_message_id.in_(message_ids),
                        Memory.source_character_message_id.in_(message_ids),
                    ),
                    Memory.status == "active",
                )
            )
        )

    def add(self, memory: Memory) -> None:
        self.session.add(memory)

    def count_by_status(self, conversation_id: int) -> dict[str, int]:
        rows = self.session.execute(
            select(Memory.status, func.count(Memory.id))
            .where(Memory.conversation_id == conversation_id)
            .group_by(Memory.status)
        )
        return {str(status): int(count) for status, count in rows}

    def record_usage(self, ids: list[int], used_at: datetime) -> None:
        for memory in self.session.scalars(select(Memory).where(Memory.id.in_(ids))):
            memory.usage_count += 1
            memory.last_used_at = used_at
