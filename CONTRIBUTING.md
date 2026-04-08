# Contributing

## Scope

Contributions that keep the repository open-source-safe are welcome. The public repository should remain runnable without proprietary systems, vendor credentials, or enterprise-only code.

## Basic workflow

1. Fork the repository.
2. Create a feature branch.
3. Keep changes focused and documented.
4. Add or update tests when behavior changes.
5. Open a pull request with a concise summary and validation notes.

## Development setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

## Security expectations

- Never commit secrets, tokens, or private keys.
- Do not include proprietary connector logic in the public repository.
- Sanitize logs, screenshots, stack traces, and proposal samples before sharing them in issues or pull requests.

## Code style

- Python 3.11+
- Small, testable modules
- Explicit redaction on any new path that handles untrusted or sensitive text
