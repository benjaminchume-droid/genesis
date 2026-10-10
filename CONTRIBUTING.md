# Contributing to Genesis

Genesis is a research project with strict architectural constraints. Contributions must preserve the non-neural design and must not disguise hard-coded answer paths as general intelligence.

## Before submitting a change

1. State the problem and the capability the change is intended to add.
2. Identify assumptions that are being supplied by the implementation.
3. Add tests for expected behavior and failure cases.
4. Include held-out tests when making a generalization claim.
5. Update architecture and status documentation when scope changes.
6. Run the test suite and report the exact command and result.
7. Avoid committing private data, credentials, generated databases, or user conversation logs.

## Prohibited shortcuts

- Neural-network inference, neural embeddings, or pretrained weights.
- External model fallback that silently violates the non-neural constraint.
- Canned demo conversations presented as general understanding.
- Claims of human-level intelligence without reproducible evidence.
- Unbounded execution or autonomous self-modification.

## Research changes

For a new learning or interpretation mechanism, document:
- The hypothesis being tested.
- Baselines and held-out evaluation.
- Known assumptions and failure modes.
- Resource use.
- What result would falsify the approach.

## Code quality

The initial runtime targets Python 3.11+ and the standard library. New dependencies require a clear justification. Keep modules narrow, deterministic where possible, and explicit about uncertainty.
