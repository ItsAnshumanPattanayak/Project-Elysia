# Project Elysia

**Status: Batch 1 foundation**

Project Elysia is a private, local-first AI character roleplay chat application. This repository currently provides requirements, a typed FastAPI health API, an Alembic-managed SQLite model, idempotent starter data, and a responsive React status screen. AI generation, Ollama integration, chat streaming, relationship calculations, memory extraction, and the finished chat interface are planned—not implemented.

## Current and planned capabilities

Current: central environment configuration and logging; `/`, `/health`, and `/api/system/info`; seven relational models with constraints; repeatable migrations and seeds; isolated backend tests; frontend loading, connected, unavailable/retry, error and 404 states; Windows setup/start scripts.

Planned: conversation APIs and UI, local Ollama streaming, structured roleplay output, transparent relationship events, user-reviewable memory, backup/export/deletion, and accessibility hardening. There are no accounts, payments, subscriptions, message limits, analytics, or paid/cloud AI APIs.

## Architecture and stack

React 19 + Vite + TypeScript + Tailwind form the browser client. It calls a loopback FastAPI service using Pydantic 2, SQLAlchemy 2, Alembic, and SQLite. A future service abstraction will call local Ollama. See [architecture](docs/ARCHITECTURE.md), [requirements](docs/PRODUCT_REQUIREMENTS.md), and [data model](docs/DATA_MODEL.md).

```text
backend/   FastAPI, models, migrations, seeds, tests
frontend/  React foundation screen and tests
docs/      product, character, safety, response, architecture specifications
scripts/   PowerShell setup and launch helpers
```

## Prerequisites and Windows setup

Install Python 3.11 or newer, Node.js 20 or newer, and npm. From PowerShell at any location:

```powershell
& "E:\Project-Elysia\scripts\setup.ps1"
& "E:\Project-Elysia\scripts\start_backend.ps1"
& "E:\Project-Elysia\scripts\start_frontend.ps1"
```

Open `http://localhost:5173`; API docs are at `http://127.0.0.1:8000/docs`. Setup creates `.env` only if absent.

## Manual setup and database

```powershell
cd backend
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.venv\Scripts\python.exe -m alembic upgrade head
& .\.venv\Scripts\python.exe scripts\init_db.py

cd ..\frontend
npm.cmd install
npm.cmd run dev
```

Run migrations with `python -m alembic upgrade head`, seed with `python scripts/init_db.py`, and perform a guarded development reset with `python scripts/reset_db.py --yes`, all from `backend`. The seed command is safe to repeat.

## Quality commands

```powershell
cd backend
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
```

## Privacy and limitations

Primary data stays in `backend/data/elysia.db`; no telemetry or cloud message storage is included. Local files remain readable to people or software with device access, so protect the Windows account and backups. The current UI is a foundation screen only and does not chat. Zara Mirza is fictional and the application does not claim consciousness or real-world presence. See [safety and privacy](docs/SAFETY_AND_PRIVACY.md).

The roadmap advances through conversation services, local AI, memory/relationship engines, then the finished experience. Version 1 excludes voice, image generation, mobile-native apps, public sharing, and cloud hosting.
