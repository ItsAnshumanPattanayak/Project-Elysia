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

Structured AI generation, parsing, relationship events, and memory extraction are **not implemented in Batch 1**.
