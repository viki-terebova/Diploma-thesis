from __future__ import annotations

import json
from difflib import unified_diff
from uuid import uuid4

from ariadne_doc_assistant.core.policies import redact_data, redact_text
from ariadne_doc_assistant.storage.models import Proposal, ProposalPatch
from ariadne_doc_assistant.utils.time import utc_now_iso


def build_proposal(
    source_event: dict,
    affected_files: list[str],
    diff_text: str,
    diff_summary: str,
    suggested_sections: list[str],
    recommended_actions: list[str],
    llm_output: str,
) -> Proposal:
    proposal_id = str(uuid4())
    redacted_event = redact_data(source_event)
    redacted_summary = redact_text(diff_summary)
    redacted_markdown = render_markdown(
        proposal_id=proposal_id,
        source_event=redacted_event,
        affected_files=affected_files,
        diff_summary=redacted_summary,
        suggested_sections=suggested_sections,
        recommended_actions=recommended_actions,
        llm_output=redact_text(llm_output),
        diff_text=redact_text(diff_text),
    )
    payload = {
        "id": proposal_id,
        "created_at": utc_now_iso(),
        "source_event": redacted_event,
        "affected_files": affected_files,
        "diff_summary": redacted_summary,
        "suggested_doc_sections": suggested_sections,
        "recommended_actions": recommended_actions,
        "status": "DRAFT",
    }
    return Proposal(
        id=proposal_id,
        created_at=payload["created_at"],
        source_event=payload["source_event"],
        affected_files=affected_files,
        diff_summary=redacted_summary,
        draft_markdown=redacted_markdown,
        draft_json=json.dumps(payload, indent=2),
        status="DRAFT",
    )


def build_patch(
    proposal: Proposal,
    *,
    target_id: str,
    target_path: str,
    patch_type: str,
    current_content: str,
    proposed_content: str,
    summary: str,
) -> ProposalPatch:
    return ProposalPatch(
        id=str(uuid4()),
        proposal_id=proposal.id,
        target_id=target_id,
        target_path=target_path,
        patch_type=patch_type,
        summary=redact_text(summary),
        current_content=current_content,
        proposed_content=proposed_content,
        diff_text=render_diff(current_content, proposed_content),
        status="PROPOSED",
        created_at=utc_now_iso(),
    )


def build_local_docs_patch_content(
    current_content: str,
    *,
    source_event: dict,
    diff_summary: str,
    affected_files: list[str],
    suggested_sections: list[str],
    llm_output: str,
) -> str:
    if not current_content.strip():
        title = source_event.get("title") or "Proposed Documentation Page"
        return "\n".join(
            [
                f"# {redact_text(title)}",
                "",
                "This page was created by the Ariadne local demo flow because no existing documentation target matched the incoming change event.",
                "",
                "## Summary of change",
                redact_text(diff_summary),
                "",
                "## Affected files",
                *([f"- `{path}`" for path in affected_files] or ["- No affected files detected"]),
                "",
                "## Suggested sections",
                *([f"- {section}" for section in suggested_sections] or ["- General documentation review"]),
                "",
                "## Draft guidance",
                redact_text(llm_output),
                "",
                "<!-- ARIADNE:PATCH-START -->",
                "## Proposed Documentation Update",
                "",
                "This document was created as a new target because no existing page was matched.",
                "<!-- ARIADNE:PATCH-END -->",
                "",
            ]
        )

    affected_file_lines = [f"- `{path}`" for path in affected_files] or ["- No affected files detected"]
    suggested_section_lines = [f"- {section}" for section in suggested_sections] or ["- General documentation review"]
    review_block = "\n".join(
        [
            "<!-- ARIADNE:PATCH-START -->",
            "## Proposed Documentation Update",
            "",
            f"Source: `{source_event.get('source_type', 'unknown')}` / `{source_event.get('event_type', 'unknown')}`",
            "",
            "### Change summary",
            redact_text(diff_summary),
            "",
            "### Affected files",
            *affected_file_lines,
            "",
            "### Suggested sections",
            *suggested_section_lines,
            "",
            "### Draft guidance",
            redact_text(llm_output),
            "<!-- ARIADNE:PATCH-END -->",
        ]
    )

    start_marker = "<!-- ARIADNE:PATCH-START -->"
    end_marker = "<!-- ARIADNE:PATCH-END -->"
    if start_marker in current_content and end_marker in current_content:
        before, remainder = current_content.split(start_marker, 1)
        _, after = remainder.split(end_marker, 1)
        return before.rstrip() + "\n\n" + review_block + "\n" + after.lstrip()

    return current_content.rstrip() + "\n\n" + review_block + "\n"


def render_markdown(
    proposal_id: str,
    source_event: dict,
    affected_files: list[str],
    diff_summary: str,
    suggested_sections: list[str],
    recommended_actions: list[str],
    llm_output: str,
    diff_text: str,
) -> str:
    files_text = "\n".join(f"- `{path}`" for path in affected_files) if affected_files else "- No file changes detected"
    sections_text = "\n".join(f"- {section}" for section in suggested_sections) if suggested_sections else "- General project overview"
    actions_text = "\n".join(f"- {action}" for action in recommended_actions) if recommended_actions else "- Review documentation impact manually"
    context = source_event.get("context", {})
    context_lines = [
        f"- Source type: `{source_event.get('source_type', 'unknown')}`",
        f"- Component: `{context.get('component') or 'n/a'}`",
        f"- Ticket: `{context.get('ticket_id') or 'n/a'}`",
    ]
    return "\n".join(
        [
            f"# Documentation Update Proposal {proposal_id}",
            "",
            "## Source context",
            *context_lines,
            "",
            "## Summary of changes",
            diff_summary,
            "",
            "## Affected files",
            files_text,
            "",
            "## Suggested documentation sections to update",
            sections_text,
            "",
            "## Recommended follow-up actions",
            actions_text,
            "",
            "## Draft notes",
            llm_output,
            "",
            "## Key diff excerpt",
            "```diff",
            truncate_diff(diff_text),
            "```",
            "",
        ]
    )


def truncate_diff(diff_text: str, max_lines: int = 80, max_chars_per_line: int = 240) -> str:
    lines = diff_text.splitlines()
    trimmed = [line[:max_chars_per_line] for line in lines[:max_lines]]
    if not trimmed:
        trimmed = ["# No diff excerpt provided"]
    elif len(lines) > max_lines:
        trimmed.append("... diff truncated ...")
    return "\n".join(trimmed)


def render_diff(current_content: str, proposed_content: str) -> str:
    diff_lines = unified_diff(
        current_content.splitlines(),
        proposed_content.splitlines(),
        fromfile="current",
        tofile="proposed",
        lineterm="",
    )
    rendered = "\n".join(diff_lines)
    return truncate_diff(rendered, max_lines=120, max_chars_per_line=240)
