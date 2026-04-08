from __future__ import annotations

import re
from collections.abc import Mapping, Sequence


SECRET_PATTERNS = [
    re.compile(r"(?i)\b(bearer)\s+[a-z0-9._\-=/+]+\b"),
    re.compile(r"(?i)\b(api[_-]?key|token|password|secret)\b\s*[:=]\s*['\"]?([^\s'\",;]+)"),
    re.compile(r"(?i)\b(sk|rk|pk)_[a-z0-9]{8,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
]

PROTECTED_START = "<!-- PROTECTED:START -->"
PROTECTED_END = "<!-- PROTECTED:END -->"


def redact_text(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(_replacement, redacted)
    return redacted


def _replacement(match: re.Match[str]) -> str:
    groups = match.groups()
    if groups:
        label = groups[0]
        return f"{label}= [REDACTED]"
    return "[REDACTED]"


def redact_data(value: object) -> object:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {key: redact_data(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [redact_data(item) for item in value]
    return value


def extract_protected_blocks(text: str) -> list[str]:
    pattern = re.compile(
        rf"{re.escape(PROTECTED_START)}[\s\S]*?{re.escape(PROTECTED_END)}",
        re.MULTILINE,
    )
    return pattern.findall(text)


def merge_preserving_protected_blocks(existing_text: str, proposed_text: str) -> str:
    blocks = extract_protected_blocks(existing_text)
    result = proposed_text
    for index, block in enumerate(blocks):
        placeholder = f"__DOCASSIS_PROTECTED_BLOCK_{index}__"
        result = result.replace(block, placeholder)
        result = result.replace(placeholder, block)
    if blocks and PROTECTED_START not in result:
        return "\n".join([existing_text.rstrip(), "", proposed_text.lstrip()])
    return result
