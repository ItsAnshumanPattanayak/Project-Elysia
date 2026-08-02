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
Local Ollama model (not implemented)
```

The **React frontend** owns navigation, accessible presentation, request states, and—later—chat interaction. It does not read SQLite or calculate authoritative relationship state. The **FastAPI API** validates transport data, applies CORS for the local Vite origin, returns safe metadata, and will eventually expose conversation commands. Batch 1 intentionally exposes only root, health, and system information.

The **service layer** holds use-case rules and transaction boundaries. It currently performs database health checking and idempotent seeding. Future conversation, relationship, memory, and generation services belong here rather than in routes or ORM models. The **database layer** uses SQLAlchemy 2 declarative mappings, Alembic migrations, explicit relationships, constraints, and a local SQLite file resolved from the backend directory.

## Future components

- **AI provider abstraction — not implemented:** a local Ollama adapter behind an interface, with model discovery, timeouts, cancellation, streaming, and structured-output validation. No paid provider is planned.
- **Memory engine — not implemented:** candidate extraction, validation, deduplication, importance scoring, user review, scoped retrieval, and recall auditing.
- **Relationship engine — not implemented:** deterministic bounded events, transparent score changes, locks, stages, and rollback; the model will not write scores directly.

Configuration comes from typed environment settings. Startup checks connectivity but does not create schemas; Alembic is the single normal schema authority. Tests replace persistence with isolated in-memory SQLite. Logs are human-readable and configured once.

