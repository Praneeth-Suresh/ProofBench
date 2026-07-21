from __future__ import annotations

from typing import Any


def paired_agent_comparison(rows: list[dict[str, Any]], *, candidate: str = "moe_fused", baseline: str = "llm_baseline", min_solve_delta: float = 0.0, max_token_multiplier: float = 2.0, max_time_multiplier: float = 2.0) -> dict[str, Any]:
    candidate_rows = _latest_lean_rows(rows, candidate)
    baseline_rows = _latest_lean_rows(rows, baseline)
    pairs = [(baseline_rows[key], candidate_row) for key, candidate_row in candidate_rows.items() if key in baseline_rows]
    if not pairs:
        return {"candidate": candidate, "baseline": baseline, "paired_tasks": 0, "reason": "No matching Lean-verified task/model/verifier rows are available.", "efficiency_gate": {"passed": False}}
    baseline_success = _average([pair[0] for pair in pairs], "success_score")
    candidate_success = _average([pair[1] for pair in pairs], "success_score")
    baseline_tokens = _average_nested([pair[0] for pair in pairs], "efficiency", "total_tokens")
    candidate_tokens = _average_nested([pair[1] for pair in pairs], "efficiency", "total_tokens")
    baseline_time = _average_nested([pair[0] for pair in pairs], "speed", "total_elapsed_s")
    candidate_time = _average_nested([pair[1] for pair in pairs], "speed", "total_elapsed_s")
    token_multiplier = _ratio(candidate_tokens, baseline_tokens)
    time_multiplier = _ratio(candidate_time, baseline_time)
    solve_delta = candidate_success - baseline_success
    return {"candidate": candidate, "baseline": baseline, "paired_tasks": len(pairs), "task_ids": [candidate_row["task_id"] for _, candidate_row in pairs], "baseline_success_rate": baseline_success, "candidate_success_rate": candidate_success, "solve_rate_delta": solve_delta, "token_multiplier": token_multiplier, "time_multiplier": time_multiplier, "efficiency_gate": {"minimum_solve_delta": min_solve_delta, "maximum_token_multiplier": max_token_multiplier, "maximum_time_multiplier": max_time_multiplier, "passed": solve_delta >= min_solve_delta and token_multiplier <= max_token_multiplier and time_multiplier <= max_time_multiplier}}


def _latest_lean_rows(rows: list[dict[str, Any]], agent: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    latest: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        if row.get("agent") != agent or row.get("metric_validity") != "lean":
            continue
        key = (str(row.get("task_id", "")), str(row.get("model", "")), str(row.get("verification", {}).get("verifier", "")))
        if key not in latest or str(row.get("created_at", "")) >= str(latest[key].get("created_at", "")):
            latest[key] = row
    return latest


def _average(rows: list[dict[str, Any]], key: str) -> float:
    return sum(float(row.get(key, 0.0)) for row in rows) / len(rows)


def _average_nested(rows: list[dict[str, Any]], container: str, key: str) -> float:
    return sum(float(row.get(container, {}).get(key, 0.0)) for row in rows) / len(rows)


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0.0:
        return 0.0 if numerator == 0.0 else float("inf")
    return numerator / denominator
