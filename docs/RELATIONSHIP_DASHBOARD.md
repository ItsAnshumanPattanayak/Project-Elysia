# Relationship dashboard

The conversation-specific dashboard is available at `/relationship/:conversationId`.
It reads the deterministic relationship state and paginated local audit log.

Seven labelled numeric progress bars show attraction, trust, affection, respect,
comfort, jealousy, and anger. Negative metrics are explicitly labelled. Mood,
stage, turn count, update time, and locks remain readable without colour.

History filters cover type, source, active/reverted state, local sentiment category,
and order. Safe evidence and source-message identifiers are shown; application keys
and hidden prompts are not. Manual updates accept only bounded scores, controlled
mood/stage/locks, and a required reason. A changed locked value requires force.

Confirmed recalculation replays the baseline and active history. It calls no AI and
does not change messages, memories, or turn count. Before/after snapshots and warnings
are returned.
