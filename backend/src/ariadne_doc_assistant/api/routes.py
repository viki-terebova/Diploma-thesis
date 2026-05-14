from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from ariadne_doc_assistant.config import settings
from ariadne_doc_assistant.core.pipeline import ProposalPipeline
from ariadne_doc_assistant.storage.db import ProposalRepository
from ariadne_doc_assistant.storage.models import DocumentationTarget
from ariadne_doc_assistant.storage.session import get_db_session


router = APIRouter()
LANDING_PAGE_PATH = Path(__file__).resolve().parents[1] / "templates" / "landing.html"


class TriggerContext(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "component": "backend",
                "ticket_id": "DOC-123",
            }
        }
    )

    component: str | None = None
    ticket_id: str | None = None


class GitTriggerPayload(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "repo_path": ".",
                "from_ref": "HEAD~1",
                "to_ref": "HEAD",
            }
        }
    )

    repo_path: str = Field(..., description="Path to local git repository")
    from_ref: str = "HEAD~1"
    to_ref: str = "HEAD"


class GitTriggerRequest(GitTriggerPayload):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "repo_path": ".",
                "from_ref": "HEAD~1",
                "to_ref": "HEAD",
                "context": {
                    "component": "backend",
                    "ticket_id": "DOC-123",
                },
            }
        }
    )

    context: TriggerContext = Field(default_factory=TriggerContext)


class WebhookTriggerPayload(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_name": "jira-webhook",
                "changed_files": [
                    "docs/architecture.md",
                    "backend/src/ariadne_doc_assistant/api/routes.py",
                ],
                "summary": "Webhook-reported API and documentation change",
                "diff_excerpt": "@@ -1 +1 @@\n- old\n+ new",
                "artifact_url": "https://example.invalid/change/DOC-456",
            }
        }
    )

    source_name: str = "external webhook"
    changed_files: list[str] = Field(default_factory=list)
    summary: str | None = None
    diff_excerpt: str | None = None
    artifact_url: str | None = None


class GenericTriggerRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "source_type": "git",
                    "payload": {
                        "repo_path": ".",
                        "from_ref": "HEAD~1",
                        "to_ref": "HEAD",
                    },
                    "context": {
                        "component": "backend",
                        "ticket_id": "DOC-123",
                    },
                },
                {
                    "source_type": "webhook",
                    "payload": {
                        "source_name": "jira-webhook",
                        "changed_files": ["docs/architecture.md"],
                        "summary": "Webhook-reported documentation change",
                        "diff_excerpt": "@@ -1 +1 @@\n- old\n+ new",
                    },
                    "context": {
                        "component": "docs",
                        "ticket_id": "DOC-456",
                    },
                },
            ]
        }
    )

    source_type: str = Field(..., description="Normalized trigger source identifier, for example 'git'")
    payload: dict[str, Any] = Field(default_factory=dict)
    context: TriggerContext = Field(default_factory=TriggerContext)

    def to_pipeline_event(self) -> tuple[str, dict[str, Any]]:
        normalized_source = self.source_type.strip().lower()
        if normalized_source == "git":
            git_payload = GitTriggerPayload.model_validate(self.payload)
            return normalized_source, {
                **git_payload.model_dump(),
                "source_type": normalized_source,
                "context": self.context.model_dump(),
            }
        if normalized_source == "webhook":
            webhook_payload = WebhookTriggerPayload.model_validate(self.payload)
            return normalized_source, {
                **webhook_payload.model_dump(),
                "source_type": normalized_source,
                "context": self.context.model_dump(),
            }
        return normalized_source, {
            **self.payload,
            "source_type": normalized_source,
            "context": self.context.model_dump(),
        }


class ProposalResponse(BaseModel):
    id: str
    created_at: str
    source_event: dict[str, Any]
    affected_files: list[str]
    diff_summary: str
    draft_markdown: str
    draft_json: dict[str, Any] | str
    status: str
    patch: dict[str, Any] | None = None


class DocumentationTargetCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "local-api-doc",
                "name": "Local API documentation",
                "target_kind": "local_docs",
                "storage_path": "sample_docs/api.md",
                "scope": "page",
                "config": {
                    "component": "backend",
                    "match_any_prefixes": ["docs/", "backend/src/ariadne_doc_assistant/api/"],
                },
                "is_enabled": True,
            }
        }
    )

    id: str | None = None
    name: str
    target_kind: str = "local_docs"
    storage_path: str
    scope: str = "page"
    config: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class DocumentationTargetResponse(BaseModel):
    id: str
    name: str
    target_kind: str
    storage_path: str
    scope: str
    config: dict[str, Any]
    is_enabled: bool


class ProposalPatchResponse(BaseModel):
    id: str
    proposal_id: str
    target_id: str
    target_path: str
    summary: str
    current_content: str
    proposed_content: str
    diff_text: str
    status: str
    created_at: str
    approved_at: str | None = None
    applied_at: str | None = None


def get_repository(session: Session = Depends(get_db_session)) -> ProposalRepository:
    return ProposalRepository(session)


def get_pipeline(
    repo: ProposalRepository = Depends(get_repository),
) -> ProposalPipeline:
    return ProposalPipeline(settings=settings, repository=repo)


@router.get("/", include_in_schema=False, response_class=HTMLResponse)
def landing_page() -> HTMLResponse:
    return HTMLResponse(content=LANDING_PAGE_PATH.read_text(encoding="utf-8"))


@router.post(
    "/trigger/git",
    tags=["Triggers"],
    summary="Trigger proposal generation from a Git diff",
    description="Compatibility endpoint for direct Git-based proposal generation using a repository path and two Git references.",
    response_model=ProposalResponse,
)
def trigger_git(
    request: GitTriggerRequest,
    pipeline: ProposalPipeline = Depends(get_pipeline),
):
    try:
        return pipeline.run_git_trigger(request.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/trigger",
    tags=["Triggers"],
    summary="Trigger proposal generation from a normalized event",
    description="Primary trigger endpoint. Accepts a generic trigger envelope with `source_type`, source-specific `payload`, and optional shared `context`.",
    response_model=ProposalResponse,
)
def trigger(
    request: GenericTriggerRequest,
    pipeline: ProposalPipeline = Depends(get_pipeline),
):
    try:
        source_type, event = request.to_pipeline_event()
        return pipeline.run_trigger(source_type=source_type, event=event)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/documentation-targets",
    tags=["Targets"],
    summary="Create a stored documentation target",
    description="Creates a documentation target that can be located and updated by the local target connector.",
    response_model=DocumentationTargetResponse,
)
def create_documentation_target(
    request: DocumentationTargetCreateRequest,
    repo: ProposalRepository = Depends(get_repository),
):
    target_id = request.id or str(uuid4())
    try:
        target = repo.create_documentation_target(
            DocumentationTarget(
                id=target_id,
                name=request.name,
                target_kind=request.target_kind,
                storage_path=request.storage_path,
                scope=request.scope,
                config=request.config,
                is_enabled=request.is_enabled,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return target.to_dict()


@router.get(
    "/documentation-targets",
    tags=["Targets"],
    summary="List stored documentation targets",
    response_model=list[DocumentationTargetResponse],
)
def list_documentation_targets(
    limit: int = 50,
    repo: ProposalRepository = Depends(get_repository),
):
    return [target.to_dict() for target in repo.list_documentation_targets(limit=limit)]


@router.get(
    "/documentation-targets/{target_id}",
    tags=["Targets"],
    summary="Get one documentation target",
    response_model=DocumentationTargetResponse,
)
def get_documentation_target(
    target_id: str,
    repo: ProposalRepository = Depends(get_repository),
):
    target = repo.get_documentation_target(target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Documentation target not found")
    return target.to_dict()


@router.get(
    "/patches",
    tags=["Patches"],
    summary="List generated documentation patches",
    response_model=list[ProposalPatchResponse],
)
def list_patches(
    limit: int = 50,
    repo: ProposalRepository = Depends(get_repository),
):
    return repo.list_patches(limit=limit)


@router.get(
    "/patches/{patch_id}",
    tags=["Patches"],
    summary="Get one documentation patch",
    response_model=ProposalPatchResponse,
)
def get_patch(
    patch_id: str,
    repo: ProposalRepository = Depends(get_repository),
):
    patch = repo.get_patch(patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")
    return patch


@router.post(
    "/patches/{patch_id}/approve",
    tags=["Patches"],
    summary="Approve a generated documentation patch",
    response_model=ProposalPatchResponse,
)
def approve_patch(
    patch_id: str,
    pipeline: ProposalPipeline = Depends(get_pipeline),
):
    patch = pipeline.approve_patch(patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")
    return patch


@router.post(
    "/patches/{patch_id}/reject",
    tags=["Patches"],
    summary="Reject a generated documentation patch",
    response_model=ProposalPatchResponse,
)
def reject_patch(
    patch_id: str,
    pipeline: ProposalPipeline = Depends(get_pipeline),
):
    patch = pipeline.reject_patch(patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")
    return patch


@router.post(
    "/patches/{patch_id}/apply",
    tags=["Patches"],
    summary="Apply a generated documentation patch to the local target",
    response_model=ProposalPatchResponse,
)
def apply_patch(
    patch_id: str,
    pipeline: ProposalPipeline = Depends(get_pipeline),
):
    try:
        patch = pipeline.apply_patch(patch_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")
    return patch


@router.get(
    "/proposals/{proposal_id}",
    tags=["Proposals"],
    summary="Get one stored proposal",
    description="Returns a single stored proposal by identifier.",
    response_model=ProposalResponse,
)
def get_proposal(
    proposal_id: str,
    repo: ProposalRepository = Depends(get_repository),
):
    proposal = repo.get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.get(
    "/proposals",
    tags=["Proposals"],
    summary="List stored proposals",
    description="Returns the most recent stored proposals.",
    response_model=list[ProposalResponse],
)
def list_proposals(
    limit: int = 20,
    repo: ProposalRepository = Depends(get_repository),
):
    return repo.list_proposals(limit=limit)
