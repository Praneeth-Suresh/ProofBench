from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any

from proofbench.agents.base import AgentResult
from proofbench.evaluators.accuracy import VerificationResult
from proofbench.models.base import ChatModel, ModelResponse
from proofbench.tasks.base import ProofTask
from proofbench.tasks.minif2f import extract_candidate_lean
from proofbench.tools.lean_check import LeanCheckTool


@dataclass
class SearchStats:
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model_latency_s: float = 0.0
    tool_calls: int = 0

    def add_response(self, response: ModelResponse) -> None:
        self.model_calls += 1
        self.input_tokens += response.input_tokens
        self.output_tokens += response.output_tokens
        self.model_latency_s += response.latency_s


@dataclass
class ProofSearchCandidate:
    label: str
    raw_answer: str
    lean_code: str
    verification: VerificationResult
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.verification.passed


def theorem_prompt(task: ProofTask, *, include_informal: bool, method: str) -> str:
    return (
        f"You are a {method} theorem-proving agent for Lean 3 miniF2F tasks.\n"
        "Return only Lean code for a complete theorem or proof body. "
        "Do not use sorry, admit, or placeholders.\n\n"
        f"{task.prompt_statement(include_informal=include_informal)}"
    )


def generate_traced(
    model: ChatModel,
    prompt: str,
    *,
    stats: SearchStats,
    trace: list[dict[str, Any]],
    trace_type: str,
    metadata: dict[str, Any] | None = None,
) -> ModelResponse:
    response = model.generate(prompt)
    stats.add_response(response)
    event: dict[str, Any] = {
        "type": trace_type,
        "prompt": prompt,
        "response": response.text,
    }
    if metadata:
        event.update(metadata)
    trace.append(event)
    return response


def check_candidate(
    *,
    task: ProofTask,
    check_tool: LeanCheckTool,
    raw_answer: str,
    label: str,
    stats: SearchStats,
    trace: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> ProofSearchCandidate:
    lean_code = extract_candidate_lean(task, raw_answer)
    verification = check_tool.run(task, lean_code)
    stats.tool_calls += 1
    score = candidate_score(verification)
    event: dict[str, Any] = {
        "type": "tool",
        "tool": "lean_check",
        "candidate": label,
        "passed": verification.passed,
        "score": score,
        "diagnostics": verification.diagnostics[-2000:],
        "proof_completion": verification.proof_completion,
        "verified_prefix_ratio": verification.verified_prefix_ratio,
        "repairability_score": verification.repairability_score,
        "failure_profile": verification.failure_profile,
    }
    if metadata:
        event.update(metadata)
    trace.append(event)
    return ProofSearchCandidate(
        label=label,
        raw_answer=raw_answer,
        lean_code=lean_code,
        verification=verification,
        score=score,
        metadata=metadata or {},
    )


def candidate_score(verification: VerificationResult) -> float:
    if verification.passed:
        return 1.0
    completion = float(verification.proof_completion)
    repairability = float(verification.repairability_score)
    return max(0.0, min(0.95, completion + (0.05 * repairability)))


def select_best_candidate(candidates: list[ProofSearchCandidate]) -> ProofSearchCandidate | None:
    if not candidates:
        return None
    return max(
        enumerate(candidates),
        key=lambda item: (
            item[1].passed,
            item[1].score,
            consistency_count(candidates, item[1]),
            -item[0],
        ),
    )[1]


def consistency_count(candidates: list[ProofSearchCandidate], target: ProofSearchCandidate) -> int:
    target_key = normalize_lean(target.lean_code)
    return sum(1 for candidate in candidates if normalize_lean(candidate.lean_code) == target_key)


def normalize_lean(lean_code: str) -> str:
    normalized = re.sub(r"--.*?$", "", lean_code, flags=re.MULTILINE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.lower()


def build_agent_result(
    *,
    agent_name: str,
    task: ProofTask,
    best: ProofSearchCandidate | None,
    trace: list[dict[str, Any]],
    stats: SearchStats,
    start: float,
) -> AgentResult:
    raw_answer = best.raw_answer if best else ""
    return AgentResult(
        agent_name=agent_name,
        task_id=task.task_id,
        raw_answer=raw_answer,
        trace=trace,
        model_calls=stats.model_calls,
        input_tokens=stats.input_tokens,
        output_tokens=stats.output_tokens,
        tool_calls=stats.tool_calls,
        model_latency_s=stats.model_latency_s,
        elapsed_s=time.perf_counter() - start,
    )


def parse_score(text: str, *, default: float = 0.0) -> float:
    matches = re.findall(r"\b(?:score|rating|value|correctness)\D+([0-9]+(?:\.[0-9]+)?)", text, flags=re.I)
    if not matches:
        matches = re.findall(r"\b([0-9]+(?:\.[0-9]+)?)\s*/\s*10\b", text)
    if not matches:
        return default
    value = float(matches[-1])
    if value > 1.0:
        value = value / 10.0
    if math.isnan(value):
        return default
    return max(0.0, min(1.0, value))
