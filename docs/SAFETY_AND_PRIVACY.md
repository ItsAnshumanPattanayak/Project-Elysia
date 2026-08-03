# Safety and Privacy

## Current guarantees

Primary application data remains in local SQLite storage. Project Elysia includes no telemetry, analytics, cloud message storage, authentication service, paid API, or external AI dependency. Credentials and real `.env` files are excluded from source control, logs avoid secrets, and API metadata never reveals the database path.

Zara is explicitly fictional. The application must not impersonate a real person or claim that Zara is conscious, physically present, watching the user, or able to act in the world. Only minimal fictional profile information should be stored; unnecessary real personal information should not be requested.

The development reset command accepts only `--yes`, only in development/test, only for a `.db` file directly inside `backend/data`, and only for SQLite. A future user-facing flow must offer clear scope, confirmation, backup/export guidance, and an understandable outcome. Deletion should cover conversations, derived memories, relationship state, and related indexes.

## Future protections

- Treat character cards, memories, user messages, retrieved text, and model output as untrusted; delimit prompt sections and reject instructions that attempt to override system policy or exfiltrate local context.
- Render generated text without executable HTML, sanitize links, apply content-security policy, and validate structured output before display or persistence.
- Add a conspicuous emergency stop that cancels generation, clears queued work, and leaves the interface responsive; document how to stop Ollama and the backend.
- Provide content controls, memory review/removal, safe defaults, bounded prompt context, export, backup, and verified complete deletion.
- Avoid dependency framing and direct users to appropriate real-world emergency resources when a future conversation indicates immediate danger, without claiming clinical capability.

Local-first is a privacy boundary, not a substitute for device security. Anyone with access to the Windows account or database file may be able to read stored conversations; future at-rest protection must be documented honestly if added.

## Prompt, provider, and persistence boundaries

Only safe lowercase hyphenated slugs can select configuration files, and resolved files must remain inside approved directories. API requests cannot provide an Ollama URL. Scenes, summaries, memories, and messages are labelled as untrusted narrative data and cannot redefine system sections. This reduces straightforward prompt injection but does not solve it completely; local models may still follow adversarial text, so output remains untrusted and is validated before rendering.

Normal logs contain status and error metadata, not complete prompts or private messages. Ollama traffic defaults to loopback, credentials in provider URLs are rejected, no cloud fallback exists, and model pulling is never automatic. Output, message, pagination, context, and stream-accumulation limits reduce accidental resource exhaustion.

Persistent conversation endpoints store private user and completed character text in local SQLite. User messages intentionally remain after provider failure so retry is explicit and auditable; partial model output is never stored. Editing/deleting earlier history requires explicit truncation confirmation. Conversation deletion removes owned messages, memories, and relationship state but preserves shared character/profile records.

Single-process locks prevent normal simultaneous sends from duplicating sequence positions. They are not a security boundary or distributed coordination mechanism. Optional client IDs are application-checked using persisted metadata but have no dedicated database uniqueness constraint. The application remains designed for one local process and is not ready for public hosting or untrusted multi-user access.

Relationship scoring never executes or obeys model-authored numeric instructions. Model event labels pass through a controlled taxonomy and deterministic resolver. Audit evidence is bounded and inspectable without storing hidden prompts. Manual force override is explicit and logged as an event. Relationship processing failure is non-fatal to already completed private chat.
