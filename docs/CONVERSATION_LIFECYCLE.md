# Conversation Lifecycle

## Completed exchange

1. Validate active, non-archived conversation.
2. Acquire its process-local lock and revalidate.
3. Persist the user message with the next sequence.
4. Build bounded context containing that message exactly once.
5. Generate without an open database transaction.
6. Persist one parsed character response at the next sequence.
7. Derive turn count from persisted character responses.
8. In a separate short transaction, resolve and apply one idempotent relationship event.

If generation fails, step 3 remains committed. No fake or partial character response, memory, relationship change, usage update, or summary is created. After completed persistence, relationship and memory application use separate short transactions. A failure in either leaves chat and the other successful processing stage intact and returns a recoverable warning.

## Streaming

The accepted user message is visible before model tokens. Tokens are relayed in order and accumulated only to the configured bound. Successful provider completion is parsed and persisted once. Error, interruption, cancellation, or disconnect retains only the user message and releases the lock.

## Regeneration

Only the latest timeline position is supported. An existing latest character reply is replaced in place only after success; its sequence and turn count remain unchanged, and `regeneration_count` increases. Its previous relationship event and model-derived memories are reverted, then the regenerated exchange receives new versioned applications. Deterministic facts from the unchanged user message remain idempotent. A failed regeneration preserves the old response, event and memories.

## Editing and deletion

User messages may be edited. When later history exists, the caller must explicitly acknowledge that all later messages will be deleted. Deletion applies the same rule to any non-latest message. Sourced relationship events and automatic memories are marked reverted before source foreign keys become null, then remaining relationship events replay from the immutable baseline. Manual and unrelated memories remain active. Turn count is recalculated before relationship replay.

Deleting the latest character leaves its preceding user message available for retry. Deleting the latest user is allowed. Historical sequence numbers are not rewritten, while future messages use the current maximum plus one.

## Concurrency boundary

One async lock exists per active conversation operation and is removed when unused. The lock has a bounded wait, returns `conversation_busy` on timeout, and is always released. It is intentionally not a distributed lock and assumes one local backend process.
