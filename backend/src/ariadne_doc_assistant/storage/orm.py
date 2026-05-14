from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ariadne_doc_assistant.storage.base import Base


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
