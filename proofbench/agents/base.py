from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from proofbench.models.base import ChatModel
from proofbench.tasks.base import ProofTask


@dataclass
class AgentResult:
    agent_name: str
    task_id: str
    raw_answer: str
    trace: list[dict[str, Any]] = field(default_factory=list)
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    model_latency_s: float = 0.0
    elapsed_s: float = 0.0


class Agent(Protocol):
    name: str

    def run(self, task: ProofTask, model: ChatModel) -> AgentResult:
        ...

