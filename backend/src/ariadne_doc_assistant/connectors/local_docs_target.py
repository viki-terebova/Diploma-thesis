from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ariadne_doc_assistant.storage.models import DocumentationTarget, ProposalPatch


@dataclass(slots=True)
class TargetContent:
    target: DocumentationTarget
    absolute_path: Path
    content: str


class LocalDocsTargetConnector:
    connector_kind = "local_docs"

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def load_content(self, target: DocumentationTarget, *, allow_missing: bool = False) -> TargetContent:
        absolute_path = self._resolve_path(target.storage_path, allow_missing=allow_missing)
        content = absolute_path.read_text(encoding="utf-8") if absolute_path.exists() else ""
        return TargetContent(target=target, absolute_path=absolute_path, content=content)

    def apply_patch(self, patch: ProposalPatch, target: DocumentationTarget) -> dict[str, Any]:
        absolute_path = self._resolve_path(target.storage_path, allow_missing=True)
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_text(patch.proposed_content, encoding="utf-8")
        return {
            "target_id": target.id,
            "target_path": str(absolute_path),
            "status": "applied",
        }

    def _resolve_path(self, storage_path: str, *, allow_missing: bool = False) -> Path:
        candidate = Path(storage_path)
        if not candidate.is_absolute():
            candidate = self.project_root / candidate
        resolved = candidate.resolve()
        resolved.relative_to(self.project_root.resolve())
        if not allow_missing and not resolved.exists():
            raise FileNotFoundError(f"Documentation target path does not exist: {resolved}")
        return resolved
