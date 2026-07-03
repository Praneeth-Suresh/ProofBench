from __future__ import annotations

from proofbench.agents.base import AgentResult


def efficiency_metrics(agent_result: AgentResult) -> dict[str, int]:
    return {
        "model_calls": agent_result.model_calls,
        "input_tokens": agent_result.input_tokens,
        "output_tokens": agent_result.output_tokens,
        "total_tokens": agent_result.input_tokens + agent_result.output_tokens,
        "tool_calls": agent_result.tool_calls,
    }

