# Architecture

```text
FastAPI routes
    ↓
ConversationService ──→ ConversationLockService
    ↓                         ↓
repositories              process-local lock
    ↓
SQLAlchemy / SQLite

ConversationService → ConversationContextBuilder
    → CharacterPromptBuilder → AIService → local Ollama provider
```

The React application still provides only the Batch 2/3 foundation status screen. It does not read SQLite, calculate authoritative state, or expose an unfinished chat UI.

Routes validate transport data, translate safe domain errors, and frame SSE. `ConversationService` owns use-case rules and commits. Repositories contain SQLAlchemy access and never commit unexpectedly. The context builder loads bounded chronological messages and read-only scene, summary, and relationship values, then reuses the existing character engine. Provider HTTP and parsing stay in the Batch 2 AI modules.

## Transactions and slow generation

User persistence and completed character persistence use separate short transactions. The backend deliberately does not keep an open database transaction during model inference. A failed provider call therefore leaves the accepted user message but no character message or turn increment. A character-persistence failure rolls back the character transaction while preserving the earlier user commit.

Streaming accumulates bounded output only in memory. Completion is parsed and persisted atomically; errors, cancellation, interruption, or disconnect never save partial character output.

## Concurrency and idempotency

An async lock registry is keyed by conversation ID. Contention waits only for the configured short timeout and then returns `conversation_busy`. Reference counts remove idle lock entries after success, error, timeout, or cancellation. This protects a single local backend process, not multiple workers.

Optional `client_message_id` values are stored in user-message JSON metadata and checked under the lock. Completed duplicates return the prior stored generation result; an accepted request without a completed reply returns a deterministic conflict. Sequence uniqueness remains protected by the existing database constraint.

## Deferred components

- Relationship scoring, mood calculation, and stage progression
- Memory extraction, relevance search, and recall
- Conversation summarization
- Story branches and checkpoints
- Distributed locks
- Finished chat frontend

Configuration remains typed, Alembic remains the schema authority, and tests replace persistence/provider dependencies with isolated deterministic implementations.
