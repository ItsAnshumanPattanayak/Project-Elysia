# Product Requirements

## Overview and user

Project Elysia is a private, local-first web application for one adult user to hold persistent fictional character roleplay conversations. Version 1 targets personal, unlimited use on a Windows computer. The initial character is Zara Mirza; all character and user-profile content is fictional and editable.

## Goals

- Deliver natural English and Hinglish roleplay with dialogue and third-person narration.
- Preserve conversations and intentional long-term memories locally.
- Maintain understandable attraction, trust, affection, mood, jealousy, and related state.
- Use a locally running Ollama model through a future provider abstraction.
- Provide a responsive, accessible browser experience without login, telemetry, or limits.

## Non-goals

Multi-user authentication, cloud hosting, paid APIs, subscriptions, payments, message limits, social features, a public character marketplace, a mobile-native application, voice in Version 1, and image generation in Version 1 are explicitly excluded.

## Functional requirements

Version 1 will manage one editable fictional character and roleplay profile; create, resume, archive, and persist conversations; generate structured local-model responses; display dialogue and narration safely; track visible relationship state; extract and recall appropriate memories; expose local settings; and offer deletion/reset controls. Batch 1 provides configuration, health information, relational models, migrations, seed data, and a status-only frontend. It does not generate messages.

## Quality requirements

- **Privacy:** Primary content and configuration remain local. No analytics, telemetry, cloud message storage, or source-controlled secrets.
- **Accessibility:** Semantic structure, keyboard operation, visible focus, accessible contrast, understandable status messages, and reduced-motion support; target WCAG 2.2 AA as the UI matures.
- **Performance:** Foundation page interactive within two seconds on a typical local machine; health response targeted below 250 ms; future streaming should show first useful output promptly without blocking navigation.
- **Reliability:** Alembic owns production schema evolution; seeds are repeatable; database failures are visible; tests never touch the personal database.
- **Compatibility:** Python 3.11+, modern evergreen browsers, PowerShell-friendly Windows workflows, UTF-8.

## Architecture and personal-use scope

The browser calls only a loopback FastAPI service. Services mediate persistence in a local SQLite file and, in a later batch, a local Ollama process. There is no account boundary or remote deployment assumption. Personal use does not weaken safe rendering, explicit reset confirmation, or fictional-character disclosure.

## Version 1 roadmap and batch boundaries

1. **Batch 1 — Foundation:** requirements, repository, health API, schema, migration, seed, status UI.
2. **Batch 2 — Conversation API:** CRUD, pagination, settings, transactional service layer; no generation claim until implemented.
3. **Batch 3 — Local AI:** Ollama provider, prompt assembly, structured parsing, cancellation, and streaming.
4. **Batch 4 — Relationship and memory:** transparent score events, extraction/retrieval, locking and user controls.
5. **Batch 5 — Finished experience:** chat UI, accessibility audit, backup/export/reset, performance hardening.

## Acceptance criteria

Batch 1 is accepted when all seven tables migrate on an empty database; seeding twice creates one character, profile, conversation, and state plus eight settings; `/`, `/health`, and `/api/system/info` return safe typed data; frontend loading, success, failure/retry, error-boundary, and 404 states work; backend and frontend quality suites pass; documentation accurately labels future work; and no real `.env` or runtime database is tracked.

