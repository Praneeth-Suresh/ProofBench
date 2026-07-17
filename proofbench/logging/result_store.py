from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


class ResultStore:
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.path = self.results_dir / f"run_{stamp}.jsonl"

    def append(self, row: dict) -> None:
        row = {"created_at": datetime.now(timezone.utc).isoformat(), **row}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_results(paths: Iterable[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        if path.is_dir():
            rows.extend(load_results(sorted(path.glob("*.jsonl"))))
            continue
        if not path.exists() or path.suffix != ".jsonl":
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def summarize(rows: list[dict]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["agent"]].append(row)
    summary: dict[str, dict[str, float]] = {}
    for agent, items in grouped.items():
        n = max(1, len(items))
        valid_proof_items = [item for item in items if item.get("metric_validity") == "lean"]
        valid_n = len(valid_proof_items)
        solved_tasks = sum(_success_score(item) for item in items)
        summary[agent] = {
            "tasks": float(len(items)),
            "solved_tasks": solved_tasks,
            "success_rate": solved_tasks / n,
            "proof_metric_coverage": valid_n / n,
            "avg_proof_completion": _average_metric(valid_proof_items, "proof_completion"),
            "avg_verified_prefix_ratio": _average_metric(valid_proof_items, "verified_prefix_ratio"),
            "avg_repairability_score": _average_metric(items, "repairability_score"),
            "avg_total_tokens": sum(item["efficiency"]["total_tokens"] for item in items) / n,
            "avg_model_calls": sum(item["efficiency"]["model_calls"] for item in items) / n,
            "avg_tool_calls": sum(item["efficiency"]["tool_calls"] for item in items) / n,
            "avg_total_elapsed_s": sum(item["speed"]["total_elapsed_s"] for item in items) / n,
        }
    return summary


def _success_score(row: dict) -> float:
    if "success_score" in row:
        return float(row["success_score"])
    if "solved" in row:
        return 1.0 if row["solved"] else 0.0
    return float(row.get("accuracy", 0.0))


def _average_metric(rows: list[dict], name: str) -> float:
    if not rows:
        return 0.0
    return sum(float(row.get(name, 0.0)) for row in rows) / len(rows)
