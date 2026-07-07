# Benchmark Protocol

The default comparison is:

```bash
./scripts/run_full_comparison.sh
```

The script runs baseline plus ReAct on the default tasks and writes `results/dashboard.html`.
By default, `proofbench run` now requires a configured LLM provider and will not
silently fall back to smoke mode when credentials are missing. Use
`--advanced` with `mock`/`mock-react` for explicit smoke-only runs.

If you run `uv run proofbench run` manually, the rapid path asks only for
comma-separated agent names and the number of default tasks. Keep the same
model, verifier mode, and miniF2F source ref for every agent in a comparison.
Use `uv run proofbench run --advanced` only when those defaults need to change.

## Task Policy

ProofBench stores only theorem IDs. At run time it retrieves Lean statements from `lean/src/test.lean` and optional informal statements from `informal/test/<task_id>.json`. Informal proofs are not provided to agents.

## Correctness

Choose the Lean compiler verifier for real runs. A successful proof must compile and must not contain `sorry`, `admit`, or placeholder markers.

## Repetition

The benchmark has three tasks to reduce single-instance noise. For stronger claims, rerun with multiple model temperatures or add more miniF2F theorem IDs while preserving the same retrieval and logging protocol.

## Practical Session Pattern

For workshop sessions focused on agent behavior, run a single challenging theorem repeatedly across:

- baseline LLM-only proof generation,
- tool-using agent variants (for example, ReAct with compiler checks),
- the same model and verifier configuration.

The target should be a proof task that is **too hard for one-shot generation** and benefits from structured iteration. Compare improvements in:

- Lean acceptance rate,
- model calls and token usage,
- wall-clock timings split into modeling, verification, and end-to-end runtime.
