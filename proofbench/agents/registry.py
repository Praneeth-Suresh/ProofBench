from __future__ import annotations

from proofbench.agents.base import Agent
from proofbench.agents.llm_baseline import LLMBaselineAgent
from proofbench.agents.react_agent import ReActLeanAgent
from proofbench.tools.lean_check import LeanCheckTool


REGISTERED_AGENT_NAMES = ("llm_baseline", "react")


def registered_agent_names() -> tuple[str, ...]:
    return REGISTERED_AGENT_NAMES


def create_agents(
    names: list[str],
    *,
    check_tool: LeanCheckTool,
    max_iters: int,
    include_informal: bool,
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
        else:
            raise ValueError(f"Unknown agent: {name}")
    return agents
