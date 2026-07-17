# Testing Policy

## Command Matrix

| Check | Command | Status | Notes |
| --- | --- | --- | --- |
| Narrow CLI/unit tests | `python3 -m unittest discover -s tests -p 'test_cli.py' -v` | available | Use for CLI workflow changes. |
| Full unit suite | `python3 -m unittest discover -s tests -v` | available | Deterministic fallback when `uv` is unavailable. |
| Project package command | `uv run pytest -q` | optional | Preferred when `uv` is installed; unavailable in some agent containers. |
| Smoke experiment | `python3 -m proofbench.cli run --agents llm_baseline --task-count 1 --model-provider mock --verifier static --results-dir proof-smoke --no-dashboard` | available | Proves non-interactive run writes a result JSONL without real API credentials. |
| Preflight tasks only | `python3 -m proofbench.cli preflight --skip-lean` | available | Verifies default tasks can be loaded without requiring Lean. |
| Markdown sanity | `./.beryl/scripts/check-md.sh` | available | Unclosed fences and tabs. |
| Test manifest immutability check | `./.beryl/scripts/check-tests-unchanged.sh` | available | Detects unmanifested test changes. |
| Affected test gate | `./.beryl/scripts/check-affected.sh --worktree` | available | Falls back to full unit suite for broad Python/config changes. |
| Aggregate deterministic gate | `./.beryl/scripts/check.sh` | available | Runs all Beryl checks. |
| Format | `not available yet` | unavailable | No formatter configured yet. |
| Lint | `not available yet` | unavailable | No linter configured yet. |
| Typecheck | `not available yet` | unavailable | No type checker configured yet. |

## Default Loop

1. Identify or add the failing behavior.
2. Select the smallest useful test level.
3. State success checks before implementation: expected artifact, narrow command, broader command, generated output when applicable, and one user-visible behavior.
4. Implement one internal feature slice.
5. Run narrow checks first, then broader checks.
6. For execution workflow changes, run a smoke experiment that writes JSONL results.
7. Repair from actual tool output.

## ProofBench-Specific Verification

- Lean compiler success is the only objective solve signal.
- `static` verifier results are smoke checks and must not be presented as theorem-proving correctness.
- `auto` mode assigns no proof credit when Lean is unavailable.
- Result persistence is verified by confirming `ResultStore` wrote a `run_*.jsonl` file under the selected results directory.

## Affected Test Gate

Commit-time tests run through the affected test gate so developers get fast feedback without choosing test subsets manually.

- The pre-commit hook sets `CHECK_AFFECTED_MODE=staged` and runs `./.beryl/scripts/check.sh`.
- Manual `./.beryl/scripts/check.sh` uses worktree mode by default and selects from all changes relative to `HEAD`.
- Broad changes run `FULL_TEST_CMD`, configured as `python3 -m unittest discover -s tests -v`.

## Test Modification Rule

Existing tests may not be weakened to make implementation pass. Intentional test changes are allowed only when all conditions are met:

1. The behavior change is explicit in the task or design artifact.
2. `./.beryl/scripts/update-test-manifest.sh` is run after the intentional change.
3. The manifest update is committed with the test change.
4. The final response explains why tests changed.

## Mocking Rules

- Mock external systems such as model APIs, Lean availability, network, clocks, and filesystem roots when needed.
- Do not mock internal ProofBench selection normalization or result summarization when testing CLI behavior.
