from __future__ import annotations

import subprocess
from pathlib import Path

from ariadne_doc_assistant.connectors.models import ArtifactBundle
from ariadne_doc_assistant.config import Settings
from ariadne_doc_assistant.core.pipeline import ProposalPipeline


class FakeProposalRepository:
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}

    def save_proposal(self, proposal) -> None:
        self._items[proposal.id] = proposal.to_dict()

    def get_proposal(self, proposal_id: str) -> dict | None:
        return self._items.get(proposal_id)

    def list_proposals(self, limit: int = 20) -> list[dict]:
        return list(self._items.values())[:limit]


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


def test_pipeline_creates_proposal(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    tracked_file = repo / "README.md"
    tracked_file.write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")

    tracked_file.write_text("hello\nworld\npassword=hunter2\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "change")

    output_dir = tmp_path / "output" / "proposals"
    settings = Settings(
        database_url="postgresql+psycopg://ariadne:ariadne@localhost:5432/test",
        output_dir=output_dir,
        log_level="INFO",
    )
    repository = FakeProposalRepository()
    pipeline = ProposalPipeline(settings=settings, repository=repository)

    result = pipeline.run_git_trigger(
        {
            "repo_path": str(repo),
            "from_ref": "HEAD~1",
            "to_ref": "HEAD",
            "context": {"component": "test", "ticket_id": "DOC-1"},
        }
    )

    assert result["status"] == "DRAFT"
    assert result["affected_files"] == ["README.md"]
    assert (output_dir / f"{result['id']}.md").exists()
    assert (output_dir / f"{result['id']}.json").exists()
    assert "hunter2" not in result["draft_markdown"]
    assert "hunter2" not in (output_dir / f"{result['id']}.json").read_text(encoding="utf-8")
    assert "## Source context" in result["draft_markdown"]
    assert "## Recommended follow-up actions" in result["draft_markdown"]
    assert "DOC-1" in result["draft_markdown"]


def test_pipeline_resolves_relative_repo_path_from_project_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "project-root"
    repo_root.mkdir()
    repo = repo_root / "repo"
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

    settings = Settings(
        project_root=repo_root,
        database_url="postgresql+psycopg://ariadne:ariadne@localhost:5432/test",
        output_dir=tmp_path / "output" / "proposals",
        log_level="INFO",
    )
    repository = FakeProposalRepository()
    pipeline = ProposalPipeline(settings=settings, repository=repository)

    result = pipeline.run_git_trigger(
        {
            "repo_path": "repo",
            "from_ref": "HEAD~1",
            "to_ref": "HEAD",
            "context": {"component": "test"},
        }
    )

    assert result["status"] == "DRAFT"
    assert result["affected_files"] == ["README.md"]


def test_pipeline_creates_proposal_from_artifact_bundle(tmp_path: Path) -> None:
    output_dir = tmp_path / "output" / "proposals"
    settings = Settings(
        database_url="postgresql+psycopg://ariadne_user:ariadne_db_password@localhost:5432/test",
        output_dir=output_dir,
        log_level="INFO",
    )
    repository = FakeProposalRepository()
    pipeline = ProposalPipeline(settings=settings, repository=repository)

    result = pipeline.run_artifact_bundle(
        ArtifactBundle(
            source_type="github",
            event_type="pull_request",
            external_event_id="12345",
            title="Update API validation",
            summary="Pull request modifies API validation and documentation-related files.",
            changed_files=["backend/src/ariadne_doc_assistant/api/routes.py", "docs/architecture.md"],
            diff_excerpt="@@ -1 +1 @@\n- old\n+ new",
            metadata={"repo": "org/repo", "branch": "main"},
            links={"pull_request": "https://example.invalid/pr/12345"},
            context={"component": "backend", "ticket_id": "DOC-500"},
        )
    )

    assert result["status"] == "DRAFT"
    assert result["source_event"]["source_type"] == "github"
    assert result["source_event"]["event_type"] == "pull_request"
    assert result["source_event"]["external_event_id"] == "12345"
    assert "pull_request" in result["source_event"]["links"]
    assert "DOC-500" in result["draft_markdown"]
