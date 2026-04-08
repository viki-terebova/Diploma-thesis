from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_doc_assistant.api.routes import get_pipeline, get_repository
from ariadne_doc_assistant.config import Settings
from ariadne_doc_assistant.connectors.models import ConnectionConfig
from ariadne_doc_assistant.core.pipeline import ProposalPipeline
from ariadne_doc_assistant.main import app


class FakeProposalRepository:
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}
        self._connections: dict[str, ConnectionConfig] = {}

    def save_proposal(self, proposal) -> None:
        self._items[proposal.id] = proposal.to_dict()

    def get_proposal(self, proposal_id: str) -> dict | None:
        return self._items.get(proposal_id)

    def list_proposals(self, limit: int = 20) -> list[dict]:
        return list(self._items.values())[:limit]

    def create_connection(self, connection: ConnectionConfig) -> ConnectionConfig:
        if connection.id in self._connections:
            raise ValueError(f"Connection with id '{connection.id}' already exists")
        self._connections[connection.id] = connection
        return connection

    def get_connection(self, connection_id: str) -> ConnectionConfig | None:
        return self._connections.get(connection_id)

    def list_connections(self, limit: int = 50) -> list[ConnectionConfig]:
        return list(self._connections.values())[:limit]


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


def _pipeline_override(project_root: Path, output_dir: Path):
    repository = FakeProposalRepository()
    test_settings = Settings(
        project_root=project_root,
        database_url="postgresql+psycopg://ariadne:ariadne@localhost:5432/test",
        output_dir=output_dir,
        log_level="INFO",
    )
    return lambda: ProposalPipeline(settings=test_settings, repository=repository)


def _shared_overrides(project_root: Path, output_dir: Path) -> FakeProposalRepository:
    repository = FakeProposalRepository()
    test_settings = Settings(
        project_root=project_root,
        database_url="postgresql+psycopg://ariadne:ariadne@localhost:5432/test",
        output_dir=output_dir,
        log_level="INFO",
    )
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_pipeline] = lambda: ProposalPipeline(
        settings=test_settings,
        repository=repository,
    )
    return repository


def test_generic_trigger_route_supports_git(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    output_dir = tmp_path / "output" / "proposals"
    app.dependency_overrides[get_pipeline] = _pipeline_override(tmp_path, output_dir)

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
                    "context": {
                        "component": "backend",
                        "ticket_id": "DOC-123",
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DRAFT"
    assert body["affected_files"] == ["README.md"]


def test_generic_trigger_route_rejects_unknown_source(tmp_path: Path) -> None:
    output_dir = tmp_path / "output" / "proposals"
    app.dependency_overrides[get_pipeline] = _pipeline_override(tmp_path, output_dir)

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
    output_dir = tmp_path / "output" / "proposals"
    app.dependency_overrides[get_pipeline] = _pipeline_override(tmp_path, output_dir)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/trigger",
                json={
                    "source_type": "webhook",
                    "payload": {
                        "source_name": "jira-webhook",
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


def test_github_webhook_route_supports_push_events(tmp_path: Path) -> None:
    output_dir = tmp_path / "output" / "proposals"
    repository = _shared_overrides(tmp_path, output_dir)
    repository.create_connection(
        ConnectionConfig(
            id="demo-connection",
            name="GitHub demo connection",
            connector_kind="github",
            role="source",
            base_url="https://api.github.com",
            config={"repository": "org/repo"},
        )
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/webhooks/github/demo-connection",
                headers={
                    "X-GitHub-Event": "push",
                    "X-GitHub-Delivery": "delivery-123",
                },
                json={
                    "ref": "refs/heads/main",
                    "before": "1111111111111111111111111111111111111111",
                    "after": "2222222222222222222222222222222222222222",
                    "compare": "https://github.com/org/repo/compare/111...222",
                    "repository": {
                        "name": "repo",
                        "full_name": "org/repo",
                    },
                    "head_commit": {
                        "message": "Update API validation docs",
                    },
                    "commits": [
                        {
                            "id": "2222222222222222222222222222222222222222",
                            "message": "Update API validation docs",
                            "modified": [
                                "docs/api.md",
                                "backend/src/ariadne_doc_assistant/api/routes.py",
                            ],
                        }
                    ],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DRAFT"
    assert body["source_event"]["source_type"] == "github"
    assert body["source_event"]["event_type"] == "push"
    assert body["source_event"]["external_event_id"] == "delivery-123"
    assert body["affected_files"] == [
        "backend/src/ariadne_doc_assistant/api/routes.py",
        "docs/api.md",
    ]
    assert "org/repo" in body["diff_summary"]


def test_connections_routes_create_and_get_connection(tmp_path: Path) -> None:
    output_dir = tmp_path / "output" / "proposals"
    _shared_overrides(tmp_path, output_dir)

    try:
        with TestClient(app) as client:
            create_response = client.post(
                "/connections",
                json={
                    "id": "github-main",
                    "name": "GitHub main repository",
                    "connector_kind": "github",
                    "role": "source",
                    "base_url": "https://api.github.com",
                    "config": {"repository": "org/repo"},
                    "secret_ref": "github-token",
                    "is_enabled": True,
                },
            )
            get_response = client.get("/connections/github-main")
            list_response = client.get("/connections")
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert get_response.status_code == 200
    assert list_response.status_code == 200
    created = create_response.json()
    assert created["id"] == "github-main"
    assert created["connector_kind"] == "github"
    assert get_response.json()["name"] == "GitHub main repository"
    assert list_response.json()[0]["id"] == "github-main"
