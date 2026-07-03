from __future__ import annotations

import time

from proofbench.models.base import ModelResponse


class MockModel:
    """Deterministic model for smoke tests and dashboard demos."""

    def __init__(self, *, mode: str = "fail"):
        self.mode = mode
        self.name = f"mock-{mode}"
        self._calls = 0

    def generate(self, prompt: str) -> ModelResponse:
        start = time.perf_counter()
        self._calls += 1
        if self.mode == "react" and self._calls % 2 == 1:
            text = "ACTION: check\n```lean\nby\n  exact by sorry\n```"
        elif self.mode == "react":
            text = "FINAL\n```lean\nbegin\n  sorry\nend\n```"
        else:
            text = "```lean\nbegin\n  sorry\nend\n```"
        return ModelResponse(
            text=text,
            input_tokens=max(1, len(prompt.split())),
            output_tokens=max(1, len(text.split())),
            latency_s=time.perf_counter() - start,
            model_name=self.name,
        )

