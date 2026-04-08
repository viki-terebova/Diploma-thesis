from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ariadne_doc_assistant.connectors.models import ConnectionConfig
from ariadne_doc_assistant.storage.orm import ConnectionORM, ProposalORM, TriggerEventORM
from ariadne_doc_assistant.storage.models import Proposal


class ProposalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_proposal(self, proposal: Proposal) -> None:
        proposal_payload = proposal.to_dict()
        source_event = proposal_payload["source_event"]
        source_type = source_event.get("source_type", "unknown")
        event_context = source_event.get("context", {})
        event_payload = {
            key: value for key, value in source_event.items() if key not in {"source_type", "context"}
        }

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

        self.session.add(trigger_event)
        self.session.add(proposal_record)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def create_connection(self, connection: ConnectionConfig) -> ConnectionConfig:
        timestamp = datetime.now(UTC)
        record = ConnectionORM(
            id=connection.id,
            name=connection.name,
            connector_kind=connection.connector_kind,
            role=connection.role,
            base_url=connection.base_url,
            config=connection.config,
            secret_ref=connection.secret_ref,
            is_enabled=connection.is_enabled,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.session.add(record)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise ValueError(f"Connection with id '{connection.id}' already exists")
        except Exception:
            self.session.rollback()
            raise
        return self._to_connection_config(record)

    def get_connection(self, connection_id: str) -> ConnectionConfig | None:
        record = self.session.get(ConnectionORM, connection_id)
        if record is None:
            return None
        return self._to_connection_config(record)

    def list_connections(self, limit: int = 50) -> list[ConnectionConfig]:
        statement = select(ConnectionORM).order_by(ConnectionORM.created_at.desc()).limit(limit)
        records = self.session.execute(statement).scalars().all()
        return [self._to_connection_config(record) for record in records]

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
        return self._to_dict(proposal, trigger_event)

    def list_proposals(self, limit: int = 20) -> list[dict[str, Any]]:
        statement = (
            select(ProposalORM, TriggerEventORM)
            .join(TriggerEventORM, ProposalORM.trigger_event_id == TriggerEventORM.id)
            .order_by(ProposalORM.created_at.desc())
            .limit(limit)
        )
        rows = self.session.execute(statement).all()
        return [self._to_dict(proposal, trigger_event) for proposal, trigger_event in rows]

    def _to_dict(self, proposal: ProposalORM, trigger_event: TriggerEventORM) -> dict[str, Any]:
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

    def _to_connection_config(self, record: ConnectionORM) -> ConnectionConfig:
        return ConnectionConfig(
            id=record.id,
            name=record.name,
            connector_kind=record.connector_kind,
            role=record.role,
            base_url=record.base_url,
            config=record.config,
            secret_ref=record.secret_ref,
            is_enabled=record.is_enabled,
        )
