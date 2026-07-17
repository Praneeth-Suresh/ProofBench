# Building Agents

Agents live under `proofbench/agents/` and are ordinary Python modules. Participants can directly edit Python during the workshop.

## Required Interface

An agent class needs a stable `name` and a `run(task, model)` method:

```python
name = "my_agent"

def run(self, task, model):
    ...
    return AgentResult(...)
```

The `task` is a `ProofTask` with `task_id`, `formal_statement`, optional `informal_statement`, and miniF2F source metadata. The `model` implements `generate(prompt)` and returns text plus token and latency metadata.

Keep provider-specific SDKs out of agents. Agents should call only the `ChatModel` interface they receive.

## Output Shape

The final answer may be either:

- a full Lean theorem, or
- a Lean proof body such as `begin ... end`.

The evaluator wraps proof bodies with the retrieved theorem header before checking them.

## Result Metadata

Return `AgentResult` with enough metadata for all three comparison axes:

- Success: generated Lean candidate checked by the configured verifier.
- Proof progress: diagnostics from the configured verifier, including proof completion and repairability.
- Efficiency: `model_calls`, token counts, and `tool_calls`.
- Speed: agent runtime and model/tool latency.
- Trace: high-signal reasoning/tool events, without secrets or unrelated local files.

## Tool Use

The starter ReAct agent uses `LeanCheckTool`, which calls the configured verifier and returns diagnostics. New agents can add retrieval, decomposition, repair, voting, routing, or consensus modules as long as all tool calls are counted in `AgentResult`.

Reusable tools belong under `proofbench/tools/`.

## Registration

Add the agent to `proofbench/agents/registry.py`:

1. Import the class.
2. Add the public name to `REGISTERED_AGENT_NAMES`.
3. Add a branch in `create_agents(...)` that constructs it.

Then verify the name appears in the run prompt or use it directly in a command.

## Fast Smoke Test

Run a no-API, no-Lean smoke test first. This proves registration, task retrieval, result writing, and summarization work:

```bash
uv run proofbench run \
  --agents llm_baseline,my_agent \
  --task-count 1 \
  --model-provider mock \
  --verifier static \
  --results-dir my-agent-smoke \
  --no-dashboard
```

If `uv` is unavailable:

```bash
python3 -m proofbench.cli run --agents llm_baseline,my_agent --task-count 1 --model-provider mock --verifier static --results-dir my-agent-smoke --no-dashboard
```

Static verifier output is only a smoke check. It is not proof correctness.

## Real Comparison Run

For claims, keep the model, verifier, and task set fixed across all agents:

```bash
uv run proofbench run \
  --agents llm_baseline,my_agent \
  --tasks aime_1988_p8 \
  --model-provider gemini \
  --verifier lean
```

If you prefer prompts:

```bash
uv run proofbench run
```

Then enter comma-separated agent names and the number of default tasks to run. Use `uv run proofbench run --advanced` only when you need to override model, verifier, source, or dashboard settings interactively.

## Managing Results

Results are stored as JSONL through `ResultStore` under `results/run_<timestamp>[_slug]/`.

Summarize and rebuild dashboards from stored rows:

```bash
uv run proofbench summarize results
uv run proofbench dashboard results --output results/dashboard.html
```

Do not hand-edit result files. If a run was misconfigured, run a new experiment with a clear `--results-dir` slug.

## Checklist for a New Agent PR

- [ ] Agent module added under `proofbench/agents/`.
- [ ] Agent registered in `proofbench/agents/registry.py`.
- [ ] Reusable tools placed under `proofbench/tools/` if needed.
- [ ] Smoke run writes a JSONL result file.
- [ ] Real run uses the same model/task/verifier setup as the baseline.
- [ ] README or docs updated if the user workflow changed.
- [ ] `python3 -m unittest discover -s tests -v` passes.
- [ ] `./.beryl/scripts/check.sh` passes.
