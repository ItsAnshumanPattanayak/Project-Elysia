# Streaming Client

The chat client uses `fetch` rather than `EventSource` because the generation
endpoint is a POST with a JSON body. `streamMessage` reads `Response.body` with a
`ReadableStreamDefaultReader`, decodes UTF-8 incrementally, and feeds text to a
small protocol parser.

## Protocol

Supported named events are processed in wire order:

1. `accepted` — the backend accepted the request; the draft can clear.
2. `user_message` — reconciles the optimistic user row with its persisted message.
3. `start` — character generation has begun.
4. `token` — appends ordered visible character text.
5. `metadata` — merges response metadata without treating it as score authority.
6. `completed` — reconciles the persisted character message and refreshes related
   conversation, relationship, and memory views.
7. `error` or `cancelled` — terminal events that remove partial character output.

The parser accepts CRLF or LF separators, buffers frames split across arbitrary
network chunks, combines multi-line `data` fields, ignores heartbeat comments,
and conservatively skips malformed JSON, unknown events, and frames without data.
It flushes a final complete frame even if the connection ends without a blank-line
delimiter.

## State machine

`idle → submitting → accepted → generating → completing → completed`

Any active phase can enter `failed` or `cancelled`. A reset removes text and ids
from the previous conversation. Partial character text exists only in reducer
state and is never represented as persisted client data.

If failure occurs before `accepted`, retry resubmits the original content and the
draft remains. If the user message was accepted, retry uses the regeneration
endpoint so the backend can finish the unanswered exchange without duplicating the
user message.

## Bounds and cancellation

An `AbortController` is owned per generation and is aborted by Cancel, route
changes, and component cleanup. The reader lock is always released. Token text is
bounded to 50,000 characters to prevent an unbounded local response from consuming
the UI. HTTP error envelopes are normalized before stream reading; connection
failures are retryable, while AbortError is preserved for cancellation semantics.

When browser streaming primitives are unavailable, ChatPage uses the existing
non-streaming message endpoint. The fallback provides the same persisted final
messages but cannot display incremental token progress.

