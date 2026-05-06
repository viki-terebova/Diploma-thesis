from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from ariadne_doc_assistant.api.routes import get_pipeline, get_repository
from ariadne_doc_assistant.config import Settings
from ariadne_doc_assistant.connectors.models import ConnectionConfig
from ariadne_doc_assistant.core.pipeline import ProposalPipeline
from ariadne_doc_assistant.main import app
from ariadne_doc_assistant.storage.models import ApprovalPolicy, DeliveryRun, DocumentationTarget, ProposalPatch


class FakeProposalRepository:
    def __init__(self) -> None:
        self._proposals: dict[str, dict[str, Any]] = {}
        self._targets: dict[str, DocumentationTarget] = {}
        self._connections: dict[str, ConnectionConfig] = {}
        self._policies: dict[str, ApprovalPolicy] = {}
        self._patches: dict[str, ProposalPatch] = {}
        self._deliveries: list[DeliveryRun] = []

    def save_proposal(self, proposal) -> None:
        self._proposals[proposal.id] = proposal.to_dict()

    def get_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        payload = self._proposals.get(proposal_id)
        if payload is None:
            return None
        patch = next((item for item in self._patches.values() if item.proposal_id == proposal_id), None)
        return payload | ({"patch": patch.to_dict()} if patch else {})

    def list_proposals(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._proposals.values())[:limit]

    def create_connection(self, connection: ConnectionConfig) -> ConnectionConfig:
        if connection.id in self._connections:
            raise ValueError(f"Connection with id '{connection.id}' already exists")
        self._connections[connection.id] = connection
        return connection

    def get_connection(self, connection_id: str) -> ConnectionConfig | None:
        return self._connections.get(connection_id)

    def list_connections(self, limit: int = 50) -> list[ConnectionConfig]:
        return list(self._connections.values())[:limit]

    def create_documentation_target(self, target: DocumentationTarget) -> DocumentationTarget:
        if target.id in self._targets:
            raise ValueError(f"Documentation target with id '{target.id}' already exists")
        self._targets[target.id] = target
        return target

    def get_documentation_target(self, target_id: str) -> DocumentationTarget | None:
        return self._targets.get(target_id)

    def list_documentation_targets(self, limit: int = 50) -> list[DocumentationTarget]:
        return list(self._targets.values())[:limit]

    def upsert_approval_policy(self, policy: ApprovalPolicy) -> ApprovalPolicy:
        self._policies[policy.target_id] = policy
        return policy

    def get_approval_policy(self, target_id: str) -> ApprovalPolicy | None:
        return self._policies.get(target_id)

    def create_patch(self, patch: ProposalPatch) -> ProposalPatch:
        self._patches[patch.id] = patch
        return patch

    def get_patch(self, patch_id: str) -> dict[str, Any] | None:
        patch = self._patches.get(patch_id)
        return None if patch is None else patch.to_dict()

    def list_patches(self, limit: int = 50) -> list[dict[str, Any]]:
        return [patch.to_dict() for patch in self._patches.values()][:limit]

    def update_patch_status(
        self,
        patch_id: str,
        *,
        status: str,
        approved_at: str | None = None,
        applied_at: str | None = None,
    ) -> dict[str, Any] | None:
        patch = self._patches.get(patch_id)
        if patch is None:
            return None
        updated = ProposalPatch(
            **{
                **patch.to_dict(),
                "status": status,
                "approved_at": approved_at or patch.approved_at,
                "applied_at": applied_at or patch.applied_at,
            }
        )
        self._patches[patch_id] = updated
        return updated.to_dict()

    def create_delivery_run(self, delivery: DeliveryRun) -> DeliveryRun:
        self._deliveries.append(delivery)
        return delivery


def _git(repo: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr)


def _create_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    tracked_file = repo / "README.md"
    tracked_file.write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")

    tracked_file.write_text("hello\nworld\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "change")
    return repo


def _shared_overrides(project_root: Path, output_dir: Path) -> FakeProposalRepository:
    repository = FakeProposalRepository()
    test_settings = Settings(
        APP_PROJECT_ROOT=project_root,
        POSTGRES_DATABASE_URL="postgresql+psycopg://ariadne:ariadne@localhost:5432/test",
        APP_OUTPUT_DIR=output_dir,
        APP_LOG_LEVEL="INFO",
    )
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_pipeline] = lambda: ProposalPipeline(settings=test_settings, repository=repository)
    return repository


def test_generic_trigger_route_supports_git(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    _shared_overrides(tmp_path, tmp_path / "output" / "proposals")

    try:
        with TestClient(app) as client:
            response = client.post(
                "/trigger",
                json={
                    "source_type": "git",
                    "payload": {
                        "repo_path": str(repo),
                        "from_ref": "HEAD~1",
                        "to_ref": "HEAD",
                    },
                    "context": {"component": "backend", "ticket_id": "DOC-123"},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DRAFT"
    assert body["affected_files"] == ["README.md"]
    assert body["patch"]["status"] == "PROPOSED"


def test_generic_trigger_route_rejects_unknown_source(tmp_path: Path) -> None:
    _shared_overrides(tmp_path, tmp_path / "output" / "proposals")

    try:
        with TestClient(app) as client:
            response = client.post(
                "/trigger",
                json={
                    "source_type": "jira",
                    "payload": {"issue_key": "DOC-123"},
                    "context": {"component": "backend"},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "Unsupported trigger source_type" in response.json()["detail"]


def test_generic_trigger_route_supports_webhook(tmp_path: Path) -> None:
    _shared_overrides(tmp_path, tmp_path / "output" / "proposals")

    try:
        with TestClient(app) as client:
            response = client.post(
                "/trigger",
                json={
                    "source_type": "webhook",
                    "payload": {
                        "source_name": "local-webhook",
                        "changed_files": ["docs/architecture.md", "backend/src/ariadne_doc_assistant/api/routes.py"],
                        "summary": "Webhook-reported API and documentation change",
                        "diff_excerpt": "@@ -1 +1 @@\n- old\n+ new",
                    },
                    "context": {"component": "docs", "ticket_id": "DOC-456"},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DRAFT"
    assert body["affected_files"] == [
        "docs/architecture.md",
        "backend/src/ariadne_doc_assistant/api/routes.py",
    ]
    assert "DOC-456" in body["draft_markdown"]


def test_connections_routes_store_future_connector_config(tmp_path: Path) -> None:
    _shared_overrides(tmp_path, tmp_path / "output" / "proposals")

    try:
        with TestClient(app) as client:
            create_response = client.post(
                "/connections",
                json={
                    "id": "future-source",
                    "name": "Future source connector",
                    "connector_kind": "future_source",
                    "role": "source",
                    "base_url": "https://example.invalid",
                    "config": {"repository": "org/repo"},
                    "secret_ref": "future-token-ref",
                    "is_enabled": True,
                },
            )
            get_response = client.get("/connections/future-source")
            list_response = client.get("/connections")
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert get_response.status_code == 200
    assert list_response.status_code == 200
    assert create_response.json()["id"] == "future-source"
    assert get_response.json()["connector_kind"] == "future_source"
    assert list_response.json()[0]["role"] == "source"


def test_target_policy_and_patch_apply_routes(tmp_path: Path) -> None:
    docs_path = tmp_path / "sample_docs" / "api.md"
    docs_path.parent.mkdir()
    docs_path.write_text("# API\n", encoding="utf-8")
    _shared_overrides(tmp_path, tmp_path / "output" / "proposals")

    try:
        with TestClient(app) as client:
            target_response = client.post(
                "/documentation-targets",
                json={
                    "id": "local-api-doc",
                    "name": "Local API documentation",
                    "target_kind": "local_docs",
                    "storage_path": "sample_docs/api.md",
                    "scope": "page",
                    "config": {"component": "backend", "match_any_prefixes": ["backend/src/ariadne_doc_assistant/api/"]},
                    "is_enabled": True,
                },
            )
            policy_response = client.post(
                "/documentation-targets/local-api-doc/policy",
                json={"review_required": True, "auto_apply": False, "allowed_scope": "page", "is_enabled": True},
            )
            trigger_response = client.post(
                "/trigger",
                json={
                    "source_type": "webhook",
                    "payload": {
                        "source_name": "local-webhook",
                        "changed_files": ["backend/src/ariadne_doc_assistant/api/routes.py"],
                        "summary": "API route changed",
                    },
                    "context": {"component": "backend"},
                },
            )
            patch_id = trigger_response.json()["patch"]["id"]
            approve_response = client.post(f"/patches/{patch_id}/approve")
            apply_response = client.post(f"/patches/{patch_id}/apply")
    finally:
        app.dependency_overrides.clear()

    assert target_response.status_code == 200
    assert policy_response.status_code == 200
    assert trigger_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"
    assert apply_response.json()["status"] == "APPLIED"
    assert "Proposed Documentation Update" in docs_path.read_text(encoding="utf-8")
