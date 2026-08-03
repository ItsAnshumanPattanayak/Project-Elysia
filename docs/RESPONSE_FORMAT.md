# Future Roleplay Response Contract

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

Relationship events and memory candidates are descriptive output only. Batch 2 never changes scores, increments turns, saves messages, or stores memories. Streaming emits `start`, ordered `token`, `metadata`, then `completed`; failures use a terminal `error` event.
