# ProofBench

**Design theorem-proving agents. Measure them fairly. Trust Lean, not a plausible-looking answer.**

ProofBench is a lightweight evaluation harness for comparing theorem-proving agent designs on miniF2F Lean tasks. It is built for workshops, experiments, and agent-design iteration: hold the model and task set constant, change one agent strategy, and see whether it actually improves the outcome.

> Lean compiler acceptance is the only objective proof-success signal. Mock and static runs validate wiring; they do not establish theorem-proving performance.

## Why ProofBench

An agent is more than one model call. Its behavior comes from the system around the model: context, tools, control flow, feedback, and a verifier. ProofBench gives each design the same task set, model configuration, and evaluation path so that comparisons remain meaningful.

Use it to answer questions such as:

- Does a repair loop improve over a one-shot baseline?
- Is broader search worth its extra model calls and latency?
- Which agent is most effective on a fixed task set and budget?
- Does a promising proof actually compile in Lean?

The harness fetches miniF2F tasks at runtime, records every comparison as JSONL, and can generate summaries, dashboards, and spreadsheet exports.

## What is included

| Component | Purpose |
| --- | --- |
| Agents | Compare a plain LLM baseline, ReAct repair, self-consistency, Tree/Graph of Thoughts, LATS, and a routed MoE-style agent. |
| Tasks | Retrieve miniF2F Lean theorems at runtime—benchmark statements and proofs are not vendored here. |
| Verifier | Use Lean as the objective proof checker; use static mode only for local smoke checks. |
| Results | Persist result rows as JSONL, then summarize, visualize, or export them without hand-editing data. |

## Get started

### 1. Install the project

```bash
git clone https://github.com/Praneeth-Suresh/ProofBench.git
cd ProofBench
uv sync
```

If you do not have `uv`, you can still use the standard-library CLI commands shown below with `python3 -m proofbench.cli`.

### 2. Run a no-cost smoke check

This confirms task retrieval, agent wiring, and result persistence without an API key or Lean installation:

```bash
uv run proofbench run \
  --agents llm_baseline \
  --task-count 1 \
  --model-provider mock \
  --verifier static \
  --results-dir workshop-smoke \
  --no-dashboard
```

Expect a zero solve rate in this mode. The `static` verifier is intentionally not a proof checker, so this run is successful when it completes and writes a JSONL result—not when it claims a theorem was proved.

To exercise the ReAct tool loop locally, substitute the agent and provider:

```bash
uv run proofbench run \
  --agents react \
  --task-count 1 \
  --model-provider mock-react \
  --verifier static \
  --results-dir react-smoke \
  --no-dashboard
```

### 3. Configure a real run

Set a supported model credential. ProofBench automatically loads a repository-root `.env` file as well.

```bash
export GEMINI_API_KEY="your-key"
# or
export GOOGLE_API_KEY="your-key"
```

For Lean-backed verification, configure a local miniF2F checkout and confirm the environment:

```bash
export PROOFBENCH_MINIF2F_LEAN_ROOT="/path/to/miniF2F"
uv run proofbench preflight
```

If you need a local task source too, set `PROOFBENCH_MINIF2F_LOCAL` to that checkout. Otherwise, ProofBench fetches and caches task content at runtime.

### 4. Compare a baseline with repair

Run the same model and task through both agents. This is the smallest useful experiment:

```bash
uv run proofbench run \
  --agents llm_baseline,react \
  --task-count 1 \
  --model-provider gemini \
  --verifier lean \
  --results-dir baseline-vs-react
```

Then inspect the stored results:

```bash
uv run proofbench summarize baseline-vs-react
uv run proofbench dashboard baseline-vs-react \
  --output baseline-vs-react/dashboard.html
```

## Experiment recipes

### Establish a control condition

Start with the plain LLM agent. This gives every later design change a fair point of comparison.

```bash
uv run proofbench run \
  --agents llm_baseline \
  --tasks aime_1988_p8 \
  --model-provider gemini \
  --verifier lean \
  --results-dir baseline
```

### Compare bounded search

Search agents trade additional calls for additional candidate proofs. Keep their budgets explicit and modest at first:

```bash
uv run proofbench run \
  --agents llm_baseline,self_consistency,tree_of_thoughts,graph_of_thoughts,lats \
  --task-count 1 \
  --model-provider gemini \
  --verifier lean \
  --search-samples 3 \
  --search-width 2 \
  --search-depth 2 \
  --lats-rollouts 4 \
  --results-dir search-sweep
```

### Try expert routing

`moe_fused` selects exactly two registered experts. Give it a results directory containing earlier Lean-backed rows if you want its router to calibrate from prior comparisons.

```bash
uv run proofbench run \
  --agents moe_fused \
  --tasks aime_1988_p8 \
  --model-provider gemini \
  --verifier lean \
  --results-dir results/lean-evaluation
```

### Run without `uv`

```bash
python3 -m proofbench.cli run \
  --agents llm_baseline \
  --task-count 1 \
  --model-provider mock \
  --verifier static \
  --results-dir smoke \
  --no-dashboard
```

## Read the results

Every agent/task comparison is appended through `proofbench/logging/result_store.py`; do not hand-edit result files. A run directory contains timestamped JSONL rows and, unless disabled, dashboard and export artifacts.

Focus on the tradeoff—not just the headline score:

| Signal | Question it answers |
| --- | --- |
| `solved` / `success_score` | Did Lean accept a complete proof? |
| `proof_completion` / `verified_prefix_ratio` | How much verifier-grounded progress was made before failure? |
| `efficiency` | How many model, token, and tool resources did the approach use? |
| `speed` | What latency and runtime did it add? |
| `metric_validity` | Did the metric come from Lean, a smoke mode, or an unavailable verifier? |

Useful result commands:

```bash
uv run proofbench summarize results
uv run proofbench dashboard results --output results/dashboard.html
uv run proofbench export results --output results/proofbench-results.xlsx
```

Proof completion can be helpful diagnostic evidence, but it is not a solved theorem. Only Lean acceptance earns proof credit.

## Choose an agent pattern

| Agent | Best first use |
| --- | --- |
| `llm_baseline` | Establish the fixed-model control condition. |
| `react` | Test whether compiler feedback and repair improve a one-shot proof. |
| `self_consistency` | Compare independent attempts and candidate selection. |
| `tree_of_thoughts` | Explore a bounded branching proof search. |
| `graph_of_thoughts` | Generate, revise, and synthesize candidate proof states. |
| `lats` | Use bounded MCTS-style search with verifier feedback. |
| `moe_fused` | Route a task to two existing agent experts. |

More complex search is not automatically better. A design earns its complexity only when it improves solve rate or useful Lean-grounded progress enough to justify its cost.

## Build your own agent

Make one deliberate change, then compare it against the baseline on identical conditions:

1. Add a module under `proofbench/agents/`.
2. Implement `run(task, model)` and return `AgentResult`.
3. Register its name in `proofbench/agents/registry.py`.
4. Run the baseline and your agent on the same task ids, model, verifier, and search budget.
5. Compare success, completion, efficiency, and speed from persisted results.

For a safe first design, change a single lever: repair count, candidate-selection rule, verifier feedback, sampling policy, or routing rule. Avoid changing the model, task set, and agent strategy all at once—then the result will not tell you what helped.

Smoke-check a newly registered agent before spending model budget:

```bash
python3 -m proofbench.cli run \
  --agents llm_baseline,my_agent \
  --task-count 1 \
  --model-provider mock \
  --verifier static \
  --no-dashboard
```

## Practical guardrails

- Keep the model and task set fixed for every comparison.
- Treat static and mock modes as pipeline checks, never as performance claims.
- Use Lean verification before claiming a proof was solved.
- Keep API keys and unrelated local content out of prompts and persisted traces.
- Keep result files immutable; rebuild summaries and dashboards from their JSONL rows.
- Increase search budgets only after a small Lean-backed run shows why they might help.

## Next steps

Run `uv run proofbench run` for a short interactive flow, or inspect the [main README](README.md) for the complete CLI reference, Lean setup details, and result-management commands. Start small, measure one change at a time, and let the verifier decide what counts.
