# Architecture

```text
React browser application
        ↓ HTTP on loopback
FastAPI local backend
        ↓
Application services
        ↓
SQLite database
        ↓ future provider call
Local Ollama model
```

The **React frontend** owns navigation, accessible presentation, request states, and—later—chat interaction. It does not read SQLite or calculate authoritative relationship state. The **FastAPI API** validates transport data, applies CORS for the local Vite origin, returns safe metadata, and will eventually expose conversation commands. Batch 1 intentionally exposes only root, health, and system information.

The **service layer** holds use-case rules and transaction boundaries. It currently performs database health checking and idempotent seeding. Future conversation, relationship, memory, and generation services belong here rather than in routes or ORM models. The **database layer** uses SQLAlchemy 2 declarative mappings, Alembic migrations, explicit relationships, constraints, and a local SQLite file resolved from the backend directory.

## Future components

- **AI provider abstraction — Batch 2:** an async local Ollama adapter behind a typed protocol, with model discovery, readiness caching, bounded options, cancellation-aware streaming, and structured-output validation. No paid provider or cloud fallback exists.
- **Memory engine — not implemented:** candidate extraction, validation, deduplication, importance scoring, user review, scoped retrieval, and recall auditing.
- **Relationship engine — not implemented:** deterministic bounded events, transparent score changes, locks, stages, and rollback; the model will not write scores directly.

## Batch 2 character and generation flow

Versioned UTF-8 JSON files are validated into nested Pydantic models by a slug-only loader rooted at `backend/characters`. The deterministic prompt builder labels trusted system rules separately from untrusted scenes, memories, summaries, and messages. `AIService` coordinates this engine with the provider protocol. `OllamaProvider` converts prompt packages to `/api/chat`, parses JSON or a plain-text fallback, and exposes non-streaming results or ordered SSE events. Preview and generation do not mutate SQLite.

Configuration comes from typed environment settings. Startup checks connectivity but does not create schemas; Alembic is the single normal schema authority. Tests replace persistence with isolated in-memory SQLite. Logs are human-readable and configured once.
