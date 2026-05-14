# Local Workflow

This document describes the current local-first Ariadne workflow. It is the first executable implementation of the planned system.

## Preconditions

- PostgreSQL is running.
- Alembic migrations have been applied.
- The FastAPI backend is running.
- `sample_docs/api.md` exists.

## Flow

1. Create a local documentation target for `sample_docs/api.md`.
2. Submit a local Git or webhook-style trigger through `POST /trigger`.
3. Ariadne masks sensitive data in the event and builds an internal artifact bundle.
4. Ariadne locates the matching local Markdown target.
5. Ariadne generates a deterministic draft proposal through `DummyLLM`.
6. Ariadne creates a candidate patch with current content, proposed content, and diff.
7. The proposal and patch are stored in PostgreSQL.
8. The proposal is also written to `output/proposals/`.
9. A reviewer approves or rejects the patch.
10. Ariadne applies approved patches to the local Markdown file.

## Visible Output

The expected visible result is an `<!-- ARIADNE:PATCH-START -->` block appended to or replaced inside the target Markdown document.

If no target matches the incoming event, Ariadne creates a generated documentation target under `sample_docs/generated/`.
