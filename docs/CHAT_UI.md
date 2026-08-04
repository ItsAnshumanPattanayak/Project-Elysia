# Chat UI

## Conversation workflow

"New conversation" loads the real character catalogue, defaults to Zara when
available, and creates a conversation for the fictional roleplay profile Anshuman.
Title and opening scene are optional. The resulting server id is routed directly
to `/chat/{id}`.

The sidebar separates recent and archived conversations and exposes rename,
archive/restore, and delete controls. Deletion is permanent and always confirmed.
The active conversation header repeats these controls and shows the character,
relationship stage, and current scene.

## Messages

User messages render their raw text. Character messages prefer the backend's
structured narration and dialogue fields, show emotion when present, and fall
back to raw content when structured fields are unavailable. Timestamps expose the
full local date through the time element, and edited messages are marked.

The latest eligible messages expose edit, delete, or regenerate actions. When an
edit or deletion would remove later history, the UI explains truncation and asks
for confirmation before sending `confirm_truncate_following_messages=true`.
Regeneration replaces the latest character answer through the backend lifecycle.

## Composer and drafts

- Enter sends non-empty text; Shift+Enter inserts a line break.
- The maximum message and stored draft size is 10,000 characters.
- Drafts are isolated by conversation and survive reloads in localStorage.
- A draft clears only after the stream emits `accepted`, or after a successful
  non-streaming fallback response.
- While generating, the send affordance becomes Cancel. Navigation also aborts
  the request.
- Archived conversations show a read-only composer.

The UI explains that local inference may respond slowly. It does not start a
download, select a cloud fallback, or claim the model is responding before the
backend accepts the request.

## Relationship and memory summaries

The insight rail displays the authoritative relationship stage, mood, turn count,
and bounded numeric values returned by the relationship endpoint. It also shows
the count of active memories and, when available, how many memory ids were selected
for the latest response. The full relationship and memory management dashboards
remain explicitly deferred to Batch 7.

## Accessibility and safety

Controls have accessible names, visible keyboard focus, and semantic dialog,
status, navigation, and message regions. Modal focus is trapped and restored.
Escape closes dialogs and the mobile drawer. Destructive confirmations initially
focus Cancel. Stream changes are announced through a polite live region without
announcing every token.

All model/user content is rendered through React text nodes. Layouts wrap long
content, honor reduced motion, and support keyboard-only operation.

