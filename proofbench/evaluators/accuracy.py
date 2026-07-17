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
    success_score: float = 0.0
    proof_completion: float = 0.0
    verified_prefix_ratio: float = 0.0
    repairability_score: float = 0.0
    failure_profile: dict[str, bool] = field(default_factory=dict)
    completion_metrics: dict[str, Any] = field(default_factory=dict)


def success_score(result: VerificationResult) -> float:
    return 1.0 if result.passed else 0.0


def accuracy_score(result: VerificationResult) -> float:
    """Legacy alias for older callers; new result rows use success_score."""

    return success_score(result)


def enrich_verification(result: VerificationResult, lean_code: str) -> VerificationResult:
    """Attach verifier-grounded success and proof-completion signals."""

    profile = failure_profile(result, lean_code)
    metrics = completion_metrics(result, lean_code, profile)
    result.failure_profile = profile
    result.completion_metrics = metrics
    result.success_score = success_score(result)
    result.verified_prefix_ratio = float(metrics["verified_prefix_ratio"])
    result.proof_completion = proof_completion(result, metrics, profile)
    result.repairability_score = repairability_score(result, profile)
    return result


def proof_completion(
    result: VerificationResult,
    metrics: dict[str, Any],
    profile: dict[str, bool],
) -> float:
    """Estimate completed formal proof work from compiler-grounded signals.

    Lean acceptance is the only proof of full completion. For failed proofs this
    is a conservative progress estimate based on the verified prefix and failure
    class, not a claim of partial mathematical correctness.
    """

    if result.passed:
        return 1.0
    if not result.verifier_available or profile["placeholder"] or profile["missing_import"]:
        return 0.0

    prefix = float(metrics["verified_prefix_ratio"])
    floor = float(metrics["diagnostic_completion_floor"])
    structure = float(metrics["formal_structure_score"])
    completion = max(prefix, floor * structure)
    return round(max(0.0, min(0.95, completion)), 4)


def completion_metrics(
    result: VerificationResult,
    lean_code: str,
    profile: dict[str, bool],
) -> dict[str, Any]:
    prefix_ratio = verified_prefix_ratio(result, lean_code, profile)
    return {
        "formal_structure_score": formal_structure_score(lean_code),
        "verified_prefix_ratio": prefix_ratio,
        "diagnostic_completion_floor": diagnostic_completion_floor(result, profile),
        "repairability_score": repairability_score(result, profile),
        "completion_basis": completion_basis(result, profile, prefix_ratio),
    }


def formal_structure_score(lean_code: str) -> float:
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


def verified_prefix_ratio(
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


def diagnostic_completion_floor(
    result: VerificationResult,
    profile: dict[str, bool],
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
    return 0.25


def repairability_score(result: VerificationResult, profile: dict[str, bool]) -> float:
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


def completion_basis(
    result: VerificationResult,
    profile: dict[str, bool],
    prefix_ratio: float,
) -> str:
    if result.passed:
        return "lean_accepted"
    if not result.verifier_available:
        return "verifier_unavailable"
    if profile["placeholder"]:
        return "placeholder_rejected"
    if profile["missing_import"]:
        return "missing_import"
    if prefix_ratio > 0.0:
        return "verified_prefix"
    for key in (
        "unsolved_goals",
        "type_error",
        "unknown_identifier",
        "parse_error",
        "timeout",
        "compilation_error",
    ):
        if profile[key]:
            return key
    return "compiler_diagnostic"


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
