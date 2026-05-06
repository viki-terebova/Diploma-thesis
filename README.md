# Ariadne

Ariadne is a connector-oriented system for automated technical documentation maintenance using large language models.

This repository contains the first local-first implementation of Ariadne. It provides the core workflow of the final system in a reproducible environment: change ingestion, event normalization, sensitive-content redaction, documentation target selection, proposal generation, candidate documentation patches, approval, and local Markdown application.

External platform connectors such as GitHub, GitLab, Confluence, Jira, ServiceNow, Notion, and internal wiki integrations are planned extensions of the same architecture. They are not implemented in the current stage.

## Current Implementation Scope

Implemented:

- FastAPI backend in Python.
- PostgreSQL persistence through SQLAlchemy and Alembic.
- Local Git diff trigger.
- Generic local webhook-style trigger.
- Markdown documentation target under `sample_docs/`.
- Deterministic `DummyLLM` layer as a placeholder for future ChatGPT API integration.
- Redaction of common secret patterns before proposal generation and storage.
- Candidate documentation patch with current content, proposed content, and diff.
- Approval and local apply endpoints.
- Generic connection records for future connector configuration.
- Focused tests for redaction, protected blocks, local triggers, proposals, patches, and apply flow.

Not implemented yet:

- Real ChatGPT API integration.
- GitHub API integration.
- Confluence/Jira/ServiceNow or other enterprise connectors.
- Full UI.
- Semantic documentation search or embeddings.
- Enterprise authentication, RBAC, audit, or secret management.

## Repository Structure

```text
backend/
  src/ariadne_doc_assistant/
    api/          FastAPI routes
    core/         proposal pipeline, redaction, patch generation
    connectors/   local Git, local webhook stub, local Markdown target, connector interfaces
    locator/      local documentation target selection
    llm/          deterministic placeholder LLM layer
    storage/      PostgreSQL models and repository
    templates/    minimal landing page
    static/       landing page styles
  tests/          backend tests
  alembic/        database migrations

docs/             architecture, local flow, evaluation plan, roadmap
sample_docs/      local Markdown documentation used by the current implementation
scripts/          shell helpers for local or Docker runs
output/           generated proposals, ignored by git
```

## Requirements

- Python 3.11+
- Git
- Docker and Docker Compose
- PostgreSQL, provided by `docker-compose.yml` for local development

## Configuration

Use `.env-template` as the local configuration template. Keep real `.env` files untracked.

Important variables:

- `APP_HOST`
- `APP_PORT`
- `APP_LOG_LEVEL`
- `POSTGRES_DATABASE_URL`
- `APP_OUTPUT_DIR`
- `APP_LLM_PROVIDER`

The current supported local LLM provider is `dummy`.

## Run Locally

From the repository root:

```bash
docker compose up postgres -d
cd backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
alembic upgrade head
uvicorn ariadne_doc_assistant.main:app --reload --port 8000
```

The API is available at:

- landing page: `http://localhost:8000/`
- OpenAPI docs: `http://localhost:8000/openapi`

## Docker Compose

From the repository root:

```bash
docker compose up --build
```

This starts PostgreSQL and the Ariadne backend.

## Local Workflow

Create a local documentation target:

```bash
curl -X POST http://localhost:8000/documentation-targets \
  -H "Content-Type: application/json" \
  -d '{
    "id": "local-api-doc",
    "name": "Local API documentation",
    "target_kind": "local_docs",
    "storage_path": "sample_docs/api.md",
    "scope": "page",
    "config": {
      "component": "backend",
      "match_any_prefixes": ["backend/src/ariadne_doc_assistant/api/"]
    },
    "is_enabled": true
  }'
```

Create an approval policy:

```bash
curl -X POST http://localhost:8000/documentation-targets/local-api-doc/policy \
  -H "Content-Type: application/json" \
  -d '{
    "review_required": true,
    "auto_apply": false,
    "allowed_scope": "page",
    "is_enabled": true
  }'
```

Trigger a local Git diff proposal:

```bash
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "git",
    "payload": {
      "repo_path": ".",
      "from_ref": "HEAD~1",
      "to_ref": "HEAD"
    },
    "context": {
      "component": "backend",
      "ticket_id": "DOC-123"
    }
  }'
```

Or trigger a simple local webhook-style event:

```bash
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "webhook",
    "payload": {
      "source_name": "local-event",
      "changed_files": ["backend/src/ariadne_doc_assistant/api/routes.py"],
      "summary": "API route behavior changed",
      "diff_excerpt": "@@ -1 +1 @@\n- old\n+ new"
    },
    "context": {
      "component": "backend",
      "ticket_id": "DOC-456"
    }
  }'
```

Approve and apply the generated patch:

```bash
curl -X POST http://localhost:8000/patches/<patch-id>/approve
curl -X POST http://localhost:8000/patches/<patch-id>/apply
```

The local Markdown target is updated in `sample_docs/api.md`.

If no matching target exists, Ariadne creates a generated local target under `sample_docs/generated/` and prepares a create patch.

## Future Connector Configuration

The backend keeps a generic `connections` table and `/connections` endpoints. These records are intended to store source or target connector configuration metadata for future connector work.

They do not mean that an external connector is implemented today. The current executable flow uses local Git, local webhook-style input, and local Markdown output as the first implementation of the connector-oriented architecture.

## Storage

PostgreSQL tables:

- `connections`
- `trigger_events`
- `proposals`
- `documentation_targets`
- `approval_policies`
- `proposal_patches`
- `delivery_runs`

Generated proposal files are written to:

```text
output/proposals/
```

## Tests

From `backend/`:

```bash
pytest
```

If `pytest` is not on PATH, use the virtual environment Python:

```bash
./.venv/Scripts/python.exe -m pytest
```

On Windows, if pytest cannot access the default temp directory, run with an explicit base temp under the backend directory:

```bash
./.venv/Scripts/python.exe -m pytest --basetemp=.tmp_pytest_run
```

## What To Show On Project Seminar 1

Useful current-system walkthrough:

- Start PostgreSQL and the backend.
- Open `/openapi`.
- Register `sample_docs/api.md` as a local documentation target.
- Send a local webhook or Git trigger.
- Inspect the generated proposal and patch.
- Approve and apply the patch.
- Show the changed Markdown document.

Do not claim yet:

- real ChatGPT API generation,
- working GitHub/Confluence/Jira integrations,
- full semantic search,
- enterprise access control,
- finished evaluation on real projects.

## Future Direction

See:

- `docs/demo-flow.md`
- `docs/architecture.md`
- `docs/future-roadmap.md`
- `docs/future-connectors.md`
- `docs/evaluation-plan.md`

## License

MIT. See `LICENSE`.
