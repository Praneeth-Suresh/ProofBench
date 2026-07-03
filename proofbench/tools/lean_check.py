from __future__ import annotations

from proofbench.evaluators.accuracy import VerificationResult
from proofbench.evaluators.lean import ProofVerifier
from proofbench.tasks.base import ProofTask


class LeanCheckTool:
    name = "lean_check"

    def __init__(self, verifier: ProofVerifier):
        self.verifier = verifier

    def run(self, task: ProofTask, lean_code: str) -> VerificationResult:
        _ = task
        return self.verifier.verify(lean_code)

