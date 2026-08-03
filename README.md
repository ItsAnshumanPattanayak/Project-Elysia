# Project Elysia

**Status: Batch 2 — character engine and local Ollama integration**

Project Elysia is a private, local-first AI character roleplay application. Batch 2 adds validated fictional character configuration, deterministic prompt composition, live Ollama readiness/model discovery, non-streaming generation, ordered SSE streaming, structured response parsing, and plain-text fallback. Persisted chat, relationship calculations, memory extraction/retrieval, and the finished chat UI are not implemented.

There are no accounts, payments, subscriptions, message limits, telemetry, paid APIs, or cloud AI fallbacks.

## Architecture

```text
React status screen
        ↓ loopback HTTP
FastAPI routes
        ↓
AIService + deterministic character engine
        ↓                         ↓
Ollama provider             SQLite Batch 1 data
        ↓                    (not mutated by generation)
Local Ollama /api/chat
```

The stack is React, Vite, TypeScript, Tailwind, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, SQLite, httpx, pytest, Vitest, Ruff, Black, Mypy, ESLint, and Prettier.

## Setup

Requirements: Python 3.11+, Node.js 20+, npm, and a separately installed Ollama application for real generation.

```powershell
& "E:\Project-Elysia\scripts\setup.ps1"
& "E:\Project-Elysia\scripts\start_backend.ps1"
& "E:\Project-Elysia\scripts\start_frontend.ps1"
```

Open `http://localhost:5173`; API documentation is at `http://127.0.0.1:8000/docs`. Setup never overwrites an existing `.env`. Ollama is not installed or updated by this project, and models are never pulled automatically.

## Ollama configuration

Copy `backend/.env.example` to ignored `backend/.env` and set `OLLAMA_MODEL` to an exact existing identifier from `ollama list`. Important settings include:

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=your-existing-model:tag
OLLAMA_CONNECT_TIMEOUT_SECONDS=3
OLLAMA_READ_TIMEOUT_SECONDS=120
OLLAMA_CONTEXT_SIZE=4096
OLLAMA_MAX_OUTPUT_TOKENS=700
```

Inspect readiness without downloading anything:

```powershell
cd E:\Project-Elysia\backend
& .\.venv\Scripts\python.exe scripts\check_ollama.py
```

See [Ollama setup](docs/OLLAMA_SETUP.md) for selection and resource guidance.

## Batch 2 API

- `GET /api/characters`
- `GET /api/characters/{slug}`
- `POST /api/characters/{slug}/prompt-preview`
- `GET /api/ai/status?refresh=false`
- `GET /api/ai/models`
- `POST /api/ai/generate`
- `POST /api/ai/generate/stream`

Existing `/`, `/health`, and `/api/system/info` endpoints remain available. Basic health does not fail when Ollama is unavailable.

Prompt preview example:

```powershell
$Body = @{
    roleplay_user_slug = "anshuman"
    current_scene = "Zara's private office after business hours."
    behaviour_hint = "concern"
    recent_messages = @(@{ role = "user"; content = "Aaj ka din bahut tiring tha." })
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/characters/zara-mirza/prompt-preview" -ContentType "application/json" -Body $Body
```

For generation, wrap that context as `{ "context": { ... } }` and post to `/api/ai/generate`. The streaming endpoint accepts the same body and returns `text/event-stream` events: `start`, `token`, `metadata`, and `completed`, or a safe `error`. These development endpoints do not save output.

## Quality commands

```powershell
cd backend
python -m alembic upgrade head
python -m ruff check .
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

Automated tests use fake providers and mocked HTTP transports; they do not need or mutate real Ollama. Test databases are isolated from `backend/data/elysia.db`.

## Privacy and current limitations

All default AI traffic stays on loopback and no private prompt is normally logged. Configuration accepts no request-supplied provider URL. Messages, memories, summaries, and scenes are treated as untrusted narrative context, although prompt injection cannot be guaranteed to be completely solved. Zara Mirza and the Anshuman roleplay profile are explicitly fictional adults and are not claims about real people.

The frontend shows backend, database, Ollama, version, configured model, and readiness state only. It intentionally has no chat or normal generation controls. See [architecture](docs/ARCHITECTURE.md), [response format](docs/RESPONSE_FORMAT.md), and [safety](docs/SAFETY_AND_PRIVACY.md).
