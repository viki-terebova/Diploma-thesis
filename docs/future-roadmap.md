# Future Roadmap

## 1. Local Demonstrator

- Keep local startup stable.
- Keep PostgreSQL migrations simple and reproducible.
- Maintain focused tests for the implemented local flow.
- Improve local Markdown patch generation.
- Make candidate documentation versions easier to inspect.

## 2. ChatGPT API Integration

- Add a provider implementation behind the existing LLM interface.
- Build prompts from sanitized event context and selected documentation excerpts.
- Keep redaction before any external API call.
- Log model, token usage, latency, and approximate cost.
- Keep deterministic test coverage by mocking the provider.

## 3. Better Documentation Selection

- Improve rules based on component names and changed file paths.
- Add document metadata for components, owners, and scopes.
- Evaluate whether embeddings are useful after the rule-based baseline is stable.

## 4. Open-Source Evaluation

- Select a suitable open-source project.
- Prepare a set of representative changes.
- Identify relevant reference documentation.
- Measure document selection quality and proposal usefulness.
- Track precision, recall, reviewer acceptance, and manual effort reduction.

## 5. Company Validation

- Use anonymized, non-public validation.
- Collect reviewer feedback through a questionnaire or rubric.
- Evaluate readability, correctness, usefulness, and safety.
- Report only aggregate results without company data.

## 6. Platform Connectors

- Add GitHub, GitLab, Confluence, Notion, and internal wiki connectors only after the local core is stable.
- Keep connector code optional and isolated from the public reproducible core where needed.
