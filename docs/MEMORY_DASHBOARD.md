# Memory dashboard

`/memories/:conversationId` is scoped to one conversation. It provides bounded
pagination, debounced search with stale-request cancellation, and status, type,
source, pinned, locked, and sensitive filters. Sensitive list content is replaced
by a warning until its detail dialog is opened.

Details include content, provenance, source messages, tags, entities, timestamps,
usage, supersession links, and safe audit metadata. Manual creation uses controlled
types, confirmed confidence 1.0, and sensitive confirmation. Secret-like content and
duplicates are rejected. Edits preserve provenance and require an audit reason.

Archive/unarchive is soft lifecycle management. Retrieval diagnostics show the
existing lexical score components and never inject scores into prompts. Confirmed
rebuild is local and AI-free, preserves manual memories, and leaves relationship
state and turn count unchanged.
