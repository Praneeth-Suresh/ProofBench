# Design Tree

## Current Design Concept

ProofBench is a thin, provider-independent evaluation harness: task retrieval, model inference, agent execution, proof verification, result persistence, and summary/dashboard reporting are separate seams. The user-facing path should be one simple command for the common case, while advanced options remain available without changing the underlying comparison contract.

## Open Decisions

| Decision | Options | Current Lean | Why |
| --- | --- | --- | --- |
| Experiment selection UX | Interactive prompts only, CLI flags only, both | Both | Workshop users benefit from prompts; automation and repeatable experiments need flags. |
| Default no-credential behavior | Fail fast, use mock smoke mode, ask user | Use mock/static only when non-interactive flags are supplied without credentials | Keeps `proofbench run` honest for real experiments while enabling local smoke checks. |
| Agent registration | Manual registry edit, plugin discovery, entry points | Manual registry edit | Simple and explicit for workshop scale; revisit when agent count grows. |

## Settled Decisions

| Decision | Choice | Date | ADR |
| --- | --- | --- | --- |
| Benchmark task storage | Store theorem ids only and retrieve miniF2F content at test/run time. | 2026-07-07 | N/A |
| Objective solve signal | Lean compiler acceptance is the only objective solve signal; proof-completion diagnostics are secondary and Lean-backed only. | 2026-07-07 | N/A |
| Result persistence | Every comparison row goes through `proofbench/logging/result_store.py` JSONL writes. | 2026-07-07 | N/A |
| Model boundary | Agents receive `ChatModel` from `proofbench/models/base.py`; provider SDK details stay behind adapters. | 2026-07-07 | N/A |
| Simple run workflow | `proofbench run` keeps the rapid prompt; `proofbench run --agents ... --tasks/--task-count ...` runs non-interactively. | 2026-07-07 | N/A |
| Search-agent comparison | Self-Consistency, Tree of Thoughts, Graph of Thoughts, and LATS are separate registered agents with bounded search budgets. | 2026-07-10 | N/A |
| Spreadsheet retrieval | JSONL remains source of truth; Excel workbooks are generated views from stored rows. | 2026-07-10 | N/A |

## Pressure Points

- The simplest command must not hide whether results came from real Lean verification, `auto` no-credit fallback, or static smoke checks.
- Result files may contain agent traces; prompts must avoid secrets and unrelated local file contents.
- CLI defaults should support both workshop demos and reproducible automation without forcing users through advanced prompts.
- `uv` may be unavailable in some agent environments; `python3 -m unittest discover -s tests -v` remains the deterministic fallback check.
- Search-agent budgets can multiply model and verifier calls quickly, so defaults should stay conservative and explicit.

## Recording Rule

Update this file when a workflow-level decision changes how users run experiments, add agents, verify proofs, or interpret results. Create an ADR only when a lasting boundary or persistence contract changes.
