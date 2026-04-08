from __future__ import annotations

from typing import Any

from ariadne_doc_assistant.connectors.base import BaseConnector, register_connector
from ariadne_doc_assistant.connectors.models import ArtifactBundle, ConnectionConfig
from ariadne_doc_assistant.core.policies import redact_data, redact_text


class GitHubSourceConnector(BaseConnector):
    name = "github"
    connector_kind = "github"
    supported_events = {"push", "pull_request"}

    def is_enabled(self) -> bool:
        return True

    def validate_config(self, connection: ConnectionConfig) -> None:
        super().validate_config(connection)
        if connection.connector_kind != "github":
            raise ValueError("GitHubSourceConnector requires a github connection")
        if connection.role != "source":
            raise ValueError("GitHubSourceConnector supports only source connections")

    def normalize_event(
        self,
        payload: dict[str, Any],
        connection: ConnectionConfig | None = None,
    ) -> dict[str, Any]:
        event_type = str(payload.get("_github_event_type") or payload.get("event_type") or "").strip().lower()
        if not event_type:
            raise ValueError("Missing GitHub event type header")
        if event_type not in self.supported_events:
            raise ValueError(f"Unsupported GitHub event type: {event_type}")

        normalized = redact_data(payload)
        normalized["event_type"] = event_type
        normalized["external_event_id"] = payload.get("_github_delivery_id") or payload.get("delivery_id")
        if connection is not None:
            normalized["connection_id"] = connection.id
        return normalized

    def collect_artifacts(
        self,
        normalized_event: dict[str, Any],
        connection: ConnectionConfig | None = None,
    ) -> ArtifactBundle:
        event_type = normalized_event["event_type"]
        if event_type == "push":
            return self._collect_push_artifacts(normalized_event, connection)
        if event_type == "pull_request":
            return self._collect_pull_request_artifacts(normalized_event, connection)
        raise ValueError(f"Unsupported GitHub event type: {event_type}")

    def _collect_push_artifacts(
        self,
        payload: dict[str, Any],
        connection: ConnectionConfig | None,
    ) -> ArtifactBundle:
        repository = payload.get("repository") or {}
        commits = payload.get("commits") or []
        changed_files = sorted(
            {
                str(path)
                for commit in commits
                for key in ("added", "modified", "removed")
                for path in (commit.get(key) or [])
            }
        )
        head_commit = payload.get("head_commit") or {}
        branch = str(payload.get("ref") or "").removeprefix("refs/heads/")
        repo_full_name = repository.get("full_name") or repository.get("name") or "unknown repository"
        commit_count = len(commits)
        title = head_commit.get("message") or f"GitHub push to {branch or 'repository'}"
        summary = (
            f"GitHub push on {repo_full_name}"
            f"{f' ({branch})' if branch else ''} with {commit_count} commit(s)"
            f" and {len(changed_files)} changed file(s)."
        )
        diff_excerpt = self._build_push_excerpt(commits)
        compare_url = payload.get("compare")
        return ArtifactBundle(
            source_type="github",
            event_type="push",
            external_event_id=payload.get("external_event_id"),
            title=title,
            summary=summary,
            changed_files=changed_files,
            diff_excerpt=diff_excerpt,
            metadata={
                "repository": repo_full_name,
                "branch": branch,
                "before": payload.get("before"),
                "after": payload.get("after"),
                "connection_id": connection.id if connection else payload.get("connection_id"),
            },
            links={"compare": compare_url} if compare_url else {},
            context=payload.get("context", {}),
        )

    def _collect_pull_request_artifacts(
        self,
        payload: dict[str, Any],
        connection: ConnectionConfig | None,
    ) -> ArtifactBundle:
        repository = payload.get("repository") or {}
        pull_request = payload.get("pull_request") or {}
        repo_full_name = repository.get("full_name") or repository.get("name") or "unknown repository"
        title = pull_request.get("title") or "GitHub pull request"
        summary = (
            f"GitHub pull request for {repo_full_name}: "
            f"{pull_request.get('title') or 'untitled pull request'}."
        )
        body_excerpt = redact_text((pull_request.get("body") or "").strip())
        if body_excerpt:
            body_excerpt = "\n".join(body_excerpt.splitlines()[:20])
        else:
            body_excerpt = "# Pull request body not provided"
        return ArtifactBundle(
            source_type="github",
            event_type="pull_request",
            external_event_id=payload.get("external_event_id"),
            title=title,
            summary=summary,
            changed_files=[],
            diff_excerpt=body_excerpt,
            metadata={
                "repository": repo_full_name,
                "action": payload.get("action"),
                "number": pull_request.get("number"),
                "connection_id": connection.id if connection else payload.get("connection_id"),
            },
            links={"pull_request": pull_request.get("html_url")} if pull_request.get("html_url") else {},
            context=payload.get("context", {}),
        )

    def _build_push_excerpt(self, commits: list[dict[str, Any]]) -> str:
        if not commits:
            return "# Push event did not include commit details"
        lines = []
        for commit in commits[:10]:
            commit_id = str(commit.get("id") or "")[:7]
            message = redact_text(str(commit.get("message") or "Commit without message"))
            lines.append(f"- {commit_id}: {message}")
        if len(commits) > 10:
            lines.append("... additional commits omitted ...")
        return "\n".join(lines)


register_connector(GitHubSourceConnector.name, GitHubSourceConnector)
