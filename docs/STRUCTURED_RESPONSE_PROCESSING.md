# Structured Response Processing

Batch 4 uses a versioned, bounded processor:

```text
raw output → size bound → BOM/whitespace cleanup → JSON fence extraction
→ strict JSON → trailing-comma repair when needed → schema validation
→ canonical normalization → safe plain-text fallback → diagnostics
```

Accepted structured fields are bounded narration/dialogue blocks, controlled emotion, controlled relationship-event suggestion, typed memory candidates with optional tags, and raw text. Missing raw text is constructed from validated narration/dialogue. Duplicate/blank blocks are removed.

The only JSON mutation is removal of predictable trailing commas before `}` or `]`. The processor does not rewrite arbitrary quotes, execute code, infer missing objects, or accept YAML/Python literals. Full or embedded Markdown JSON fences are extracted. Unknown emotion/event strings are retained only in bounded original-suggestion fields and do not become authoritative values.

Fallback preserves bounded visible text and extracts simple `*narration*` and quoted Zara dialogue. It deliberately sets emotion and relationship event to null and creates no memory candidates.

Diagnostics contain parse status, parser version, repair flag/actions, schema-valid flag, fallback flag, and short warnings. They contain neither complete prompts nor complete private output. Memory candidates remain inside message generation metadata for possible Batch 5 processing; they never create `Memory` records in Batch 4.
