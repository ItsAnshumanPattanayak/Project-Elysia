"""Add deterministic relationship event history and replay baseline."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260803_0002"
down_revision: str | None = "20260802_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "relationship_states",
        sa.Column(
            "baseline_values",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.execute(
        """
        UPDATE relationship_states
        SET baseline_values = json_object(
            'attraction', attraction,
            'trust', trust,
            'affection', affection,
            'respect', respect,
            'comfort', comfort,
            'jealousy', jealousy,
            'anger', anger,
            'mood', mood,
            'relationship_stage', relationship_stage
        )
        """
    )
    op.create_table(
        "relationship_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id"),
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
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("score_deltas", sa.JSON(), nullable=False),
        sa.Column("values_before", sa.JSON(), nullable=False),
        sa.Column("values_after", sa.JSON(), nullable=False),
        sa.Column("mood_before", sa.String(100), nullable=False),
        sa.Column("mood_after", sa.String(100), nullable=False),
        sa.Column("stage_before", sa.String(100), nullable=False),
        sa.Column("stage_after", sa.String(100), nullable=False),
        sa.Column("application_key", sa.String(250), nullable=False),
        sa.Column(
            "is_reverted", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("reverted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_relationship_event_confidence",
        ),
    )
    op.create_index(
        "ix_relationship_events_application_key",
        "relationship_events",
        ["application_key"],
        unique=True,
    )
    op.create_index(
        "ix_relationship_events_conversation_created",
        "relationship_events",
        ["conversation_id", "created_at"],
    )
    op.create_index(
        "ix_relationship_events_user_message",
        "relationship_events",
        ["source_user_message_id"],
    )
    op.create_index(
        "ix_relationship_events_character_message",
        "relationship_events",
        ["source_character_message_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_relationship_events_character_message", table_name="relationship_events"
    )
    op.drop_index(
        "ix_relationship_events_user_message", table_name="relationship_events"
    )
    op.drop_index(
        "ix_relationship_events_conversation_created",
        table_name="relationship_events",
    )
    op.drop_index(
        "ix_relationship_events_application_key", table_name="relationship_events"
    )
    op.drop_table("relationship_events")
    with op.batch_alter_table("relationship_states") as batch_op:
        batch_op.drop_column("baseline_values")
