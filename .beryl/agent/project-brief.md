# Project Brief

## Product Goal

Build **ProofBench** for **agent-design workshop participants and maintainers** so they can **drop in theorem-proving agent designs, select agents and miniF2F tasks, run a fixed-model comparison, and immediately inspect persisted evaluation results**.

## Primary Workflows

1. **Run an experiment quickly**: choose registered agents and task ids/count from one command, run the configured LLM/verifier, and write JSONL results plus optional dashboard output.
2. **Compare results**: summarize stored runs across success rate, proof completion, efficiency, and speed without hand-editing result files.
3. **Add an agent design**: implement `run(task, model) -> AgentResult`, register the name, and evaluate it against the baseline on the same tasks/model.
4. **Verify proof progress**: use Lean compiler acceptance as the objective solve signal when Lean is configured; treat static checks only as smoke tests.

## Non-Goals

- Vendoring miniF2F benchmark statements or proofs into this repository.
- Letting agents bypass `proofbench/models/base.py` for provider-specific model access.
- Treating mock/static smoke results as final theorem-proving success or completion claims.
- Replacing human interpretation of research tradeoffs with a single score.

## External Systems

| System | Why it exists | Interface owner | Failure fallback |
| --- | --- | --- | --- |
| Gemini or configured LLM API | Provides model inference for all agents under comparison | `proofbench/models/` | Mock provider for smoke tests only |
| miniF2F GitHub/local checkout | Supplies theorem statements at run time | `proofbench/tasks/minif2f.py` | Cached/runtime fetch diagnostics; never vendor statements |
| Lean / miniF2F Lean root | Objective proof acceptance signal | `proofbench/evaluators/lean.py` | `auto` assigns no proof credit when Lean is unavailable; `static` is smoke-only |
| GitHub | PR review and CI for ProofBench changes | Repository workflow | Local deterministic checks remain required |

## Definition Of Done

A workflow or agent-platform feature is complete only when it has:

1. A small test proving the CLI/runtime behavior or a documented reason no new test is needed.
2. Passing `python3 -m unittest discover -s tests -v` and `./.beryl/scripts/check.sh`.
3. A smoke run that writes a result JSONL when the change touches experiment execution.
4. Updated README/docs for user-facing workflow changes.
5. No benchmark task content or secrets stored in prompts, traces, docs, or committed files.
