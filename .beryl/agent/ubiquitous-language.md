# Ubiquitous Language

| Business Term | Technical Symbol | Definition | Constraints | Avoid |
| --- | --- | --- | --- | --- |
| Agent Router | `AgentRouter` | GLaM-inspired sparse gate that ranks existing agent experts for one task and returns exactly two distinct expert names with normalized weights. | Uses static task features with calibrated Lean-row history; never selects models or wider top-k sets. | A model router or arbitrary expert fan-out |
| Fused Agent | `moe_fused` | Agent that runs the router-selected two experts, verifier-ranks their candidates, and synthesizes one repair only when both are incomplete. | Keeps the `AgentResult` contract and stores transparency data in trace. | A separate result writer or a third selected expert |
| ProofBench | `proofbench` | Evaluation harness for comparing theorem-proving agents on runtime-fetched miniF2F tasks. | Keeps model/task/verifier seams explicit. | Treating it as one monolithic script |
| Agent Design | `Agent` | A theorem-proving strategy that receives a `ProofTask` and `ChatModel` and returns `AgentResult`. | Must be registered before running by name. | Provider-specific agent that imports SDKs directly |
| Baseline Agent | `llm_baseline` | Plain one-shot LLM proof attempt preserved for comparison. | Must remain available. | Replacing baseline with an experimental design |
| Task ID | `task_id` | miniF2F theorem identifier used to retrieve task content at run time. | Store ids, not theorem statements/proofs. | Vendored benchmark fixture |
| Default Task Set | `DEFAULT_TASK_IDS` | Small reproducible workshop task set. | Used by rapid runs and `--task-count`. | Hidden random sample |
| Experiment Run | `proofbench run` | Execution of selected agents against selected tasks with one model/verifier configuration. | Writes rows through `ResultStore`. | Manual result editing |
| Run Selection | `selections` | Normalized dictionary describing agents, tasks, model, verifier, source, results, and dashboard settings. | Shared by prompt and flag-based workflows. | Divergent prompt-only config |
| Result Row | `row` | One persisted comparison for an agent/task pair including solve status, proof-completion diagnostics, efficiency, speed, raw answer, and trace. | JSONL through `ResultStore.append`. | Spreadsheet-only record |
| Success Rate | `success_rate` | Percentage of attempted tasks accepted by the configured verifier. | Lean-backed rows are objective; static/mock rows are smoke-only and labeled through `metric_validity`. | Vague proof accuracy |
| Proof Completion | `proof_completion` | Lean-backed estimate of formal proof work completed before failure. | Averaged only over rows with `metric_validity == "lean"`. | Treating static or mock output as proof progress |
| Metric Validity | `metric_validity` | Row label describing whether proof metrics are Lean-backed, static smoke, mock smoke, or unavailable. | Dashboards and summaries use it to avoid misleading proof-completion averages. | Silent fallback to smoke correctness |
| Efficiency | `efficiency` | Model calls, token counts, and tool calls consumed by an agent. | Report beside success and completion. | Success-only ranking |
| Speed | `speed` | Runtime, model latency, and verification time. | Report beside success, completion, and efficiency. | Ignoring slow tool loops |
| Verifier | `ProofVerifier` | Component that assigns proof verification outcome. | `lean` is objective; `auto` gives no credit when unavailable; `static` is smoke. | Silent fallback to smoke correctness |
| Result Store | `ResultStore` | JSONL persistence abstraction for benchmark rows. | Only writer for comparison results. | Hand-edited result file |
| Dashboard | `write_dashboard` | Lightweight HTML view over result JSONL rows. | Generated from stored rows. | Source of truth for results |
| Search Agent | `self_consistency`, `tree_of_thoughts`, `graph_of_thoughts`, `lats` | Agent design that spends extra inference/verifier calls exploring multiple proof candidates. | Must remain registered as explicit comparable agents. | Hidden mode inside the baseline |
| Proof Candidate | `ProofSearchCandidate` | A generated Lean attempt plus verifier result and search score. | Selected by verifier pass first, then completion, repairability, and consistency. | Treating model preference as objective success |
| Thought Graph | `GraphOfThoughtsLeanAgent` trace graph | Vertices are proof attempts or refinements; edges are transformations such as improve or aggregate. | Stored as trace metadata only. | Separate result persistence path |
| Excel Export | `write_excel` | Spreadsheet view generated from persisted JSONL rows. | JSONL remains the source of truth. | Hand-edited benchmark record |
| Beryl Control Plane | `.beryl/` | Repository-owned persistent agent memory, checks, hooks, and driver context. | Must stay project-specific after install. | Hidden chat memory |
