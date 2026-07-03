# ProofBench

ProofBench is the workshop benchmark for comparing a baseline LLM proof attempt against
agent-based alternatives on Lean theorems from miniF2F.

Use this repository as:
- a fixed-model comparison harness
- a fast smoke-testing setup for local iteration
- a Lean-verified workflow when toolchain and API credentials are available

## Quick Setup

```bash
cd /home/prane/vibing/ResearchGroup/ProofBench
uv sync
```

If you want real model calls, set:

```bash
export GEMINI_API_KEY="your-key"
```

Without `GEMINI_API_KEY`, runs use the local mock model in smoke mode.

## Core Runtime Commands

- `uv run proofbench preflight [--skip-lean]`  
  Verify that default tasks are retrievable and Lean checks are available.
- `uv run proofbench run`  
  Quick flow (default: rapid profile, registered agents prompt, number of default tasks).
- `uv run proofbench run --advanced`  
  Full prompt flow for custom model/verifier/source/dashboards.
- `./scripts/preflight.sh`  
  Convenience wrapper for preflight using `.uv-cache`.
- `./scripts/run_full_comparison.sh`  
  Runs baseline + ReAct on the three default tasks and writes to a timestamped results dir.
- `uv run proofbench summarize results`  
  Print a compact summary from result files.
- `uv run proofbench dashboard results --output results/dashboard.html`  
  Build or rebuild the HTML dashboard.
- `./scripts/clean_runs.sh [paths...]`  
  Remove previous benchmark run artifacts (`run_*.jsonl`, `dashboard*.html`, `*.log`) after confirmation.

## Lean-Verified Runs (optional but recommended for final claims)

By default, no local miniF2F checkout is required; tasks are downloaded and cached from GitHub.

For Lean verification, configure:

```bash
export PROOFBENCH_MINIF2F_LOCAL="/path/to/miniF2F"
export PROOFBENCH_MINIF2F_LEAN_ROOT="/path/to/miniF2F"
```

Then ensure Lean tooling is usable for miniF2F:

```bash
cd /path/to/miniF2F
leanpkg configure
leanproject get-mathlib-cache
leanproject build
```

If `leanpkg` is unavailable, install mathlib tools and elan tooling first, then retry:

```bash
uv tool install mathlibtools
curl https://elan.lean-lang.org/elan-init.sh -sSf | sh
```

After Lean is working, `uv run proofbench preflight` should pass without `--skip-lean`.

## Default Tasks

Default miniF2F test IDs:

- `algebra_9onxpypzleqsum2onxpy`
- `aime_1988_p8`
- `numbertheory_exk2powkeqapb2mulbpa2_aeq1`

Use them to keep comparisons reproducible across sessions.

## Clear prior benchmark outputs

Run this command when you want to reset previous run data before starting a fresh experiment:

```bash
./scripts/clean_runs.sh
```

To clear specific directories:

```bash
./scripts/clean_runs.sh results y --dry-run
```

By default the script clears `$PROOFBENCH_RESULTS_DIR` when set, otherwise `./results`, and `./y`.
It will list all matching files and requires you to type `yes` before removing anything.

## Working with Agents

ProofBench expects agent modules under `proofbench/agents/`.

1. Add a module in `proofbench/agents/` with a class exposing:
   - `name` (string)
   - `run(task, model) -> AgentResult`
2. Return `AgentResult` with generated Lean text and execution metadata.
3. Register the agent name in `proofbench/agents/registry.py`.
4. Run benchmark commands with the same tasks/model configuration for all agents.

For example, run a two-agent comparison:

```bash
uv run proofbench run
```

Then enter:

```text
llm_baseline,react
3
```

Use `--advanced` when you need custom task IDs or non-default model/verifier settings.

## Practical Workshop Track

For the workshop exercise, keep the model fixed and compare designs on the same difficult task family:

1. Pick one of the default IDs (or another custom task) that is too hard to solve in one shot.
2. Run baseline + at least one tool-using agent on that same task.
3. Compare:
   - Lean acceptance rate
   - model calls and tokens
   - tool calls
   - end-to-end timing and verifier latency
4. Repeat with more tasks once a pattern is clear.

This keeps the evaluation focused on agent behavior (reasoning loops, repair, consensus/verification integration)
rather than on changing prompt style or model size.
