import math
from datetime import UTC, datetime

from app.core.config import Settings
from app.memory.normalization import tokens
from app.memory.schemas import MemoryScoreBreakdown, MemorySelectionResult, RankedMemory
from app.memory.types import MemoryType
from app.models import Memory
from app.repositories.memories import MemoryRepository


class MemoryRetrievalService:
    def __init__(self, repository: MemoryRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def _score(self, memory: Memory, query: str, now: datetime) -> MemoryScoreBreakdown:
        query_tokens = tokens(query)
        content_tokens = tokens(memory.normalized_content)
        lexical = len(query_tokens & content_tokens) / max(
            1, len(query_tokens | content_tokens)
        )
        tag_tokens = tokens(" ".join([*memory.tags, *memory.entities]))
        tag_entity = len(query_tokens & tag_tokens) / max(1, len(query_tokens))
        created = memory.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        age_days = max(0.0, (now - created).total_seconds() / 86400)
        recency = math.pow(0.5, age_days / self.settings.memory_recency_half_life_days)
        pinned = (
            self.settings.memory_pinned_bonus
            if memory.is_pinned and (lexical > 0 or tag_entity > 0)
            else (self.settings.memory_pinned_bonus * 0.5 if memory.is_pinned else 0.0)
        )
        final = min(
            1.0,
            0.35 * lexical
            + 0.20 * (memory.importance / 100)
            + 0.15 * memory.confidence
            + 0.10 * recency
            + 0.10 * tag_entity
            + pinned,
        )
        return MemoryScoreBreakdown(
            lexical=round(lexical, 6),
            importance=round(memory.importance / 100, 6),
            confidence=round(memory.confidence, 6),
            recency=round(recency, 6),
            tag_entity=round(tag_entity, 6),
            pinned_type=round(pinned, 6),
            final_score=round(final, 6),
        )

    def retrieve(
        self,
        conversation_id: int,
        query: str,
        *,
        limit: int | None = None,
        memory_types: set[str] | None = None,
        now: datetime | None = None,
    ) -> MemorySelectionResult:
        current = now or datetime.now(UTC)
        scored: list[tuple[Memory, MemoryScoreBreakdown]] = []
        for memory in self.repository.active(conversation_id):
            if memory_types and memory.memory_type not in memory_types:
                continue
            breakdown = self._score(memory, query, current)
            if breakdown.final_score >= self.settings.memory_min_relevance_score:
                scored.append((memory, breakdown))
        scored.sort(
            key=lambda item: (
                -item[1].final_score,
                -int(item[0].is_pinned),
                -item[0].importance,
                item[0].id,
            )
        )
        selected: list[RankedMemory] = []
        characters = 0
        for memory, breakdown in scored:
            if len(selected) >= (limit or self.settings.memory_retrieval_limit):
                break
            if (
                len(memory.content) > self.settings.memory_max_content_length
                or characters + len(memory.content)
                > self.settings.memory_retrieval_max_characters
            ):
                continue
            selected.append(
                RankedMemory(
                    id=memory.id,
                    content=memory.content,
                    memory_type=MemoryType(memory.memory_type),
                    importance=memory.importance,
                    score=breakdown,
                    created_at=memory.created_at,
                )
            )
            characters += len(memory.content)
        return MemorySelectionResult(
            items=selected,
            selected_ids=[item.id for item in selected],
            total_characters=characters,
        )
