from __future__ import annotations

from typing import Any

from ariadne_doc_assistant.connectors.base import BaseConnector, register_connector
from ariadne_doc_assistant.connectors.models import ArtifactBundle, ConnectionConfig
from ariadne_doc_assistant.core.policies import redact_data, redact_text


class WebhookStubConnector(BaseConnector):
    name = "webhook"
    connector_kind = "webhook"

    def is_enabled(self) -> bool:
        return True

    def validate_config(self, connection: ConnectionConfig) -> None:
        super().validate_config(connection)
        if connection.role != "source":
            raise ValueError("WebhookStubConnector supports only source connections")

    def normalize_event(
        self,
        payload: dict[str, Any],
        connection: ConnectionConfig | None = None,
    ) -> dict[str, Any]:
        return redact_data(payload)

    def collect_artifacts(
        self,
        normalized_event: dict[str, Any],
        connection: ConnectionConfig | None = None,
    ) -> ArtifactBundle:
        collected = self.collect(normalized_event)
        return ArtifactBundle(
            source_type="webhook",
            event_type=str(normalized_event.get("event_type") or "webhook_event"),
            external_event_id=normalized_event.get("external_event_id"),
            title=normalized_event.get("title"),
            summary=collected["summary"],
            changed_files=collected["files"],
            diff_excerpt=collected["diff_excerpt"],
            metadata={"source_name": collected["source_name"], "payload": collected["payload"]},
            links={"artifact": normalized_event.get("artifact_url")} if normalized_event.get("artifact_url") else {},
            context=normalized_event.get("context", {}),
        )

    def collect(self, payload: dict[str, Any]) -> dict[str, Any]:
        changed_files = payload.get("changed_files") or []
        if not isinstance(changed_files, list):
            raise ValueError("Webhook payload field 'changed_files' must be a list")

        summary = payload.get("summary")
        if summary is not None and not isinstance(summary, str):
            raise ValueError("Webhook payload field 'summary' must be a string when provided")

        diff_excerpt = payload.get("diff_excerpt")
        if diff_excerpt is not None and not isinstance(diff_excerpt, str):
            raise ValueError("Webhook payload field 'diff_excerpt' must be a string when provided")

        source_name = payload.get("source_name") or "external webhook"
        if not isinstance(source_name, str):
            raise ValueError("Webhook payload field 'source_name' must be a string when provided")

        return {
            "source_name": source_name,
            "files": [str(path) for path in changed_files],
            "summary": redact_text(summary or f"Change event received from {source_name}."),
            "diff_excerpt": redact_text(diff_excerpt or ""),
            "payload": redact_data(payload),
        }


register_connector(WebhookStubConnector.name, WebhookStubConnector)
