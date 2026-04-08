# Threat Model

## Security goals

- Prevent secrets from being committed, logged, or emitted in proposal drafts.
- Keep the open-source repository runnable without proprietary dependencies.
- Allow enterprise-specific integrations to remain private and optional.

## Assumptions

- The Ariadne backend runs either in a controlled local environment or in a controlled production deployment.
- Git diffs may contain sensitive strings.
- Operators may configure enterprise connectors through environment variables and private plugins.
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

### Unsafe enterprise coupling

Risk: the public repository requires vendor SDKs, enterprise endpoints, or private configuration.

Mitigation:

- Public repo ships only interfaces and stubs
- Private plugins are mounted dynamically using `APP_PLUGIN_PATH`
- Integrated production deployment is opt-in and organization-specific

## RBAC concept

The current implementation does not implement full RBAC, but the intended production model is:

- Service runtime identity has read access only to the minimum required systems.
- Connector-specific credentials are scoped per system.
- Proposal review and publication are separate privileges.
- Audit trails should exist for proposal generation and publication in enterprise deployments.
