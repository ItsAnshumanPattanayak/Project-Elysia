# Batch 1 Data Model

## Entities

- **Character:** one fictional persona, identified by unique indexed `slug`; stores identity text, JSON personality/speaking/behaviour configuration, greeting and future prompt template. It has many conversations.
- **RoleplayProfile:** editable fictional user-side story identity—not authentication data. It has many conversations.
- **Conversation:** joins one character and one roleplay profile; stores title, summary, scene, stage, and lifecycle flags. It owns messages, memories, and at most one relationship state.
- **Message:** an ordered user, character, or system record with raw content and optional narration/dialogue/emotion/metadata. `(conversation_id, sequence_number)` is unique.
- **RelationshipState:** exactly zero or one state per conversation at the schema level, with unique foreign key. Seven bounded 0–100 values, mood, stage, turns, and future locks are persisted; no update algorithm exists yet.
- **Memory:** a conversation-scoped candidate fact/event with type, content, tags, importance 1–5, emotional value -100–100, lifecycle flags, optional source message, and recall timestamp. Source deletion sets the reference to null.
- **ApplicationSetting:** a unique indexed key and JSON value with category and description. It is local application configuration, not a secret store.

## Relationships and deletion

```text
Character 1 ── * Conversation * ── 1 RoleplayProfile
                       │
                       ├── * Message ── 0..* source for Memory
                       ├── * Memory
                       └── 0..1 RelationshipState
```

Conversation-owned messages, memories, and relationship state use ORM delete-orphan semantics when an explicit application operation deletes a conversation. Character and roleplay profile links do not use database cascading, preventing their deletion while referenced. A deleted source message sets a memory's optional source reference to null at the database level. Future service APIs must add confirmation, archive-first behavior, and transaction handling before exposing deletion.

All entities use integer primary keys. Mutable entities carry UTC-aware `created_at` and `updated_at`; messages use `created_at` plus optional `edited_at`. SQLite may return naive datetime objects despite timezone metadata, so application boundaries must normalize to UTC. JSON is suitable for flexible local configuration but fields that drive integrity remain relational or constrained.

