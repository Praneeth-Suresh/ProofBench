# ProofBench Workshop Guide

This workshop is a hands-on introduction to theorem-proving agents. You will
run several existing agent designs on the same miniF2F tasks, inspect how they
behave, and then build your own agent. The goal is not only to obtain a high
score; it is to understand which design choices produce useful proof progress
and which choices add cost without improving Lean success.

## Learning goals

By the end of the workshop, you should be able to:

- distinguish a one-shot model call from an agent that acts in a feedback loop;
- explain why Lean compiler feedback changes agent behavior;
- compare success, proof completion, efficiency, and speed;
- identify when search produces useful diversity and when it only produces more
  failed candidates;
- design, register, and evaluate one new theorem-proving agent.

## Before you start

From the repository root, install the project and configure a real model and
Lean checkout. A real workshop comparison must use the same model, task set,
miniF2F revision, and Lean verifier for every agent.

```bash
uv sync
export GEMINI_API_KEY="your-key"
export PROOFBENCH_MINIF2F_LEAN_ROOT="/path/to/miniF2F/lean"
```

The default tasks are:

- `algebra_9onxpypzleqsum2onxpy`
- `aime_1988_p8`
- `numbertheory_exk2powkeqapb2mulbpa2_aeq1`

If you do not have a model or Lean checkout yet, use the smoke command below
to learn the workflow. Static/mock results verify wiring and persistence only;
they are not evidence that a theorem was proved.

## Activity 1: establish the baseline

Run the plain one-shot baseline on one task:

```bash
uv run proofbench run \
  --agents llm_baseline \
  --task-count 1 \
  --model-provider gemini \
  --verifier lean \
  --results-dir workshop-results
```

Before looking at the output, predict:

1. How many model calls will the baseline make?
2. What kinds of errors can a one-shot agent discover before it stops?
3. If Lean rejects the proof, what information does the model receive about
   the failure?

Now inspect the summary:

```bash
uv run proofbench summarize workshop-results
```

Record the baseline's `success_rate`, `proof_completion`, token count, and
runtime. Keep this row as the control condition for the rest of the workshop.

## Activity 2: add compiler feedback with ReAct

Run the same task with ReAct:

```bash
uv run proofbench run \
  --agents react \
  --task-count 1 \
  --max-iters 3 \
  --model-provider gemini \
  --verifier lean \
  --results-dir workshop-results
```

Guiding questions:

1. Does ReAct improve actual Lean success, or only proof completion?
2. Which compiler errors are easy for the model to repair?
3. Which errors require a new mathematical idea rather than a local edit?
4. Is the extra model and verifier cost justified by the improvement?
5. What happens if the final response is empty or uses the wrong output
   format?

The important design idea is that ReAct maintains one proof trajectory. It can
use Lean's diagnostics to repair the current candidate instead of starting
from an unrelated proof every time.

## Activity 3: compare search patterns

Run the search-agent suite on the same task. Use a separate results directory
if you want a clean comparison, or use the same directory if you want one
dashboard containing all rows.

```bash
uv run proofbench run \
  --agents self_consistency,tree_of_thoughts,graph_of_thoughts,lats \
  --task-count 1 \
  --search-samples 3 \
  --search-width 2 \
  --search-depth 2 \
  --lats-rollouts 4 \
  --model-provider gemini \
  --verifier lean \
  --results-dir workshop-results
```

Before running, make a prediction for each design:

| Design | Prediction question |
| --- | --- |
| Self-Consistency | Will independent attempts be diverse enough to contain a correct proof? |
| Tree of Thoughts | Does branching preserve and improve a verified proof state, or mostly regenerate full proofs? |
| Graph of Thoughts | Can two failed proof attempts be safely aggregated? |
| LATS | Is its search reward based on Lean evidence or on model self-evaluation? |

After the run, compare:

- accepted proofs, not just completion scores;
- compiler failure classes;
- model calls and tool calls;
- token and runtime cost;
- whether a larger search budget produced a better final candidate.

Discuss this question: if an agent generates five failed proofs, has it made
more progress than an agent that generates one failed proof with a useful
compiler diagnostic?

## Activity 4: inspect routing and fusion

Run the MoE design:

```bash
uv run proofbench run \
  --agents moe_fused \
  --task-count 1 \
  --model-provider gemini \
  --verifier lean \
  --results-dir workshop-results
```

Inspect the dashboard or the stored trace. Ask:

1. Which two experts did the router select?
2. Did the experts produce compatible proof fragments?
3. Did fusion improve success, or only increase calls and tokens?
4. Would it be better to pass intermediate proof states between experts than
   to fuse their final answers?

## Activity 5: build your own 100%-success agent

Your challenge is to add exactly one new registered agent and try to achieve a
100% Lean success rate on the default tasks.

Start by reading:

- `proofbench/agents/base.py` for the public result contract;
- `proofbench/agents/search_common.py` for candidate checking and selection;
- `proofbench/agents/react_agent.py` for compiler-guided repair;
- `proofbench/agents/registry.py` for registration;
- `proofbench/agents/README.md` for the analysis of the observed outcomes.

Create a module under `proofbench/agents/`, implement:

```python
run(task, model) -> AgentResult
```

Then register the agent and test it first with a deterministic mock model. For
real claims, run it with exactly the same model, task IDs, and Lean verifier as
the comparison agents:

```bash
uv run proofbench run \
  --agents your_agent \
  --tasks all \
  --model-provider gemini \
  --verifier lean \
  --lean-root "$PROOFBENCH_MINIF2F_LEAN_ROOT" \
  --max-iters 8 \
  --results-dir workshop-results
```

Use the following improvement loop five times:

1. Run the agent on all three tasks.
2. Record the first Lean error for every failed proof.
3. Change one design choice only: for example, candidate diversity, proof
   state preservation, error-specific repair, or tactic/lemma retrieval.
4. Rerun only your new agent in a new iteration directory.
5. Keep the best version based on Lean acceptance first, then completion and
   efficiency.

Questions to answer after every iteration:

- Did the agent find a new proof strategy or merely rewrite the same failure?
- Did the verified prefix become longer because the proof improved, or because
  the first error moved later in the file?
- Did repairs preserve valid code from the previous candidate?
- Did the model invent theorem names, use unavailable imports, or emit
  placeholders?
- Is the bottleneck search, mathematical insight, Lean syntax, or result
  selection?

Do not treat `proof_completion == 1` as success unless `solved == true` and the
Lean verifier accepted the proof. Do not hand-edit JSONL results, and do not
vendor miniF2F theorem statements or proofs into the repository.

## If you get stuck

If the behavior is confusing, consult
[`proofbench/agents/README.md`](../proofbench/agents/README.md). It contains
the workshop answer key: why ReAct tends to outperform the search agents, why
independent sampling can fail repeatedly, why fusion does not automatically
compose proofs, and why the Ultimatum agent still failed to reach 100%.

In particular, remember that a compiler diagnostic tells an agent what is
wrong with the current Lean program, but it does not necessarily provide the
missing mathematical idea. A successful workshop design must bridge both
problems: discover a valid proof strategy and express it in the exact Lean
environment available to the verifier.

## Final reflection

Write a short report answering:

1. Which agent had the best Lean success rate, and how many tasks did it solve?
2. Which agent had the best proof completion, and why is that not equivalent
   to correctness?
3. Which design spent the most resources, and did that cost buy success?
4. What was the most common failure class?
5. Why did your final agent succeed or fail to reach 100%?
6. What would you try next: better theorem retrieval, structured proof-state
   editing, task-specific planning, or a different search policy?

If your agent does not reach 100%, that is a useful result when the failure is
explained with Lean evidence and a clear account of the design tradeoffs.
