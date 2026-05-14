from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ariadne_doc_assistant.api.routes import router
from ariadne_doc_assistant.config import settings
from ariadne_doc_assistant.logging_conf import configure_logging


configure_logging(settings.log_level)

OPENAPI_TAGS = [
    {
        "name": "Targets",
        "description": "Endpoints for managing local Markdown documentation targets.",
    },
    {
        "name": "Triggers",
        "description": "Endpoints used to submit change events and start proposal generation.",
    },
    {
        "name": "Proposals",
        "description": "Endpoints for listing and retrieving generated documentation proposals.",
    },
    {
        "name": "Patches",
        "description": "Endpoints for reviewing, approving, and applying generated documentation patches.",
    },
]

app = FastAPI(
    title=settings.app_name,
    summary="Artifact-connected documentation assistant",
    description=(
        "Ariadne analyzes software change events and produces documentation update proposals. "
        "The API supports generic triggers, Git-based compatibility routes, and retrieval of stored proposals."
    ),
    version="0.1.0",
    openapi_tags=OPENAPI_TAGS,
    docs_url="/openapi",
    redoc_url=None,
    openapi_url="/openapi.json",
)
app.include_router(router)

assets_dir = settings.project_root / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=Path(assets_dir)), name="assets")

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

def main() -> None:
    import uvicorn

    uvicorn.run("ariadne_doc_assistant.main:app", host=settings.host, port=settings.port, reload=False)
