from __future__ import annotations

import time
from typing import Any

from proofbench.agents.base import Agent, AgentResult
from proofbench.agents.router import AgentRouter
from proofbench.agents.search_common import SearchStats, build_agent_result, check_candidate, generate_traced, select_best_candidate
from proofbench.models.base import ChatModel
from proofbench.tasks.base import ProofTask
from proofbench.tools.lean_check import LeanCheckTool


class GLaMTopTwoFusedAgent:
    """Runs the router's two experts and produces one verifier-ranked proof result."""

    name = "moe_fused"

    def __init__(self, *, router: AgentRouter, experts: dict[str, Agent], check_tool: LeanCheckTool, include_informal: bool = True):
        self.router = router
        self.experts = experts
        self.check_tool = check_tool
        self.include_informal = include_informal

    def run(self, task: ProofTask, model: ChatModel) -> AgentResult:
        start = time.perf_counter()
        trace: list[dict[str, Any]] = []
        stats = SearchStats()
        decision = self.router.route(task)
        trace.append(decision.trace_event())
        candidates = []
        for index, expert_name in enumerate(decision.experts, start=1):
            expert_result = self.experts[expert_name].run(task, model)
            _add_agent_result_stats(stats, expert_result)
            trace.append({"type": "expert_result", "expert": expert_name, "rank": index, "weight": decision.weights[index - 1], "model_calls": expert_result.model_calls, "tool_calls": expert_result.tool_calls, "elapsed_s": expert_result.elapsed_s})
            candidates.append(check_candidate(task=task, check_tool=self.check_tool, raw_answer=expert_result.raw_answer, label=f"expert_{index}_{expert_name}", stats=stats, trace=trace, metadata={"phase": "expert_selection", "expert": expert_name}))
        if not any(candidate.passed for candidate in candidates):
            response = generate_traced(model, _fusion_prompt(task, candidates, include_informal=self.include_informal), stats=stats, trace=trace, trace_type="model", metadata={"phase": "fusion", "experts": list(decision.experts)})
            candidates.append(check_candidate(task=task, check_tool=self.check_tool, raw_answer=response.text, label="fused_candidate", stats=stats, trace=trace, metadata={"phase": "fusion", "experts": list(decision.experts)}))
        best = select_best_candidate(candidates)
        trace.append({"type": "selection", "strategy": "verifier_first_fused_top_2", "candidate_count": len(candidates), "selected": best.label if best else None, "selected_passed": best.passed if best else False, "selected_score": best.score if best else None})
        return build_agent_result(agent_name=self.name, task=task, best=best, trace=trace, stats=stats, start=start)


def _add_agent_result_stats(stats: SearchStats, result: AgentResult) -> None:
    stats.model_calls += result.model_calls
    stats.input_tokens += result.input_tokens
    stats.output_tokens += result.output_tokens
    stats.tool_calls += result.tool_calls
    stats.model_latency_s += result.model_latency_s


def _fusion_prompt(task: ProofTask, candidates: list[Any], *, include_informal: bool) -> str:
    expert_attempts = "\n\n".join("\n".join((f"Expert: {candidate.metadata['expert']}", f"Verifier diagnostics: {candidate.verification.diagnostics[-1200:]}", "Candidate proof:", candidate.raw_answer)) for candidate in candidates)
    return ("You are a Lean 3 proof-fusion agent. Produce one complete Lean proof by repairing or combining the two expert attempts below. Return only Lean code. Do not use sorry, admit, or placeholders. Prefer a verified fragment when it is compatible with the theorem.\n\n" f"{task.prompt_statement(include_informal=include_informal)}\n\n" f"Expert attempts:\n{expert_attempts}")
