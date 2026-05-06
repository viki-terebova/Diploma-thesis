from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ariadne_doc_assistant.storage.base import Base


class ConnectionORM(Base):
    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    secret_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentationTargetORM(Base):
    __tablename__ = "documentation_targets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    patches: Mapped[list["ProposalPatchORM"]] = relationship(back_populates="target")
    approval_policies: Mapped[list["ApprovalPolicyORM"]] = relationship(back_populates="target")


class ApprovalPolicyORM(Base):
    __tablename__ = "approval_policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    target_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documentation_targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_apply: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allowed_scope: Mapped[str] = mapped_column(String(64), nullable=False, default="review_only")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    target: Mapped[DocumentationTargetORM] = relationship(back_populates="approval_policies")


class TriggerEventORM(Base):
    __tablename__ = "trigger_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    proposals: Mapped[list["ProposalORM"]] = relationship(back_populates="trigger_event")


class ProposalORM(Base):
    __tablename__ = "proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trigger_event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("trigger_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    affected_files: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    diff_summary: Mapped[str] = mapped_column(Text, nullable=False)
    draft_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    draft_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    trigger_event: Mapped[TriggerEventORM] = relationship(back_populates="proposals")
    patches: Mapped[list["ProposalPatchORM"]] = relationship(back_populates="proposal")


class ProposalPatchORM(Base):
    __tablename__ = "proposal_patches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("proposals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documentation_targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_path: Mapped[str] = mapped_column(String(512), nullable=False)
    patch_type: Mapped[str] = mapped_column(String(32), nullable=False, default="update")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    current_content: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_content: Mapped[str] = mapped_column(Text, nullable=False)
    diff_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    proposal: Mapped[ProposalORM] = relationship(back_populates="patches")
    target: Mapped[DocumentationTargetORM] = relationship(back_populates="patches")
    delivery_runs: Mapped[list["DeliveryRunORM"]] = relationship(back_populates="patch")


class DeliveryRunORM(Base):
    __tablename__ = "delivery_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patch_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("proposal_patches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documentation_targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patch: Mapped[ProposalPatchORM] = relationship(back_populates="delivery_runs")
