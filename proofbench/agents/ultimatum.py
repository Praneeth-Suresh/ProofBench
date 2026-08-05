from __future__ import annotations

import re
import time
from typing import Any

from proofbench.agents.base import AgentResult
from proofbench.agents.search_common import (
    ProofSearchCandidate,
    SearchStats,
    build_agent_result,
    check_candidate,
    generate_traced,
    select_best_candidate,
    theorem_prompt,
)
from proofbench.models.base import ChatModel
from proofbench.tasks.base import ProofTask
from proofbench.tools.lean_check import LeanCheckTool


_REPAIR_GUIDANCE = {
    "placeholder": (
        "Remove every sorry, admit, and placeholder. Replace it with a real "
        "term or tactic proof; do not merely rename the placeholder."
    ),
    "missing_import": (
        "Use only declarations available from the theorem's existing imports. "
        "Avoid adding imports unless the complete returned file can compile "
        "with them."
    ),
    "parse_error": (
        "Repair Lean 3 syntax first: balance delimiters, use valid tactic and "
        "calc syntax, and return one complete declaration."
    ),
    "type_error": (
        "Repair types and coercions explicitly. Inspect the expected type at "
        "the first error, add typed intermediate facts if needed, and use "
        "norm_num, ring, linarith, or exact only when their types fit."
    ),
    "unknown_identifier": (
        "Replace unknown names with imported lemmas or elementary tactics. "
        "Do not invent theorem names; simplify the proof if necessary."
    ),
    "unsolved_goals": (
        "Continue from the remaining goals. Close each goal explicitly with "
        "the smallest valid tactic sequence; preserve all preceding steps that "
        "already compile."
    ),
    "timeout": (
        "Reduce search and simplify the proof. Prefer a short deterministic "
        "tactic proof over expensive automation or broad simp sets."
    ),
    "compilation_error": (
        "Address the first compiler error only, then re-check the whole proof. "
        "Do not replace a useful verified prefix with an unrelated guess."
    ),
    "compiler_diagnostic": (
        "Use the exact diagnostic to make one minimal, compiler-testable repair."
    ),
}

_PROOF_MODES = (
    (
        "direct_tactic",
        "Try a short direct tactic proof first: norm_num, ring, linarith, nlinarith, simp, omega, or aesop only when the theorem's types and imports support it.",
    ),
    (
        "explicit_lemma_induction",
        "Use explicit intermediate facts, named imported lemmas, or induction when the theorem has recursive/natural-number structure. Make every type and coercion explicit.",
    ),
    (
        "arithmetic_normalization",
        "Expose the arithmetic identity with typed have statements, then normalize with norm_num, ring, ring_nf, linarith, or positivity as appropriate. Avoid opaque automation.",
    ),
    (
        "conservative_repair",
        "Prefer the smallest complete proof that can compile under the existing imports. Preserve the theorem header and avoid speculative theorem names or broad rewrites.",
    ),
)


def repair_class(candidate: ProofSearchCandidate) -> str:
    """Return the most actionable stable repair class for a failed candidate."""

    profile = candidate.verification.failure_profile
    for key in (
        "placeholder",
        "missing_import",
        "parse_error",
        "type_error",
        "unknown_identifier",
        "unsolved_goals",
        "timeout",
        "compilation_error",
    ):
        if profile.get(key, False):
            return key
    return "compiler_diagnostic"


class UltimatumLeanAgent:
    """A bounded generate, verify, repair, and preserve proof agent.

    The first calls explore different proof strategies. Once Lean has ranked
    them, every remaining call repairs the retained best candidate, preserving
    its theorem structure and any compiler-validated progress.
    """

    name = "ultimatum"

    def __init__(
        self,
        check_tool: LeanCheckTool,
        *,
        max_iters: int = 5,
        initial_candidates: int = 4,
        include_informal: bool = True,
    ):
        self.check_tool = check_tool
        self.max_iters = max(1, max_iters)
        # Reserve one call for compiler-guided repair whenever possible.
        exploration_budget = max(1, self.max_iters - 1)
        self.initial_candidates = max(1, min(initial_candidates, exploration_budget, len(_PROOF_MODES)))
        self.include_informal = include_informal

    def run(self, task: ProofTask, model: ChatModel) -> AgentResult:
        start = time.perf_counter()
        stats = SearchStats()
        trace: list[dict[str, Any]] = []
        candidates: list[ProofSearchCandidate] = []
        rejected_candidates: list[ProofSearchCandidate] = []
        base_prompt = theorem_prompt(
            task,
            include_informal=self.include_informal,
            method="Ultimatum compiler-guided proof repair",
        )

        for index in range(self.initial_candidates):
            mode_name, mode_guidance = _PROOF_MODES[index]
            response = generate_traced(
                model,
                (
                    f"{base_prompt}\n\n"
                    "Generate one complete proof using the assigned mode. The "
                    "candidate must compile as Lean 3 with the existing imports. "
                    "Return only Lean code; never return prose, sorry, admit, or "
                    "placeholder text.\n"
                    f"Proof mode: {mode_name}\n"
                    f"Mode guidance: {mode_guidance}\n"
                    f"Strategy candidate: {index + 1}"
                ),
                stats=stats,
                trace=trace,
                trace_type="model",
                metadata={"phase": "generate", "candidate": index + 1, "mode": mode_name},
            )
            candidate = check_candidate(
                task=task,
                check_tool=self.check_tool,
                raw_answer=response.text,
                label=f"candidate_{index + 1}",
                stats=stats,
                trace=trace,
                metadata={"phase": "verify", "source": f"candidate_{index + 1}"},
            )
            if _candidate_is_eligible(candidate):
                candidates.append(candidate)
            else:
                rejected_candidates.append(candidate)
                trace.append(
                    {
                        "type": "decision",
                        "phase": "reject",
                        "reason": "placeholder_candidate",
                        "candidate": candidate.label,
                    }
                )
            if candidate.passed:
                return self._result(task, candidate, trace, stats, start)

        best = select_best_candidate(candidates)
        # A placeholder may be used as transient repair context, but can never
        # enter the retained candidate list or the returned AgentResult.
        if best is None:
            best = select_best_candidate(rejected_candidates)
        for repair_index in range(self.max_iters - self.initial_candidates):
            if best is None or best.passed:
                break
            response = generate_traced(
                model,
                self._repair_prompt(base_prompt, best, repair_index),
                stats=stats,
                trace=trace,
                trace_type="model",
                metadata={
                    "phase": "repair",
                    "iteration": repair_index + 1,
                    "source": best.label,
                },
            )
            if not response.text.strip():
                trace.append(
                    {
                        "type": "decision",
                        "phase": "preserve",
                        "reason": "empty_model_response",
                        "preserved": best.label,
                    }
                )
                continue
            repaired = check_candidate(
                task=task,
                check_tool=self.check_tool,
                raw_answer=response.text,
                label=f"repair_{repair_index + 1}",
                stats=stats,
                trace=trace,
                metadata={
                    "phase": "verify_repair",
                    "iteration": repair_index + 1,
                    "source": best.label,
                },
            )
            if not _candidate_is_eligible(repaired):
                rejected_candidates.append(repaired)
                trace.append(
                    {
                        "type": "decision",
                        "phase": "reject",
                        "reason": "placeholder_candidate",
                        "candidate": repaired.label,
                    }
                )
                continue
            candidates.append(repaired)
            if repaired.passed:
                best = repaired
                break
            selected = select_best_candidate([best, repaired])
            if selected is not None:
                best = selected

        return self._result(task, best, trace, stats, start)

    @staticmethod
    def _repair_prompt(
        base_prompt: str,
        candidate: ProofSearchCandidate,
        repair_index: int,
    ) -> str:
        failure_class = repair_class(candidate)
        guidance = _REPAIR_GUIDANCE[failure_class]
        repair_mode, repair_mode_guidance = _PROOF_MODES[
            (repair_index + 1) % len(_PROOF_MODES)
        ]
        return (
            f"{base_prompt}\n\n"
            "Lean rejected the current proof. Repair it with the smallest safe "
            "change that preserves its already valid theorem structure and "
            "verified fragments. Address the first diagnostic directly. Do not "
            "use sorry, admit, placeholders, or informal prose. Return only "
            "the complete Lean code.\n\n"
            f"Repair iteration: {repair_index + 1}\n"
            f"Repair class: {failure_class}\n"
            f"Class guidance: {guidance}\n\n"
            f"Repair mode: {repair_mode}\n"
            f"Repair-mode guidance: {repair_mode_guidance}\n\n"
            "Structured proof state (preserve useful fields and repair only "
            "what the diagnostic requires):\n"
            f"candidate_label: {candidate.label}\n"
            f"passed: {candidate.verification.passed}\n"
            f"proof_completion: {candidate.verification.proof_completion}\n"
            f"verified_prefix_ratio: {candidate.verification.verified_prefix_ratio}\n"
            f"repairability_score: {candidate.verification.repairability_score}\n"
            f"current_candidate:\n{candidate.lean_code}\n\n"
            f"first_diagnostic_to_fix:\n{_first_diagnostic(candidate.verification.diagnostics)}\n\n"
            f"full_diagnostics (latest tail):\n{candidate.verification.diagnostics[-4000:]}"
        )

    def _result(
        self,
        task: ProofTask,
        best: ProofSearchCandidate | None,
        trace: list[dict[str, Any]],
        stats: SearchStats,
        start: float,
    ) -> AgentResult:
        if best is not None and not _candidate_is_eligible(best):
            best = None
        return build_agent_result(
            agent_name=self.name,
            task=task,
            best=best,
            trace=trace,
            stats=stats,
            start=start,
        )


def _first_diagnostic(diagnostics: str) -> str:
    """Extract the first actionable compiler message for targeted repair."""

    lines = [line.strip() for line in diagnostics.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if "error:" in line.lower():
            return "\n".join(lines[index : index + 2])[:1200]
    return (lines[0] if lines else "Lean rejected the candidate without a diagnostic.")[:1200]


def _candidate_is_eligible(candidate: ProofSearchCandidate) -> bool:
    """Keep placeholders out of the retained/final candidate set."""

    return not bool(re.search(r"\b(?:sorry|admit|placeholder)\b", candidate.lean_code, re.IGNORECASE))
