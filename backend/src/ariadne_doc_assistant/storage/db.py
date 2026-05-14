from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ariadne_doc_assistant.storage.models import DocumentationTarget, Proposal, ProposalPatch
from ariadne_doc_assistant.storage.orm import (
    DocumentationTargetORM,
    ProposalORM,
    ProposalPatchORM,
    TriggerEventORM,
)


class ProposalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_proposal(self, proposal: Proposal) -> None:
        proposal_payload = proposal.to_dict()
        source_event = proposal_payload["source_event"]
        source_type = source_event.get("source_type", "unknown")
        event_context = source_event.get("context", {})
        event_payload = {key: value for key, value in source_event.items() if key not in {"source_type", "context"}}

        created_at = self._parse_datetime(proposal.created_at)
        trigger_event = TriggerEventORM(
            id=proposal.id,
            source_type=source_type,
            payload=event_payload,
            context=event_context,
            created_at=created_at,
        )
        proposal_record = ProposalORM(
            id=proposal.id,
            trigger_event_id=trigger_event.id,
            created_at=created_at,
            affected_files=proposal.affected_files,
            diff_summary=proposal.diff_summary,
            draft_markdown=proposal.draft_markdown,
            draft_json=self._parse_json_document(proposal.draft_json),
            status=proposal.status,
        )
        self._commit_objects(trigger_event, proposal_record)

    def create_documentation_target(self, target: DocumentationTarget) -> DocumentationTarget:
        timestamp = datetime.now(UTC)
        record = DocumentationTargetORM(
            id=target.id,
            name=target.name,
            target_kind=target.target_kind,
            storage_path=target.storage_path,
            scope=target.scope,
            config=target.config,
            is_enabled=target.is_enabled,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._commit_objects(record, unique_error=f"Documentation target with id '{target.id}' already exists")
        return self._to_documentation_target(record)

    def get_documentation_target(self, target_id: str) -> DocumentationTarget | None:
        record = self.session.get(DocumentationTargetORM, target_id)
        return None if record is None else self._to_documentation_target(record)

    def list_documentation_targets(self, limit: int = 50) -> list[DocumentationTarget]:
        statement = select(DocumentationTargetORM).order_by(DocumentationTargetORM.created_at.desc()).limit(limit)
        records = self.session.execute(statement).scalars().all()
        return [self._to_documentation_target(record) for record in records]

    def create_patch(self, patch: ProposalPatch) -> ProposalPatch:
        record = ProposalPatchORM(
            id=patch.id,
            proposal_id=patch.proposal_id,
            target_id=patch.target_id,
            target_path=patch.target_path,
            patch_type=patch.patch_type,
            summary=patch.summary,
            current_content=patch.current_content,
            proposed_content=patch.proposed_content,
            diff_text=patch.diff_text,
            status=patch.status,
            created_at=self._parse_datetime(patch.created_at),
            approved_at=self._parse_datetime(patch.approved_at) if patch.approved_at else None,
            applied_at=self._parse_datetime(patch.applied_at) if patch.applied_at else None,
        )
        self._commit_objects(record)
        return self._to_patch(record)

    def get_patch(self, patch_id: str) -> dict[str, Any] | None:
        record = self.session.get(ProposalPatchORM, patch_id)
        return None if record is None else self._to_patch(record).to_dict()

    def list_patches(self, limit: int = 50) -> list[dict[str, Any]]:
        statement = select(ProposalPatchORM).order_by(ProposalPatchORM.created_at.desc()).limit(limit)
        records = self.session.execute(statement).scalars().all()
        return [self._to_patch(record).to_dict() for record in records]

    def update_patch_status(
        self,
        patch_id: str,
        *,
        status: str,
        approved_at: str | None = None,
        applied_at: str | None = None,
    ) -> dict[str, Any] | None:
        record = self.session.get(ProposalPatchORM, patch_id)
        if record is None:
            return None
        record.status = status
        if approved_at:
            record.approved_at = self._parse_datetime(approved_at)
        if applied_at:
            record.applied_at = self._parse_datetime(applied_at)
        self._commit()
        return self._to_patch(record).to_dict()

    def get_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        statement = (
            select(ProposalORM, TriggerEventORM)
            .join(TriggerEventORM, ProposalORM.trigger_event_id == TriggerEventORM.id)
            .where(ProposalORM.id == proposal_id)
        )
        row = self.session.execute(statement).one_or_none()
        if row is None:
            return None
        proposal, trigger_event = row
        payload = self._to_proposal_dict(proposal, trigger_event)
        patch = self._latest_patch_for_proposal(proposal.id)
        if patch is not None:
            payload["patch"] = patch.to_dict()
        return payload

    def list_proposals(self, limit: int = 20) -> list[dict[str, Any]]:
        statement = (
            select(ProposalORM, TriggerEventORM)
            .join(TriggerEventORM, ProposalORM.trigger_event_id == TriggerEventORM.id)
            .order_by(ProposalORM.created_at.desc())
            .limit(limit)
        )
        rows = self.session.execute(statement).all()
        payloads: list[dict[str, Any]] = []
        for proposal, trigger_event in rows:
            payload = self._to_proposal_dict(proposal, trigger_event)
            patch = self._latest_patch_for_proposal(proposal.id)
            if patch is not None:
                payload["patch"] = patch.to_dict()
            payloads.append(payload)
        return payloads

    def _latest_patch_for_proposal(self, proposal_id: str) -> ProposalPatch | None:
        statement = (
            select(ProposalPatchORM)
            .where(ProposalPatchORM.proposal_id == proposal_id)
            .order_by(ProposalPatchORM.created_at.desc())
            .limit(1)
        )
        record = self.session.execute(statement).scalar_one_or_none()
        return None if record is None else self._to_patch(record)

    def _to_proposal_dict(self, proposal: ProposalORM, trigger_event: TriggerEventORM) -> dict[str, Any]:
        source_event = {
            "source_type": trigger_event.source_type,
            **trigger_event.payload,
            "context": trigger_event.context,
        }
        return {
            "id": proposal.id,
            "created_at": proposal.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "source_event": source_event,
            "affected_files": proposal.affected_files,
            "diff_summary": proposal.diff_summary,
            "draft_markdown": proposal.draft_markdown,
            "draft_json": proposal.draft_json,
            "status": proposal.status,
        }

    def _parse_datetime(self, value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _parse_json_document(self, value: dict[str, Any] | str) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return json.loads(value)

    def _to_documentation_target(self, record: DocumentationTargetORM) -> DocumentationTarget:
        return DocumentationTarget(
            id=record.id,
            name=record.name,
            target_kind=record.target_kind,
            storage_path=record.storage_path,
            scope=record.scope,
            config=record.config,
            is_enabled=record.is_enabled,
        )

    def _to_patch(self, record: ProposalPatchORM) -> ProposalPatch:
        return ProposalPatch(
            id=record.id,
            proposal_id=record.proposal_id,
            target_id=record.target_id,
            target_path=record.target_path,
            patch_type=record.patch_type,
            summary=record.summary,
            current_content=record.current_content,
            proposed_content=record.proposed_content,
            diff_text=record.diff_text,
            status=record.status,
            created_at=record.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            approved_at=record.approved_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            if record.approved_at
            else None,
            applied_at=record.applied_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            if record.applied_at
            else None,
        )

    def _commit_objects(self, *objects: Any, unique_error: str | None = None) -> None:
        for obj in objects:
            self.session.add(obj)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            if unique_error is not None:
                raise ValueError(unique_error)
            raise
        except Exception:
            self.session.rollback()
            raise

    def _commit(self) -> None:
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
