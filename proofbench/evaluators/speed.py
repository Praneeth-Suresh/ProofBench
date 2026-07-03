from __future__ import annotations

from proofbench.agents.base import AgentResult
from proofbench.evaluators.accuracy import VerificationResult


def speed_metrics(agent_result: AgentResult, verification: VerificationResult) -> dict[str, float]:
    return {
        "agent_elapsed_s": agent_result.elapsed_s,
        "model_latency_s": agent_result.model_latency_s,
        "verification_elapsed_s": verification.elapsed_s,
        "total_elapsed_s": agent_result.elapsed_s + verification.elapsed_s,
    }

