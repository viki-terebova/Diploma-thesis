from __future__ import annotations

from abc import ABC, abstractmethod

from ariadne_doc_assistant.core.policies import mask_text


class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class DummyLLM(BaseLLM):
    def generate(self, prompt: str) -> str:
        safe_prompt = mask_text(prompt)
        lower_prompt = safe_prompt.lower()
        focus_points: list[str] = []
        if "api" in lower_prompt:
            focus_points.append("API contracts and usage examples")
        if "docker" in lower_prompt or "compose" in lower_prompt or ".env" in lower_prompt:
            focus_points.append("deployment and environment configuration")
        if "readme" in lower_prompt or "docs/" in lower_prompt:
            focus_points.append("existing documentation cross-references")
        if not focus_points:
            focus_points.append("behavioral changes and operator guidance")
        return (
            "Deterministic draft generated from sanitized input. "
            f"Prompt length: {len(safe_prompt)} characters. "
            "Primary review focus: "
            + ", ".join(focus_points)
            + ". Confirm that examples, runbooks, and user-facing instructions still match the implemented behavior."
        )


def get_llm_client(provider: str) -> BaseLLM:
    if provider.lower() == "dummy":
        return DummyLLM()
    return DummyLLM()
