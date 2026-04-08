from __future__ import annotations

import json
from dataclasses import dataclass


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
