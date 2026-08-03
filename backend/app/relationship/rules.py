from app.relationship.schemas import RelationshipEventType

RULES_VERSION = "1.0"

BASE_DELTAS: dict[RelationshipEventType, dict[str, int]] = {
    RelationshipEventType.SUPPORTIVE: {"trust": 2, "affection": 1, "comfort": 2},
    RelationshipEventType.AFFECTIONATE: {
        "affection": 2,
        "attraction": 1,
        "comfort": 1,
    },
    RelationshipEventType.ROMANTIC: {"attraction": 2, "affection": 2},
    RelationshipEventType.RESPECTFUL: {"respect": 2, "trust": 1},
    RelationshipEventType.PROTECTIVE: {"trust": 2, "affection": 1, "comfort": 1},
    RelationshipEventType.HONEST: {"trust": 2, "respect": 1},
    RelationshipEventType.VULNERABLE: {"trust": 2, "comfort": 2, "affection": 1},
    RelationshipEventType.APOLOGETIC: {"anger": -3, "trust": 1, "respect": 1},
    RelationshipEventType.REASSURING: {"comfort": 2, "jealousy": -1, "anger": -1},
    RelationshipEventType.HUMOROUS: {"comfort": 1, "affection": 1},
    RelationshipEventType.THOUGHTFUL: {"affection": 1, "respect": 1},
    RelationshipEventType.PROMISE_KEPT: {"trust": 4, "respect": 2},
    RelationshipEventType.CONFLICT_RESOLVED: {
        "anger": -4,
        "trust": 2,
        "comfort": 2,
    },
    RelationshipEventType.RUDE: {"respect": -3, "anger": 3, "affection": -1},
    RelationshipEventType.DISMISSIVE: {
        "comfort": -2,
        "affection": -2,
        "anger": 2,
    },
    RelationshipEventType.DISHONEST: {"trust": -5, "respect": -2},
    RelationshipEventType.MANIPULATIVE: {"trust": -5, "respect": -4, "anger": 3},
    RelationshipEventType.INSENSITIVE: {
        "comfort": -3,
        "affection": -2,
        "anger": 2,
    },
    RelationshipEventType.THREATENING: {"trust": -6, "comfort": -5, "anger": 5},
    RelationshipEventType.PROMISE_BROKEN: {"trust": -6, "respect": -3, "anger": 3},
    RelationshipEventType.DISRESPECTFUL: {"respect": -4, "anger": 3},
    RelationshipEventType.TRUST_BREACH: {"trust": -8, "respect": -4, "anger": 5},
    RelationshipEventType.CONFLICT_ESCALATED: {
        "anger": 4,
        "trust": -2,
        "comfort": -3,
    },
    RelationshipEventType.EMOTIONALLY_DISTANT: {"affection": -2, "comfort": -2},
}

NEGATIVE_EVENTS = {
    RelationshipEventType.RUDE,
    RelationshipEventType.DISMISSIVE,
    RelationshipEventType.DISHONEST,
    RelationshipEventType.MANIPULATIVE,
    RelationshipEventType.INSENSITIVE,
    RelationshipEventType.THREATENING,
    RelationshipEventType.PROMISE_BROKEN,
    RelationshipEventType.DISRESPECTFUL,
    RelationshipEventType.TRUST_BREACH,
    RelationshipEventType.CONFLICT_ESCALATED,
    RelationshipEventType.EMOTIONALLY_DISTANT,
}

POSITIVE_EVENTS = set(BASE_DELTAS) - NEGATIVE_EVENTS
