import pytest

from app.ai.schemas import StructuredRoleplayResponse
from app.relationship.engine import MoodResolver, RelationshipEngine, StageResolver
from app.relationship.resolver import RelationshipEventResolver
from app.relationship.schemas import (
    EventIntensity,
    EventSource,
    Mood,
    RelationshipEventType,
    RelationshipStage,
    ResolvedRelationshipEvent,
)


def scores(**overrides: int) -> dict[str, int]:
    value = {
        "attraction": 70,
        "trust": 75,
        "affection": 72,
        "respect": 80,
        "comfort": 70,
        "jealousy": 20,
        "anger": 0,
    }
    value.update(overrides)
    return value


def event(
    event_type: RelationshipEventType,
    intensity: EventIntensity = EventIntensity.NORMAL,
) -> ResolvedRelationshipEvent:
    return ResolvedRelationshipEvent(
        event_type=event_type,
        source=EventSource.DETERMINISTIC,
        confidence=0.8,
        intensity=intensity,
    )


def test_base_deltas_and_clamping() -> None:
    engine = RelationshipEngine()
    deltas, suppressed = engine.calculate_deltas(
        event(RelationshipEventType.SUPPORTIVE), scores(), {}, []
    )
    assert deltas == {"trust": 2, "affection": 1, "comfort": 2}
    assert suppressed == []
    assert engine.apply_deltas(scores(trust=99), {"trust": 5})["trust"] == 100
    assert engine.apply_deltas(scores(anger=1), {"anger": -5})["anger"] == 0


def test_intensity_boundaries_and_diminishing_returns() -> None:
    engine = RelationshipEngine()
    high, _ = engine.calculate_deltas(
        event(RelationshipEventType.SUPPORTIVE, EventIntensity.HIGH), scores(), {}, []
    )
    repeated, _ = engine.calculate_deltas(
        event(RelationshipEventType.SUPPORTIVE),
        scores(),
        {},
        [RelationshipEventType.SUPPORTIVE, RelationshipEventType.SUPPORTIVE],
    )
    near_cap, _ = engine.calculate_deltas(
        event(RelationshipEventType.SUPPORTIVE), scores(trust=95), {}, []
    )
    assert high["trust"] == 3
    assert repeated["trust"] == 1
    assert near_cap["trust"] == 1


def test_context_modifiers_and_locks() -> None:
    engine = RelationshipEngine()
    apology, _ = engine.calculate_deltas(
        event(RelationshipEventType.APOLOGETIC), scores(anger=30), {}, []
    )
    assert apology == {"anger": -3, "trust": 0, "respect": 0}
    reassurance, suppressed = engine.calculate_deltas(
        event(RelationshipEventType.REASSURING),
        scores(jealousy=60),
        {"comfort": True},
        [],
    )
    assert reassurance["jealousy"] == -2
    assert reassurance["comfort"] == 0
    assert suppressed == ["comfort"]
    romantic, _ = engine.calculate_deltas(
        event(RelationshipEventType.ROMANTIC), scores(anger=70), {}, []
    )
    assert romantic == {"attraction": 1, "affection": 1}


@pytest.mark.parametrize(
    ("event_type", "values", "expected"),
    [
        (RelationshipEventType.RUDE, scores(anger=70), Mood.ANGRY),
        (RelationshipEventType.TRUST_BREACH, scores(anger=20), Mood.SUSPICIOUS),
        (RelationshipEventType.JEALOUS, scores(jealousy=70), Mood.JEALOUS),
        (RelationshipEventType.CONFLICT_RESOLVED, scores(), Mood.RELIEVED),
        (RelationshipEventType.PROTECTIVE, scores(), Mood.PROTECTIVE),
        (RelationshipEventType.ROMANTIC, scores(), Mood.ROMANTIC),
        (RelationshipEventType.HUMOROUS, scores(), Mood.PLAYFUL),
    ],
)
def test_mood_rules(
    event_type: RelationshipEventType,
    values: dict[str, int],
    expected: Mood,
) -> None:
    mood, reason = MoodResolver().resolve(event_type, values, Mood.AFFECTIONATE, False)
    assert mood == expected
    assert reason


def test_mood_lock_preserves_value() -> None:
    mood, reason = MoodResolver().resolve(
        RelationshipEventType.TRUST_BREACH,
        scores(anger=90),
        Mood.HAPPY,
        True,
    )
    assert (mood, reason) == (Mood.HAPPY, "mood_locked")


def test_stage_progression_is_conservative_and_single_step() -> None:
    resolver = StageResolver()
    unchanged, _ = resolver.resolve(
        RelationshipStage.COMMITTED,
        scores(),
        1,
        [RelationshipEventType.SUPPORTIVE],
        False,
    )
    bonded, _ = resolver.resolve(
        RelationshipStage.COMMITTED,
        scores(trust=90, affection=90, respect=90, comfort=90),
        35,
        [RelationshipEventType.SUPPORTIVE] * 5,
        False,
    )
    progressed, _ = resolver.resolve(
        RelationshipStage.FRIENDS,
        scores(trust=70, respect=70, comfort=70),
        20,
        [RelationshipEventType.SUPPORTIVE] * 5,
        False,
    )
    assert unchanged == RelationshipStage.COMMITTED
    assert bonded == RelationshipStage.DEEPLY_BONDED
    assert progressed == RelationshipStage.CLOSE_FRIENDS


def test_stage_regression_recovery_and_lock() -> None:
    resolver = StageResolver()
    strained, _ = resolver.resolve(
        RelationshipStage.COMMITTED,
        scores(anger=75),
        10,
        [RelationshipEventType.RUDE, RelationshipEventType.TRUST_BREACH],
        False,
    )
    recovered, _ = resolver.resolve(
        RelationshipStage.STRAINED,
        scores(trust=60, anger=10),
        20,
        [RelationshipEventType.SUPPORTIVE] * 3,
        False,
    )
    locked, _ = resolver.resolve(
        RelationshipStage.COMMITTED,
        scores(anger=100),
        20,
        [RelationshipEventType.TRUST_BREACH] * 3,
        True,
    )
    assert strained == RelationshipStage.STRAINED
    assert recovered == RelationshipStage.FRIENDS
    assert locked == RelationshipStage.COMMITTED


def test_resolver_is_conservative_and_validates_model_suggestions() -> None:
    resolver = RelationshipEventResolver()
    arbitrary = resolver.resolve(
        user_text="Normal update.",
        response=StructuredRoleplayResponse(
            dialogue_blocks=["The report is ready."],
            model_relationship_suggestion="increase_everything",
            raw_text="The report is ready.",
        ),
    )
    supportive = resolver.resolve(
        user_text="Aaj difficult tha.",
        response=StructuredRoleplayResponse(
            dialogue_blocks=["Tum theek ho? I'm with you."],
            emotion=Mood.CONCERNED,
            relationship_event=RelationshipEventType.SUPPORTIVE,
            model_relationship_suggestion="supportive",
            raw_text="Tum theek ho?",
        ),
    )
    assert arbitrary.event_type == RelationshipEventType.NEUTRAL
    assert supportive.event_type == RelationshipEventType.SUPPORTIVE
    assert supportive.source == EventSource.MODEL_SUGGESTED_VALIDATED


def test_resolver_ignores_threat_only_in_fictional_narration() -> None:
    resolved = RelationshipEventResolver().resolve(
        user_text="Continue the fictional scene.",
        response=StructuredRoleplayResponse(
            narration_blocks=["The villain threatens someone in the distant scene."],
            dialogue_blocks=["Let's leave this place."],
            raw_text="Fictional scene",
        ),
    )
    assert resolved.event_type == RelationshipEventType.NEUTRAL


def test_promise_kept_requires_supporting_context() -> None:
    response = StructuredRoleplayResponse(
        dialogue_blocks=["I did it."],
        emotion=Mood.HAPPY,
        relationship_event=RelationshipEventType.PROMISE_KEPT,
        model_relationship_suggestion="promise_kept",
        raw_text="I did it.",
    )
    without = RelationshipEventResolver().resolve(
        user_text="Thanks.", response=response, recent_text="ordinary context"
    )
    with_context = RelationshipEventResolver().resolve(
        user_text="Thanks.",
        response=response,
        recent_text="She made a promise earlier.",
    )
    assert without.event_type == RelationshipEventType.NEUTRAL
    assert with_context.event_type == RelationshipEventType.PROMISE_KEPT
