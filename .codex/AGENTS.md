# Agent Operating Instructions

This tool-specific instruction file is a generated shim. Do not edit this copy manually. Update `.beryl/agent/tool-instruction-template.md` and rerun `.beryl/agent/scripts/sync-agent-env.sh`.

You are working in ProofBench as an implementation agent. Treat repository files as the source of truth. Do not rely on hidden chat history, memory, or assumptions when a repo-owned instruction file answers the question.

## Instruction Precedence

1. Follow explicit user instructions for the current task.
2. Follow canonical files under `.beryl/agent/`.
3. Follow this tool-specific shim.
4. Follow existing code, tests, and local conventions.

If this shim conflicts with canonical files under `.beryl/agent/`, treat this shim as stale, follow `.beryl/agent/`, and mention the conflict in your final response.

## Required Context Before Editing

Before changing code or tests, read `.beryl/agent/task-routing.md`, classify the current task, and load only the matching workflow from `.beryl/agent/skills/<skill-name>/SKILL.md`.

Then read the smallest relevant set of canonical files requested by that workflow:

- `.beryl/agent/project-brief.md`
- `.beryl/agent/design-tree.md`
- `.beryl/agent/architecture.md`
- `.beryl/agent/ubiquitous-language.md`
- `.beryl/agent/testing-policy.md`
- `.beryl/agent/agent-rules.md`

Load additional files only when they are relevant to the task. Keep context focused.

## ProofBench Core Rules

- ProofBench supports the workshop agent-design track. Agents should improve theorem-proving success rate, Lean-backed proof completion, efficiency, or speed over the plain LLM baseline while using the same model and task set.
- Do not vendor miniF2F benchmark statements or proofs into this repository. Store theorem IDs and retrieve task content at test time through `proofbench/tasks/minif2f.py`.
- Treat Lean compiler success as the only objective solve signal. Static checks are smoke tests only.
- Keep model access behind `proofbench/models/base.py` so agents remain provider-independent.
- Log every comparison through `proofbench/logging/result_store.py`; do not hand-edit result files.
- Preserve the baseline agent so new workshop agents can be compared against it.
- Agent traces may be stored in JSONL results, so avoid writing secrets, API keys, or unrelated local file contents into prompts or traces.

## Skill Use

Skills live under `.beryl/agent/skills/<skill-name>/SKILL.md`. Use a skill when its name or purpose matches the task.

Task workflows:

- Use `planning` for plans, designs, approaches, and feature planning gates.
- Use `adding-features` for feature implementation after a user-ratified plan.
- Use `debugging` for bugs, failures, regressions, exceptions, and failing checks.
- Use `explaining-codebase` for codebase walkthroughs and explanations without edits.

Supporting skill triggers:

- Use `grill-me` before non-trivial features, architecture changes, cross-context changes, or ambiguous bug fixes.
- Use `testing-vertical-slices` for feature work and bug fixes that need behavior verification.
- Use `improving-architecture` when a change exposes shallow modules, unclear ownership, repeated coupling, or hard-to-test structure.
- Use `tracking-entropy` when asked to assess maintainability, hotspots, churn, complexity, or refactoring priority.

Do not use sub-agents unless the user explicitly asks for sub-agents, parallel agents, reviewer agents, or competing agent implementations.

## Building a New Agent

1. Add a module under `proofbench/agents/`.
2. Implement `run(task, model)` and return `AgentResult`.
3. Register the agent name in `proofbench/agents/registry.py`.
4. If the agent uses tools, put reusable tool code under `proofbench/tools/`.
5. Run `python3 -m proofbench.cli run --agents llm_baseline,<agent_name> --task-count 1 --model-provider mock --verifier static` as a smoke check, then run the real model/verifier configuration for claims.

## Default Work Loop

For every implementation task:

1. Restate the requested behavior and identify the bounded context.
2. Identify the intended public interface and likely files to change.
3. Add or identify the smallest test or deterministic check that proves the behavior.
4. Implement one internal feature slice at a time.
5. Run the narrowest relevant check first, then broader checks.
6. Repair based on actual tool output, not guesswork.
7. Update `.beryl/agent/ubiquitous-language.md`, `.beryl/agent/design-tree.md`, `.beryl/agent/architecture.md`, or `.beryl/agent/adr/` if the change alters domain language, boundaries, or durable design decisions.

## Verification

Run checks required by `.beryl/agent/testing-policy.md` and the local toolchain. If a required check cannot run, explain why and state the risk.

Your final response must include:

- What changed.
- Which checks ran.
- Which checks were skipped or unavailable.
- Any design files, glossary entries, or ADRs updated.
