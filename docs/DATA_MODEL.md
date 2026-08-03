# Data Model

## Entities

- **Character:** unique local fictional persona referenced by conversations.
- **RoleplayProfile:** editable fictional user-side identity, not authentication data.
- **Conversation:** character/profile association plus title, scene, summary, relationship-stage text, and lifecycle flags.
- **Message:** ordered `user`, `character`, or internal `system` record. `(conversation_id, sequence_number)` is unique. JSON metadata stores bounded generation metadata, optional client ID, parse status, and regeneration count.
- **RelationshipState:** one state per conversation with seven bounded scores, mood, stage, and `turn_count`.
- **RelationshipEvent:** immutable audit record for one automatic/manual application, including source messages, evidence, deltas, snapshots, transitions, unique key, and reversion state.
- **Memory:** conversation-scoped future memory data with an optional source message.
- **ApplicationSetting:** local JSON configuration, not a secret store.

```text
Character 1 ── * Conversation * ── 1 RoleplayProfile
                       │
                       ├── * Message
                       ├── * Memory
                       └── 0..1 RelationshipState
                       └── * RelationshipEvent
```

## Batch 3 invariants

- Sequence allocation uses the current maximum plus one and is protected by the process-local conversation lock plus the existing unique constraint.
- A turn is one persisted character response completing a user-to-character exchange.
- Turn count is authoritatively recalculated from persisted character messages after history changes.
- User-only failed/cancelled requests contribute no turn.
- Replacing an existing character response during regeneration preserves its sequence and turn count.
- Editing or deleting earlier history truncates all later messages after explicit confirmation; messages are not renumbered.
- Future sequence allocation remains `max(sequence_number) + 1`.
- No automatic relationship values, memories, or summaries are produced.

## Deletion

Explicit conversation deletion uses existing ORM delete-orphan ownership for its messages, memories, and relationship state. Character and roleplay-profile rows remain intact. Deleting a source message leaves any retained memory source nullable through the existing foreign-key behavior. Archived conversations are readable and remain stored.

Batch 4 migration `20260803_0002` adds `relationship_events` and `relationship_states.baseline_values`. Existing states are backfilled from their pre-migration values. Source-message foreign keys use `SET NULL`, retaining audit records after message deletion; conversation ownership still cascades the history when the conversation itself is explicitly deleted. Confidence is constrained to 0–1 and application keys are unique.
