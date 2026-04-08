from __future__ import annotations

from typing import Any, Protocol

from ariadne_doc_assistant.connectors.models import ArtifactBundle, ConnectionConfig, DeliveryResult


class SourceConnector(Protocol):
    connector_kind: str

    def validate_config(self, connection: ConnectionConfig) -> None: ...

    def normalize_event(
        self,
        payload: dict[str, Any],
        connection: ConnectionConfig | None = None,
    ) -> dict[str, Any]: ...

    def collect_artifacts(
        self,
        normalized_event: dict[str, Any],
        connection: ConnectionConfig | None = None,
    ) -> ArtifactBundle: ...


class TargetConnector(Protocol):
    connector_kind: str

    def validate_config(self, connection: ConnectionConfig) -> None: ...

    def deliver_proposal(
        self,
        proposal: dict[str, Any],
        connection: ConnectionConfig,
    ) -> DeliveryResult: ...
