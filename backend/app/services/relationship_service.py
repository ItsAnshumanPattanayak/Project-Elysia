from typing import Any
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.schemas import StructuredRoleplayResponse
from app.db.base import utc_now
from app.models import Conversation, Message, RelationshipEvent, RelationshipState
from app.relationship.engine import MoodResolver, RelationshipEngine, StageResolver
from app.relationship.resolver import RelationshipEventResolver
from app.relationship.schemas import (
    SCORE_FIELDS,
    EventSource,
    ManualRelationshipUpdate,
    Mood,
    RelationshipApplicationResult,
    RelationshipEventListResponse,
    RelationshipEventResponse,
    RelationshipEventType,
    RelationshipStage,
    RelationshipStateResponse,
    RelationshipValues,
)
from app.repositories.relationship_events import RelationshipEventRepository
from app.services.conversation_errors import (
    RelationshipProcessingError,
    RelationshipValueLockedError,
)


def _score_snapshot(state: RelationshipState) -> dict[str, int]:
    return {field: int(getattr(state, field)) for field in SCORE_FIELDS}


def _full_snapshot(state: RelationshipState) -> dict[str, Any]:
    return {
        **_score_snapshot(state),
        "mood": state.mood,
        "relationship_stage": state.relationship_stage,
    }


class RelationshipService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = RelationshipEventRepository(session)
        self.resolver = RelationshipEventResolver()
        self.engine = RelationshipEngine()
        self.moods = MoodResolver()
        self.stages = StageResolver()

    @staticmethod
    def ensure_baseline(state: RelationshipState) -> None:
        if not state.baseline_values:
            state.baseline_values = _full_snapshot(state)

    @staticmethod
    def _result(
        event: RelationshipEvent, already_applied: bool = False
    ) -> RelationshipApplicationResult:
        evidence = event.evidence if isinstance(event.evidence, list) else []
        suppressed = [
            str(item["field"])
            for item in evidence
            if isinstance(item, dict)
            and item.get("kind") == "lock_suppression"
            and item.get("field")
        ]
        return RelationshipApplicationResult(
            event_id=event.id,
            event_type=RelationshipEventType(event.event_type),
            source=EventSource(event.source),
            confidence=event.confidence,
            score_deltas=event.score_deltas,
            suppressed_by_locks=suppressed,
            values_before=RelationshipValues.model_validate(event.values_before),
            values_after=RelationshipValues.model_validate(event.values_after),
            mood_before=Mood(event.mood_before),
            mood_after=Mood(event.mood_after),
            stage_before=RelationshipStage(event.stage_before),
            stage_after=RelationshipStage(event.stage_after),
            application_key=event.application_key,
            already_applied=already_applied,
        )

    def apply_exchange(
        self,
        conversation: Conversation,
        user_message: Message,
        character_message: Message,
        response: StructuredRoleplayResponse,
        *,
        commit: bool = True,
    ) -> RelationshipApplicationResult:
        regeneration = int(
            character_message.message_metadata.get("regeneration_count", 0)
        )
        application_key = (
            f"exchange:{conversation.id}:{user_message.id}:"
            f"{character_message.id}:v{regeneration}"
        )
        existing = self.events.get_by_application_key(application_key)
        if existing is not None:
            return self._result(existing, already_applied=True)
        state = conversation.relationship_state
        if state is None:
            raise RelationshipProcessingError(
                "The conversation has no relationship state."
            )
        self.ensure_baseline(state)
        recent = self.events.recent(conversation.id, 10)
        recent_types = [RelationshipEventType(item.event_type) for item in recent]
        recent_text = " ".join(
            str(item.get("description", ""))
            for event in recent
            for item in event.evidence
            if isinstance(item, dict)
        )
        resolved = self.resolver.resolve(
            user_text=user_message.raw_content,
            response=response,
            recent_text=recent_text,
            behaviour_hint=(
                str(user_message.message_metadata.get("behaviour_hint"))
                if user_message.message_metadata.get("behaviour_hint")
                else None
            ),
        )
        before = _score_snapshot(state)
        deltas, suppressed = self.engine.calculate_deltas(
            resolved, before, state.locked_values, recent_types
        )
        after = self.engine.apply_deltas(before, deltas)
        previous_mood = Mood(state.mood)
        mood, mood_rule = self.moods.resolve(
            resolved.event_type,
            after,
            previous_mood,
            bool(state.locked_values.get("mood")),
        )
        previous_stage = RelationshipStage(state.relationship_stage)
        stage, stage_rule = self.stages.resolve(
            previous_stage,
            after,
            state.turn_count,
            [*recent_types, resolved.event_type],
            bool(state.locked_values.get("relationship_stage")),
        )
        for field, value in after.items():
            setattr(state, field, value)
        state.mood = mood.value
        state.relationship_stage = stage.value
        conversation.relationship_stage = stage.value
        evidence = [item.model_dump(mode="json") for item in resolved.evidence]
        evidence.extend(
            {
                "kind": "lock_suppression",
                "field": field,
                "description": "Automatic delta suppressed by a locked value.",
            }
            for field in suppressed
        )
        evidence.extend(
            [
                {"kind": "mood_rule", "description": mood_rule},
                {"kind": "stage_rule", "description": stage_rule},
                {"kind": "resolver_version", "description": resolved.resolver_version},
            ]
        )
        event = RelationshipEvent(
            conversation_id=conversation.id,
            source_user_message_id=user_message.id,
            source_character_message_id=character_message.id,
            event_type=resolved.event_type.value,
            source=resolved.source.value,
            confidence=resolved.confidence,
            evidence=evidence,
            score_deltas=deltas,
            values_before=before,
            values_after=after,
            mood_before=previous_mood.value,
            mood_after=mood.value,
            stage_before=previous_stage.value,
            stage_after=stage.value,
            application_key=application_key,
        )
        self.events.add(event)
        self.session.flush()
        character_message.message_metadata = {
            **character_message.message_metadata,
            "relationship_processing": {
                "event_id": event.id,
                "event_type": event.event_type,
                "application_key": application_key,
                "score_deltas": deltas,
                "mood": mood.value,
                "relationship_stage": stage.value,
            },
        }
        if commit:
            try:
                self.session.commit()
            except SQLAlchemyError as exc:
                self.session.rollback()
                raise RelationshipProcessingError(
                    "Relationship processing could not be persisted."
                ) from exc
        return self._result(event)

    def supersede_and_apply(
        self,
        conversation: Conversation,
        user_message: Message,
        character_message: Message,
        response: StructuredRoleplayResponse,
    ) -> RelationshipApplicationResult:
        for event in self.events.for_character_message(character_message.id):
            event.is_reverted = True
            event.reverted_at = utc_now()
        self.recalculate(conversation)
        try:
            return self.apply_exchange(
                conversation, user_message, character_message, response, commit=True
            )
        except Exception:
            self.session.rollback()
            raise

    def revert_for_messages(
        self,
        conversation: Conversation,
        message_ids: list[int],
        *,
        recalculate: bool = True,
    ) -> None:
        changed = False
        for event in self.events.for_message_ids(message_ids):
            event.is_reverted = True
            event.reverted_at = utc_now()
            changed = True
        if changed and recalculate:
            self.recalculate(conversation)

    def recalculate(self, conversation: Conversation) -> None:
        state = conversation.relationship_state
        if state is None:
            raise RelationshipProcessingError(
                "The conversation has no relationship state."
            )
        self.ensure_baseline(state)
        baseline = state.baseline_values
        values = {
            field: int(baseline.get(field, getattr(state, field)))
            for field in SCORE_FIELDS
        }
        mood = Mood(str(baseline.get("mood", "neutral")))
        stage = RelationshipStage(
            str(baseline.get("relationship_stage", conversation.relationship_stage))
        )
        recent_types: list[RelationshipEventType] = []
        for event in self.events.active(conversation.id):
            values = self.engine.apply_deltas(values, event.score_deltas)
            event_type = RelationshipEventType(event.event_type)
            recent_types.append(event_type)
            if event.source == EventSource.MANUAL.value:
                mood = Mood(event.mood_after)
                stage = RelationshipStage(event.stage_after)
            else:
                mood, _ = self.moods.resolve(
                    event_type,
                    values,
                    mood,
                    bool(state.locked_values.get("mood")),
                )
                stage, _ = self.stages.resolve(
                    stage,
                    values,
                    state.turn_count,
                    recent_types,
                    bool(state.locked_values.get("relationship_stage")),
                )
        for field, value in values.items():
            setattr(state, field, value)
        state.mood = mood.value
        state.relationship_stage = stage.value
        conversation.relationship_stage = stage.value

    def state(self, conversation: Conversation) -> RelationshipStateResponse:
        state = conversation.relationship_state
        if state is None:
            raise RelationshipProcessingError(
                "The conversation has no relationship state."
            )
        self.ensure_baseline(state)
        return RelationshipStateResponse(
            conversation_id=conversation.id,
            **_score_snapshot(state),
            mood=Mood(state.mood),
            relationship_stage=RelationshipStage(state.relationship_stage),
            turn_count=state.turn_count,
            locked_values={
                key: bool(value) for key, value in state.locked_values.items()
            },
            baseline_values=state.baseline_values,
            updated_at=state.updated_at,
        )

    def history(
        self,
        conversation_id: int,
        *,
        limit: int,
        offset: int,
        event_type: str | None = None,
        source: str | None = None,
        reverted: bool | None = None,
        oldest_first: bool = False,
    ) -> RelationshipEventListResponse:
        items, total = self.events.page(
            conversation_id,
            limit=limit,
            offset=offset,
            event_type=event_type,
            source=source,
            reverted=reverted,
            oldest_first=oldest_first,
        )
        return RelationshipEventListResponse(
            items=[RelationshipEventResponse.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )

    def manual_update(
        self, conversation: Conversation, payload: ManualRelationshipUpdate
    ) -> RelationshipApplicationResult:
        state = conversation.relationship_state
        if state is None:
            raise RelationshipProcessingError(
                "The conversation has no relationship state."
            )
        self.ensure_baseline(state)
        before = _score_snapshot(state)
        mood_before = Mood(state.mood)
        stage_before = RelationshipStage(state.relationship_stage)
        updates = payload.model_dump(
            exclude={"locked_values", "force", "reason"}, exclude_none=True
        )
        for field in updates:
            if bool(state.locked_values.get(field)) and not payload.force:
                raise RelationshipValueLockedError(
                    f"Relationship value '{field}' is locked."
                )
        for field, value in updates.items():
            setattr(state, field, value.value if hasattr(value, "value") else value)
        lock_updates = {str(key): value for key, value in payload.locked_values.items()}
        state.locked_values = {**state.locked_values, **lock_updates}
        conversation.relationship_stage = state.relationship_stage
        after = _score_snapshot(state)
        deltas = {
            field: after[field] - before[field]
            for field in SCORE_FIELDS
            if after[field] != before[field]
        }
        event = RelationshipEvent(
            conversation_id=conversation.id,
            event_type=RelationshipEventType.NEUTRAL.value,
            source=EventSource.MANUAL.value,
            confidence=1.0,
            evidence=[{"kind": "manual_reason", "description": payload.reason}],
            score_deltas=deltas,
            values_before=before,
            values_after=after,
            mood_before=mood_before.value,
            mood_after=state.mood,
            stage_before=stage_before.value,
            stage_after=state.relationship_stage,
            application_key=f"manual:{conversation.id}:{uuid4()}",
        )
        self.events.add(event)
        self.session.flush()
        self.session.commit()
        return self._result(event)
