# Benchmark Protocol

The default comparison is:

```bash
./scripts/run_full_comparison.sh
```

The script runs baseline plus ReAct on the default tasks and writes `results/dashboard.html`.
The script chooses a Lean/Gemini run when the required environment is available;
otherwise it runs an explicit mock/static smoke comparison. The rapid interactive
`proofbench run` path itself requires Gemini credentials. Non-interactive runs
with omitted provider/verifier flags also select Gemini when credentials exist and
otherwise use `mock` plus `static`; pass `--model-provider` and `--verifier`
explicitly when the distinction matters.

If you run `uv run proofbench run` manually, the rapid path asks only for
comma-separated agent names and the number of default tasks. Keep the same
model, verifier mode, and miniF2F source ref for every agent in a comparison.
Use `uv run proofbench run --advanced` only when those defaults need to change.

## Workshop Technique Sweep

To exercise every registered design on one task with no API key or Lean checkout,
run the explicit smoke sweep:

```bash
uv run proofbench run \
  --agents llm_baseline,react,self_consistency,tree_of_thoughts,graph_of_thoughts,lats,moe_fused \
  --task-count 1 \
  --model-provider mock \
  --verifier static \
  --results-dir workshop-smoke \
  --no-dashboard
```

This validates wiring and persistence only. For workshop claims, use the same
agent list, task ids, model, and `--verifier lean` configuration, then compare
the persisted rows. `moe_fused` routes to exactly two registered experts and may
use prior Lean-backed rows in its results directory for calibration.

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
