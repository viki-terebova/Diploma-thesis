# Threat Model

## Security goals

- Prevent secrets from being committed, logged, or emitted in proposal drafts.
- Keep the repository runnable without proprietary dependencies.
- Keep future external integrations optional and separated from the local-first core until they are intentionally implemented.

## Assumptions

- The Ariadne backend currently runs in a controlled local development environment.
- Git diffs may contain sensitive strings.
- Human review is required before any documentation is published.

## Main risks

### Secret leakage through logs

Risk: access tokens, passwords, or copied key material appear in structured or exception logs.

Mitigation:

- Regex-based redaction for common secret patterns
- Redaction of environment-derived secret values before log emission
- Default logging configuration that attaches a redaction filter to handlers

### Secret leakage through proposal drafts

Risk: generated Markdown or JSON proposals reproduce secrets found in source changes.

Mitigation:

- Redaction is applied to the diff summary and all generated draft content before storage
- Proposal artifacts are deterministic and minimal in the first operational version

### Secret leakage to the LLM

Risk: external model providers receive raw secrets embedded in diffs or metadata.

Mitigation:

- All text is redacted before it reaches the LLM abstraction
- The default provider is local and deterministic
- External providers are optional and disabled by default

### Premature external integration coupling

Risk: the first implementation starts depending on vendor SDKs, external endpoints, or private configuration before the core workflow is stable.

Mitigation:

- The current runtime ships only local source and target flows.
- Future connector work is documented separately from the currently implemented local-first core.
- External integrations should be optional and added only after local evaluation is stable.

## Future RBAC concept

The current implementation does not implement RBAC. A possible future production model is:

- Service runtime identity has read access only to the minimum required systems.
- Connector-specific credentials are scoped per system.
- Proposal review and publication are separate privileges.
- Audit trails should exist for proposal generation and publication in enterprise deployments.
