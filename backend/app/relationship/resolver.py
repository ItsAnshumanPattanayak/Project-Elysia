import re

from app.ai.schemas import StructuredRoleplayResponse
from app.relationship.schemas import (
    EventEvidence,
    EventIntensity,
    EventSource,
    RelationshipEventType,
    ResolvedRelationshipEvent,
)

ALIASES = {
    "support": RelationshipEventType.SUPPORTIVE,
    "affection": RelationshipEventType.AFFECTIONATE,
    "apology": RelationshipEventType.APOLOGETIC,
    "reassurance": RelationshipEventType.REASSURING,
    "conflict_resolution": RelationshipEventType.CONFLICT_RESOLVED,
}

SIGNALS: list[tuple[RelationshipEventType, tuple[str, ...]]] = [
    (
        RelationshipEventType.THREATENING,
        ("i will hurt you", "i'll hurt you", "threaten you"),
    ),
    (RelationshipEventType.TRUST_BREACH, ("betrayed", "betrayal", "broke your trust")),
    (RelationshipEventType.DISHONEST, ("i lied", "jhooth bola", "dishonest")),
    (RelationshipEventType.DISRESPECTFUL, ("shut up", "stupid", "worthless")),
    (RelationshipEventType.APOLOGETIC, ("i am sorry", "i'm sorry", "maaf", "apolog")),
    (
        RelationshipEventType.REASSURING,
        ("i'm here", "main hoon", "don't worry", "safe with me"),
    ),
    (
        RelationshipEventType.SUPPORTIVE,
        ("theek ho", "with you", "support", "take care"),
    ),
    (RelationshipEventType.AFFECTIONATE, ("love you", "missed you", "care about you")),
    (RelationshipEventType.ROMANTIC, ("kiss", "romantic", "date with you")),
    (RelationshipEventType.HUMOROUS, ("haha", "laugh", "joke")),
    (RelationshipEventType.RESPECTFUL, ("respect", "proud of you", "admire")),
    (RelationshipEventType.CONFLICT_RESOLVED, ("we're okay", "forgive", "resolved")),
]


class RelationshipEventResolver:
    version = "1.0"

    def resolve(
        self,
        *,
        user_text: str,
        response: StructuredRoleplayResponse,
        recent_text: str = "",
        behaviour_hint: str | None = None,
    ) -> ResolvedRelationshipEvent:
        del behaviour_hint
        bounded = (
            f"{user_text[:5000]} {' '.join(response.dialogue_blocks)[:5000]}".lower()
        )
        evidence: list[EventEvidence] = []
        deterministic: RelationshipEventType | None = None
        for event_type, phrases in SIGNALS:
            match = next((phrase for phrase in phrases if phrase in bounded), None)
            if match:
                deterministic = event_type
                evidence.append(
                    EventEvidence(
                        kind="text_signal",
                        description=f"Matched the inspectable signal '{match}'.",
                    )
                )
                break

        suggestion = response.model_relationship_suggestion
        canonical_suggestion = response.relationship_event
        if (
            canonical_suggestion == RelationshipEventType.PROMISE_KEPT
            and not re.search(r"\bpromise|vaada\b", recent_text[-5000:], re.I)
        ):
            canonical_suggestion = None
            evidence.append(
                EventEvidence(
                    kind="guardrail",
                    description="Promise-kept suggestion lacked prior promise context.",
                )
            )
        if deterministic is not None:
            source = EventSource.DETERMINISTIC
            confidence = 0.85
            event_type = deterministic
            if canonical_suggestion == deterministic:
                confidence = 0.95
                source = EventSource.MODEL_SUGGESTED_VALIDATED
                evidence.append(
                    EventEvidence(
                        kind="model_support",
                        description=(
                            "Canonical model suggestion matched deterministic "
                            "evidence."
                        ),
                    )
                )
        elif canonical_suggestion is not None and response.emotion is not None:
            event_type = canonical_suggestion
            source = EventSource.MODEL_SUGGESTED_VALIDATED
            confidence = 0.65
            evidence.append(
                EventEvidence(
                    kind="model_support",
                    description=(
                        "Validated suggestion was supported by normalized emotion."
                    ),
                )
            )
        else:
            event_type = RelationshipEventType.NEUTRAL
            source = EventSource.DETERMINISTIC
            confidence = 0.4
            evidence.append(
                EventEvidence(
                    kind="conservative_default",
                    description="Evidence was insufficient for a scored event.",
                )
            )
        intensity = (
            EventIntensity.HIGH
            if any(
                token in bounded for token in ("very", "extremely", "never", "always")
            )
            else EventIntensity.NORMAL
        )
        return ResolvedRelationshipEvent(
            event_type=event_type,
            source=source,
            confidence=confidence,
            evidence=evidence,
            intensity=intensity,
            model_suggestion=suggestion,
            resolver_version=self.version,
        )
