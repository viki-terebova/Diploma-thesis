from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Proposal:
    id: str
    created_at: str
    source_event: dict
    affected_files: list[str]
    diff_summary: str
    draft_markdown: str
    draft_json: str
    status: str

    def to_dict(self) -> dict:
        draft_json_value = self.draft_json
        try:
            draft_json_value = json.loads(self.draft_json)
        except (TypeError, json.JSONDecodeError):
            pass
        return {
            "id": self.id,
            "created_at": self.created_at,
            "source_event": self.source_event,
            "affected_files": self.affected_files,
            "diff_summary": self.diff_summary,
            "draft_markdown": self.draft_markdown,
            "draft_json": draft_json_value,
            "status": self.status,
        }


@dataclass(slots=True)
class DocumentationTarget:
    id: str
    name: str
    target_kind: str
    storage_path: str
    scope: str
    config: dict[str, Any]
    is_enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "target_kind": self.target_kind,
            "storage_path": self.storage_path,
            "scope": self.scope,
            "config": self.config,
            "is_enabled": self.is_enabled,
        }


@dataclass(slots=True)
class ProposalPatch:
    id: str
    proposal_id: str
    target_id: str
    target_path: str
    patch_type: str
    summary: str
    current_content: str
    proposed_content: str
    diff_text: str
    status: str
    created_at: str
    approved_at: str | None = None
    applied_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "proposal_id": self.proposal_id,
            "target_id": self.target_id,
            "target_path": self.target_path,
            "patch_type": self.patch_type,
            "summary": self.summary,
            "current_content": self.current_content,
            "proposed_content": self.proposed_content,
            "diff_text": self.diff_text,
            "status": self.status,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "applied_at": self.applied_at,
        }
