from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0002_add_connections"
down_revision = "0001_initial"
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


def downgrade() -> None:
    op.drop_index(op.f("ix_connections_role"), table_name="connections")
    op.drop_index(op.f("ix_connections_is_enabled"), table_name="connections")
    op.drop_index(op.f("ix_connections_connector_kind"), table_name="connections")
    op.drop_table("connections")
