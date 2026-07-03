from __future__ import annotations

import time

from proofbench.agents.base import AgentResult
from proofbench.models.base import ChatModel
from proofbench.tasks.base import ProofTask


class LLMBaselineAgent:
    name = "llm_baseline"

    def __init__(self, *, include_informal: bool = True):
        self.include_informal = include_informal

    def run(self, task: ProofTask, model: ChatModel) -> AgentResult:
        start = time.perf_counter()
        prompt = (
            "You are proving a miniF2F Lean 3 theorem.\n"
            "Return only Lean code for a complete theorem or a proof body. "
            "Do not use sorry, admit, or placeholders.\n\n"
            f"{task.prompt_statement(include_informal=self.include_informal)}"
        )
        response = model.generate(prompt)
        return AgentResult(
            agent_name=self.name,
            task_id=task.task_id,
            raw_answer=response.text,
            trace=[{"type": "model", "prompt": prompt, "response": response.text}],
            model_calls=1,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            model_latency_s=response.latency_s,
            elapsed_s=time.perf_counter() - start,
        )

