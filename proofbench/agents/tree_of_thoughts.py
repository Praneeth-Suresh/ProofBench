from __future__ import annotations

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
    select_best_candidate,
    theorem_prompt,
)
from proofbench.models.base import ChatModel
from proofbench.tasks.base import ProofTask
from proofbench.tools.lean_check import LeanCheckTool


@dataclass
class ThoughtState:
    thoughts: list[str] = field(default_factory=list)
    candidate: ProofSearchCandidate | None = None

    @property
    def score(self) -> float:
        return self.candidate.score if self.candidate else 0.0


class TreeOfThoughtsLeanAgent:
    name = "tree_of_thoughts"

    def __init__(
        self,
        check_tool: LeanCheckTool,
        *,
        width: int = 2,
        depth: int = 2,
        include_informal: bool = True,
    ):
        self.check_tool = check_tool
        self.width = width
        self.depth = depth
        self.include_informal = include_informal

    def run(self, task: ProofTask, model: ChatModel) -> AgentResult:
        start = time.perf_counter()
        trace: list[dict[str, Any]] = []
        stats = SearchStats()
        base_prompt = theorem_prompt(task, include_informal=self.include_informal, method="Tree of Thoughts")
        frontier = [ThoughtState()]
        candidates: list[ProofSearchCandidate] = []

        for depth_index in range(self.depth):
            next_frontier: list[ThoughtState] = []
            for state_index, state in enumerate(frontier):
                for branch_index in range(self.width):
                    prompt = (
                        f"{base_prompt}\n\n"
                        "You are exploring a tree of proof thoughts. A thought is a concise proof strategy "
                        "followed by the Lean proof that attempts that strategy.\n"
                        f"Existing thoughts:\n{format_thoughts(state.thoughts)}\n\n"
                        "Generate the next thought and then a complete Lean proof.\n"
                        "Use this shape:\n"
                        "THOUGHT: <short strategy>\n"
                        "```lean\n<complete theorem or proof body>\n```\n"
                        f"Depth: {depth_index + 1}; branch: {branch_index + 1}; parent: {state_index + 1}."
                    )
                    response = generate_traced(
                        model,
                        prompt,
                        stats=stats,
                        trace=trace,
                        trace_type="model",
                        metadata={
                            "phase": "thought_generation",
                            "depth": depth_index + 1,
                            "branch": branch_index + 1,
                            "parent": state_index + 1,
                        },
                    )
                    thought = extract_thought(response.text)
                    candidate = check_candidate(
                        task=task,
                        check_tool=self.check_tool,
                        raw_answer=response.text,
                        label=f"d{depth_index + 1}_p{state_index + 1}_b{branch_index + 1}",
                        stats=stats,
                        trace=trace,
                        metadata={"phase": "state_evaluation", "depth": depth_index + 1},
                    )
                    candidates.append(candidate)
                    next_frontier.append(ThoughtState(thoughts=[*state.thoughts, thought], candidate=candidate))

            next_frontier.sort(key=lambda item: (item.candidate.passed if item.candidate else False, item.score), reverse=True)
            frontier = next_frontier[: self.width]
            trace.append(
                {
                    "type": "selection",
                    "strategy": "tree_of_thoughts_beam",
                    "depth": depth_index + 1,
                    "kept": [state.candidate.label for state in frontier if state.candidate],
                }
            )
            if any(state.candidate and state.candidate.passed for state in frontier):
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


def format_thoughts(thoughts: list[str]) -> str:
    if not thoughts:
        return "(none yet)"
    return "\n".join(f"{index + 1}. {thought}" for index, thought in enumerate(thoughts))


def extract_thought(text: str) -> str:
    for line in text.splitlines():
        if line.strip().lower().startswith("thought:"):
            return line.split(":", 1)[1].strip()
    return text.strip().splitlines()[0][:200] if text.strip() else ""

