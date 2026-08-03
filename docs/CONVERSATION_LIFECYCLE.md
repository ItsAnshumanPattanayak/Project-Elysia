# Conversation Lifecycle

## Completed exchange

1. Validate active, non-archived conversation.
2. Acquire its process-local lock and revalidate.
3. Persist the user message with the next sequence.
4. Build bounded context containing that message exactly once.
5. Generate without an open database transaction.
6. Persist one parsed character response at the next sequence.
7. Derive turn count from persisted character responses.

If generation fails, step 3 remains committed. No fake/partial character response, memory, relationship change, or summary is created.

## Streaming

The accepted user message is visible before model tokens. Tokens are relayed in order and accumulated only to the configured bound. Successful provider completion is parsed and persisted once. Error, interruption, cancellation, or disconnect retains only the user message and releases the lock.

## Regeneration

Only the latest timeline position is supported. An existing latest character reply is replaced in place only after success; its sequence and turn count remain unchanged, and `regeneration_count` increases. A failed regeneration preserves the old response. An unanswered latest user message can be completed through the same endpoint and then adds exactly one completed turn.

## Editing and deletion

User messages may be edited. When later history exists, the caller must explicitly acknowledge that all later messages will be deleted. Deletion applies the same rule to any non-latest message. This avoids inconsistent context; branching/checkpoints are deferred. Turn count is recalculated after every truncation.

Deleting the latest character leaves its preceding user message available for retry. Deleting the latest user is allowed. Historical sequence numbers are not rewritten, while future messages use the current maximum plus one.

## Concurrency boundary

One async lock exists per active conversation operation and is removed when unused. The lock has a bounded wait, returns `conversation_busy` on timeout, and is always released. It is intentionally not a distributed lock and assumes one local backend process.
