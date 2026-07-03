from __future__ import annotations

from proofbench.config import DEFAULT_TASK_IDS, ProofBenchConfig
from proofbench.tasks.base import ProofTask
from proofbench.tasks.minif2f import MiniF2FRepository


def resolve_task_ids(task_args: list[str] | None) -> list[str]:
    if not task_args or task_args == ["all"] or "all" in task_args:
        return list(DEFAULT_TASK_IDS)
    resolved: list[str] = []
    for item in task_args:
        resolved.extend(part.strip() for part in item.split(",") if part.strip())
    return resolved


def load_tasks(config: ProofBenchConfig, task_ids: list[str]) -> list[ProofTask]:
    repo = MiniF2FRepository(config)
    return [repo.load_task(task_id) for task_id in task_ids]

