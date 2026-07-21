# Architecture

## Bounded Contexts

| Context | Owns | Does Not Own | Public Entry Point |
| --- | --- | --- | --- |
| CLI Workflow | Argument parsing, interactive prompts, run orchestration, summaries, dashboard commands | Agent internals, model SDKs, miniF2F parsing details | `proofbench/cli.py` |
| Agents | Agent strategies that transform a `ProofTask` plus `ChatModel` into `AgentResult` | Provider-specific model calls, result file writes, task fetching | `proofbench/agents/registry.py`, `proofbench/agents/base.py` |
| Models | Provider adapters implementing `ChatModel.generate` | Agent reasoning, verification, result persistence | `proofbench/models/base.py`, `proofbench/models/registry.py` |
| Tasks | Runtime retrieval and parsing of miniF2F theorem statements by id | Stored benchmark proofs/statements in the repo, agent design | `proofbench/tasks/registry.py`, `proofbench/tasks/minif2f.py` |
| Evaluation | Running agents against tasks, extracting Lean candidates, verifying, and computing metrics | CLI prompting, model provider internals, result storage format decisions beyond row content | `proofbench/evaluators/runner.py` |
| Results | JSONL persistence, loading, summaries, HTML dashboard rendering | Hand-edited result rows, proof verification | `proofbench/logging/result_store.py`, `proofbench/logging/dashboard.py` |
| Beryl Control Plane | Repository-owned agent context, deterministic checks, hooks, and driver files | ProofBench product logic | `.beryl/` |

The Agents context includes `moe_fused`: it selects only two existing registered experts, stores routing transparency in `AgentResult.trace`, and leaves all row persistence to Results.

## Boundary Rules

1. Keep model access behind `proofbench/models/base.py` and provider adapters.
2. Do not vendor miniF2F benchmark statements or proofs; store theorem ids and retrieve task content through `proofbench/tasks/minif2f.py`.
3. Treat Lean compiler success as the only objective solve signal; label static checks as smoke tests and do not average them into Lean-backed proof-completion metrics.
4. Log every comparison through `ResultStore`; do not hand-edit result JSONL files.
5. Preserve the baseline agent so new agents can be compared against it.
6. Keep reusable tool code under `proofbench/tools/` when agent strategies need tools.
7. Agent traces may be persisted, so prompts and traces must not include secrets, API keys, or unrelated local file contents.

## Public Interface Rule

- New agents implement `run(task, model) -> AgentResult` and are registered in `proofbench/agents/registry.py`.
- CLI changes should flow through selection dictionaries consumed by `_run` so interactive and non-interactive paths share execution.
- New model providers implement `ChatModel` and are created through `proofbench/models/registry.py`.
- New task sources expose `load_tasks(config, task_ids)`-compatible behavior through `proofbench/tasks/registry.py`.

## Forbidden Import Policy

- `proofbench/agents/**` must not import provider SDKs directly; use the `ChatModel` interface.
- `proofbench/logging/**` must not fetch tasks or call models.
- `proofbench/tasks/**` must not contain committed miniF2F statement/proof fixtures.

## Delivery Interfaces

- `proofbench run` is the primary experiment entry point.
- `proofbench run --agents ... --tasks ...` is the repeatable non-interactive path.
- `proofbench summarize <paths>` and `proofbench dashboard <paths>` are the result-management entry points.
- `.beryl/scripts/check.sh` is the repository deterministic gate.
