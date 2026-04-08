# Architecture

## Overview

The current Ariadne implementation is a single FastAPI service with a modular internal structure. It is intended as the first operational, production-oriented version of a broader connector-based system that can run both in standalone local mode and in an integrated production environment.

- `api/` exposes HTTP endpoints.
- `core/` owns the proposal pipeline, redaction, and document-safe helpers.
- `connectors/` exposes built-in connectors and a registry for private plugins.
- `llm/` provides an abstraction for future LLM providers.
- `storage/` persists trigger events and proposals in PostgreSQL through SQLAlchemy.
- `utils/` contains runtime helpers such as plugin loading and time utilities.

The architecture separates the core proposal workflow from source and target integrations. This allows the same service to be used locally with only built-in components, while also making it possible to connect organization-specific platforms later through private connectors.

## Request flow

1. `POST /trigger` receives a normalized trigger envelope with `source_type`, `payload`, and optional context.
2. In the current implementation, `source_type="git"` dispatches to the Git connector, which computes changed files and a unified diff.
3. Redaction policies sanitize the diff and request context.
4. The pipeline constructs a deterministic proposal draft.
5. The proposal is stored in PostgreSQL and written to disk as Markdown and JSON.
6. The API returns the stored proposal record.

`POST /trigger/git` remains available as a compatibility endpoint for direct Git-specific requests.

## Module boundaries

- API modules should not perform Git or database operations directly.
- Connector modules should not contain persistence logic.
- Redaction should happen before logging, before persistence, and before LLM calls.
- Protected block handling is isolated so future document update workflows can preserve human-managed sections.

## Extensibility

- Additional connectors can be registered at runtime from `APP_PLUGIN_PATH`.
- The LLM interface is provider-agnostic and defaults to `DummyLLM`.
- Publishing to systems such as Confluence is intentionally stubbed in the public repository.
- The same core service is designed to run with private source or target connectors in a production deployment.
- The internal proposal representation remains platform-neutral so it can later be transformed for different documentation systems.
