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
        "connections",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("connector_kind", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("secret_ref", sa.String(length=255), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_connections_connector_kind"), "connections", ["connector_kind"], unique=False)
    op.create_index(op.f("ix_connections_is_enabled"), "connections", ["is_enabled"], unique=False)
    op.create_index(op.f("ix_connections_role"), "connections", ["role"], unique=False)

    op.create_table(
        "documentation_targets",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("target_kind", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documentation_targets_is_enabled"), "documentation_targets", ["is_enabled"], unique=False)
    op.create_index(op.f("ix_documentation_targets_scope"), "documentation_targets", ["scope"], unique=False)
    op.create_index(op.f("ix_documentation_targets_target_kind"), "documentation_targets", ["target_kind"], unique=False)

    op.create_table(
        "approval_policies",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("review_required", sa.Boolean(), nullable=False),
        sa.Column("auto_apply", sa.Boolean(), nullable=False),
        sa.Column("allowed_scope", sa.String(length=64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["target_id"], ["documentation_targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_approval_policies_target_id"), "approval_policies", ["target_id"], unique=False)

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

    op.create_table(
        "proposal_patches",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("target_path", sa.String(length=512), nullable=False),
        sa.Column("patch_type", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("current_content", sa.Text(), nullable=False),
        sa.Column("proposed_content", sa.Text(), nullable=False),
        sa.Column("diff_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["proposal_id"], ["proposals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["documentation_targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proposal_patches_proposal_id"), "proposal_patches", ["proposal_id"], unique=False)
    op.create_index(op.f("ix_proposal_patches_status"), "proposal_patches", ["status"], unique=False)
    op.create_index(op.f("ix_proposal_patches_target_id"), "proposal_patches", ["target_id"], unique=False)

    op.create_table(
        "delivery_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("patch_id", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["patch_id"], ["proposal_patches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["documentation_targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_delivery_runs_patch_id"), "delivery_runs", ["patch_id"], unique=False)
    op.create_index(op.f("ix_delivery_runs_status"), "delivery_runs", ["status"], unique=False)
    op.create_index(op.f("ix_delivery_runs_target_id"), "delivery_runs", ["target_id"], unique=False)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS delivery_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS proposal_patches CASCADE")
    op.execute("DROP TABLE IF EXISTS proposals CASCADE")
    op.execute("DROP TABLE IF EXISTS trigger_events CASCADE")
    op.execute("DROP TABLE IF EXISTS approval_policies CASCADE")
    op.execute("DROP TABLE IF EXISTS documentation_targets CASCADE")
    op.execute("DROP TABLE IF EXISTS connections CASCADE")
