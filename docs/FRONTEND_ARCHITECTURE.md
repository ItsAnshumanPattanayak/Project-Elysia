# Frontend Architecture

Batch 6 turns the React package into the local desktop chat client. It remains a
single-page application served by Vite and talks only to the configured loopback
FastAPI origin (`VITE_API_BASE_URL`, default `http://127.0.0.1:8000`). No account,
cloud service, analytics SDK, or remote font is involved.

## Layers

- `src/api` is the typed transport boundary. `client.ts` centralizes JSON and
  empty-response handling; resource modules own paths and response validation;
  `streaming.ts` owns the fetch-based SSE connection.
- `src/types` mirrors public backend response shapes without leaking HTTP details
  into components.
- `src/state/AppContext.tsx` owns the conversation index, active/archived filter,
  drawer, and creation dialog. `chatReducer.ts` owns one explicit generation
  state machine.
- `src/pages/ChatPage.tsx` coordinates route validation, paginated messages,
  relationship/memory summaries, optimistic rows, stream reconciliation, and
  message mutations.
- `src/components` contains accessible presentation and small interaction units.
  Common modals trap focus, close on Escape, restore focus, and default destructive
  confirmations to Cancel.
- `src/hooks/useDraft.ts` keeps a bounded draft per conversation in localStorage.
  It is convenience state, not authoritative conversation data.

## Routes and responsive shell

- `/` redirects to the most recently updated active conversation, or displays a
  first-run empty state.
- `/chat/:conversationId` displays one conversation and validates the numeric id
  before issuing detail requests.
- Unknown routes render a local 404.

The shell uses a persistent conversation sidebar and compact insight rail on wide
screens. At narrower widths the insight rail collapses into the chat flow; at
mobile widths the sidebar becomes an explicitly controlled, scrim-backed drawer.
The composer remains reachable at 320 CSS pixels and honors reduced-motion
preferences.

## Data ownership

SQLite through FastAPI remains the source of truth for conversations, messages,
relationship state, and memories. The client stores only draft text. Mutations
refresh their affected server-backed views. Raw model text is rendered as text;
the application does not inject response HTML.

Conversation history is requested oldest-first. The initial page calculates an
offset from the conversation message count to retrieve the newest bounded window;
"Load earlier messages" prepends older rows while preserving the scroll position.

## Failure boundaries

API errors are normalized to `AppApiError` with code, status, retryability, and
safe details. Backend availability and AI/model readiness are reported separately.
The status indicator polls only while the tab is visible and permits manual
refresh. Archived conversations are readable but the composer and message
mutations are disabled.

Generation navigation aborts the active request. Partial character output is
discarded on failure or cancellation; persisted server messages are reloaded when
reconciliation is uncertain. The accepted event is the boundary after which the
user message may already exist on the server.

