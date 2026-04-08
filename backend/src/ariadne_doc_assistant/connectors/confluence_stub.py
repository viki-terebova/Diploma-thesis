from __future__ import annotations

import os

from ariadne_doc_assistant.connectors.base import BaseConnector, register_connector


class ConfluenceStubConnector(BaseConnector):
    name = "confluence_stub"

    def is_enabled(self) -> bool:
        return bool(os.getenv("CONFLUENCE_BASE_URL") and os.getenv("CONFLUENCE_TOKEN"))

    def publish(self, proposal_id: str) -> dict[str, str]:
        return {
            "status": "stub",
            "message": f"Publishing for proposal {proposal_id} is intentionally not implemented in the public repository.",
        }


register_connector(ConfluenceStubConnector.name, ConfluenceStubConnector)
