"""Create Batch 1 schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260802_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "characters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("age", sa.Integer()),
        sa.Column("profession", sa.String(250)),
        sa.Column("archetype", sa.String(250)),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("backstory", sa.Text(), nullable=False),
        sa.Column("personality", sa.JSON(), nullable=False),
        sa.Column("speaking_style", sa.JSON(), nullable=False),
        sa.Column("behaviour_rules", sa.JSON(), nullable=False),
        sa.Column("preferred_language", sa.String(50), nullable=False),
        sa.Column("avatar_path", sa.String(500)),
        sa.Column("greeting_message", sa.Text(), nullable=False),
        sa.Column("system_prompt_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_characters_slug", "characters", ["slug"], unique=True)
    op.create_table(
        "roleplay_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("roleplay_name", sa.String(200), nullable=False),
        sa.Column("age", sa.Integer()),
        sa.Column("profession", sa.String(250)),
        sa.Column("personality", sa.JSON(), nullable=False),
        sa.Column("relationship_description", sa.Text(), nullable=False),
        sa.Column("preferred_address", sa.JSON(), nullable=False),
        sa.Column("background", sa.JSON(), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_index(
        "ix_roleplay_profiles_roleplay_name", "roleplay_profiles", ["roleplay_name"]
    )
    op.create_table(
        "application_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(150), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        *timestamps(),
    )
    op.create_index(
        "ix_application_settings_key", "application_settings", ["key"], unique=True
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "character_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=False
        ),
        sa.Column(
            "roleplay_profile_id",
            sa.Integer(),
            sa.ForeignKey("roleplay_profiles.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("current_scene", sa.Text(), nullable=False),
        sa.Column("relationship_stage", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_conversations_character_id", "conversations", ["character_id"])
    op.create_index(
        "ix_conversations_roleplay_profile_id", "conversations", ["roleplay_profile_id"]
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column(
            "sender",
            sa.Enum(
                "USER", "CHARACTER", "SYSTEM", name="messagesender", native_enum=False
            ),
            nullable=False,
        ),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("narration", sa.Text()),
        sa.Column("dialogue", sa.Text()),
        sa.Column("emotion", sa.String(100)),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("is_edited", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "conversation_id", "sequence_number", name="uq_message_sequence"
        ),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_table(
        "relationship_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id"),
            nullable=False,
            unique=True,
        ),
        *[
            sa.Column(name, sa.Integer(), nullable=False)
            for name in (
                "attraction",
                "trust",
                "affection",
                "respect",
                "comfort",
                "jealousy",
                "anger",
            )
        ],
        sa.Column("mood", sa.String(100), nullable=False),
        sa.Column("relationship_stage", sa.String(100), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("locked_values", sa.JSON(), nullable=False),
        *timestamps(),
        *[
            sa.CheckConstraint(
                f"{name} BETWEEN 0 AND 100", name=f"ck_relationship_{name}"
            )
            for name in (
                "attraction",
                "trust",
                "affection",
                "respect",
                "comfort",
                "jealousy",
                "anger",
            )
        ],
    )
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
        *timestamps(),
        sa.CheckConstraint("importance BETWEEN 1 AND 5", name="ck_memory_importance"),
        sa.CheckConstraint(
            "emotional_value BETWEEN -100 AND 100", name="ck_memory_emotional_value"
        ),
    )
    op.create_index("ix_memories_conversation_id", "memories", ["conversation_id"])
    op.create_index("ix_memories_source_message_id", "memories", ["source_message_id"])


def downgrade() -> None:
    for table in (
        "memories",
        "relationship_states",
        "messages",
        "conversations",
        "application_settings",
        "roleplay_profiles",
        "characters",
    ):
        op.drop_table(table)
