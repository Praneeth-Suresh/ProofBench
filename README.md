# ProofBench

ProofBench compares theorem-proving agents on the same miniF2F Lean problems. Start with a one-shot baseline and a repair loop, then compare Lean acceptance, model calls, tokens, and latency on the resulting JSONL.

| If you want to… | Start here |
| --- | --- |
| Check your installation without a model or Lean | Run the [mock/static smoke test](#fastest-experiment-command). It checks wiring, not proof correctness. |
| Compare two agents with the Lean compiler | Follow the [one-task, pinned miniF2F example](#lean-verified-runs). |
| Understand the metrics or run a workshop | See the [benchmark protocol](docs/benchmark_protocol.md) and [workshop handout](HANDOUT.md). |

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

Run the baseline against the search-agent suite:

```bash
uv run proofbench run \
  --agents llm_baseline,self_consistency,tree_of_thoughts,graph_of_thoughts,lats \
  --task-count 1 \
  --search-samples 3 \
  --search-width 2 \
  --search-depth 2 \
  --lats-rollouts 4
```

Run the complete workshop technique sweep on one task with local smoke settings:

```bash
uv run proofbench run \
  --agents llm_baseline,react,self_consistency,tree_of_thoughts,graph_of_thoughts,lats,moe_fused \
  --task-count 1 \
  --model-provider mock \
  --verifier static \
  --results-dir workshop-smoke \
  --no-dashboard
```

Static/mock output proves task retrieval, agent wiring, and result persistence;
it is not evidence of theorem-proving correctness. Repeat the sweep with the
same task set, a real model, and `--verifier lean` before drawing success-rate
or efficiency conclusions.

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

Run the GLaM-inspired top-2 agent MoE without re-running comparison agents already stored in a results directory:

```bash
uv run proofbench run \
  --agents moe_fused \
  --tasks aime_1988_p8 \
  --results-dir results/lean-evaluation \
  --model-provider gemini \
  --verifier lean \
  --dashboard results/lean-evaluation/dashboard.html
```

`moe_fused` reads prior Lean-backed rows from its selected results directory to calibrate its deterministic top-2 router. It still runs exactly two registered experts for each new task.

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
| `--search-samples N` | Self-Consistency independent proof attempts. |
| `--search-width N` | Branching width for Tree of Thoughts, Graph of Thoughts, and LATS. |
| `--search-depth N` | Search depth for Tree of Thoughts and LATS. |
| `--lats-rollouts N` | Monte Carlo Tree Search rollout count for LATS. |
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
- `uv run proofbench export results --output results/proofbench-results.xlsx`  
  Export persisted JSONL rows to an Excel workbook with `Summary` and `Rows` sheets.
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
uv run proofbench export results --output results/proofbench-results.xlsx
```

Every row includes:

- `metric_validity`: whether proof metrics came from real Lean, static smoke, mock smoke, or an unavailable verifier.
- `solved` and `success_score`: proof-assistant acceptance and its numeric solve score.
- `proof_completion`, `verified_prefix_ratio`, `repairability_score`, `failure_profile`: verifier-grounded proof diagnostics.
- `efficiency`: model calls, token counts, and tool calls.
- `speed`: total runtime, model latency, and verification time.
- `raw_answer` and `trace`: agent output and trace metadata.

Traces may contain prompts and model output, so never include secrets or unrelated local file contents in agent prompts.

Runs also write `proofbench-results.xlsx` next to the dashboard when dashboard output is enabled. The HTML dashboard includes downloads for Excel, CSV, and JSON, but the JSONL files remain the source of truth.

## Built-In Search Agents

Registered agents:

| Agent | Design | How ProofBench adapts it |
| --- | --- | --- |
| `llm_baseline` | One-shot LLM proof generation | Plain fixed-model baseline for every comparison. |
| `react` | ReAct-style repair loop | Alternates model proof attempts with Lean-check feedback. |
| `self_consistency` | Self-Consistency | Samples independent proof attempts, verifies each, then selects the verified or most consistent/highest-quality candidate. |
| `tree_of_thoughts` | Tree of Thoughts | Explores a bounded beam of proof thoughts and keeps the strongest Lean-checked states. |
| `graph_of_thoughts` | Graph of Thoughts | Generates proof vertices, improves failed candidates, and aggregates strong attempts through graph edges. |
| `lats` | Language Agent Tree Search | Runs a bounded MCTS-style proof search with Lean diagnostics as environment feedback and reflection for failed candidates. |
| `moe_fused` | GLaM-style top-2 agent MoE | Routes to exactly two existing agents with normalized weights, then verifier-selects or repairs their proof candidates. |

Search budgets intentionally default small so workshop runs stay affordable. Increase them only when the model/verifier setup is ready for a real comparison.

## Lean-Verified Runs

This one-task example runs `llm_baseline` and `react` on the same theorem from a
[pinned miniF2F revision](https://github.com/facebookresearch/miniF2F/tree/e4f113090ad82d64f8ce064d2f55b613a9b6bded). It is an example configuration, not a published benchmark result. Use it to check your setup before running a larger comparison.

You need Gemini credentials and a Lean 3 toolchain managed by [elan](https://github.com/leanprover/elan). The pinned miniF2F [package file](https://github.com/facebookresearch/miniF2F/blob/e4f113090ad82d64f8ce064d2f55b613a9b6bded/leanpkg.toml) specifies Lean 3.42.1 and a mathlib commit. Follow [miniF2F's Lean setup instructions](https://github.com/facebookresearch/miniF2F/blob/e4f113090ad82d64f8ce064d2f55b613a9b6bded/README.md#structure) if your checkout cannot build, and use the Lean 3 binary from that toolchain (not Lean 4).

From the ProofBench checkout, after `uv sync` and configuring the credentials shown above:

```bash
export PROOFBENCH_MINIF2F_REF=e4f113090ad82d64f8ce064d2f55b613a9b6bded
git clone https://github.com/facebookresearch/miniF2F.git ../miniF2F-proofbench
git -C ../miniF2F-proofbench checkout --detach "$PROOFBENCH_MINIF2F_REF"
export PROOFBENCH_MINIF2F_LOCAL="$(cd ../miniF2F-proofbench && pwd)"
export PROOFBENCH_MINIF2F_LEAN_ROOT="$PROOFBENCH_MINIF2F_LOCAL"
(
  cd "$PROOFBENCH_MINIF2F_LOCAL" &&
  leanpkg configure &&
  leanpkg build
)
export PROOFBENCH_LEAN_EXE="$(cd "$PROOFBENCH_MINIF2F_LOCAL" && elan which lean)"
```

Then run from ProofBench. Set `PROOFBENCH_MODEL` to a Gemini model ID available to your account, and keep it the same for both agents:

```bash
: "${PROOFBENCH_MODEL:?Set PROOFBENCH_MODEL to your Gemini model ID}"
uv run proofbench preflight --minif2f-ref "$PROOFBENCH_MINIF2F_REF" algebra_9onxpypzleqsum2onxpy
uv run proofbench run \
  --agents llm_baseline,react \
  --tasks algebra_9onxpypzleqsum2onxpy \
  --minif2f-ref "$PROOFBENCH_MINIF2F_REF" \
  --model-provider gemini \
  --model-name "$PROOFBENCH_MODEL" \
  --verifier lean \
  --results-dir results/lean-example \
  --no-dashboard
uv run proofbench summarize results/lean-example
```

Inspect the two agent/task rows in the generated JSONL. Check that `metric_validity` is `lean` before comparing `solved`; a Lean-verified attempt can fail to solve the theorem. A no-credentials run of this same pair with `--model-provider mock --verifier static` writes two `mock_smoke` rows with zero proof-metric coverage. Do not include those rows in a proof-solvability comparison. Save the upstream revision, exact model ID, Lean version, and experiment options alongside the run.

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
3. Compare success rate, proof completion diagnostics, model calls/tokens/tool calls, and runtime/verification time.
4. Repeat with more tasks once a pattern is clear.

For the full technique exercise, use the sweep command above and then inspect
the result summary or run a paired Lean-only gate for the MoE candidate:

```bash
uv run proofbench summarize workshop-results
uv run proofbench compare workshop-results --baseline llm_baseline --candidate moe_fused
```

The paired comparison ignores static/mock rows and only reports matching
Lean-verified task/model/verifier rows.

This keeps the evaluation focused on agent behavior rather than on changing prompt style or model size.
