from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


PLACEHOLDER_MARKERS = ("sorry", "admit", "placeholder")


@dataclass
class VerificationResult:
    passed: bool
    verifier: str
    verifier_available: bool
    diagnostics: str
    elapsed_s: float
    proof_quality_score: float = 0.0
    proof_progress: float = 0.0
    failure_profile: dict[str, bool] = field(default_factory=dict)
    proof_quality_metrics: dict[str, Any] = field(default_factory=dict)


def accuracy_score(result: VerificationResult) -> float:
    return 1.0 if result.passed else 0.0


def enrich_verification(result: VerificationResult, lean_code: str) -> VerificationResult:
    """Attach continuous proof-quality signals derived from verifier output."""

    profile = failure_profile(result, lean_code)
    metrics = proof_quality_metrics(result, lean_code, profile)
    result.failure_profile = profile
    result.proof_quality_metrics = metrics
    result.proof_progress = float(metrics["verified_prefix_progress"])
    result.proof_quality_score = proof_quality_score(result, metrics)
    return result


def proof_quality_score(result: VerificationResult, metrics: dict[str, Any]) -> float:
    if result.passed:
        return 1.0

    weights = {
        "formal_wellformedness": 0.20,
        "verified_prefix_progress": 0.30,
        "goal_progress": 0.20,
        "premise_grounding": 0.15,
        "repairability": 0.15,
    }
    score = sum(float(metrics[name]) * weight for name, weight in weights.items())
    return round(max(0.0, min(0.95, score)), 4)


def proof_quality_metrics(
    result: VerificationResult,
    lean_code: str,
    profile: dict[str, bool],
) -> dict[str, Any]:
    prefix_progress = verified_prefix_progress(result, lean_code, profile)
    return {
        "formal_wellformedness": formal_wellformedness(lean_code),
        "verified_prefix_progress": prefix_progress,
        "goal_progress": goal_progress(result, profile, prefix_progress),
        "premise_grounding": premise_grounding(result, profile),
        "repairability": repairability(result, profile),
        "proof_plan_alignment": None,
        "proof_plan_alignment_available": False,
    }


def formal_wellformedness(lean_code: str) -> float:
    lowered = lean_code.lower()
    score = 0.0
    if re.search(r"^\s*import\s+", lean_code, flags=re.MULTILINE):
        score += 0.15
    if re.search(r"\btheorem\s+\w+", lean_code):
        score += 0.25
    if ":=" in lean_code:
        score += 0.20
    if re.search(r"\bbegin\b|\bby\b|\bexact\b|\bapply\b|\brw\b|\bsimp\b", lean_code):
        score += 0.20
    if not any(marker in lowered for marker in PLACEHOLDER_MARKERS):
        score += 0.20
    return round(min(1.0, score), 4)


def verified_prefix_progress(
    result: VerificationResult,
    lean_code: str,
    profile: dict[str, bool],
) -> float:
    if result.passed:
        return 1.0
    if not result.verifier_available or profile["placeholder"] or profile["missing_import"]:
        return 0.0

    first_error_line = _first_diagnostic_line(result.diagnostics)
    if first_error_line is not None:
        lines = lean_code.splitlines() or [lean_code]
        theorem_line = _theorem_line(lines)
        proof_span = max(1, len(lines) - theorem_line + 1)
        progressed = max(0, first_error_line - theorem_line)
        return round(max(0.0, min(0.95, progressed / proof_span)), 4)

    if profile["unsolved_goals"]:
        return 0.70
    if profile["type_error"]:
        return 0.45
    if profile["unknown_identifier"]:
        return 0.35
    if profile["parse_error"]:
        return 0.20
    if profile["timeout"]:
        return 0.20
    return 0.25


def goal_progress(
    result: VerificationResult,
    profile: dict[str, bool],
    prefix_progress: float,
) -> float:
    if result.passed:
        return 1.0
    if not result.verifier_available or profile["placeholder"]:
        return 0.0
    if profile["unsolved_goals"]:
        return 0.65
    if profile["type_error"]:
        return 0.35
    if profile["unknown_identifier"]:
        return 0.25
    if profile["parse_error"]:
        return 0.10
    if profile["timeout"]:
        return 0.20
    return round(prefix_progress * 0.5, 4)


def premise_grounding(result: VerificationResult, profile: dict[str, bool]) -> float:
    if result.passed:
        return 1.0
    if profile["missing_import"]:
        return 0.0
    if profile["unknown_identifier"]:
        return 0.20
    if not result.verifier_available:
        return 0.0
    return 0.80


def repairability(result: VerificationResult, profile: dict[str, bool]) -> float:
    if result.passed:
        return 1.0
    if not result.verifier_available:
        return 0.0
    if profile["placeholder"]:
        return 0.05
    if profile["unsolved_goals"]:
        return 0.75
    if profile["type_error"]:
        return 0.55
    if profile["unknown_identifier"]:
        return 0.45
    if profile["parse_error"]:
        return 0.25
    if profile["timeout"]:
        return 0.20
    return 0.35


def failure_profile(result: VerificationResult, lean_code: str) -> dict[str, bool]:
    text = f"{result.diagnostics}\n{lean_code}".lower()
    diagnostics = result.diagnostics.lower()
    placeholder = any(marker in lean_code.lower() for marker in PLACEHOLDER_MARKERS)
    timeout = "timed out" in diagnostics or "timeout" in diagnostics
    unknown_identifier = "unknown identifier" in diagnostics
    missing_import = "file not found" in diagnostics or "unknown module" in diagnostics
    parse_error = any(
        marker in diagnostics
        for marker in (
            "invalid expression",
            "parser",
            "parse",
            "unexpected token",
            "invalid '",
            "invalid declaration",
        )
    )
    type_error = any(
        marker in diagnostics
        for marker in (
            "type mismatch",
            "invalid application",
            "failed to synthesize",
            "application type mismatch",
            "tactic failed",
        )
    )
    unsolved_goals = "unsolved goals" in diagnostics or "goals unsolved" in diagnostics
    compilation_error = not result.passed and result.verifier_available and "error" in text

    return {
        "passed": result.passed,
        "verifier_unavailable": not result.verifier_available,
        "placeholder": placeholder,
        "timeout": timeout,
        "parse_error": parse_error,
        "type_error": type_error,
        "unknown_identifier": unknown_identifier,
        "missing_import": missing_import,
        "unsolved_goals": unsolved_goals,
        "compilation_error": compilation_error,
    }


def _first_diagnostic_line(diagnostics: str) -> int | None:
    line_numbers = [
        int(match.group(1))
        for match in re.finditer(r":(\d+):\d+:\s*(?:error|warning|information):", diagnostics)
    ]
    if line_numbers:
        return min(line_numbers)
    return None


def _theorem_line(lines: list[str]) -> int:
    for index, line in enumerate(lines, start=1):
        if re.search(r"\btheorem\s+\w+", line):
            return index
    return 1
