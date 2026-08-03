# Conversation API

All endpoints are local-development APIs under `/api/conversations`. Errors use `{ "error": { "code", "message", "details", "retryable" } }`; they never include prompts, model output, stack traces, secrets, or filesystem paths.

## Conversations

- `POST /api/conversations` validates local character/profile definitions, resolves their seeded database rows, creates a relationship state, and never calls AI.
- `GET /api/conversations` supports `limit`, `offset`, `archived`, `active`, and optional `character_slug`. Ordering is latest `updated_at`, then latest ID.
- `GET /api/conversations/{id}` returns a relationship snapshot and at most ten recent-message previews, never unbounded history.
- `PATCH /api/conversations/{id}` updates title, scene, relationship-stage text, active state, or archive state.
- `DELETE /api/conversations/{id}` explicitly deletes conversation-owned data without deleting its character/profile.

## Messages

- `GET /api/conversations/{id}/messages` returns stable ascending sequence order with bounded offset pagination.
- `POST /api/conversations/{id}/messages` persists a user message, generates, then persists one completed character message.
- `POST /api/conversations/{id}/messages/stream` uses SSE: `accepted`, `user_message`, `start`, ordered `token`, `metadata`, `completed`; failure uses `error` and disconnection/cancellation uses `cancelled` when delivery remains possible.
- `POST /api/conversations/{id}/messages/regenerate` replaces the latest character response after successful generation. If the latest message is an unanswered user message, it completes that exchange instead.
- `PATCH /api/conversations/{id}/messages/{message_id}` edits user messages only. Earlier edits require `confirm_truncate_following_messages` in the JSON body.
- `DELETE /api/conversations/{id}/messages/{message_id}` deletes the selected message and, when required and confirmed by the same-named query parameter, all following messages.
- `GET /api/conversations/{id}/relationship` returns bounded scores, deterministic mood/stage, turn count, locks, and replay baseline.
- `GET /api/conversations/{id}/relationship/events` returns paginated audit history, including reverted events.
- `PATCH /api/conversations/{id}/relationship` performs an auditable manual update with a required reason. Locked values require explicit `force: true`.

## Send request

```json
{
  "content": "Aaj ka din bahut tiring tha.",
  "client_message_id": "desktop-001",
  "behaviour_hint": "concern",
  "response_length": "concise",
  "language_mode": "natural Hinglish",
  "generation_overrides": { "max_output_tokens": 200, "seed": 42 }
}
```

Clients cannot supply a system prompt, provider URL, file path, or sender. Overrides use the Batch 2 safe bounds. `client_message_id` is optional, bounded, safe-character validated, and unique by application policy within one conversation.

Successful persistent generation responses include compact relationship and memory-processing results. Either post-processing stage may return a non-fatal warning because completed chat and the other successful stage are not rolled back. Streaming includes both results and warnings in its final `metadata` event.

## Memory API

`GET` and `POST /api/conversations/{id}/memories` list and manually create memories. `GET`, `PATCH` and `DELETE /api/conversations/{id}/memories/{memory_id}` provide detail, controlled manual edits and soft archival. List filters cover status, controlled type, source, pin, sensitivity and bounded text search. `POST .../search-preview` returns deterministic score diagnostics for development. `POST .../rebuild` requires `{"confirm":true}` and never calls AI.

## Pagination

Conversation defaults/maxima are 20/100. Message defaults/maxima are 50/200. Negative offsets and limits outside configured bounds are rejected. Responses contain `total`, `limit`, `offset`, and `has_more`.
