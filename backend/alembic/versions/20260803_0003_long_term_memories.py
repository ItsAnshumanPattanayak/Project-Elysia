"""Upgrade the placeholder memory table into the Batch 5 memory lifecycle."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260803_0003"
down_revision: str | None = "20260803_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _new_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_user_message_id",
            sa.Integer(),
            sa.ForeignKey("messages.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "source_character_message_id",
            sa.Integer(),
            sa.ForeignKey("messages.id", ondelete="SET NULL"),
        ),
        sa.Column("memory_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("normalized_content", sa.Text(), nullable=False),
        sa.Column("canonical_fact_key", sa.String(250)),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("entities", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("application_key", sa.String(250), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column(
            "supersedes_memory_id",
            sa.Integer(),
            sa.ForeignKey("memories.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "superseded_by_memory_id",
            sa.Integer(),
            sa.ForeignKey("memories.id", ondelete="SET NULL"),
        ),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("last_confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("reverted_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("importance BETWEEN 0 AND 100", name="ck_memory_importance"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_memory_confidence"),
        sa.CheckConstraint(
            "status IN ('active','archived','superseded','reverted')",
            name="ck_memory_status",
        ),
    ]


def upgrade() -> None:
    op.rename_table("memories", "memories_legacy")
    op.create_table("memories", *_new_columns())
    op.execute(
        """
        INSERT INTO memories (
            id, conversation_id, source_user_message_id, memory_type, content,
            normalized_content, importance, confidence, tags, entities, source,
            application_key, status, is_sensitive, is_pinned, is_locked,
            usage_count, last_used_at, metadata, created_at, updated_at
        )
        SELECT id, conversation_id, source_message_id, memory_type, content,
            lower(trim(content)), importance * 20, 0.70, tags, '[]', 'system_rebuild',
            'legacy:' || id, CASE WHEN is_active THEN 'active' ELSE 'archived' END,
            0, is_permanent, is_permanent, 0, last_recalled_at, '{}',
            created_at, updated_at
        FROM memories_legacy
        """
    )
    op.drop_table("memories_legacy")
    for name, columns, unique in (
        ("ix_memories_conversation_id", ["conversation_id"], False),
        ("ix_memories_source_user_message_id", ["source_user_message_id"], False),
        (
            "ix_memories_source_character_message_id",
            ["source_character_message_id"],
            False,
        ),
        ("ix_memories_memory_type", ["memory_type"], False),
        ("ix_memories_canonical_fact_key", ["canonical_fact_key"], False),
        ("ix_memories_source", ["source"], False),
        ("ix_memories_application_key", ["application_key"], True),
        ("ix_memories_status", ["status"], False),
    ):
        op.create_index(name, "memories", columns, unique=unique)


def downgrade() -> None:
    op.rename_table("memories", "memories_batch5")
    op.create_table(
        "memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column("memory_type", sa.String(100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("emotional_value", sa.Integer(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column(
            "source_message_id",
            sa.Integer(),
            sa.ForeignKey("messages.id", ondelete="SET NULL"),
        ),
        sa.Column("is_permanent", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_recalled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("importance BETWEEN 1 AND 5", name="ck_memory_importance"),
        sa.CheckConstraint(
            "emotional_value BETWEEN -100 AND 100", name="ck_memory_emotional_value"
        ),
    )
    op.execute(
        """
        INSERT INTO memories (id, conversation_id, memory_type, content, importance,
            emotional_value, tags, source_message_id, is_permanent, is_active,
            last_recalled_at, created_at, updated_at)
        SELECT id, conversation_id, memory_type, content,
            max(1, min(5, CAST((importance + 19) / 20 AS INTEGER))), 0, tags,
            source_user_message_id, is_locked, status = 'active', last_used_at,
            created_at, updated_at FROM memories_batch5
        """
    )
    op.drop_table("memories_batch5")
    op.create_index("ix_memories_conversation_id", "memories", ["conversation_id"])
    op.create_index("ix_memories_source_message_id", "memories", ["source_message_id"])
