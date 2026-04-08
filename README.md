# Ariadne (ariadne-doc-assistant)

![Ariadne logo](assets/ariadne-logo-dark.png)

Ariadne is an artifact-connected documentation assistant for reducing documentation drift.

This repository contains the first operational version of Ariadne, a diploma thesis project focused on reducing documentation drift. Ariadne listens for a change event, computes a diff, applies redaction policies, and generates documentation update proposals in both Markdown and JSON. The public repository remains open-source-safe, while the same codebase and architecture are intended to support production deployment with private connectors, authenticated APIs, and organization-specific integration logic.

## Branding

The product is called **Ariadne**, but the Python module is **`ariadne_doc_assistant`** to avoid conflict with the existing `ariadne` GraphQL library.

- Product name: `Ariadne`
- GitHub repo name: `ariadne-doc-assistant`
- Python package/import path: `ariadne_doc_assistant`
- CLI/docs command name: `ariadne-doc`

See [docs/branding.md](docs/branding.md) and [assets/brand.md](assets/brand.md) for naming and asset rules.

## Current Implementation Scope

- FastAPI backend in Python 3.11+
- PostgreSQL-only persistence managed through Alembic migrations
- Git-based trigger flow in the first operational version
- Proposal generation written to `output/proposals/`
- Deterministic drafting with a `DummyLLM` abstraction
- Redaction applied to logs, proposal outputs, and text sent to the LLM interface
- Runtime plugin loading from `APP_PLUGIN_PATH`

## Operating Contexts

### Standalone local mode

Default mode. Only the built-in Git connector is active. The app can generate proposal drafts from local Git diffs without any proprietary systems or secrets. This mode is intended for local development, testing, evaluation, and open-source reproducibility.

### Production-integrated mode

Optional mode. Private connector plugins can be mounted at runtime through `APP_PLUGIN_PATH`. Stub connector modules for systems such as Confluence and ServiceNow are included only as safe examples in the public repository. In a company environment, the same core service can be deployed with private connectors, token-based API access, service credentials with scoped permissions, and organization-specific integration logic.

## Threat model summary

- Secrets must never be committed. Use `.env.example` as the template and keep real values in untracked `.env` files or platform secret stores.
- Logs are redacted using regex rules and environment-derived secret values.
- Proposal drafts are redacted before they are persisted or written to disk.
- Any text passed to the LLM interface is redacted first, even when using the default dummy provider.
- Protected documentation blocks marked with `<!-- PROTECTED:START -->` and `<!-- PROTECTED:END -->` are reserved for future update flows and must not be modified by automated documentation rewrites.

## Deployment Intent

The target system is broader than the currently implemented public version. Ariadne is designed as a connector-based service that should work in two practical contexts:

- locally, as a standalone environment for development, testing, and thesis evaluation
- in production, as an integrated service connected to the platforms used by a specific team or company

The current codebase therefore represents a production-oriented first version of the larger system architecture. Its implemented trigger is Git-first, but its outputs are platform-neutral and its connector model is intended to support additional source and target platforms later.

## Quickstart

### Requirements

- Python 3.11+
- Git
- Docker and Docker Compose

### 1. Local run with `venv`

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

If Docker is not available, you can use any existing PostgreSQL instance. Create a database and user, then point `POSTGRES_DATABASE_URL` at it before running Alembic.

Example SQL:

```sql
CREATE USER ariadne_user WITH PASSWORD 'ariadne_db_password';
CREATE DATABASE ariadne_db OWNER ariadne_user;
```

Example connection string:

```bash
export POSTGRES_DATABASE_URL=postgresql+psycopg://ariadne_user:ariadne_db_password@localhost:5433/ariadne_db
```

Windows PowerShell:

```powershell
cd scripts
.\run_local.ps1
```

Windows PowerShell manual alternative:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
alembic upgrade head
uvicorn ariadne_doc_assistant.main:app --reload --port 8000
```

### 2. Docker Compose run

From the repository root:

```bash
docker compose up --build
```

If this fails with an error mentioning `dockerDesktopLinuxEngine` or `//./pipe/dockerDesktopLinuxEngine`, Docker Desktop is not running. Start Docker Desktop first and wait until the engine is available.

### Database initialization

After PostgreSQL is running and `POSTGRES_DATABASE_URL` points to the correct database, initialize the schema from the `backend/` directory:

```bash
alembic upgrade head
```

Useful Alembic commands:

```bash
alembic current
alembic history
alembic downgrade -1
```

If `alembic upgrade head` fails with `password authentication failed`, PostgreSQL is running but the username, password, or database name in `POSTGRES_DATABASE_URL` does not match the actual server configuration. If you already have a local PostgreSQL server on `localhost:5432`, use the Docker-mapped port `localhost:5433` for this project.

Windows PowerShell from `scripts/`:

```powershell
cd scripts
.\run_docker.ps1
```

### 3. Trigger example using `curl`

Create a stored GitHub source connection:

```bash
curl -X POST http://localhost:8000/connections \
  -H "Content-Type: application/json" \
  -d '{
    "id": "github-main",
    "name": "GitHub main repository",
    "connector_kind": "github",
    "role": "source",
    "base_url": "https://api.github.com",
    "config": {
      "repository": "org/repo"
    },
    "is_enabled": true
  }'
```

Run this from the repository root while the service is running:

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

Windows PowerShell:

```powershell
$body = @{
  source_type = "git"
  payload = @{
    repo_path = "."
    from_ref = "HEAD~1"
    to_ref = "HEAD"
  }
  context = @{
    component = "backend"
    ticket_id = "DOC-123"
  }
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/trigger" -ContentType "application/json" -Body $body
```

`POST /trigger/git` remains available as a compatibility route for direct Git-only requests.
Relative `repo_path` values are resolved from the Ariadne project root. Use an absolute path if you want to target a repository outside this project tree.

Example of the second trigger source stub:

```bash
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "webhook",
    "payload": {
      "source_name": "jira-webhook",
      "changed_files": ["docs/architecture.md", "backend/src/ariadne_doc_assistant/api/routes.py"],
      "summary": "Webhook-reported API and documentation change",
      "diff_excerpt": "@@ -1 +1 @@\n- old\n+ new"
    },
    "context": {
      "component": "docs",
      "ticket_id": "DOC-456"
    }
  }'
```

Example of the stored GitHub webhook route:

```bash
curl -X POST http://localhost:8000/webhooks/github/github-main \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-GitHub-Delivery: delivery-123" \
  -d '{
    "ref": "refs/heads/main",
    "before": "1111111111111111111111111111111111111111",
    "after": "2222222222222222222222222222222222222222",
    "compare": "https://github.com/org/repo/compare/111...222",
    "repository": {
      "name": "repo",
      "full_name": "org/repo"
    },
    "head_commit": {
      "message": "Update API validation docs"
    },
    "commits": [
      {
        "id": "2222222222222222222222222222222222222222",
        "message": "Update API validation docs",
        "modified": ["docs/api.md"]
      }
    ]
  }'
```

### 4. Run tests

```bash
cd backend
pytest
```

## Storage locations

- PostgreSQL tables: `connections`, `trigger_events`, and `proposals`
- Generated proposal files: `output/proposals/<proposal-id>.md` and `output/proposals/<proposal-id>.json`

The database connection and output directory can be overridden with environment variables:

- `POSTGRES_DATABASE_URL`
- `APP_OUTPUT_DIR`

## Configuration

Copy `.env.example` to `.env` if needed and fill only non-secret local values. Sensitive values should come from environment variables or an external secret manager in production deployments.

Notable environment variables:

- `APP_HOST`
- `APP_PORT`
- `POSTGRES_DATABASE_URL`
- `APP_OUTPUT_DIR`
- `APP_LOG_LEVEL`
- `APP_PLUGIN_PATH`
- `APP_ENABLE_INTEGRATED_CONNECTORS`
- `APP_LLM_PROVIDER`

## Private Connector Model

Private connector plugins can be added without modifying this repository:

1. Create a private Python module directory.
2. Set `APP_PLUGIN_PATH` to that directory.
3. In a plugin module, import `register_connector` from `ariadne_doc_assistant.connectors.base` and register your connector class.

The public repository does not ship any vendor SDKs, tokens, or proprietary connector logic. This separation keeps the public core reproducible while allowing the same service to be integrated with company platforms in production.

## Development

Install dependencies and run tests:

```bash
cd backend
pip install -e .[dev]
pytest
```

## Design notes

- Proposal storage uses SQLAlchemy over PostgreSQL with Alembic migrations.
- Proposal generation is deterministic so the repository remains runnable without an external LLM.
- The `llm` package exists as an abstraction point for later providers such as LiteLLM or OpenAI-compatible backends.
- The architecture is designed for both standalone local use and integrated production deployment through private connectors.

## License

MIT. See `LICENSE`.
