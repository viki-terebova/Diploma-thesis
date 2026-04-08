from __future__ import annotations

import importlib.util
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def load_plugins(plugin_path: Path | None) -> list[str]:
    if plugin_path is None:
        return []
    path = Path(plugin_path)
    if not path.exists() or not path.is_dir():
        logger.warning("Plugin path is not available: %s", str(path))
        return []

    loaded_modules: list[str] = []
    for file_path in sorted(path.glob("*.py")):
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        loaded_modules.append(file_path.stem)
    logger.info("Loaded %s plugin module(s)", len(loaded_modules))
    return loaded_modules
