from __future__ import annotations

import os
import time

from proofbench.models.base import ModelResponse


class GeminiModel:
    def __init__(self, model_name: str = "gemini-3.1-flash-lite"):
        self.name = model_name
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Set GEMINI_API_KEY before using the Gemini provider. "
                "See ProofBench/README.md for setup instructions."
            )
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - dependency setup
            raise RuntimeError("Install dependencies with `uv sync`.") from exc
        self._client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> ModelResponse:
        start = time.perf_counter()
        response = self._client.models.generate_content(
            model=self.name,
            contents=prompt,
        )
        elapsed = time.perf_counter() - start
        usage = getattr(response, "usage_metadata", None)
        return ModelResponse(
            text=getattr(response, "text", "") or "",
            input_tokens=int(getattr(usage, "prompt_token_count", 0) or 0),
            output_tokens=int(getattr(usage, "candidates_token_count", 0) or 0),
            latency_s=elapsed,
            model_name=self.name,
        )
