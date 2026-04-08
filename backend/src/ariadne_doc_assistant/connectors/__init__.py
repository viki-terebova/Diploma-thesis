"""Connector package."""

from ariadne_doc_assistant.connectors.interfaces import SourceConnector, TargetConnector
from ariadne_doc_assistant.connectors.models import ArtifactBundle, ConnectionConfig, DeliveryResult

__all__ = [
    "ArtifactBundle",
    "ConnectionConfig",
    "DeliveryResult",
    "SourceConnector",
    "TargetConnector",
]
