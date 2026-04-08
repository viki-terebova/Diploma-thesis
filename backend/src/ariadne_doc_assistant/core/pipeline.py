from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ariadne_doc_assistant.config import Settings
from ariadne_doc_assistant.connectors.github_source import GitHubSourceConnector
from ariadne_doc_assistant.connectors.git_repo import GitRepositoryConnector
from ariadne_doc_assistant.connectors.models import ArtifactBundle
from ariadne_doc_assistant.connectors.webhook_stub import WebhookStubConnector
from ariadne_doc_assistant.core.policies import redact_data, redact_text
from ariadne_doc_assistant.core.proposals import build_proposal
from ariadne_doc_assistant.llm.client import get_llm_client
from ariadne_doc_assistant.llm.prompts import build_prompt
from ariadne_doc_assistant.storage.db import ProposalRepository


logger = logging.getLogger(__name__)


class ProposalPipeline:
    def __init__(self, settings: Settings, repository: ProposalRepository) -> None:
        self.settings = settings
        self.repository = repository
        self.git_connector = GitRepositoryConnector()
        self.github_connector = GitHubSourceConnector()
        self.webhook_connector = WebhookStubConnector()
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
        return self._build_and_store_proposal(
            source_event=redacted_event,
            affected_files=affected_files,
            diff_text=diff_text,
            diff_summary=summary,
            suggested_sections=self._suggest_sections(affected_files),
            recommended_actions=self._build_recommended_actions(affected_files, summary, redacted_event),
        )

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
