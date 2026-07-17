import unittest

from proofbench.evaluators.accuracy import VerificationResult, enrich_verification


class EvaluationMetricTests(unittest.TestCase):
    def test_success_and_completion_are_full_for_accepted_proof(self):
        result = enrich_verification(
            VerificationResult(
                passed=True,
                verifier="lean",
                verifier_available=True,
                diagnostics="Lean accepted the proof.",
                elapsed_s=0.01,
            ),
            "import minif2f_import\n\ntheorem sample : True := by trivial",
        )

        self.assertEqual(result.success_score, 1.0)
        self.assertEqual(result.proof_completion, 1.0)
        self.assertEqual(result.verified_prefix_ratio, 1.0)
        self.assertEqual(result.repairability_score, 1.0)
        self.assertEqual(result.completion_metrics["completion_basis"], "lean_accepted")

    def test_completion_uses_verified_prefix_for_failed_lean_proof(self):
        result = enrich_verification(
            VerificationResult(
                passed=False,
                verifier="lean",
                verifier_available=True,
                diagnostics="/tmp/proof.lean:5:2: error: unsolved goals",
                elapsed_s=0.01,
            ),
            "\n".join(
                [
                    "import minif2f_import",
                    "",
                    "theorem sample : True :=",
                    "begin",
                    "  exact trivial",
                    "end",
                ]
            ),
        )

        self.assertEqual(result.success_score, 0.0)
        self.assertGreater(result.proof_completion, 0.0)
        self.assertLess(result.proof_completion, 1.0)
        self.assertEqual(result.completion_metrics["completion_basis"], "verified_prefix")

    def test_unavailable_verifier_has_no_proof_completion_credit(self):
        result = enrich_verification(
            VerificationResult(
                passed=False,
                verifier="auto",
                verifier_available=False,
                diagnostics="Lean verifier unavailable.",
                elapsed_s=0.01,
            ),
            "theorem sample : True := by trivial",
        )

        self.assertEqual(result.success_score, 0.0)
        self.assertEqual(result.proof_completion, 0.0)
        self.assertEqual(result.verified_prefix_ratio, 0.0)
        self.assertEqual(result.repairability_score, 0.0)
        self.assertEqual(result.completion_metrics["completion_basis"], "verifier_unavailable")


if __name__ == "__main__":
    unittest.main()
