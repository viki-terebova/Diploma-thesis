from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trigger_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trigger_events_source_type"), "trigger_events", ["source_type"], unique=False)

    op.create_table(
        "proposals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trigger_event_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("affected_files", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("diff_summary", sa.Text(), nullable=False),
        sa.Column("draft_markdown", sa.Text(), nullable=False),
        sa.Column("draft_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["trigger_event_id"], ["trigger_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proposals_created_at"), "proposals", ["created_at"], unique=False)
    op.create_index(op.f("ix_proposals_status"), "proposals", ["status"], unique=False)
    op.create_index(op.f("ix_proposals_trigger_event_id"), "proposals", ["trigger_event_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_proposals_trigger_event_id"), table_name="proposals")
    op.drop_index(op.f("ix_proposals_status"), table_name="proposals")
    op.drop_index(op.f("ix_proposals_created_at"), table_name="proposals")
    op.drop_table("proposals")
    op.drop_index(op.f("ix_trigger_events_source_type"), table_name="trigger_events")
    op.drop_table("trigger_events")
