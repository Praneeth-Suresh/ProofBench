from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProofTask:
    task_id: str
    split: str
    proof_system: str
    source_ref: str
    formal_statement: str
    informal_statement: str | None = None
    source_urls: dict[str, str] = field(default_factory=dict)

    def prompt_statement(self, include_informal: bool = True) -> str:
        parts = [f"Task id: {self.task_id}", "Lean theorem statement:", self.formal_statement]
        if include_informal and self.informal_statement:
            parts.extend(["Informal statement:", self.informal_statement])
        return "\n\n".join(parts)

