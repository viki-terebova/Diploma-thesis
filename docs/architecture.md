# Architecture

## Current Scope

Ariadne is a connector-oriented documentation maintenance system. The current repository contains its first local-first backend implementation.

This implementation establishes the core workflow that later external connectors should reuse: local change events are normalized, sensitive content is redacted, relevant documentation targets are selected, reviewable documentation update proposals are generated, candidate patches are stored in PostgreSQL, and approved patches can be applied to local Markdown files.

## Main Modules

- `api/`: HTTP routes for triggers, documentation targets, policies, proposals, and patches.
- `core/`: proposal pipeline, redaction helpers, proposal rendering, and patch rendering.
- `connectors/`: local Git source connector, generic local webhook stub, local Markdown target connector, and connector interfaces for future extensions.
- `locator/`: simple local documentation target selection based on component and changed file prefixes.
- `llm/`: deterministic placeholder LLM layer. This is the future integration point for ChatGPT API usage.
- `storage/`: PostgreSQL-backed persistence through SQLAlchemy and Alembic.

## Request Flow

1. `POST /trigger` receives a local event envelope with `source_type`, `payload`, and optional `context`.
2. `source_type="git"` computes changed files and a unified diff from a local repository.
3. `source_type="webhook"` accepts an already summarized local event payload.
4. The pipeline normalizes the event into an `ArtifactBundle`.
5. Redaction removes common secret patterns from text and structured data.
6. The local locator tries to match the event to a `DocumentationTarget`.
7. If no target matches, a generated local target is created under `sample_docs/generated/`.
8. `DummyLLM` creates deterministic draft guidance from sanitized input.
9. The proposal and candidate patch are stored in PostgreSQL.
10. Proposal files are also written to `output/proposals/`.
11. A reviewer can approve and apply the patch to local Markdown documentation.

## Data Model

Current PostgreSQL tables:

- `connections`
- `trigger_events`
- `proposals`
- `documentation_targets`
- `approval_policies`
- `proposal_patches`
- `delivery_runs`

The `connections` table stores generic source or target connector configuration metadata. It is part of the connector-oriented final architecture, even though external connector execution is not implemented in the current stage.

## Extension Points

The code keeps connector and LLM boundaries because they are useful for the thesis direction:

- Future source connectors can normalize external events into `ArtifactBundle`.
- Future target connectors can write proposals to external documentation systems.
- Future LLM providers can replace `DummyLLM` behind the same interface.

These extension points keep the first implementation aligned with the planned final system while allowing the current stage to remain reproducible and local.
