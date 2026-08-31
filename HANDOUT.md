# Architecting Agentic Systems Workshop Handout

This handout is a practical companion to the workshop deck in `Architecting Agentic Systems.pdf`. It is designed to help participants move from the ideas on the slides into actual experiments in this codebase, using the same mental model: an agent is not just a model, but a system with context, state, tools, control flow, and a verifier.

The goal is simple:

- understand how agentic patterns differ from a single LLM call,
- compare those patterns on the same tasks and same model,
- learn to read evaluation signals instead of trusting raw output,
- and iterate on agent design with real evidence.

This repo is the laboratory. The slides are the theory. This guide is the map.

---

## 1) What this workshop is really about

The slides frame modern AI as a systems problem, not just a model problem.

At a high level, the workshop asks:

- What makes an agent useful?
- What makes an agent reliable?
- Why do search, repair, and verification matter?
- How do we compare agent designs fairly?
- When does extra complexity improve outcomes and when does it create cost without value?

A useful mental model is:

+------------------------------+
| Model / policy               |
| LLM decides next action      |
+---------------+--------------+
                |
                v
+------------------------------+
| Context + State + Memory     |
| prompt history, tool results, |
| partial proof state          |
+---------------+--------------+
                |
                v
+------------------------------+
| Tools + Environment          |
| Lean verifier, browser, code |
| executor, retrieval         |
+---------------+--------------+
                |
                v
+------------------------------+
| Control loop                 |
| plan -> act -> observe -> re-|
| act / search / repair       |
+---------------+--------------+
                |
                v
+------------------------------+
| Verifier / objective signal  |
| Lean success, not vibes      |
+------------------------------+

In this repo, the verifier is Lean: the agent is judged by whether it can produce a proof that the Lean compiler accepts.

That is the workshop’s key principle: no “looks convincing” claims. The environment decides.

---

## 2) Why the repo matters

This project is a benchmark harness for theorem-proving agents. It has four essential ingredients:

1. Agents
   - baseline one-shot model
   - ReAct repair loop
   - search agents like self-consistency, Tree of Thoughts, Graph of Thoughts, and LATS
   - a fused MoE-style router

2. Tasks
   - miniF2F Lean theorems fetched at runtime
   - no benchmark statements are vendored into the repo

3. Verifier
   - `lean` is the real success signal
   - `static` is only smoke test mode

4. Results
   - JSONL artifacts for comparison
   - summaries, dashboards, and exports

This is exactly what the deck asks us to do: evaluate agents systematically, not by intuition.

---

## 3) Workshop storyline: from basics to system design

The deck moves through a few big ideas. The repo lets you try them hands-on.

### A. Agent basics

A good agent is not just a single prompt. It includes:

- a policy (the model),
- context and memory,
- state, tools, and an action loop,
- an environment to interact with,
- and a verifier or evaluator.

This repo gives you a concrete version of that:

- the model generates a Lean proof,
- the Lean compiler checks it,
- errors are fed back into the loop,
- the agent chooses its next move.

That is the same pattern shown in the slides: agentic systems cycle through observation, decision, and action.

### B. Search as a design choice

The workshop deck highlights multiple search patterns:

- Self-Consistency: run a few independent proof attempts and pick the best
- Tree of Thoughts: branch through candidate reasoning steps
- Graph of Thoughts: reason over a graph of dependencies and revisions
- LATS / Language Agent Tree Search: combine search with environment feedback

The repo implements these as real agents:

- `llm_baseline`
- `react`
- `self_consistency`
- `tree_of_thoughts`
- `graph_of_thoughts`
- `lats`
- `moe_fused`

These are not just names — they embody a design spectrum:

- no search
- repair loop
- independent sampling
- branching search
- graph-based synthesis
- hybrid routing

### C. Evaluation matters more than intuition

The slides highlight the same challenge as the repo: an agent’s score is not the full story.

You need to ask:

- Did the model solve the theorem?
- Did it make progress even when it failed?
- Did the strategy spend more tokens or take longer for marginal gains?
- Did the environment actually verify the solution?

This repo records these signals in result rows such as:

- `solved`
- `success_score`
- `proof_completion`
- `verified_prefix_ratio`
- `efficiency`
- `speed`

That is exactly how a workshop should behave: compare under equal conditions, not cherry-picked conditions.

### D. Governance, safety, and authority

Even though this repo is about theorem proving, the slides remind us that architecture matters. A system’s behavior should be constrained by policy and verification.

In this repo, “authority” is the environment:

- the model may propose a proof,
- the verifier decides whether that proof is valid,
- the agent can only improve if the system gives it correct feedback.

That makes the environment and the verifier a safety boundary. The agent is not the final authority on correctness.

---

## 4) Your workshop plan

Use this sequence to get the most value with minimal friction.

### Route A: beginner flow (best for first-time participants)

1. Install dependencies and verify the repo works
2. Run a smoke test with a mock model
3. Run the baseline on one task
4. Run a ReAct repair loop
5. Inspect the metrics and compare the results
6. Try one more search-style agent
7. Reflect on which strategy improved the right metric

### Route B: advanced flow (for experienced workshop participants)

1. Run a baseline and a strong search agent on the same small task set
2. Compare solve rate, proof completion, and efficiency
3. Test whether the extra search budget improves performance materially
4. Try routing or fusion (`moe_fused`)
5. Add a custom agent with one design change
6. Evaluate under matched conditions and report the tradeoff

### Route C: challenge flow (for teams)

1. Pick one design choice to change only once: search width, repair depth, expert routing, or verifier feedback
2. Run the same tasks with and without that change
3. Measure: success, completion, cost, and latency
4. Write a 1-page design note explaining the outcome

---

## 5) Quick start

### 5.1 Setup

From the repo root:

```bash
cd /path/to/ProofBench
uv sync
```

If `uv` is unavailable, the repo still supports a fallback path:

```bash
python3 -m proofbench.cli run --agents llm_baseline --task-count 1 --model-provider mock --verifier static --results-dir smoke --no-dashboard
```

For real model calls, you need a key:

```bash
export GEMINI_API_KEY="your-key"
# or
export GOOGLE_API_KEY="your-key"
```

ProofBench also loads `.env` automatically from the repo root.

### 5.2 Smoke test (safest first step)

This checks that the wiring works without needing a real model or Lean environment:

```bash
uv run proofbench run \
  --agents llm_baseline \
  --task-count 1 \
  --model-provider mock \
  --verifier static \
  --results-dir workshop-smoke \
  --no-dashboard
```

This is not proof correctness, but it is a good sanity check.

### 5.3 Real run with Lean verification

Once the repo works, use a real verifier and a small task set:

```bash
uv run proofbench run \
  --agents llm_baseline,react \
  --task-count 1 \
  --model-provider gemini \
  --verifier lean \
  --results-dir workshop-01
```

If you have a local miniF2F Lean checkout, point the project at it:

```bash
export PROOFBENCH_MINIF2F_LEAN_ROOT="/path/to/miniF2F"
```

Then validate setup:

```bash
uv run proofbench preflight
```

---

## 6) The exercises participants should actually do

### Exercise 1: establish the baseline

Goal: understand the default condition.

Run:

```bash
uv run proofbench run \
  --agents llm_baseline \
  --task-count 1 \
  --model-provider gemini \
  --verifier lean \
  --results-dir baseline-run
```

Ask these questions:

- Did the proof solve the task?
- Did the model produce a valid proof or a near miss?
- What was the run cost in tokens and time?

This is your control condition.

### Exercise 2: add repair and feedback

Goal: compare a one-shot baseline to a repair loop.

Run:

```bash
uv run proofbench run \
  --agents llm_baseline,react \
  --task-count 1 \
  --model-provider gemini \
  --verifier lean \
  --results-dir react-vs-baseline
```

Questions:

- Did the repair loop fix the errors that the baseline missed?
- Did it increase solve rate, completion, or just time and token cost?
- Was the verifier actually helpful as feedback?

### Exercise 3: compare search patterns

Goal: feel the difference between a single trajectory and multi-agent search.

Run:

```bash
uv run proofbench run \
  --agents llm_baseline,self_consistency,tree_of_thoughts,graph_of_thoughts,lats \
  --task-count 1 \
  --search-samples 3 \
  --search-width 2 \
  --search-depth 2 \
  --lats-rollouts 4 \
  --model-provider gemini \
  --verifier lean \
  --results-dir search-sweep
```

Discuss:

- Which method offered the best signal-to-cost ratio?
- Did the strongest method just add breadth or did it improve decision quality?
- Was there a case where more search obviously increased cost without solving more tasks?

### Exercise 4: test routing and fusion

Goal: learn what happens when we combine multiple specialists.

Run:

```bash
uv run proofbench run \
  --agents moe_fused \
  --tasks aime_1988_p8 \
  --results-dir moe-demo \
  --model-provider gemini \
  --verifier lean \
  --dashboard moe-demo/dashboard.html
```

The `moe_fused` agent reads prior results and routes to the top two experts.

Ask:

- Does the route selection help?
- Does it help enough to justify its complexity?
- Is the “fusion” effect real or just additional overhead?

---

## 7) How to read the results

After each run, generate structured summaries:

```bash
uv run proofbench summarize results
uv run proofbench dashboard results --output results/dashboard.html
uv run proofbench export results --output results/proofbench-results.xlsx
```

The key metrics to focus on are:

- `solved`: was the theorem actually accepted by Lean?
- `success_score`: a numeric solver metric
- `proof_completion`: how much of the proof was valid before failure
- `efficiency`: token counts, model calls, and steps
- `speed`: runtime and latency

Important: proof completion is not the same as success.

A model can generate a promising partial proof that is close to correct but still fails. That is useful information, but it is not the same thing as a solved theorem.

This is a subtle but critical workshop lesson.

---

## 8) A short guide to choosing the right pattern

The slides suggest a design taxonomy. In this repo, use it like this:

- If you need a clean baseline: `llm_baseline`
- If you want a cheap feedback loop: `react`
- If you want independent attempts with a voting signal: `self_consistency`
- If you want deliberate branching and state tracking: `tree_of_thoughts`
- If you want dependency-aware synthesis: `graph_of_thoughts`
- If you want MCTS-style structured search: `lats`
- If you want routing among experts: `moe_fused`

Matching the technique to the problem is the point.

A good rule of thumb:

- simple problems: baseline or cheap repair
- harder problems: search and repair
- broad or mixed task spaces: routing and fusion

But do not assume more complexity equals better performance. Measure it.

---

## 9) Safety and architecture mindset from the slides

The slides on governance and authority are not just “extra slides.” They are a reminder that agentic systems need boundaries.

In workshop terms:

- the model is not the final judge,
- the environment is a constrained authority,
- the verifier is the trust anchor,
- and the system should be designed to prevent unsafe or unbounded behavior.

In ProofBench, the equivalent of the safety boundary is Lean verification and the task environment. The agent is allowed to try many ideas, but the system enforces what counts as valid progress.

That is a perfect bridge from the slides to the lab: a strong agent design is not just creative; it is constrained, observable, and evaluable.

---

## 10) Making your own agent

This is where participants move from running other agents to inventing one.

The base pattern is straightforward:

1. Create a Python module under `proofbench/agents/`
2. Implement `run(task, model)` or follow the existing agent contract
3. Register it in `proofbench/agents/registry.py`
4. Run it on the same task set as the baseline
5. Compare under identical conditions

The quick way to start is to copy a small idea from an existing agent and change one variable:

- more repair attempts,
- a different sampling policy,
- a different selection heuristic,
- a new verifier feedback strategy,
- a different routing rule.

Do not rewrite the entire architecture at once. Change one lever. Compare. Repeat.

---

## 11) Suggested workshop agenda

### 30 minutes: orientation and setup

- explain the deck’s architectural framing
- verify the repo works
- run smoke test

### 30 minutes: baseline + repair

- run baseline
- run ReAct
- compare solve rate and efficiency

### 45 minutes: search strategies

- run self-consistency and ToT
- inspect tradeoffs between exploration and cost

### 30 minutes: fusion and evaluation

- run MoE-style routing
- discuss metrics and design decisions

### 20 minutes: reflection

- ask which design improved the right objective
- identify what would be tried next

---

## 12) What advanced users should do

If you want more than a first pass, here are good next steps:

- compare models under the same task set,
- vary search width/depth and record the cost curve,
- use `--results-dir` to keep runs readable and comparable,
- inspect the persisted JSONL rows rather than trusting a single dashboard summary,
- try a custom agent that changes one design decision only,
- report not just solve rate but the cost of each improved success.

The best workshop insight is not “this agent wins once.” It is:

> “This agent wins on these task types under these constraints because it improves the right failure mode without exploding cost.”

---

## 13) Recommended first commands to run

Use these as a safe, canonical sequence:

```bash
# 1. Setup
uv sync

# 2. Smoke test
uv run proofbench run \
  --agents llm_baseline \
  --task-count 1 \
  --model-provider mock \
  --verifier static \
  --results-dir smoke \
  --no-dashboard

# 3. Baseline with real model (small run)
uv run proofbench run \
  --agents llm_baseline \
  --task-count 1 \
  --model-provider gemini \
  --verifier lean \
  --results-dir baseline

# 4. Feedback loop
uv run proofbench run \
  --agents llm_baseline,react \
  --task-count 1 \
  --model-provider gemini \
  --verifier lean \
  --results-dir react-demo

# 5. Search comparison
uv run proofbench run \
  --agents llm_baseline,self_consistency,tree_of_thoughts,graph_of_thoughts,lats \
  --task-count 1 \
  --search-samples 3 \
  --search-width 2 \
  --search-depth 2 \
  --lats-rollouts 4 \
  --model-provider gemini \
  --verifier lean \
  --results-dir search-demo
```

Then summarize and inspect:

```bash
uv run proofbench summarize search-demo
uv run proofbench dashboard search-demo --output search-demo/dashboard.html
```

---

## 14) Final takeaway

The workshop deck and this codebase are aligned around the same idea:

- modern systems are not just models,
- agent design is a systems design problem,
- evaluation is the mechanism that turns intuition into evidence,
- and verifiers are the boundary that separates plausible output from valid action.

ProofBench gives participants a way to test that idea concretely: pick an agent, run it on the same theorem tasks, compare it under the same model and verifier, and decide whether the added complexity actually buys you better performance.

If you want to get the most from the workshop, do not start by asking which agent is best in general. Start by asking:

- What problem are we solving?
- What is the right verification signal?
- What is the real cost of the search strategy?
- What does the evidence say after controlled comparison?

That is the spirit of the deck and the repo.

---

## 15) One-sentence workshop summary

In one sentence: use this repo to turn the architecting-agentic-systems slides into a concrete experiment where you build, compare, and critique agent designs using a real objective signal.
