# Roleplay Response Contract

The intended visual form is:

```text
[ATTRACTION: 78/100 | MOOD: PROTECTIVE | TURNS: 46]

*Zara slowly turns away from the office window and looks toward you.*

Zara: "Tumne mujhe pehle kyun nahi bataya?"

*Her expression remains controlled, but concern is visible in her eyes.*
```

The status line is application state, not model-authored truth. Narration uses italics, dialogue identifies the speaker, and user actions are never invented. Rendering must treat all generated content as untrusted text.

The future backend-normalized representation is:

```json
{
  "narration_blocks": ["..."],
  "dialogue_blocks": ["..."],
  "emotion": "protective",
  "relationship_event": "supportive",
  "memory_candidates": [],
  "raw_text": "..."
}
```

`narration_blocks` and `dialogue_blocks` preserve ordered display units; `emotion` is a constrained presentation hint; `relationship_event` is an input to a future deterministic service, never a direct score mutation; `memory_candidates` require validation and policy filtering; and `raw_text` supports debugging and graceful fallback. Schema validation, versioning, safe escaping, length limits, and parse-failure fallback are required when generation is introduced.

Batch 2 requests this JSON contract through local Ollama and validates it with Pydantic. Valid JSON receives `parse_status: structured`. Markdown-fenced JSON is accepted defensively. Noncompliant plain text receives `parse_status: plain_text_fallback`; visible `*narration*` and attributed dialogue are extracted where possible, while the raw text is preserved.

Relationship-event strings remain model suggestions. Batch 4 canonicalizes them, resolves an authoritative event through deterministic evidence, and applies only centralized backend deltas. Batch 5 treats memory candidates as untrusted suggestions: controlled backend extraction requires user evidence, applies safety and quality thresholds, and may store, consolidate, supersede or reject them after a completed exchange. Persistent sends retain the validated structured response and compact processing metadata for audit and rebuild.

Memory candidates support bounded `content`, controlled or safely normalized `memory_type`, 0–100 suggested `importance`, optional 0–1 `confidence`, bounded `tags` and `entities`, optional `reason`, `is_sensitive`, and permanence hint. These fields cannot bypass backend policy and plain-text fallback invents no candidates.

Strict JSON, complete/embedded Markdown fences, and limited trailing-comma repair are supported. Unknown labels do not become canonical. Plain-text fallback preserves visible output while setting emotion/event to null. See `STRUCTURED_RESPONSE_PROCESSING.md`.

Conversation streaming wraps provider events with persistence lifecycle events: `accepted`, `user_message`, `start`, ordered `token`, `metadata`, and `completed`. A terminal `error` or `cancelled` never persists partial character text. The older `/api/ai/generate/stream` development endpoint retains its Batch 2 stateless event contract.
