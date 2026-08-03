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

If generation fails, step 3 remains committed. No fake/partial character response, memory, relationship change, or summary is created. If relationship processing alone fails after step 7, chat remains completed and the API returns a recoverable warning.

## Streaming

The accepted user message is visible before model tokens. Tokens are relayed in order and accumulated only to the configured bound. Successful provider completion is parsed and persisted once. Error, interruption, cancellation, or disconnect retains only the user message and releases the lock.

## Regeneration

Only the latest timeline position is supported. An existing latest character reply is replaced in place only after success; its sequence and turn count remain unchanged, and `regeneration_count` increases. Its previous relationship event is marked reverted and the regenerated exchange receives a new versioned event. A failed regeneration preserves the old response and event. An unanswered latest user message can be completed through the same endpoint and then adds exactly one completed turn/event.

## Editing and deletion

User messages may be edited. When later history exists, the caller must explicitly acknowledge that all later messages will be deleted. Deletion applies the same rule to any non-latest message. Sourced relationship events are marked reverted before source foreign keys become null, then remaining active events replay from the immutable baseline. This avoids inconsistent context; branching/checkpoints are deferred. Turn count is recalculated before relationship replay.

Deleting the latest character leaves its preceding user message available for retry. Deleting the latest user is allowed. Historical sequence numbers are not rewritten, while future messages use the current maximum plus one.

## Concurrency boundary

One async lock exists per active conversation operation and is removed when unused. The lock has a bounded wait, returns `conversation_busy` on timeout, and is always released. It is intentionally not a distributed lock and assumes one local backend process.
