from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ariadne_doc_assistant.connectors.models import ArtifactBundle
from ariadne_doc_assistant.config import Settings
from ariadne_doc_assistant.core.pipeline import ProposalPipeline
from ariadne_doc_assistant.storage.models import ApprovalPolicy, DeliveryRun, DocumentationTarget, ProposalPatch


class FakeProposalRepository:
    def __init__(self) -> None:
        self._proposals: dict[str, dict[str, Any]] = {}
        self._targets: dict[str, DocumentationTarget] = {}
        self._policies: dict[str, ApprovalPolicy] = {}
        self._patches: dict[str, ProposalPatch] = {}
        self._deliveries: list[DeliveryRun] = []

    def save_proposal(self, proposal) -> None:
        self._proposals[proposal.id] = proposal.to_dict()

    def get_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        return self._proposals.get(proposal_id)

    def list_proposals(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._proposals.values())[:limit]

    def create_documentation_target(self, target: DocumentationTarget) -> DocumentationTarget:
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


def _create_git_repo(tmp_path: Path) -> Path:
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
    return repo


def _settings(tmp_path: Path, project_root: Path | None = None) -> Settings:
    return Settings(
        APP_PROJECT_ROOT=project_root or tmp_path,
        POSTGRES_DATABASE_URL="postgresql+psycopg://ariadne:ariadne@localhost:5432/test",
        APP_OUTPUT_DIR=tmp_path / "output" / "proposals",
        APP_LOG_LEVEL="INFO",
    )


def test_pipeline_creates_proposal_and_candidate_patch_from_git(tmp_path: Path) -> None:
    repo = _create_git_repo(tmp_path)
    repository = FakeProposalRepository()
    pipeline = ProposalPipeline(settings=_settings(tmp_path), repository=repository)

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
    assert result["patch"]["patch_type"] == "create"
    assert result["patch"]["status"] == "PROPOSED"
    assert "hunter2" not in result["draft_markdown"]
    assert "hunter2" not in result["patch"]["proposed_content"]
    assert (_settings(tmp_path).output_dir / f"{result['id']}.md").exists()
    assert (_settings(tmp_path).output_dir / f"{result['id']}.json").exists()


def test_pipeline_resolves_relative_repo_path_from_project_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "project-root"
    repo_root.mkdir()
    repo = _create_git_repo(repo_root)
    repository = FakeProposalRepository()
    pipeline = ProposalPipeline(settings=_settings(tmp_path, project_root=repo_root), repository=repository)

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


def test_pipeline_updates_matching_local_documentation_target(tmp_path: Path) -> None:
    docs_path = tmp_path / "sample_docs" / "api.md"
    docs_path.parent.mkdir()
    docs_path.write_text("# API\n\nExisting notes.\n", encoding="utf-8")

    repository = FakeProposalRepository()
    repository.create_documentation_target(
        DocumentationTarget(
            id="local-api-doc",
            name="Local API documentation",
            target_kind="local_docs",
            storage_path="sample_docs/api.md",
            scope="page",
            config={"component": "backend", "match_any_prefixes": ["backend/src/ariadne_doc_assistant/api/"]},
        )
    )
    pipeline = ProposalPipeline(settings=_settings(tmp_path, project_root=tmp_path), repository=repository)

    result = pipeline.run_artifact_bundle(
        ArtifactBundle(
            source_type="webhook",
            event_type="webhook_event",
            external_event_id="evt-1",
            title="Update API validation",
            summary="Webhook-reported API change.",
            changed_files=["backend/src/ariadne_doc_assistant/api/routes.py"],
            diff_excerpt="@@ -1 +1 @@\n- old\n+ new",
            context={"component": "backend", "ticket_id": "DOC-500"},
        )
    )

    assert result["patch"]["patch_type"] == "update"
    assert result["patch"]["target_id"] == "local-api-doc"
    assert "<!-- ARIADNE:PATCH-START -->" in result["patch"]["proposed_content"]


def test_pipeline_approves_and_applies_local_patch(tmp_path: Path) -> None:
    docs_path = tmp_path / "sample_docs" / "api.md"
    docs_path.parent.mkdir()
    docs_path.write_text("# API\n", encoding="utf-8")

    repository = FakeProposalRepository()
    repository.create_documentation_target(
        DocumentationTarget(
            id="local-api-doc",
            name="Local API documentation",
            target_kind="local_docs",
            storage_path="sample_docs/api.md",
            scope="page",
            config={"component": "backend"},
        )
    )
    pipeline = ProposalPipeline(settings=_settings(tmp_path, project_root=tmp_path), repository=repository)
    result = pipeline.run_artifact_bundle(
        ArtifactBundle(
            source_type="webhook",
            event_type="webhook_event",
            external_event_id=None,
            title="Update API docs",
            summary="API docs changed.",
            changed_files=["backend/src/ariadne_doc_assistant/api/routes.py"],
            diff_excerpt="",
            context={"component": "backend"},
        )
    )

    patch_id = result["patch"]["id"]
    approved = pipeline.approve_patch(patch_id)
    applied = pipeline.apply_patch(patch_id)

    assert approved["status"] == "APPROVED"
    assert applied["status"] == "APPLIED"
    assert "Proposed Documentation Update" in docs_path.read_text(encoding="utf-8")
