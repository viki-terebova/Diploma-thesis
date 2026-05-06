from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from ariadne_doc_assistant.config import Settings
from ariadne_doc_assistant.connectors.github_source import GitHubSourceConnector
from ariadne_doc_assistant.connectors.git_repo import GitRepositoryConnector
from ariadne_doc_assistant.connectors.local_docs_target import LocalDocsTargetConnector
from ariadne_doc_assistant.connectors.models import ArtifactBundle
from ariadne_doc_assistant.connectors.webhook_stub import WebhookStubConnector
from ariadne_doc_assistant.locator.local import LocalContentLocator
from ariadne_doc_assistant.core.policies import redact_data, redact_text
from ariadne_doc_assistant.core.proposals import build_local_docs_patch_content, build_patch, build_proposal
from ariadne_doc_assistant.llm.client import get_llm_client
from ariadne_doc_assistant.llm.prompts import build_prompt
from ariadne_doc_assistant.storage.db import ProposalRepository
from ariadne_doc_assistant.storage.models import ApprovalPolicy, DeliveryRun, DocumentationTarget, Proposal, ProposalPatch
from ariadne_doc_assistant.utils.time import utc_now_iso


logger = logging.getLogger(__name__)


class ProposalPipeline:
    def __init__(self, settings: Settings, repository: ProposalRepository) -> None:
        self.settings = settings
        self.repository = repository
        self.git_connector = GitRepositoryConnector()
        self.github_connector = GitHubSourceConnector()
        self.webhook_connector = WebhookStubConnector()
        self.local_docs_connector = LocalDocsTargetConnector(settings.project_root)
        self.locator = LocalContentLocator()
        self.llm = get_llm_client(settings.llm_provider)

    def run_trigger(self, source_type: str, event: dict) -> dict:
        normalized_source = source_type.strip().lower()
        if normalized_source == "git":
            return self.run_git_trigger(event)
        if normalized_source == "github":
            return self.run_github_trigger(event)
        if normalized_source == "webhook":
            return self.run_webhook_trigger(event)
        raise ValueError(f"Unsupported trigger source_type: {source_type}")

    def run_git_trigger(self, event: dict) -> dict:
        repo_path = self.resolve_repo_path(event["repo_path"])
        normalized_event = self.git_connector.normalize_event(
            {
                **event,
                "repo_path": str(repo_path),
            }
        )
        bundle = self.git_connector.collect_artifacts(normalized_event)
        logger.info("Processing git trigger for %s", str(repo_path))
        return self.run_artifact_bundle(bundle)

    def run_webhook_trigger(self, event: dict[str, Any]) -> dict:
        normalized_event = self.webhook_connector.normalize_event(event)
        bundle = self.webhook_connector.collect_artifacts(normalized_event)
        logger.info("Processing webhook trigger from %s", bundle.metadata.get("source_name", "external webhook"))
        return self.run_artifact_bundle(bundle)

    def run_github_trigger(self, event: dict[str, Any]) -> dict:
        normalized_event = self.github_connector.normalize_event(event)
        bundle = self.github_connector.collect_artifacts(normalized_event)
        logger.info(
            "Processing GitHub %s event for %s",
            bundle.event_type,
            bundle.metadata.get("repository", "unknown repository"),
        )
        return self.run_artifact_bundle(bundle)

    def run_artifact_bundle(self, bundle: ArtifactBundle) -> dict[str, Any]:
        source_event = self._source_event_from_bundle(bundle)
        redacted_event = redact_data(source_event)
        diff_text = redact_text(bundle.diff_excerpt)
        summary = redact_text(bundle.summary)
        affected_files = bundle.changed_files
        result = self._build_and_store_proposal(
            source_event=redacted_event,
            affected_files=affected_files,
            diff_text=diff_text,
            diff_summary=summary,
            suggested_sections=self._suggest_sections(affected_files),
            recommended_actions=self._build_recommended_actions(affected_files, summary, redacted_event),
        )
        patch_payload = self._build_and_store_patch(
            proposal=result,
            bundle=bundle,
            diff_summary=summary,
        )
        if patch_payload is not None:
            result["patch"] = patch_payload
        return result

    def resolve_repo_path(self, repo_path_value: str) -> Path:
        candidate = Path(repo_path_value).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        return (self.settings.project_root / candidate).resolve()

    def _build_and_store_proposal(
        self,
        source_event: dict[str, Any],
        affected_files: list[str],
        diff_text: str,
        diff_summary: str,
        suggested_sections: list[str],
        recommended_actions: list[str],
    ) -> dict:
        prompt = build_prompt(
            source_event=source_event,
            affected_files=affected_files,
            diff_summary=diff_summary,
            diff_text=diff_text,
        )
        llm_output = self.llm.generate(prompt)
        proposal = build_proposal(
            source_event=source_event,
            affected_files=affected_files,
            diff_text=diff_text,
            diff_summary=diff_summary,
            suggested_sections=suggested_sections,
            recommended_actions=recommended_actions,
            llm_output=llm_output,
        )
        self.repository.save_proposal(proposal)
        self._write_outputs(proposal)
        return proposal.to_dict()

    def _build_and_store_patch(
        self,
        *,
        proposal: dict[str, Any],
        bundle: ArtifactBundle,
        diff_summary: str,
    ) -> dict[str, Any] | None:
        target = self.locator.locate(bundle, self.repository.list_documentation_targets())
        patch_type = "update"
        if target is None:
            target = self._create_target_for_bundle(bundle)
            patch_type = "create"

        target_content = self.local_docs_connector.load_content(target, allow_missing=(patch_type == "create"))
        suggested_sections = proposal.get("draft_json", {}).get("suggested_doc_sections", []) if isinstance(
            proposal.get("draft_json"), dict
        ) else []
        llm_output = self.llm.generate(
            build_prompt(
                source_event=proposal["source_event"],
                affected_files=proposal["affected_files"],
                diff_summary=proposal["diff_summary"],
                diff_text=bundle.diff_excerpt,
            )
        )
        proposed_content = build_local_docs_patch_content(
            target_content.content,
            source_event=proposal["source_event"],
            diff_summary=diff_summary,
            affected_files=proposal["affected_files"],
            suggested_sections=suggested_sections,
            llm_output=llm_output,
        )
        patch = build_patch(
            proposal=Proposal(
                id=proposal["id"],
                created_at=proposal["created_at"],
                source_event=proposal["source_event"],
                affected_files=proposal["affected_files"],
                diff_summary=proposal["diff_summary"],
                draft_markdown=proposal["draft_markdown"],
                draft_json=json.dumps(proposal.get("draft_json", {}), indent=2)
                if isinstance(proposal.get("draft_json"), dict)
                else proposal.get("draft_json", "{}"),
                status=proposal["status"],
            ),
            target_id=target.id,
            target_path=target.storage_path,
            patch_type=patch_type,
            current_content=target_content.content,
            proposed_content=proposed_content,
            summary=f"Proposed {'new document' if patch_type == 'create' else 'update'} for {target.name}",
        )
        stored_patch = self.repository.create_patch(patch)

        policy = self.repository.get_approval_policy(target.id)
        if policy is None:
            policy = self.repository.upsert_approval_policy(
                ApprovalPolicy(
                    id=f"policy-{target.id}",
                    target_id=target.id,
                    review_required=True,
                    auto_apply=False,
                    allowed_scope="review_only",
                    is_enabled=True,
                )
            )

        patch_payload = stored_patch.to_dict()
        patch_payload["target"] = target.to_dict()
        patch_payload["policy"] = policy.to_dict()

        if policy.auto_apply and policy.is_enabled:
            applied_patch = self.apply_patch(stored_patch.id, mode="auto")
            if applied_patch is not None:
                patch_payload = applied_patch

        return patch_payload

    def _create_target_for_bundle(self, bundle: ArtifactBundle):
        repository_name = str(bundle.metadata.get("repository") or "generated-docs").replace("/", "-").lower()
        title_source = (bundle.title or bundle.summary or "generated documentation").lower()
        slug = "-".join(
            token
            for token in "".join(ch if ch.isalnum() else "-" for ch in title_source).split("-")
            if token
        )[:80] or "generated-documentation"
        target_id = f"generated-{slug}"
        existing = self.repository.get_documentation_target(target_id)
        if existing is not None:
            return existing

        target = self.repository.create_documentation_target(
            DocumentationTarget(
                id=target_id,
                name=f"Generated documentation for {bundle.title or bundle.event_type}",
                target_kind="local_docs",
                storage_path=f"sample_docs/generated/{repository_name}/{slug}.md",
                scope="page",
                config={
                    "repository": bundle.metadata.get("repository", ""),
                    "component": bundle.context.get("component", ""),
                    "match_any_prefixes": [],
                    "generated_from_source": bundle.source_type,
                },
                is_enabled=True,
            )
        )
        self.repository.upsert_approval_policy(
            ApprovalPolicy(
                id=f"policy-{target.id}",
                target_id=target.id,
                review_required=True,
                auto_apply=False,
                allowed_scope="page",
                is_enabled=True,
            )
        )
        return target

    def approve_patch(self, patch_id: str) -> dict[str, Any] | None:
        patch = self.repository.update_patch_status(
            patch_id,
            status="APPROVED",
            approved_at=utc_now_iso(),
        )
        return patch

    def apply_patch(self, patch_id: str, mode: str = "manual") -> dict[str, Any] | None:
        patch_payload = self.repository.get_patch(patch_id)
        if patch_payload is None:
            return None
        target = self.repository.get_documentation_target(patch_payload["target_id"])
        if target is None:
            raise FileNotFoundError(f"Documentation target not found for patch {patch_id}")

        if patch_payload["status"] not in {"APPROVED", "PROPOSED"}:
            raise ValueError(f"Patch {patch_id} is not in an applicable state")

        if patch_payload["status"] == "PROPOSED":
            patch_payload = self.repository.update_patch_status(
                patch_id,
                status="APPROVED",
                approved_at=utc_now_iso(),
            ) or patch_payload

        self.local_docs_connector.apply_patch(
            ProposalPatch(
                id=patch_payload["id"],
                proposal_id=patch_payload["proposal_id"],
                target_id=patch_payload["target_id"],
                target_path=patch_payload["target_path"],
                patch_type=patch_payload["patch_type"],
                summary=patch_payload["summary"],
                current_content=patch_payload["current_content"],
                proposed_content=patch_payload["proposed_content"],
                diff_text=patch_payload["diff_text"],
                status=patch_payload["status"],
                created_at=patch_payload["created_at"],
                approved_at=patch_payload.get("approved_at"),
                applied_at=patch_payload.get("applied_at"),
            ),
            target,
        )
        self.repository.create_delivery_run(
            DeliveryRun(
                id=str(uuid4()),
                patch_id=patch_id,
                target_id=target.id,
                status="APPLIED",
                mode=mode,
                created_at=utc_now_iso(),
                completed_at=utc_now_iso(),
                details={"target_path": target.storage_path},
            )
        )
        return self.repository.update_patch_status(
            patch_id,
            status="APPLIED",
            applied_at=utc_now_iso(),
        )

    def _suggest_sections(self, files: list[str]) -> list[str]:
        sections: list[str] = []
        for file_path in files:
            suffix = Path(file_path).suffix.lower()
            if "api" in file_path.lower():
                sections.append("API behavior and endpoint reference")
            elif "readme" in file_path.lower():
                sections.append("Setup and usage instructions")
            elif suffix in {".py", ".js", ".ts", ".java"}:
                sections.append("Implementation notes and developer workflow")
            elif file_path.startswith("docs/"):
                sections.append("Cross-reference related documentation pages")
        if not sections:
            sections.append("Release notes or change summary")
        return sorted(set(sections))

    def _build_recommended_actions(self, files: list[str], summary: str, source_event: dict[str, Any]) -> list[str]:
        actions = [
            "Review the affected documentation areas and confirm the change is reflected accurately.",
            "Update user-facing instructions, examples, or operational notes where behavior changed.",
        ]
        if any("api" in file_path.lower() for file_path in files):
            actions.append("Verify endpoint descriptions, request examples, and response formats against the new API behavior.")
        if any(file_path.lower().endswith(("readme.md", ".env.example", "docker-compose.yml")) for file_path in files):
            actions.append("Check setup and deployment instructions for command, configuration, or environment changes.")
        ticket_id = source_event.get("context", {}).get("ticket_id")
        if ticket_id:
            actions.append(f"Link the documentation update to ticket or change reference {ticket_id}.")
        if "added" in summary or "removed" in summary:
            actions.append("Confirm the proposal reflects the scope of additions and removals captured in the source change.")
        actions.append("Perform a final confidentiality review before sharing or publishing updated documentation.")
        return actions

    def _source_event_from_bundle(self, bundle: ArtifactBundle) -> dict[str, Any]:
        metadata = redact_data(bundle.metadata)
        links = {key: value for key, value in bundle.links.items() if value}
        event: dict[str, Any] = {
            "source_type": bundle.source_type,
            "event_type": bundle.event_type,
            "context": redact_data(bundle.context),
            "metadata": metadata,
        }
        if bundle.external_event_id:
            event["external_event_id"] = bundle.external_event_id
        if bundle.title:
            event["title"] = bundle.title
        if links:
            event["links"] = links
        return event

    def _write_outputs(self, proposal) -> None:
        output_dir = self.settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = output_dir / f"{proposal.id}.md"
        json_path = output_dir / f"{proposal.id}.json"
        markdown_path.write_text(proposal.draft_markdown, encoding="utf-8")
        json_path.write_text(
            json.dumps(redact_data(proposal.to_dict()), indent=2),
            encoding="utf-8",
        )
        logger.info("Wrote proposal outputs for %s", proposal.id)
