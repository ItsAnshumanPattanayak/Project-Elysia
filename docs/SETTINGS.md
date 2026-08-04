# Settings

`/settings` contains General, Appearance, Chat, AI and Ollama, Relationship, Memory,
Privacy and local data, and About sections.

Precedence is: hard safety validation, environment deployment boundaries,
allow-listed `ApplicationSetting` values, browser UI preferences, then bounded
request options. Provider URL and CORS remain environment-controlled.

The backend exposes `GET /api/settings`, `GET /api/settings/schema`,
`PATCH /api/settings`, and `POST /api/settings/reset`. Editable keys cover installed
model selection, bounded sampling/context/output defaults, response length,
relationship processing, and automatic memory processing. Model names must be in
the local Ollama list. No endpoint downloads models or executes commands.

Provider URLs, credentials, `.env`, filesystem paths, hidden prompts, raw character
prompts, and safety limits are not editable. Theme and chat preferences apply without
reload using versioned local storage.

Export/import schema version 1 includes only UI/chat preferences and allow-listed
settings. Unknown or unsafe keys reject the import before preview. Messages,
relationship history, memories, secrets, paths, prompts, and environment values are
never exported. Reset never changes conversation data, `.env`, or hard restrictions.
