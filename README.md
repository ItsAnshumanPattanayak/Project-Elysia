# Project Elysia

**Status: Batch 4 — deterministic relationship and response processing**

Project Elysia is a private, local-first AI character roleplay application. The backend supports persistent conversation workflows plus deterministic relationship events, bounded score changes, mood/stage resolution, audit history, replay after history truncation, manual locks/overrides, and robust structured-response processing. The finished chat frontend, memory extraction/retrieval, and automatic summaries remain deferred.

There are no accounts, payments, subscriptions, telemetry, paid APIs, automatic model downloads, or cloud AI fallbacks.

## Architecture

```text
React status screen → loopback FastAPI routes
                         ↓
                ConversationService
                  ↙             ↘
       repositories/SQLite    context builder
                                  ↓
                         character prompt engine
                                  ↓
                         local Ollama provider
```

Routes own HTTP and SSE details. `ConversationService` owns workflow and transaction boundaries. Repositories perform SQLAlchemy queries without hidden commits. `ConversationContextBuilder` converts bounded persisted history into the existing trusted `PromptPackage` structure.

## Setup

Requirements: Python 3.11+, Node.js 20+, npm, and separately installed Ollama for real generation.

```powershell
& "E:\Project-Elysia\scripts\setup.ps1"
& "E:\Project-Elysia\scripts\start_backend.ps1"
& "E:\Project-Elysia\scripts\start_frontend.ps1"
```

Open `http://localhost:5173`; API docs are at `http://127.0.0.1:8000/docs`. Setup does not overwrite `.env`, install Ollama, or pull models.

## Conversation API

- `POST /api/conversations`
- `GET /api/conversations?limit=20&offset=0`
- `GET /api/conversations/{id}`
- `PATCH /api/conversations/{id}`
- `DELETE /api/conversations/{id}`
- `GET /api/conversations/{id}/messages?limit=50&offset=0`
- `POST /api/conversations/{id}/messages`
- `POST /api/conversations/{id}/messages/stream`
- `POST /api/conversations/{id}/messages/regenerate`
- `PATCH /api/conversations/{id}/messages/{message_id}`
- `DELETE /api/conversations/{id}/messages/{message_id}`
- `GET /api/conversations/{id}/relationship`
- `GET /api/conversations/{id}/relationship/events`
- `PATCH /api/conversations/{id}/relationship`

Batch 2 character, prompt-preview, AI status/model, and stateless development-generation endpoints remain available.

Create and send:

```powershell
$Conversation = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/conversations" `
  -ContentType "application/json" `
  -Body '{"character_slug":"zara-mirza","roleplay_user_slug":"anshuman"}'

$Body = @{
  content = "Aaj ka din bahut tiring tha."
  client_message_id = "desktop-001"
  behaviour_hint = "concern"
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/conversations/$($Conversation.id)/messages" `
  -ContentType "application/json" -Body $Body
```

The streaming endpoint accepts the same body and returns `accepted`, `user_message`, `start`, ordered `token`, `metadata`, and `completed`, or terminal `error`/`cancelled` events.

## Persistence rules

- The user message is committed before slow generation and remains if generation fails.
- Partial streamed character output is never persisted.
- A completed character response is committed once, then turn count is derived from persisted character messages.
- Regenerating an existing latest character response replaces it only after success and does not add a turn.
- Retrying an unanswered latest user message through regeneration completes the exchange and adds one turn.
- Editing/deleting earlier history requires `confirm_truncate_following_messages=true`; later messages are removed rather than branched.
- The optional `client_message_id` is scoped to one conversation. Persisted lookup plus the process lock prevents normal duplicate retries; no cross-process uniqueness constraint is claimed.
- Locks are local to one backend process. A future multi-process deployment needs distributed coordination.

Messages use stable ascending sequence numbers. Lists use bounded offset pagination. Archived conversations remain readable but cannot generate or mutate messages.

## Ollama and hardware note

The ignored `backend/.env` selects an exact already-installed model. Check it without downloading anything:

```powershell
cd E:\Project-Elysia\backend
& .\.venv\Scripts\python.exe scripts\check_ollama.py
```

The inspected computer has only `llama3.1:latest` (8B, Q4_K_M) with about 7.68 GiB RAM and integrated graphics. Connectivity and readiness work, but earlier real generation attempts timed out. Batch 3 uses a deterministic fake provider for persistence verification and does not repeat prolonged inference. See [Ollama setup](docs/OLLAMA_SETUP.md).

## Quality commands

```powershell
cd backend
python -m alembic upgrade head
python -m ruff check . --no-cache
python -m black --check .
python -m mypy app
python -m pytest

cd ..\frontend
npm.cmd run lint
npm.cmd run format:check
npm.cmd run typecheck
npm.cmd run test -- --run
npm.cmd run build
npm.cmd audit
```

Automated tests use isolated in-memory SQLite and fake/mocked AI providers. They do not require real Ollama or mutate `backend/data/elysia.db`.

## Relationship and response processing

Numeric relationship changes come only from centralized backend rules. Model event strings are suggestions, not score instructions. Completed exchanges receive a unique audit event; failures and partial streams receive none. Regeneration supersedes the earlier event, and edit/delete truncation replays remaining active history from a stored baseline. Locked values suppress automatic changes.

Strict JSON, Markdown-fenced JSON, limited trailing-comma repair, canonical normalization, and plain-text fallback are supported with safe parser diagnostics. Fallback never invents emotion or relationship events. See [relationship engine](docs/RELATIONSHIP_ENGINE.md) and [structured response processing](docs/STRUCTURED_RESPONSE_PROCESSING.md).

## Current boundaries

Memories and summaries are not automatically created. Model-proposed memory candidates stay only in character-message generation metadata. Relationship scoring is conservative and inspectable, not a claim of perfect sentiment understanding. The frontend remains a system foundation screen and intentionally has no production-looking chat page yet.

See [conversation API](docs/CONVERSATION_API.md), [lifecycle](docs/CONVERSATION_LIFECYCLE.md), [architecture](docs/ARCHITECTURE.md), [data model](docs/DATA_MODEL.md), and [safety](docs/SAFETY_AND_PRIVACY.md).
