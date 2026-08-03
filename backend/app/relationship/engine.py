import math

from app.relationship.rules import BASE_DELTAS, NEGATIVE_EVENTS, POSITIVE_EVENTS
from app.relationship.schemas import (
    SCORE_FIELDS,
    EventIntensity,
    Mood,
    RelationshipEventType,
    RelationshipStage,
    ResolvedRelationshipEvent,
)


def _scaled(value: int, factor: float) -> int:
    if value == 0 or factor == 0:
        return 0
    magnitude = max(1, math.floor(abs(value) * factor + 0.5))
    return magnitude if value > 0 else -magnitude


class RelationshipEngine:
    def calculate_deltas(
        self,
        event: ResolvedRelationshipEvent,
        current: dict[str, int],
        locked_values: dict[str, object],
        recent_types: list[RelationshipEventType],
    ) -> tuple[dict[str, int], list[str]]:
        deltas = dict(BASE_DELTAS.get(event.event_type, {}))
        factor = {
            EventIntensity.LOW: 0.5,
            EventIntensity.NORMAL: 1.0,
            EventIntensity.HIGH: 1.5,
        }[event.intensity]
        repetitions = recent_types[-5:].count(event.event_type)
        if event.event_type in POSITIVE_EVENTS and repetitions:
            factor *= 0.5 ** min(repetitions, 2)
        if event.event_type == RelationshipEventType.APOLOGETIC and not any(
            item in NEGATIVE_EVENTS for item in recent_types[-5:]
        ):
            deltas["trust"] = 0
            deltas["respect"] = 0
        if (
            event.event_type == RelationshipEventType.REASSURING
            and current["jealousy"] >= 40
        ):
            deltas["jealousy"] = -2
        if (
            event.event_type == RelationshipEventType.ROMANTIC
            and current["anger"] >= 60
        ):
            factor *= 0.5

        result: dict[str, int] = {}
        suppressed: list[str] = []
        for field, raw_delta in deltas.items():
            if field not in SCORE_FIELDS:
                continue
            if bool(locked_values.get(field)):
                suppressed.append(field)
                result[field] = 0
                continue
            boundary_factor = 1.0
            if raw_delta > 0 and current[field] >= 90:
                boundary_factor = 0.5
            elif raw_delta < 0 and current[field] <= 10:
                boundary_factor = 0.5
            result[field] = _scaled(raw_delta, factor * boundary_factor)
        return result, suppressed

    @staticmethod
    def apply_deltas(current: dict[str, int], deltas: dict[str, int]) -> dict[str, int]:
        return {
            field: max(0, min(100, current[field] + deltas.get(field, 0)))
            for field in SCORE_FIELDS
        }


class MoodResolver:
    version = "1.0"

    def resolve(
        self,
        event_type: RelationshipEventType,
        values: dict[str, int],
        previous: Mood,
        locked: bool,
    ) -> tuple[Mood, str]:
        if locked:
            return previous, "mood_locked"
        if values["anger"] >= 60:
            return Mood.ANGRY, "high_anger"
        if event_type in {
            RelationshipEventType.TRUST_BREACH,
            RelationshipEventType.DISHONEST,
        }:
            return (
                (Mood.SUSPICIOUS, "trust_breach_suspicion")
                if values["anger"] < 40
                else (Mood.HURT, "trust_breach_hurt")
            )
        if values["jealousy"] >= 60 or event_type == RelationshipEventType.JEALOUS:
            return Mood.JEALOUS, "high_jealousy"
        mapping = {
            RelationshipEventType.CONFLICT_RESOLVED: (
                Mood.RELIEVED,
                "conflict_resolved",
            ),
            RelationshipEventType.PROTECTIVE: (Mood.PROTECTIVE, "protective_event"),
            RelationshipEventType.CONCERNED: (Mood.CONCERNED, "concern_event"),
            RelationshipEventType.ROMANTIC: (Mood.ROMANTIC, "romantic_event"),
            RelationshipEventType.HUMOROUS: (Mood.PLAYFUL, "humorous_event"),
            RelationshipEventType.PLAYFUL: (Mood.PLAYFUL, "playful_event"),
        }
        if event_type in mapping:
            return mapping[event_type]
        if (
            event_type
            in {
                RelationshipEventType.SUPPORTIVE,
                RelationshipEventType.AFFECTIONATE,
                RelationshipEventType.REASSURING,
            }
            and values["affection"] >= 60
        ):
            return Mood.AFFECTIONATE, "positive_high_affection"
        return (
            previous if previous != Mood.NEUTRAL else Mood.NEUTRAL
        ), "preserve_previous"


class StageResolver:
    version = "1.0"
    ORDER = [
        RelationshipStage.STRANGERS,
        RelationshipStage.ACQUAINTANCES,
        RelationshipStage.FRIENDS,
        RelationshipStage.CLOSE_FRIENDS,
        RelationshipStage.INTERESTED,
        RelationshipStage.DATING,
        RelationshipStage.COMMITTED,
        RelationshipStage.DEEPLY_BONDED,
    ]

    def resolve(
        self,
        current: RelationshipStage,
        values: dict[str, int],
        turn_count: int,
        recent_types: list[RelationshipEventType],
        locked: bool,
    ) -> tuple[RelationshipStage, str]:
        if locked:
            return current, "stage_locked"
        severe = recent_types[-5:].count(RelationshipEventType.TRUST_BREACH)
        negatives = sum(item in NEGATIVE_EVENTS for item in recent_types[-5:])
        if (
            values["trust"] <= 20
            and values["respect"] <= 20
            and turn_count >= 10
            and severe >= 2
        ):
            return RelationshipStage.SEPARATED, "sustained_severe_breach"
        if negatives >= 2 or values["anger"] >= 70 or values["trust"] <= 35:
            return RelationshipStage.STRAINED, "serious_negative_conditions"
        if current == RelationshipStage.STRAINED:
            positives = sum(item in POSITIVE_EVENTS for item in recent_types[-5:])
            if positives >= 3 and values["trust"] >= 50 and values["anger"] <= 30:
                return RelationshipStage.FRIENDS, "sustained_recovery"
            return current, "recovery_not_sustained"
        if current == RelationshipStage.SEPARATED:
            return current, "separation_requires_manual_change"
        if current == RelationshipStage.COMMITTED:
            if (
                turn_count >= 30
                and min(
                    values["trust"],
                    values["affection"],
                    values["respect"],
                    values["comfort"],
                )
                >= 85
                and values["anger"] <= 20
            ):
                return RelationshipStage.DEEPLY_BONDED, "committed_thresholds_met"
            return current, "committed_preserved"
        index = self.ORDER.index(current)
        if (
            turn_count >= (index + 1) * 5
            and min(values["trust"], values["respect"], values["comfort"]) >= 60
            and index < len(self.ORDER) - 1
        ):
            return self.ORDER[index + 1], "single_step_progression"
        return current, "thresholds_not_met"
