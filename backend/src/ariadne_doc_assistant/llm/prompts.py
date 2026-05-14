from __future__ import annotations

from ariadne_doc_assistant.core.policies import mask_data, mask_text


def build_prompt(
    source_event: dict,
    affected_files: list[str],
    diff_summary: str,
    diff_text: str,
) -> str:
    safe_event = mask_data(source_event)
    safe_summary = mask_text(diff_summary)
    safe_diff = mask_text(diff_text)
    return "\n".join(
        [
            "Create a concise documentation update proposal.",
            f"Source event: {safe_event}",
            f"Affected files: {', '.join(affected_files)}",
            f"Summary: {safe_summary}",
            "Diff excerpt:",
            safe_diff[:4000],
        ]
    )
