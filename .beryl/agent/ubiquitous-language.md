# Ubiquitous Language

| Business Term | Technical Symbol | Definition | Constraints | Avoid |
| --- | --- | --- | --- | --- |
| ProofBench | `proofbench` | Evaluation harness for comparing theorem-proving agents on runtime-fetched miniF2F tasks. | Keeps model/task/verifier seams explicit. | Treating it as one monolithic script |
| Agent Design | `Agent` | A theorem-proving strategy that receives a `ProofTask` and `ChatModel` and returns `AgentResult`. | Must be registered before running by name. | Provider-specific agent that imports SDKs directly |
| Baseline Agent | `llm_baseline` | Plain one-shot LLM proof attempt preserved for comparison. | Must remain available. | Replacing baseline with an experimental design |
| Task ID | `task_id` | miniF2F theorem identifier used to retrieve task content at run time. | Store ids, not theorem statements/proofs. | Vendored benchmark fixture |
| Default Task Set | `DEFAULT_TASK_IDS` | Small reproducible workshop task set. | Used by rapid runs and `--task-count`. | Hidden random sample |
| Experiment Run | `proofbench run` | Execution of selected agents against selected tasks with one model/verifier configuration. | Writes rows through `ResultStore`. | Manual result editing |
| Run Selection | `selections` | Normalized dictionary describing agents, tasks, model, verifier, source, results, and dashboard settings. | Shared by prompt and flag-based workflows. | Divergent prompt-only config |
| Result Row | `row` | One persisted comparison for an agent/task pair including accuracy, efficiency, speed, raw answer, and trace. | JSONL through `ResultStore.append`. | Spreadsheet-only record |
| Accuracy | `accuracy` | Lean compiler acceptance rate when Lean verifier is available. | Static checks are smoke-only and must be labeled. | Treating static success as proof correctness |
| Efficiency | `efficiency` | Model calls, token counts, and tool calls consumed by an agent. | Report beside accuracy. | Accuracy-only ranking |
| Speed | `speed` | Runtime, model latency, and verification time. | Report beside accuracy and efficiency. | Ignoring slow tool loops |
| Verifier | `ProofVerifier` | Component that assigns proof verification outcome. | `lean` is objective; `auto` gives no credit when unavailable; `static` is smoke. | Silent fallback to smoke correctness |
| Result Store | `ResultStore` | JSONL persistence abstraction for benchmark rows. | Only writer for comparison results. | Hand-edited result file |
| Dashboard | `write_dashboard` | Lightweight HTML view over result JSONL rows. | Generated from stored rows. | Source of truth for results |
| Beryl Control Plane | `.beryl/` | Repository-owned persistent agent memory, checks, hooks, and driver context. | Must stay project-specific after install. | Hidden chat memory |
