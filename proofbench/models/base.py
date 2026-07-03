from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ModelResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    model_name: str = "unknown"


class ChatModel(Protocol):
    name: str

    def generate(self, prompt: str) -> ModelResponse:
        ...

