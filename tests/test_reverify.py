import tempfile
import unittest
from pathlib import Path

from proofbench.cli import _reverify_rows
from proofbench.config import ProofBenchConfig
from proofbench.evaluators.lean import ProofVerifier
from proofbench.logging.result_store import ResultStore, load_results


class ReverifyTests(unittest.TestCase):
    def test_reverify_rows_uses_existing_raw_answer_without_model_calls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mini = root / "miniF2F"
            (mini / "lean" / "src").mkdir(parents=True)
            (mini / "lean" / "src" / "test.lean").write_text(
                "theorem sample_task : True :=\nby trivial\n",
                encoding="utf-8",
            )
            results = root / "results"
            config = ProofBenchConfig(
                minif2f_local=mini,
                lean_root=mini,
                results_dir=results,
            )
            store = ResultStore(results)
            original = {
                "created_at": "2026-07-10T00:00:00+00:00",
                "agent": "llm_baseline",
                "task_id": "sample_task",
                "split": "test",
                "proof_system": "lean3",
                "source_ref": "main",
                "source_urls": {},
                "model": "gemini-test",
                "accuracy": 0.0,
                "raw_answer": "```lean\nby trivial\n```",
                "trace": [],
                "efficiency": {
                    "model_calls": 1,
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                    "tool_calls": 0,
                },
                "speed": {"agent_elapsed_s": 2.0, "model_latency_s": 1.0},
            }

            rows = _reverify_rows(
                [original],
                config=config,
                verifier=ProofVerifier(mode="static", lean_root=mini),
                store=store,
            )

            self.assertEqual(rows[0]["model"], "gemini-test")
            self.assertTrue(rows[0]["reverified_without_model_calls"])
            self.assertEqual(rows[0]["efficiency"]["model_calls"], 1)
            self.assertTrue(rows[0]["solved"])
            self.assertEqual(rows[0]["success_score"], 1.0)
            self.assertEqual(rows[0]["proof_completion"], 1.0)
            self.assertNotIn("accuracy", rows[0])
            self.assertEqual(len(load_results([store.path])), 1)

    def test_reverify_rows_recovers_candidate_from_trace_when_raw_answer_is_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mini = root / "miniF2F"
            (mini / "lean" / "src").mkdir(parents=True)
            (mini / "lean" / "src" / "test.lean").write_text(
                "theorem sample_task : True :=\nby trivial\n",
                encoding="utf-8",
            )
            results = root / "results"
            config = ProofBenchConfig(
                minif2f_local=mini,
                lean_root=mini,
                results_dir=results,
            )
            store = ResultStore(results)
            original = {
                "created_at": "2026-07-10T00:00:00+00:00",
                "agent": "react",
                "task_id": "sample_task",
                "split": "test",
                "proof_system": "lean3",
                "source_ref": "main",
                "source_urls": {},
                "model": "gemini-test",
                "accuracy": 0.0,
                "raw_answer": "",
                "trace": [{"type": "model", "response": "ACTION: check\n```lean\nby trivial\n```"}],
                "efficiency": {
                    "model_calls": 1,
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                    "tool_calls": 1,
                },
                "speed": {"agent_elapsed_s": 2.0, "model_latency_s": 1.0},
            }

            rows = _reverify_rows(
                [original],
                config=config,
                verifier=ProofVerifier(mode="static", lean_root=mini),
                store=store,
            )

            self.assertIn("by trivial", rows[0]["raw_answer"])
            self.assertTrue(rows[0]["solved"])
            self.assertEqual(rows[0]["success_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
