from __future__ import annotations

import re
import time

from proofbench.agents.base import AgentResult
from proofbench.models.base import ChatModel
from proofbench.tasks.base import ProofTask
from proofbench.tasks.minif2f import extract_candidate_lean
from proofbench.tools.lean_check import LeanCheckTool


class ReActLeanAgent:
    name = "react"

    def __init__(
        self,
        check_tool: LeanCheckTool,
        *,
        max_iters: int = 3,
        include_informal: bool = True,
    ):
        self.check_tool = check_tool
        self.max_iters = max_iters
        self.include_informal = include_informal

    def run(self, task: ProofTask, model: ChatModel) -> AgentResult:
        start = time.perf_counter()
        trace: list[dict[str, object]] = []
        model_calls = input_tokens = output_tokens = tool_calls = 0
        model_latency = 0.0
        transcript = (
            "You are a ReAct-style theorem-proving agent for Lean 3.\n"
            "At each step either request compiler feedback or submit a final proof.\n"
            "Use exactly one of these formats:\n"
            "ACTION: check\n```lean\n<complete theorem or proof body>\n```\n"
            "FINAL\n```lean\n<complete theorem or proof body>\n```\n"
            "Do not use sorry, admit, or placeholders.\n\n"
            f"{task.prompt_statement(include_informal=self.include_informal)}"
        )
        final_answer = ""

        for _ in range(self.max_iters):
            response = model.generate(transcript)
            model_calls += 1
            input_tokens += response.input_tokens
            output_tokens += response.output_tokens
            model_latency += response.latency_s
            trace.append({"type": "model", "response": response.text})

            if response.text.strip().upper().startswith("FINAL"):
                final_answer = response.text
                break

            if "ACTION: check" in response.text:
                candidate = extract_candidate_lean(task, response.text)
                check = self.check_tool.run(task, candidate)
                tool_calls += 1
                trace.append(
                    {
                        "type": "tool",
                        "tool": "lean_check",
                        "passed": check.passed,
                        "diagnostics": check.diagnostics[-2000:],
                    }
                )
                transcript += (
                    "\n\nCompiler feedback:\n"
                    f"passed={check.passed}\n"
                    f"{check.diagnostics[-2000:]}\n"
                    "Revise the proof and continue."
                )
                if check.passed:
                    final_answer = response.text
                    break
                continue

            final_answer = response.text
            if not re.search(r"```", response.text):
                transcript += "\n\nYour previous response was not Lean code. Try again."

        if not final_answer and trace:
            final_answer = str(trace[-1].get("response", ""))

        return AgentResult(
            agent_name=self.name,
            task_id=task.task_id,
            raw_answer=final_answer,
            trace=trace,
            model_calls=model_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tool_calls=tool_calls,
            model_latency_s=model_latency,
            elapsed_s=time.perf_counter() - start,
        )

