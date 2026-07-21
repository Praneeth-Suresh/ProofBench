from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from proofbench.tasks.base import ProofTask


SAFE_DEFAULT_EXPERTS = ("llm_baseline", "react")


@dataclass(frozen=True)
class RouterDecision:
    experts: tuple[str, str]
    weights: tuple[float, float]
    scores: tuple[dict[str, Any], ...]
    features: dict[str, Any]
    fallback_reason: str | None
    calibration: dict[str, Any]

    def trace_event(self) -> dict[str, Any]:
        return {
            "type": "router",
            "strategy": "glam_top_2_agent_routing",
            "selected_experts": list(self.experts),
            "weights": list(self.weights),
            "scores": list(self.scores),
            "features": self.features,
            "fallback_reason": self.fallback_reason,
            "calibration": self.calibration,
        }


@dataclass(frozen=True)
class HistoricalExpertStats:
    samples: int
    mean_success: float
    mean_completion: float
    mean_tokens: float
    mean_elapsed_s: float


class AgentRouter:
    """Sparse, deterministic top-2 gate with calibrated historical-result overlays."""

    def __init__(
        self,
        expert_names: Iterable[str],
        *,
        history_rows: Iterable[dict[str, Any]] = (),
    ):
        self.expert_names = tuple(dict.fromkeys(expert_names))
        if len(self.expert_names) < 2:
            raise ValueError("AgentRouter needs at least two distinct experts.")
        self._history = self._summarize_history(history_rows)

    def route(
        self,
        task: ProofTask,
        *,
        previous_diagnostics: str | None = None,
    ) -> RouterDecision:
        features = task_features(task, previous_diagnostics=previous_diagnostics)
        ranked: list[dict[str, Any]] = []
        usable_history = 0

        for expert in self.expert_names:
            static_score = static_expert_score(expert, features)
            history = self._history.get((task.task_id, expert)) or self._history.get((task.split, expert))
            score = static_score
            calibration = 0.0
            expected_tokens = 0.0
            expected_elapsed_s = 0.0
            if history:
                usable_history += history.samples
                calibration = history.samples / (history.samples + 5.0)
                empirical_score = history.mean_success + (0.25 * history.mean_completion)
                score = ((1.0 - calibration) * static_score) + (calibration * empirical_score)
                expected_tokens = history.mean_tokens
                expected_elapsed_s = history.mean_elapsed_s
            ranked.append(
                {
                    "agent": expert,
                    "score": round(score, 6),
                    "static_score": round(static_score, 6),
                    "history_samples": history.samples if history else 0,
                    "expected_tokens": round(expected_tokens, 3),
                    "expected_elapsed_s": round(expected_elapsed_s, 6),
                }
            )

        ranked.sort(key=lambda item: (-item["score"], item["agent"]))
        selected = ranked[:2]
        fallback_reason = None
        if len(selected) != 2 or len({item["agent"] for item in selected}) != 2:
            selected = self._fallback_scores(features)
            fallback_reason = "invalid_router_output"
        elif usable_history == 0:
            fallback_reason = "no_usable_historical_rows; static_scores_used"

        total_score = sum(max(0.0, item["score"]) for item in selected)
        if total_score == 0.0:
            weights = (0.5, 0.5)
            fallback_reason = fallback_reason or "zero_router_scores"
        else:
            first_weight = round(max(0.0, selected[0]["score"]) / total_score, 6)
            weights = (first_weight, round(1.0 - first_weight, 6))

        return RouterDecision(
            experts=(selected[0]["agent"], selected[1]["agent"]),
            weights=weights,
            scores=tuple(ranked),
            features=features,
            fallback_reason=fallback_reason,
            calibration={
                "method": "empirical_bayes_success_completion",
                "history_samples": usable_history,
                "prior_strength": 5,
                "expected_cost_available": usable_history > 0,
            },
        )

    def history_summary(self) -> dict[str, dict[str, float]]:
        summary: dict[str, list[HistoricalExpertStats]] = defaultdict(list)
        for (_, expert), stats in self._history.items():
            summary[expert].append(stats)
        return {
            expert: {
                "samples": float(sum(stats.samples for stats in values)),
                "mean_success": _weighted_average(values, "mean_success"),
                "mean_completion": _weighted_average(values, "mean_completion"),
                "mean_tokens": _weighted_average(values, "mean_tokens"),
                "mean_elapsed_s": _weighted_average(values, "mean_elapsed_s"),
            }
            for expert, values in summary.items()
        }

    def _fallback_scores(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        defaults = [name for name in SAFE_DEFAULT_EXPERTS if name in self.expert_names]
        defaults.extend(name for name in self.expert_names if name not in defaults)
        return [
            {
                "agent": expert,
                "score": static_expert_score(expert, features),
                "static_score": static_expert_score(expert, features),
                "history_samples": 0,
                "expected_tokens": 0.0,
                "expected_elapsed_s": 0.0,
            }
            for expert in defaults[:2]
        ]

    def _summarize_history(
        self, history_rows: Iterable[dict[str, Any]]
    ) -> dict[tuple[str, str], HistoricalExpertStats]:
        buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in history_rows:
            expert = row.get("agent")
            if expert not in self.expert_names or row.get("metric_validity") != "lean":
                continue
            buckets[(str(row.get("task_id", "")), expert)].append(row)
            buckets[(str(row.get("split", "")), expert)].append(row)
        return {key: _history_stats(rows) for key, rows in buckets.items() if rows}


def task_features(task: ProofTask, *, previous_diagnostics: str | None = None) -> dict[str, Any]:
    statement = task.formal_statement
    quantifier_depth = len(re.findall(r"∀|∃|\\b(?:forall|exists)\\b", statement, flags=re.IGNORECASE))
    symbol_count = sum(statement.count(symbol) for symbol in ("→", "∧", "∨", "=", "<", ">", "^"))
    diagnostic_text = (previous_diagnostics or "").lower()
    return {
        "task_id": task.task_id,
        "split": task.split,
        "source_ref": task.source_ref,
        "statement_chars": len(statement),
        "symbol_count": symbol_count,
        "quantifier_depth": quantifier_depth,
        "long_statement": len(statement) >= 400,
        "formal_check_failure": any(
            marker in diagnostic_text
            for marker in ("error", "failed", "unsolved", "unknown identifier", "type mismatch")
        ),
    }


def static_expert_score(expert: str, features: dict[str, Any]) -> float:
    score = 0.2
    if expert == "llm_baseline":
        score += 0.02
    if expert == "react" and features["formal_check_failure"]:
        score += 0.35
    if expert == "lats" and features["formal_check_failure"]:
        score += 0.3
    if expert in {"self_consistency", "tree_of_thoughts"} and features["long_statement"]:
        score += 0.3
    if expert == "graph_of_thoughts" and (features["quantifier_depth"] >= 2 or features["symbol_count"] >= 8):
        score += 0.25
    return score


def _history_stats(rows: list[dict[str, Any]]) -> HistoricalExpertStats:
    n = len(rows)
    return HistoricalExpertStats(
        samples=n,
        mean_success=sum(float(row.get("success_score", 0.0)) for row in rows) / n,
        mean_completion=sum(float(row.get("proof_completion", 0.0)) for row in rows) / n,
        mean_tokens=sum(float(row.get("efficiency", {}).get("total_tokens", 0.0)) for row in rows) / n,
        mean_elapsed_s=sum(float(row.get("speed", {}).get("total_elapsed_s", 0.0)) for row in rows) / n,
    )


def _weighted_average(values: list[HistoricalExpertStats], field: str) -> float:
    total_samples = sum(stats.samples for stats in values)
    if not total_samples:
        return 0.0
    return sum(stats.samples * float(getattr(stats, field)) for stats in values) / total_samples
