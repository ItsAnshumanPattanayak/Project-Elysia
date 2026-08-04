# Relationship Engine

The [relationship dashboard](RELATIONSHIP_DASHBOARD.md) manages this deterministic
engine. Manual changes are audited, locks suppress automatic changes, and recovery
recalculation replays active history without AI or message/memory mutation.

Batch 4 applies deterministic relationship changes only after a completed character reply has been persisted. The model may suggest an event label, but it cannot provide numeric score changes. The backend validates suggestions against a controlled taxonomy and inspectable text/context signals; insufficient evidence becomes `neutral`.

## Pipeline

```text
completed user + character messages
    → normalized structured response
    → event resolver
    → centralized score rules and modifiers
    → mood resolver
    → conservative stage resolver
    → RelationshipState + immutable audit event
```

Every event stores its source messages, confidence, bounded evidence, effective deltas, before/after values, mood/stage transition, application key, and reversion state. Evidence contains short rule identifiers/descriptions, never hidden prompts or unrestricted private model output.

## Scoring rules

Base deltas are centralized in `app/relationship/rules.py`. They cover supportive, affectionate, romantic, respectful, protective, honest, vulnerable, apologetic, reassuring, humorous, thoughtful, promise-kept, conflict-resolved, and negative conflict/trust events.

Deterministic modifiers are:

- Low/normal/high intensity scales deltas by 0.5/1/1.5.
- Repeated positive events in the latest five active events receive 0.5, then 0.25 scaling.
- Positive changes at 90+ and negative changes at 10 or lower are halved.
- An apology without a recent negative event receives no trust/respect gain, though anger may fall.
- Reassurance at jealousy 40+ reduces jealousy by two.
- Romantic positives at anger 60+ are halved.
- Promise-kept requires bounded prior promise evidence or manual control.
- Locked fields suppress automatic deltas and are recorded in event evidence.
- All values are clamped to 0–100.

## Mood and stage

Mood is calculated without AI. High anger, trust breach, jealousy, reconciliation, protection, concern, romance, humor, and high-affection support use ordered explicit rules. Otherwise the previous mood is preserved. A mood lock wins over automatic rules.

Stages are `strangers`, `acquaintances`, `friends`, `close_friends`, `interested`, `dating`, `committed`, `deeply_bonded`, `strained`, and `separated`. Positive progression is at most one stage and requires minimum turns plus score thresholds. `committed` requires at least 30 turns and four scores at 85+ to become `deeply_bonded`. Serious negative conditions can enter `strained`; `separated` requires sustained severe breaches. Recovery from `strained` requires at least three recent positives. Separation recovery is manual in Version 1.

## Idempotency and replay

Exchange keys include conversation, user-message, character-message, and regeneration version. The database enforces uniqueness. Duplicate send retries return the saved exchange and cannot apply a second event.

Each relationship state has an immutable `baseline_values` snapshot. Editing/deleting history marks sourced events reverted, then deterministically replays remaining active event deltas from that baseline. Regeneration atomically reverts the prior event and applies the new response version. Failed regeneration preserves its prior message, event, and state.

Chat persistence and relationship persistence are separate short transactions. If relationship processing fails, completed chat remains saved and the API returns a warning. No `Memory` rows are created.

## Manual control

`GET /api/conversations/{id}/relationship` reads state. Event history is available at `/relationship/events`. `PATCH /relationship` changes selected values and locks with a required reason. Normal updates cannot change an already locked field; `force: true` is an explicit administrative override. Manual changes are auditable events and survive message-history replay.
