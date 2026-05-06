# Local Workflow

This document describes the current local-first Ariadne workflow. It is the first executable implementation of the planned system, not a separate demo architecture.

## Preconditions

- PostgreSQL is running.
- Alembic migrations have been applied.
- The FastAPI backend is running.
- `sample_docs/api.md` exists.

## Flow

1. Create a local documentation target for `sample_docs/api.md`.
2. Create an approval policy for that target.
3. Submit a local Git or webhook-style trigger through `POST /trigger`.
4. Ariadne redacts the event and builds an internal artifact bundle.
5. Ariadne locates the matching local Markdown target.
6. Ariadne generates a deterministic draft proposal through `DummyLLM`.
7. Ariadne creates a candidate patch with current content, proposed content, and diff.
8. The proposal and patch are stored in PostgreSQL.
9. The proposal is also written to `output/proposals/`.
10. A reviewer approves the patch.
11. Ariadne applies the patch to the local Markdown file.

## Visible Output

The expected visible result is an `<!-- ARIADNE:PATCH-START -->` block appended to or replaced inside the target Markdown document.

If no target matches the incoming event, Ariadne creates a generated documentation target under `sample_docs/generated/`.
