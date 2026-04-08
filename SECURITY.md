# Security Policy

## Reporting

Please do not file public issues for suspected security problems that may expose secrets or internal deployment details.

Report security concerns privately to the project maintainer using a private channel suitable for your environment. If this repository is used inside an organization, follow that organization's incident reporting process first.

## Safe issue hygiene

When reporting bugs or requesting help:

- Do not paste secrets into issues, pull requests, or chat transcripts.
- Do not attach unredacted logs.
- Do not attach proprietary connector configuration.
- Do not share generated proposal files unless you have reviewed them for sensitive content.

## Secret handling expectations

- Real credentials must stay out of source control.
- `.env` and similar local configuration files are ignored by Git.
- The service applies redaction to logs, proposal artifacts, and text sent to the LLM abstraction.

## Supported hardening measures

- Runtime environment variables
- Private plugin directories mounted outside the repository
- Least-privilege service accounts for enterprise connectors
- Human review before publishing documentation changes
