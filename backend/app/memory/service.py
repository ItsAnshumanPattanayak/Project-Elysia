from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.schemas import StructuredRoleplayResponse
from app.core.config import Settings
from app.db.base import utc_now
from app.memory.extraction import MemoryExtractionService
from app.memory.normalization import application_hash, tokens
from app.memory.schemas import MemoryProcessingResult
from app.memory.types import MemorySource
from app.models import Conversation, Memory, Message, MessageSender
from app.repositories.memories import MemoryRepository


class MemoryApplicationService:
    VERSION = "lexical-v1"

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repository = MemoryRepository(session)
        self.extractor = MemoryExtractionService(settings)

    @staticmethod
    def _overlap(left: str, right: str) -> float:
        a, b = tokens(left), tokens(right)
        return len(a & b) / max(1, len(a | b))

    def apply_exchange(
        self,
        conversation: Conversation,
        user: Message,
        character: Message,
        response: StructuredRoleplayResponse,
        *,
        commit: bool = True,
    ) -> MemoryProcessingResult:
        result = MemoryProcessingResult()
        if (
            not self.settings.memory_engine_enabled
            or not self.settings.memory_auto_extraction_enabled
        ):
            return result
        generation = int(character.message_metadata.get("regeneration_count", 0))
        candidates = self.extractor.extract(
            user.raw_content, response.memory_candidates
        )
        for candidate in candidates:
            identity = (
                user.id
                if candidate.source == MemorySource.DETERMINISTIC_USER_FACT
                else f"{user.id}:{character.id}:v{generation}"
            )
            digest = application_hash(
                candidate.memory_type.value,
                candidate.normalized_content,
                self.VERSION,
            )
            key = (
                f"memory:{conversation.id}:{candidate.source.value}:"
                f"{identity}:{digest}"
            )
            existing_key = self.repository.by_application_key(key)
            if existing_key is not None:
                if existing_key.status == "reverted":
                    existing_key.status = "active"
                    existing_key.reverted_at = None
                result.already_applied += 1
                result.memory_ids.append(existing_key.id)
                continue
            duplicate = self.repository.exact(
                conversation.id,
                candidate.normalized_content,
                candidate.memory_type.value,
            )
            if duplicate is None:
                duplicate = next(
                    (
                        item
                        for item in self.repository.active(conversation.id)
                        if item.memory_type == candidate.memory_type.value
                        and self._overlap(
                            item.normalized_content, candidate.normalized_content
                        )
                        >= 0.88
                    ),
                    None,
                )
            if duplicate is not None:
                prior_confirmations = list(
                    duplicate.memory_metadata.get("confirmations", [])
                )
                if any(
                    isinstance(item, dict) and item.get("application_key") == key
                    for item in prior_confirmations
                ):
                    result.already_applied += 1
                    result.memory_ids.append(duplicate.id)
                    continue
                duplicate.confidence = min(1.0, duplicate.confidence + 0.03)
                duplicate.importance = min(
                    100, max(duplicate.importance, candidate.importance)
                )
                duplicate.last_confirmed_at = utc_now()
                metadata = dict(duplicate.memory_metadata)
                confirmations = prior_confirmations
                confirmations.append(
                    {
                        "application_key": key,
                        "user_message_id": user.id,
                        "character_message_id": character.id,
                    }
                )
                metadata["confirmations"] = confirmations[-20:]
                duplicate.memory_metadata = metadata
                # Preserve retry identity without creating another active fact.
                # The confirmation key is retained and checked on future retries.
                result.consolidated += 1
                result.memory_ids.append(duplicate.id)
                continue
            conflict = (
                self.repository.fact(conversation.id, candidate.canonical_fact_key)
                if candidate.canonical_fact_key
                else None
            )
            if conflict is not None and conflict.is_locked:
                result.rejected += 1
                result.warnings.append("A candidate conflicted with a locked memory.")
                continue
            memory = Memory(
                conversation_id=conversation.id,
                source_user_message_id=user.id,
                source_character_message_id=(
                    character.id
                    if candidate.source == MemorySource.MODEL_CANDIDATE
                    else None
                ),
                memory_type=candidate.memory_type.value,
                content=candidate.content,
                normalized_content=candidate.normalized_content,
                canonical_fact_key=candidate.canonical_fact_key,
                importance=candidate.importance,
                confidence=candidate.confidence,
                tags=candidate.tags,
                entities=candidate.entities,
                source=candidate.source.value,
                application_key=key,
                status="active",
                is_sensitive=candidate.is_sensitive,
                is_pinned=False,
                is_locked=False,
                usage_count=0,
                last_confirmed_at=utc_now(),
                memory_metadata={
                    "extractor_version": self.VERSION,
                    "reason": candidate.reason,
                },
            )
            self.repository.add(memory)
            self.session.flush()
            if conflict is not None:
                conflict.status = "superseded"
                conflict.superseded_by_memory_id = memory.id
                memory.supersedes_memory_id = conflict.id
                result.superseded += 1
            result.created += 1
            result.memory_ids.append(memory.id)
        if commit:
            self.session.commit()
        return result


class MemoryLifecycleService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repository = MemoryRepository(session)
        self.application = MemoryApplicationService(session, settings)

    def invalidate_for_messages(
        self,
        conversation_id: int,
        message_ids: list[int],
        *,
        preserve_deterministic_user_ids: set[int] | None = None,
        commit: bool = False,
    ) -> int:
        now = utc_now()
        count = 0
        preserve = preserve_deterministic_user_ids or set()
        for memory in self.repository.source_linked(conversation_id, message_ids):
            if memory.source == MemorySource.MANUAL.value or memory.is_locked:
                continue
            if (
                memory.source == MemorySource.DETERMINISTIC_USER_FACT.value
                and memory.source_user_message_id in preserve
            ):
                continue
            memory.status = "reverted"
            memory.reverted_at = now
            count += 1
        if commit:
            self.session.commit()
        return count

    def rebuild(
        self, conversation: Conversation, *, commit: bool = True
    ) -> tuple[dict[str, int], dict[str, int], list[str]]:
        before = self.repository.count_by_status(conversation.id)
        automatic = list(
            self.session.scalars(
                select(Memory).where(
                    Memory.conversation_id == conversation.id,
                    Memory.source != MemorySource.MANUAL.value,
                    Memory.status == "active",
                )
            )
        )
        for memory in automatic:
            if not memory.is_locked:
                memory.status = "reverted"
                memory.reverted_at = utc_now()
        messages = list(
            self.session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.sequence_number)
            )
        )
        warnings: list[str] = []
        for index, user in enumerate(messages[:-1]):
            character = messages[index + 1]
            if (
                user.sender != MessageSender.USER
                or character.sender != MessageSender.CHARACTER
            ):
                continue
            raw = character.message_metadata.get("generation")
            if not isinstance(raw, dict) or not isinstance(
                raw.get("parsed_response"), dict
            ):
                warnings.append(
                    f"Skipped exchange ending at message {character.id}: "
                    "no retained structured metadata."
                )
                continue
            try:
                parsed = StructuredRoleplayResponse.model_validate(
                    raw["parsed_response"]
                )
                self.application.apply_exchange(
                    conversation, user, character, parsed, commit=False
                )
            except Exception:
                warnings.append(
                    f"Skipped exchange ending at message {character.id}: "
                    "invalid retained metadata."
                )
        if commit:
            self.session.commit()
        return before, self.repository.count_by_status(conversation.id), warnings
