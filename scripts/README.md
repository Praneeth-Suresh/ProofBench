# ProofBench Scripts

This folder contains lightweight shell entrypoints used by the workshop:

- `preflight.sh` runs `proofbench preflight` with a default `.uv-cache` profile.
- `run_full_comparison.sh` runs the benchmark with baseline vs ReAct defaults.

`run_full_comparison.sh` is intentionally non-interactive: it feeds the rapid
run prompts with `llm_baseline,react` and the full default task count so
participants can quickly reproduce the comparison flow.

When Lean and miniF2F checker infrastructure is available (`PROOFBENCH_MINIF2F_LEAN_ROOT`
and `GEMINI_API_KEY`), it switches automatically to Lean-mode defaults.
