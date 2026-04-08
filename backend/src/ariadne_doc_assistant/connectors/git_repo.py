from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ariadne_doc_assistant.connectors.base import BaseConnector, register_connector
from ariadne_doc_assistant.connectors.models import ArtifactBundle, ConnectionConfig
from ariadne_doc_assistant.core.policies import redact_text


class GitRepositoryConnector(BaseConnector):
    name = "git"
    connector_kind = "git"

    def is_enabled(self) -> bool:
        return True

    def validate_config(self, connection: ConnectionConfig) -> None:
        super().validate_config(connection)
        if connection.role != "source":
            raise ValueError("GitRepositoryConnector supports only source connections")

    def normalize_event(
        self,
        payload: dict[str, Any],
        connection: ConnectionConfig | None = None,
    ) -> dict[str, Any]:
        repo_path = payload.get("repo_path")
        if not isinstance(repo_path, str) or not repo_path.strip():
            raise ValueError("Git payload field 'repo_path' must be a non-empty string")
        return {
            "repo_path": repo_path,
            "from_ref": payload.get("from_ref", "HEAD~1"),
            "to_ref": payload.get("to_ref", "HEAD"),
            "context": payload.get("context", {}),
            "external_event_id": payload.get("external_event_id"),
            "title": payload.get("title"),
            "links": payload.get("links", {}),
            "metadata": payload.get("metadata", {}),
        }

    def collect_artifacts(
        self,
        normalized_event: dict[str, Any],
        connection: ConnectionConfig | None = None,
    ) -> ArtifactBundle:
        repo_path = Path(normalized_event["repo_path"])
        diff_result = self.collect_diff(
            repo_path=repo_path,
            from_ref=normalized_event["from_ref"],
            to_ref=normalized_event["to_ref"],
        )
        summary = self._summarize_changes(diff_result["files"], diff_result["diff"])
        return ArtifactBundle(
            source_type="git",
            event_type="git_diff",
            external_event_id=normalized_event.get("external_event_id"),
            title=normalized_event.get("title"),
            summary=summary,
            changed_files=diff_result["files"],
            diff_excerpt=redact_text(diff_result["diff"]),
            metadata={
                **normalized_event.get("metadata", {}),
                "from_ref": normalized_event["from_ref"],
                "to_ref": normalized_event["to_ref"],
                "repo_path": str(repo_path),
            },
            links=normalized_event.get("links", {}),
            context=normalized_event.get("context", {}),
        )

    def collect_diff(self, repo_path: Path, from_ref: str, to_ref: str) -> dict[str, object]:
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
        if not (repo_path / ".git").exists():
            raise RuntimeError(f"Path is not a git repository: {repo_path}")

        files = self._run_git(repo_path, ["diff", "--name-only", from_ref, to_ref]).splitlines()
        diff = self._run_git(repo_path, ["diff", "--unified=3", from_ref, to_ref])
        return {
            "files": [file for file in files if file],
            "diff": diff,
        }

    def _run_git(self, repo_path: Path, args: list[str]) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "git command failed")
        return completed.stdout

    def _summarize_changes(self, files: list[str], diff_text: str) -> str:
        added = sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---"))
        return (
            f"Changed {len(files)} file(s), added {added} line(s), removed {removed} line(s). "
            f"Files: {', '.join(files) if files else 'none'}."
        )


register_connector(GitRepositoryConnector.name, GitRepositoryConnector)
