from __future__ import annotations

import time
from typing import Any

from proofbench.agents.base import AgentResult
from proofbench.agents.search_common import (
    SearchStats,
    build_agent_result,
    check_candidate,
    generate_traced,
    select_best_candidate,
    theorem_prompt,
)
from proofbench.models.base import ChatModel
from proofbench.tasks.base import ProofTask
from proofbench.tools.lean_check import LeanCheckTool


class SelfConsistencyLeanAgent:
    name = "self_consistency"

    def __init__(
        self,
        check_tool: LeanCheckTool,
        *,
        samples: int = 3,
        include_informal: bool = True,
    ):
        self.check_tool = check_tool
        self.samples = samples
        self.include_informal = include_informal

    def run(self, task: ProofTask, model: ChatModel) -> AgentResult:
        start = time.perf_counter()
        trace: list[dict[str, Any]] = []
        stats = SearchStats()
        candidates = []
        base_prompt = theorem_prompt(
            task,
            include_informal=self.include_informal,
            method="self-consistency",
        )

        for index in range(self.samples):
            prompt = (
                f"{base_prompt}\n\n"
                "Generate an independent proof attempt. Use a distinct proof strategy from previous attempts "
                "when possible, but still return only Lean code.\n"
                f"Attempt number: {index + 1}"
            )
            response = generate_traced(
                model,
                prompt,
                stats=stats,
                trace=trace,
                trace_type="model",
                metadata={"phase": "sample", "sample": index + 1},
            )
            candidates.append(
                check_candidate(
                    task=task,
                    check_tool=self.check_tool,
                    raw_answer=response.text,
                    label=f"sample_{index + 1}",
                    stats=stats,
                    trace=trace,
                    metadata={"phase": "sample", "sample": index + 1},
                )
            )

        best = select_best_candidate(candidates)
        trace.append(
            {
                "type": "selection",
                "strategy": "self_consistency",
                "candidate_count": len(candidates),
                "selected": best.label if best else None,
                "selected_score": best.score if best else None,
                "selected_passed": best.passed if best else False,
            }
        )
        return build_agent_result(
            agent_name=self.name,
            task=task,
            best=best,
            trace=trace,
            stats=stats,
            start=start,
        )

