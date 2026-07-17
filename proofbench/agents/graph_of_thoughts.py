from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from proofbench.agents.base import AgentResult
from proofbench.agents.search_common import (
    ProofSearchCandidate,
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


@dataclass
class ThoughtNode:
    node_id: str
    operation: str
    candidate: ProofSearchCandidate


class GraphOfThoughtsLeanAgent:
    name = "graph_of_thoughts"

    def __init__(
        self,
        check_tool: LeanCheckTool,
        *,
        width: int = 2,
        include_informal: bool = True,
    ):
        self.check_tool = check_tool
        self.width = width
        self.include_informal = include_informal

    def run(self, task: ProofTask, model: ChatModel) -> AgentResult:
        start = time.perf_counter()
        trace: list[dict[str, Any]] = []
        stats = SearchStats()
        base_prompt = theorem_prompt(task, include_informal=self.include_informal, method="Graph of Thoughts")
        nodes: list[ThoughtNode] = []
        edges: list[dict[str, str]] = []

        for index in range(self.width):
            response = generate_traced(
                model,
                (
                    f"{base_prompt}\n\n"
                    "Generate one independent proof thought and a complete Lean proof. "
                    "This will become a graph vertex for later refinement."
                ),
                stats=stats,
                trace=trace,
                trace_type="model",
                metadata={"phase": "generate", "node": f"g{index + 1}"},
            )
            candidate = check_candidate(
                task=task,
                check_tool=self.check_tool,
                raw_answer=response.text,
                label=f"g{index + 1}",
                stats=stats,
                trace=trace,
                metadata={"phase": "generate"},
            )
            nodes.append(ThoughtNode(node_id=f"g{index + 1}", operation="generate", candidate=candidate))

        for node in list(nodes):
            if node.candidate.passed:
                continue
            response = generate_traced(
                model,
                (
                    f"{base_prompt}\n\n"
                    "Improve this failed proof using the verifier diagnostics. Return only revised Lean code.\n\n"
                    f"Previous proof:\n{node.candidate.raw_answer}\n\n"
                    f"Verifier diagnostics:\n{node.candidate.verification.diagnostics[-2000:]}"
                ),
                stats=stats,
                trace=trace,
                trace_type="model",
                metadata={"phase": "improve", "source": node.node_id},
            )
            improved_id = f"{node.node_id}_i"
            candidate = check_candidate(
                task=task,
                check_tool=self.check_tool,
                raw_answer=response.text,
                label=improved_id,
                stats=stats,
                trace=trace,
                metadata={"phase": "improve", "source": node.node_id},
            )
            nodes.append(ThoughtNode(node_id=improved_id, operation="improve", candidate=candidate))
            edges.append({"from": node.node_id, "to": improved_id, "operation": "improve"})

        top = sorted(nodes, key=lambda node: (node.candidate.passed, node.candidate.score), reverse=True)[:2]
        if len(top) == 2 and not any(node.candidate.passed for node in top):
            response = generate_traced(
                model,
                (
                    f"{base_prompt}\n\n"
                    "Aggregate the strongest parts of these two proof attempts into one complete Lean proof. "
                    "Return only Lean code.\n\n"
                    f"Attempt A:\n{top[0].candidate.raw_answer}\n\n"
                    f"Attempt B:\n{top[1].candidate.raw_answer}"
                ),
                stats=stats,
                trace=trace,
                trace_type="model",
                metadata={"phase": "aggregate", "sources": [top[0].node_id, top[1].node_id]},
            )
            candidate = check_candidate(
                task=task,
                check_tool=self.check_tool,
                raw_answer=response.text,
                label="aggregate_1",
                stats=stats,
                trace=trace,
                metadata={"phase": "aggregate", "sources": [top[0].node_id, top[1].node_id]},
            )
            nodes.append(ThoughtNode(node_id="aggregate_1", operation="aggregate", candidate=candidate))
            edges.append({"from": top[0].node_id, "to": "aggregate_1", "operation": "aggregate"})
            edges.append({"from": top[1].node_id, "to": "aggregate_1", "operation": "aggregate"})

        trace.append(
            {
                "type": "graph",
                "nodes": [
                    {
                        "id": node.node_id,
                        "operation": node.operation,
                        "score": node.candidate.score,
                        "passed": node.candidate.passed,
                    }
                    for node in nodes
                ],
                "edges": edges,
            }
        )
        best = select_best_candidate([node.candidate for node in nodes])
        return build_agent_result(
            agent_name=self.name,
            task=task,
            best=best,
            trace=trace,
            stats=stats,
            start=start,
        )

