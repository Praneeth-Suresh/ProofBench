from __future__ import annotations

from proofbench.agents.base import Agent
from proofbench.agents.graph_of_thoughts import GraphOfThoughtsLeanAgent
from proofbench.agents.lats import LanguageAgentTreeSearchLeanAgent
from proofbench.agents.llm_baseline import LLMBaselineAgent
from proofbench.agents.react_agent import ReActLeanAgent
from proofbench.agents.self_consistency import SelfConsistencyLeanAgent
from proofbench.agents.tree_of_thoughts import TreeOfThoughtsLeanAgent
from proofbench.tools.lean_check import LeanCheckTool


REGISTERED_AGENT_NAMES = (
    "llm_baseline",
    "react",
    "self_consistency",
    "tree_of_thoughts",
    "graph_of_thoughts",
    "lats",
)


def registered_agent_names() -> tuple[str, ...]:
    return REGISTERED_AGENT_NAMES


def create_agents(
    names: list[str],
    *,
    check_tool: LeanCheckTool,
    max_iters: int,
    include_informal: bool,
    search_samples: int = 3,
    search_width: int = 2,
    search_depth: int = 2,
    lats_rollouts: int = 4,
) -> list[Agent]:
    agents: list[Agent] = []
    for name in names:
        if name == "llm_baseline":
            agents.append(LLMBaselineAgent(include_informal=include_informal))
        elif name == "react":
            agents.append(
                ReActLeanAgent(
                    check_tool,
                    max_iters=max_iters,
                    include_informal=include_informal,
                )
            )
        elif name == "self_consistency":
            agents.append(
                SelfConsistencyLeanAgent(
                    check_tool,
                    samples=search_samples,
                    include_informal=include_informal,
                )
            )
        elif name == "tree_of_thoughts":
            agents.append(
                TreeOfThoughtsLeanAgent(
                    check_tool,
                    width=search_width,
                    depth=search_depth,
                    include_informal=include_informal,
                )
            )
        elif name == "graph_of_thoughts":
            agents.append(
                GraphOfThoughtsLeanAgent(
                    check_tool,
                    width=search_width,
                    include_informal=include_informal,
                )
            )
        elif name == "lats":
            agents.append(
                LanguageAgentTreeSearchLeanAgent(
                    check_tool,
                    rollouts=lats_rollouts,
                    width=search_width,
                    depth=search_depth,
                    include_informal=include_informal,
                )
            )
        else:
            raise ValueError(f"Unknown agent: {name}")
    return agents
