from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ConnectionConfig:
    id: str
    name: str
    connector_kind: str
    role: str
    base_url: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    secret_ref: str | None = None
    is_enabled: bool = True


@dataclass(slots=True)
class ArtifactBundle:
    source_type: str
    event_type: str
    external_event_id: str | None
    title: str | None
    summary: str
    changed_files: list[str] = field(default_factory=list)
    diff_excerpt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    links: dict[str, str] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DeliveryResult:
    status: str
    external_id: str | None = None
    response: dict[str, Any] = field(default_factory=dict)
