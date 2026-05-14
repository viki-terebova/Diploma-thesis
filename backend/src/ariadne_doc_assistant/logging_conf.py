from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence

from ariadne_doc_assistant.core.policies import mask_text


SENSITIVE_ENV_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "KEY", "BEARER", "PRIVATE")


def _collect_secret_values() -> list[str]:
    values: list[str] = []
    for key, value in os.environ.items():
        if value and any(marker in key.upper() for marker in SENSITIVE_ENV_MARKERS):
            values.append(value)
    return values


class MaskingFilter(logging.Filter):
    def __init__(self) -> None:
        super().__init__()
        self._env_secret_values = _collect_secret_values()

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._mask_value(record.msg)
        if record.args:
            if isinstance(record.args, Mapping):
                record.args = {key: self._mask_value(value) for key, value in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._mask_value(value) for value in record.args)
            else:
                record.args = self._mask_value(record.args)
        return True

    def _mask_value(self, value: object) -> object:
        if isinstance(value, str):
            text = mask_text(value)
            for secret in self._env_secret_values:
                text = text.replace(secret, "[MASKED]")
            return text
        if isinstance(value, Mapping):
            return {key: self._mask_value(val) for key, val in value.items()}
        if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
            return type(value)(self._mask_value(item) for item in value)
        return value


def configure_logging(log_level: str) -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(handler)

    for handler in root.handlers:
        if not any(isinstance(existing_filter, MaskingFilter) for existing_filter in handler.filters):
            handler.addFilter(MaskingFilter())
