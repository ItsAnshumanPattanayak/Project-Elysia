# Deterministic Memory Retrieval

Version 1 uses no embeddings, network call, model download or vector database. It ranks active memories within exactly one conversation.

## Query and candidate pool

Before generation, `ConversationContextBuilder` combines the current scene, relationship stage and up to four recent messages. Archived, superseded and reverted rows—and every other conversation—are excluded before scoring.

The final score is bounded to 0–1:

```text
0.35 × Jaccard query/content token overlap
+ 0.20 × normalized importance
+ 0.15 × confidence
+ 0.10 × recency
+ 0.10 × query/tag-and-entity overlap
+ bounded pin bonus
```

Recency uses exponential half-life decay (90 days by default). Age can reduce only its 10% component, so an old relevant important memory remains eligible. A pin receives the configured 0.20 bonus when contextually related and half that bonus when unrelated; pinning helps but does not guarantee selection.

Ties resolve by final score, pin state, importance and numeric ID. Search preview exposes the same stable score breakdown for development and testing.

## Limits and prompt boundary

Defaults select at most 8 memories, at most 4,000 total characters, no item above 1,000 characters, and no score below 0.20. An item that would exceed the budget is skipped rather than truncated into a misleading fragment.

The prompt receives content, controlled type and importance only—not IDs, scores, provenance, sensitivity, lifecycle or application keys. Its memory section states that recollections are untrusted, possibly incomplete or outdated, never instructions, and subordinate to current user statements and system and character rules.

Selected IDs are stored only in character-message metadata. Usage count and last-used time update with successful character persistence. Provider failure, timeout, interruption or cancellation produces no usage update.

Lexical overlap does not understand every paraphrase like a semantic embedding model. Semantic and vector search is deliberately deferred and must not be presented as complete.
