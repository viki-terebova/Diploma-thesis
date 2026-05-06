# Future Connectors

Connectors are planned extensions of Ariadne's current architecture. The first implementation keeps connector boundaries in place while executing only local source and target flows.

## Source Connectors

Potential future source connectors:

- GitHub API
- GitLab
- Jira
- ServiceNow
- internal deployment or change-management systems
- generic webhooks

Their responsibility would be to normalize external changes into Ariadne's internal artifact bundle.

## Target Connectors

Potential future target connectors:

- Confluence
- Notion
- internal wiki
- Git-backed documentation repositories
- Markdown file stores

Their responsibility would be to deliver approved documentation updates or create review tasks in an external documentation system.

## Current Boundary

The current repository only implements:

- local Git diff collection,
- local webhook-style event input,
- local Markdown target updates.

The repository also keeps generic `connections` records so future connector configuration has a stable place in the data model.

No external platform connector is currently implemented.
