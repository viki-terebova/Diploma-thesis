from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ariadne_doc_assistant.connectors.models import ArtifactBundle, ConnectionConfig


CONNECTOR_REGISTRY: dict[str, type["BaseConnector"]] = {}


class BaseConnector(ABC):
    name: str
    connector_kind: str

    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError

    def validate_config(self, connection: ConnectionConfig) -> None:
        if not connection.is_enabled:
            raise ValueError(f"Connection {connection.name} is disabled")

    def normalize_event(
        self,
        payload: dict[str, Any],
        connection: ConnectionConfig | None = None,
    ) -> dict[str, Any]:
        return payload

    def collect_artifacts(
        self,
        normalized_event: dict[str, Any],
        connection: ConnectionConfig | None = None,
    ) -> ArtifactBundle:
        raise NotImplementedError(f"Connector {self.name} does not implement collect_artifacts()")

    def collect(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(f"Connector {self.name} does not implement collect()")


def register_connector(name: str, connector_cls: type[BaseConnector]) -> None:
    CONNECTOR_REGISTRY[name] = connector_cls
