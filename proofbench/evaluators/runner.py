from __future__ import annotations

from dataclasses import asdict

from proofbench.agents.base import Agent
from proofbench.evaluators.accuracy import success_score
from proofbench.evaluators.efficiency import efficiency_metrics
from proofbench.evaluators.lean import ProofVerifier
from proofbench.evaluators.speed import speed_metrics
from proofbench.logging.result_store import ResultStore
from proofbench.models.base import ChatModel
from proofbench.tasks.base import ProofTask
from proofbench.tasks.minif2f import extract_candidate_lean


class EvaluationRunner:
    def __init__(self, *, verifier: ProofVerifier, result_store: ResultStore):
        self.verifier = verifier
        self.result_store = result_store

    def run(self, *, agents: list[Agent], tasks: list[ProofTask], model: ChatModel) -> list[dict]:
        rows: list[dict] = []
        for task in tasks:
            for agent in agents:
                agent_result = agent.run(task, model)
                candidate = extract_candidate_lean(task, agent_result.raw_answer)
                verification = self.verifier.verify(candidate)
                row = {
                    "agent": agent_result.agent_name,
                    "task_id": task.task_id,
                    "split": task.split,
                    "proof_system": task.proof_system,
                    "source_ref": task.source_ref,
                    "source_urls": task.source_urls,
                    "model": getattr(model, "name", "unknown"),
                    "metric_validity": metric_validity(verification, getattr(model, "name", "unknown")),
                    "solved": verification.passed,
                    "success_score": success_score(verification),
                    "proof_completion": verification.proof_completion,
                    "verified_prefix_ratio": verification.verified_prefix_ratio,
                    "repairability_score": verification.repairability_score,
                    "failure_profile": verification.failure_profile,
                    "completion_metrics": verification.completion_metrics,
                    "verification": asdict(verification),
                    "efficiency": efficiency_metrics(agent_result),
                    "speed": speed_metrics(agent_result, verification),
                    "raw_answer": agent_result.raw_answer,
                    "trace": agent_result.trace,
                }
                self.result_store.append(row)
                rows.append(row)
        return rows


def metric_validity(verification, model_name: str) -> str:
    if str(model_name).startswith("mock-"):
        return "mock_smoke"
    if not verification.verifier_available:
        return "unavailable"
    if verification.verifier == "lean":
        return "lean"
    if verification.verifier == "static":
        return "static_smoke"
    return verification.verifier
