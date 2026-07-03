# Agent Instructions for ProofBench

ProofBench exists to support the workshop's agent-design track. Agents should improve theorem-proving accuracy, efficiency, or speed over the plain LLM baseline while using the same model and task set.

## Core Rules

- Do not vendor miniF2F benchmark statements or proofs into this repository. Store theorem IDs and retrieve task content at test time through `proofbench/tasks/minif2f.py`.
- Treat Lean compiler success as the only objective accuracy signal. Static checks are smoke tests only.
- Keep model access behind `proofbench/models/base.py` so agents remain provider-independent.
- Log every comparison through `proofbench/logging/result_store.py`; do not hand-edit result files.
- Preserve the baseline agent so new workshop agents can be compared against it.

## Building a New Agent

1. Add a module under `proofbench/agents/`.
2. Implement `run(task, model)` and return `AgentResult`.
3. Register the agent name in `proofbench/agents/registry.py`.
4. If the agent uses tools, put reusable tool code under `proofbench/tools/`.
5. Run:

```bash
uv run proofbench run
```

Then enter comma-separated agent names and the number of default tasks to run. Use `uv run proofbench run --advanced` only when you need to override model, verifier, task source, or dashboard settings.

## Evaluation Expectations

Report all three axes:

- Accuracy: Lean compiler acceptance rate.
- Efficiency: model calls, tokens, tool calls.
- Speed: agent runtime, model latency, verification time.

Agent traces may be stored in JSONL results, so avoid writing secrets, API keys, or unrelated local file contents into prompts or traces.
