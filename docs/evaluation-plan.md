# Evaluation Plan

## Thesis objective

Evaluate whether Ariadne's artifact-connected proposal generation can reduce documentation drift while maintaining secrecy constraints and human oversight.

## Proposed metrics

- Proposal coverage: percentage of change events that produce a useful draft
- Reviewer acceptance rate: percentage of proposals accepted with minor edits
- Time to update documentation: baseline manual process versus proposal-assisted process
- Secret handling failures: number of leaks detected in logs or proposal artifacts

## Experimental design

1. Select representative repositories or modules with recurring documentation drift.
2. Trigger proposal generation from controlled Git change events.
3. Ask reviewers to score proposals against a rubric.
4. Compare assisted and non-assisted documentation update workflows.

## Human review rubric

- Relevance: proposal addresses the actual changed components
- Accuracy: summary reflects the implemented change
- Actionability: suggested documentation sections are useful
- Safety: no sensitive content appears in the draft
- Effort reduction: reviewer reports reduced manual work

## Expected limitations

- Heuristic proposal generation may miss semantic impacts.
- Git-only context is weaker than enterprise artifact context.
- Human review remains necessary to prevent incorrect updates.
