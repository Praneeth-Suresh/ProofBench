# ProofBench

ProofBench is a small evaluation harness for comparing theorem-proving agent designs on runtime-fetched miniF2F Lean tasks. The intended workflow is simple:

1. Pick which registered agents to run.
2. Pick which miniF2F task ids, or how many default tasks, to use.
3. Run the same configured model and verifier for every selected agent/task pair.
4. Let ProofBench write JSONL results and optional dashboard output.
5. Compare accuracy, efficiency, and speed.

ProofBench is designed for workshop iteration: keep the model and task set fixed, change the agent design, and measure whether the agent improves over the plain LLM baseline.

## Quick Setup

```bash
cd /path/to/ProofBench
uv sync
```

If `uv` is unavailable in a constrained agent environment, the unit tests can still be run with `python3 -m unittest discover -s tests -v`.

For real model calls, set one of:

```bash
export GEMINI_API_KEY="your-key"
# or
export GOOGLE_API_KEY="your-key"
```

ProofBench loads `.env` from the repository root automatically, so local environment variable files do not need to be sourced manually.

## Fastest Experiment Command

Run the baseline and ReAct agents on the first default task and write results without prompts:

```bash
uv run proofbench run \
  --agents llm_baseline,react \
  --task-count 1
```

Run specific miniF2F theorem ids:

```bash
uv run proofbench run \
  --agents llm_baseline,my_agent \
  --tasks aime_1988_p8,algebra_9onxpypzleqsum2onxpy
```

Use a local smoke test with no API key and no Lean dependency:

```bash
uv run proofbench run \
  --agents llm_baseline \
  --task-count 1 \
  --model-provider mock \
  --verifier static \
  --results-dir smoke \
  --no-dashboard
```

Equivalent fallback if `uv` is not available:

```bash
python3 -m proofbench.cli run --agents llm_baseline --task-count 1 --model-provider mock --verifier static --results-dir smoke --no-dashboard
```

## Interactive Runs

For the simplest guided flow:

```bash
uv run proofbench run
```

Answer two prompts:

```text
Agents to run, comma-separated [llm_baseline,react]: llm_baseline,react
Number of default tasks to run (1-3) [3]: 3
```

Use the advanced prompt only when you need custom model, verifier, task source, Lean root, or results settings:

```bash
uv run proofbench run --advanced
```

## Run Options

Common non-interactive flags:

| Flag | Meaning |
| --- | --- |
| `--agents llm_baseline,react` | Comma-separated registered agents. |
| `--tasks id1,id2` | Exact miniF2F task ids, or `all` for defaults. |
| `--task-count N` | First N default task ids. Mutually exclusive with `--tasks`. |
| `--model-provider gemini|mock|mock-react` | LLM provider adapter. |
| `--model-name NAME` | Provider-specific model override. |
| `--verifier auto|lean|static` | Proof checker mode. Lean is the objective signal; static is smoke-only. |
| `--lean-root PATH` | miniF2F Lean checkout root for Lean verification. |
| `--minif2f-local PATH` | Local miniF2F checkout for task retrieval. |
| `--results-dir NAME_OR_PATH` | Results directory or run slug under `results/`. |
| `--max-iters N` | ReAct repair/tool iterations. |
| `--formal-only` | Exclude informal statement from agent prompts. |
| `--no-dashboard` | Skip dashboard generation. |

## Core Runtime Commands

- `uv run proofbench preflight [--skip-lean]`  
  Verify that default tasks are retrievable and Lean checks are available.
- `uv run proofbench list-tasks`  
  Print the default miniF2F task ids.
- `uv run proofbench run`  
  Rapid two-question interactive flow.
- `uv run proofbench run --agents ... --tasks/--task-count ...`  
  Repeatable non-interactive experiment flow.
- `uv run proofbench run --advanced`  
  Full prompt flow for custom model/verifier/source/dashboard settings.
- `uv run proofbench summarize results`  
  Print a compact summary from result files.
- `uv run proofbench dashboard results --output results/dashboard.html`  
  Build or rebuild the HTML dashboard.
- `./scripts/preflight.sh`  
  Convenience wrapper for preflight using `.uv-cache`.
- `./scripts/run_full_comparison.sh`  
  Runs baseline + ReAct on the three default tasks and writes to a timestamped results dir.
- `./scripts/clean_runs.sh [paths...]`  
  Remove previous benchmark run artifacts after confirmation.

## Results Management

Each agent/task comparison is appended through `proofbench/logging/result_store.py` to a timestamped JSONL file:

```text
results/run_<timestamp>[_slug]/run_<timestamp>.jsonl
```

Do not hand-edit result files. Rebuild views from stored rows instead:

```bash
uv run proofbench summarize results
uv run proofbench dashboard results --output results/dashboard.html
```

Every row includes:

- `accuracy`: proof acceptance score from the configured verifier.
- `proof_quality_score`, `proof_progress`, `failure_profile`: richer proof diagnostics.
- `efficiency`: model calls, token counts, and tool calls.
- `speed`: total runtime, model latency, and verification time.
- `raw_answer` and `trace`: agent output and trace metadata.

Traces may contain prompts and model output, so never include secrets or unrelated local file contents in agent prompts.

## Lean-Verified Runs

Lean compiler success is the only objective accuracy signal. Static checks are smoke tests only.

By default, no local miniF2F checkout is required for task retrieval; tasks are downloaded and cached from GitHub. For Lean verification, configure:

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

After Lean is working, this should pass without `--skip-lean`:

```bash
uv run proofbench preflight
```

## Default Tasks

Default miniF2F test ids:

- `algebra_9onxpypzleqsum2onxpy`
- `aime_1988_p8`
- `numbertheory_exk2powkeqapb2mulbpa2_aeq1`

Use them to keep comparisons reproducible across sessions.

## Adding a New Agent Design

ProofBench expects agent modules under `proofbench/agents/`.

1. Add a module in `proofbench/agents/`.
2. Implement a class with `run(task, model) -> AgentResult`.
3. Return `AgentResult` with generated Lean text and execution metadata.
4. Register the agent name in `proofbench/agents/registry.py`.
5. If the agent uses reusable tools, put them under `proofbench/tools/`.
6. Smoke-test the agent:

```bash
uv run proofbench run \
  --agents llm_baseline,my_agent \
  --task-count 1 \
  --model-provider mock \
  --verifier static \
  --results-dir my-agent-smoke \
  --no-dashboard
```

7. Run a real comparison with the same model/task/verifier configuration for every agent:

```bash
uv run proofbench run \
  --agents llm_baseline,my_agent \
  --tasks aime_1988_p8 \
  --model-provider gemini \
  --verifier lean
```

For more detail, see `docs/building_agents.md`.

## Beryl Agent Control Plane

This repository includes Beryl under `.beryl/` for persistent agent context, deterministic checks, generated tool shims, and driver workflows.

Important files:

- `.beryl/agent/project-brief.md`
- `.beryl/agent/design-tree.md`
- `.beryl/agent/architecture.md`
- `.beryl/agent/ubiquitous-language.md`
- `.beryl/agent/testing-policy.md`
- `.beryl/scripts/check.sh`
- `.beryl/driver/run.sh`

Run the Beryl gate before finishing changes:

```bash
./.beryl/scripts/check.sh
```

## Practical Workshop Track

For the workshop exercise, keep the model fixed and compare designs on the same difficult task family:

1. Pick one of the default ids, or another custom task, that is too hard to solve in one shot.
2. Run baseline plus at least one tool-using agent on that same task.
3. Compare accuracy, model calls/tokens/tool calls, and runtime/verification time.
4. Repeat with more tasks once a pattern is clear.

This keeps the evaluation focused on agent behavior rather than on changing prompt style or model size.
