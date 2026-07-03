# Tests

Tests cover parser, preflight, and dashboard plumbing behavior that should work without Lean, a model API key, or network access.

- `test_preflight.py` validates task-checker behavior and lean-root checks.
- `test_dashboard.py` validates dashboard generation and result summarization for baseline/agent comparison rows.

Full proof correctness is tested by running ProofBench and selecting the Lean verifier in a configured miniF2F Lean environment.
