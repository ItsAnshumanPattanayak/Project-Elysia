# Long-Term Memory System

The [memory dashboard](MEMORY_DASHBOARD.md) adds scoped lifecycle management.
Version 1 archives instead of physically deleting. Manual memories survive automatic
rebuilds, and locked destructive changes remain explicit.

Batch 5 adds a local, deterministic and user-controllable memory layer. It prefers a small number of supported memories over recording every sentence. Model candidates are untrusted suggestions; only backend rules decide what becomes active memory.

## Taxonomy and sources

The controlled types cover user facts, preferences, dislikes, goals, habits, boundaries and relationship facts; shared experiences, promises, commitments, conflict and reconciliation; emotional moments; character, scene and story facts; important quotes, recurring topics and private notes. `private_note` is user data, never a hidden instruction store.

Sources are `model_candidate`, `deterministic_user_fact`, `manual`, `consolidation`, and `system_rebuild`. Automatic extraction occurs only after a completed user/character exchange and never makes an additional AI call.

Centralized patterns conservatively recognize explicit favourites, preferences, dislikes, allergies, goals, habits, boundaries, remember requests, promises and joint decisions. Questions, quoted claims, hypotheticals, narration, greetings and acknowledgements are ignored. Structured candidates require lexical evidence in the user message.

## Validation and safety

Content, tags, entities, candidate count and type are bounded. Password, token and API-key forms and local absolute paths are rejected. Medical, contact and financial-like data is marked sensitive. Automatic sensitive storage is disabled by default, except an explicitly stated allergy; manual sensitive storage requires `confirm_sensitive=true`. Sensitive content is not written to normal logs.

Backend importance uses 0–100 and confidence uses 0–1. Explicit deterministic statements receive high confidence; manual memories receive 1.0; unsupported model claims fall below the storage threshold. Model scores are bounded suggestions only.

## Identity, consolidation and conflicts

Display text is retained while an NFKC, case-folded, punctuation-normalized form supports comparison. Stable SHA-256-derived application identities include conversation, source exchange/version, candidate identity and extractor version. The database enforces uniqueness.

Exact and very-high-overlap same-type memories consolidate, modestly raising confidence and retaining confirmation provenance. Canonical favourite facts identify updates: the old row becomes `superseded`, links to the replacement and remains auditable. A locked conflict is rejected. Unrelated types are never merged.

## Lifecycle and provenance

Only `active` rows are retrieved. `archived` rows are user-disabled, `superseded` rows retain replaced facts, and `reverted` rows retain invalidated automatic derivations. Pinning adds bounded retrieval preference. Locking prevents automatic invalidation or supersession. Manual memories are never automatically reverted.

Each automatic row records its source user message and, for model candidates, source character message. Source foreign keys use `SET NULL` so audit rows survive source deletion; invalidation runs before deletion. Conversation deletion owns all its memories.

Successful regeneration reverts old character-derived memories and applies the replacement version. Unchanged deterministic user facts remain idempotent. Edit/delete truncation uses one lifecycle service to revert dependent automatic rows before messages disappear.

`POST /api/conversations/{id}/memories/rebuild` requires `{"confirm":true}`. It calls no provider, preserves manual and locked memories, replays deterministic extraction plus retained structured response metadata, and changes neither messages, relationship state nor turn count. Deleted data cannot be recovered.

## APIs

- List supports bounded pagination plus status, type, source, pinned, sensitive and text filters.
- Detail exposes safe provenance, lifecycle and usage fields.
- Create always produces a manual memory.
- Patch edits content, type, importance, tags, sensitivity, pin, lock and archive state and appends audit metadata.
- Delete is soft archival; locked rows must first be explicitly unlocked.
- Search preview returns development-oriented score components without prompts.

The React client contains types and API calls for future work, but Batch 5 intentionally adds no visible dashboard.
