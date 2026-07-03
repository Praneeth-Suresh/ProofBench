from __future__ import annotations

from proofbench.models.base import ChatModel
from proofbench.models.gemini import GeminiModel
from proofbench.models.mock import MockModel


def create_model(provider: str, model_name: str | None = None) -> ChatModel:
    if provider == "gemini":
        return GeminiModel(model_name or "gemini-3.1-flash-lite")
    if provider == "mock":
        return MockModel(mode="fail")
    if provider == "mock-react":
        return MockModel(mode="react")
    raise ValueError(f"Unknown model provider: {provider}")
