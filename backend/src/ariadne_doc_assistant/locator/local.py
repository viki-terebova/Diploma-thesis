from __future__ import annotations

from ariadne_doc_assistant.connectors.models import ArtifactBundle
from ariadne_doc_assistant.storage.models import DocumentationTarget


class LocalContentLocator:
    def locate(self, bundle: ArtifactBundle, targets: list[DocumentationTarget]) -> DocumentationTarget | None:
        enabled_targets = [target for target in targets if target.is_enabled]
        if not enabled_targets:
            return None

        scored_targets = sorted(
            (
                (self._score_target(bundle, target), target)
                for target in enabled_targets
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        best_score, best_target = scored_targets[0]
        if best_score <= 0:
            return None
        return best_target

    def _score_target(self, bundle: ArtifactBundle, target: DocumentationTarget) -> int:
        score = 0
        config = target.config or {}
        patterns = [str(value).lower() for value in config.get("match_any_prefixes", [])]
        repository = str(bundle.metadata.get("repository", "")).lower()
        target_component = str(config.get("component", "")).lower()
        event_component = str(bundle.context.get("component", "")).lower()

        for changed_file in bundle.changed_files:
            lowered = changed_file.lower()
            if any(lowered.startswith(pattern) for pattern in patterns):
                score += 10
            if target_component and target_component in lowered:
                score += 4

        if target_component and event_component and target_component == event_component:
            score += 5
        if repository and str(config.get("repository", "")).lower() == repository:
            score += 3
        return score
