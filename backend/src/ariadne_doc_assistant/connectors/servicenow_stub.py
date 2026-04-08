from __future__ import annotations

import os

from ariadne_doc_assistant.connectors.base import BaseConnector, register_connector


class ServiceNowStubConnector(BaseConnector):
    name = "servicenow_stub"

    def is_enabled(self) -> bool:
        return bool(os.getenv("SERVICENOW_INSTANCE") and os.getenv("SERVICENOW_TOKEN"))

    def sync_ticket_context(self, ticket_id: str) -> dict[str, str]:
        return {
            "status": "stub",
            "message": f"Ticket sync for {ticket_id} is intentionally not implemented in the public repository.",
        }


register_connector(ServiceNowStubConnector.name, ServiceNowStubConnector)
