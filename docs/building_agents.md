# Building Agents

Agents live under `proofbench/agents/` and are ordinary Python modules. Participants can directly edit Python during the workshop.

## Required Interface

An agent class needs:

```python
name = "my_agent"

def run(self, task, model):
    ...
    return AgentResult(...)
```

The `task` is a `ProofTask` with `task_id`, `formal_statement`, optional `informal_statement`, and miniF2F source metadata. The `model` implements `generate(prompt)` and returns text plus token and latency metadata.

## Output Shape

The final answer may be either:

- a full Lean theorem, or
- a Lean proof body such as `begin ... end`.

The evaluator wraps proof bodies with the retrieved theorem header before checking them.

## Tool Use

The starter ReAct agent uses `LeanCheckTool`, which calls the configured verifier and returns diagnostics. New agents can add retrieval, decomposition, repair, voting, routing, or consensus modules as long as all tool calls are counted in `AgentResult`.

## Registration

Add the agent to `proofbench/agents/registry.py`, then run:

```bash
uv run proofbench run
```

Then enter the agents to compare as comma-separated names, for example `llm_baseline,my_agent`, and choose how many default tasks to run. Use `uv run proofbench run --advanced` only when you need to override model, verifier, source, or dashboard settings.
