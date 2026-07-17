from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from proofbench.agents.base import AgentResult
from proofbench.agents.search_common import (
    ProofSearchCandidate,
    SearchStats,
    build_agent_result,
    check_candidate,
    generate_traced,
    parse_score,
    select_best_candidate,
    theorem_prompt,
)
from proofbench.models.base import ChatModel
from proofbench.tasks.base import ProofTask
from proofbench.tools.lean_check import LeanCheckTool


@dataclass
class LatsNode:
    node_id: str
    parent: "LatsNode | None" = None
    children: list["LatsNode"] = field(default_factory=list)
    candidate: ProofSearchCandidate | None = None
    reflection: str = ""
    visits: int = 0
    value: float = 0.0
    depth: int = 0

    @property
    def average_value(self) -> float:
        return self.value / self.visits if self.visits else 0.0


class LanguageAgentTreeSearchLeanAgent:
    name = "lats"

    def __init__(
        self,
        check_tool: LeanCheckTool,
        *,
        rollouts: int = 4,
        width: int = 2,
        depth: int = 2,
        exploration: float = 1.4,
        include_informal: bool = True,
    ):
        self.check_tool = check_tool
        self.rollouts = rollouts
        self.width = width
        self.depth = depth
        self.exploration = exploration
        self.include_informal = include_informal

    def run(self, task: ProofTask, model: ChatModel) -> AgentResult:
        start = time.perf_counter()
        trace: list[dict[str, Any]] = []
        stats = SearchStats()
        base_prompt = theorem_prompt(
            task,
            include_informal=self.include_informal,
            method="Language Agent Tree Search",
        )
        root = LatsNode(node_id="root")
        candidates: list[ProofSearchCandidate] = []
        next_id = 1

        for rollout in range(self.rollouts):
            leaf = select_lats_leaf(root, self.exploration, self.depth)
            if leaf.depth >= self.depth:
                reward = leaf.candidate.score if leaf.candidate else 0.0
                backpropagate(leaf, reward)
                continue

            children = []
            for branch in range(self.width):
                prompt = (
                    f"{base_prompt}\n\n"
                    "Use MCTS-style planning. Expand the current trajectory by proposing one proof action: "
                    "a short reasoning step plus a complete Lean proof attempt. Return Lean code in a code fence.\n\n"
                    f"Parent reflection:\n{leaf.reflection or '(none)'}\n\n"
                    f"Parent proof:\n{leaf.candidate.raw_answer if leaf.candidate else '(root)'}\n\n"
                    f"Rollout: {rollout + 1}; branch: {branch + 1}."
                )
                response = generate_traced(
                    model,
                    prompt,
                    stats=stats,
                    trace=trace,
                    trace_type="model",
                    metadata={"phase": "mcts_expand", "rollout": rollout + 1, "parent": leaf.node_id},
                )
                node_id = f"n{next_id}"
                next_id += 1
                candidate = check_candidate(
                    task=task,
                    check_tool=self.check_tool,
                    raw_answer=response.text,
                    label=node_id,
                    stats=stats,
                    trace=trace,
                    metadata={"phase": "environment_feedback", "rollout": rollout + 1},
                )
                child = LatsNode(
                    node_id=node_id,
                    parent=leaf,
                    candidate=candidate,
                    depth=leaf.depth + 1,
                )
                leaf.children.append(child)
                children.append(child)
                candidates.append(candidate)

            selected = max(children, key=lambda node: node.candidate.score if node.candidate else 0.0)
            reward = selected.candidate.score if selected.candidate else 0.0
            if selected.candidate and not selected.candidate.passed:
                reflection = self_reflect(
                    model=model,
                    base_prompt=base_prompt,
                    node=selected,
                    stats=stats,
                    trace=trace,
                )
                selected.reflection = reflection
                reward = max(reward, parse_score(reflection, default=reward))
            backpropagate(selected, reward)
            trace.append(
                {
                    "type": "mcts",
                    "rollout": rollout + 1,
                    "selected": selected.node_id,
                    "reward": reward,
                    "root_visits": root.visits,
                }
            )
            if selected.candidate and selected.candidate.passed:
                break

        best = select_best_candidate(candidates)
        return build_agent_result(
            agent_name=self.name,
            task=task,
            best=best,
            trace=trace,
            stats=stats,
            start=start,
        )


def select_lats_leaf(root: LatsNode, exploration: float, max_depth: int) -> LatsNode:
    node = root
    while node.children and node.depth < max_depth:
        node = max(node.children, key=lambda child: uct(child, node.visits, exploration))
    return node


def uct(node: LatsNode, parent_visits: int, exploration: float) -> float:
    if node.visits == 0:
        return float("inf")
    return node.average_value + exploration * math.sqrt(math.log(max(1, parent_visits)) / node.visits)


def backpropagate(node: LatsNode, reward: float) -> None:
    current: LatsNode | None = node
    while current is not None:
        current.visits += 1
        current.value += reward
        current = current.parent


def self_reflect(
    *,
    model: ChatModel,
    base_prompt: str,
    node: LatsNode,
    stats: SearchStats,
    trace: list[dict[str, Any]],
) -> str:
    assert node.candidate is not None
    response = generate_traced(
        model,
        (
            f"{base_prompt}\n\n"
            "Reflect on why this proof failed and give a concise repair plan. "
            "End with a correctness score from 1 to 10.\n\n"
            f"Failed proof:\n{node.candidate.raw_answer}\n\n"
            f"Verifier diagnostics:\n{node.candidate.verification.diagnostics[-2000:]}"
        ),
        stats=stats,
        trace=trace,
        trace_type="model",
        metadata={"phase": "self_reflection", "node": node.node_id},
    )
    return response.text

