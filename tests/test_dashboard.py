import json
import tempfile
import base64
import unittest
from pathlib import Path

from proofbench.logging.dashboard import write_dashboard
from proofbench.logging.result_store import load_results, summarize


class DashboardTests(unittest.TestCase):
    def _sample_rows(self):
        return [
            {
                "agent": "llm_baseline",
                "task_id": "task_a",
                "split": "test",
                "proof_system": "lean3",
                "source_ref": "main",
                "source_urls": {},
                "model": "mock-fail",
                "accuracy": 0.0,
                "proof_quality_score": 0.25,
                "proof_progress": 0.2,
                "failure_profile": {"parse_error": True, "passed": False},
                "verification": {"verifier": "static", "verifier_available": True, "diagnostics": "", "passed": False, "elapsed_s": 0.01},
                "efficiency": {"model_calls": 1, "input_tokens": 10, "output_tokens": 5, "total_tokens": 15, "tool_calls": 0},
                "speed": {"agent_elapsed_s": 0.01, "model_latency_s": 0.01, "verification_elapsed_s": 0.01, "total_elapsed_s": 0.02},
                "raw_answer": "proof_1",
                "trace": [],
            },
            {
                "agent": "react",
                "task_id": "task_a",
                "split": "test",
                "proof_system": "lean3",
                "source_ref": "main",
                "source_urls": {},
                "model": "mock-fail",
                "accuracy": 0.0,
                "proof_quality_score": 0.55,
                "proof_progress": 0.5,
                "failure_profile": {"unsolved_goals": True, "passed": False},
                "verification": {"verifier": "static", "verifier_available": True, "diagnostics": "", "passed": False, "elapsed_s": 0.01},
                "efficiency": {"model_calls": 5, "input_tokens": 20, "output_tokens": 10, "total_tokens": 30, "tool_calls": 2},
                "speed": {"agent_elapsed_s": 0.02, "model_latency_s": 0.02, "verification_elapsed_s": 0.02, "total_elapsed_s": 0.04},
                "raw_answer": "proof_2",
                "trace": [],
            },
        ]

    def test_dashboard_includes_comparison_rows_and_summary(self):
        rows = self._sample_rows()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl = tmp / "run.jsonl"
            jsonl.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

            loaded = load_results([jsonl])
            self.assertEqual(len(loaded), 2)
            self.assertEqual(len({row["agent"] for row in loaded}), 2)

            dashboard_path = tmp / "dashboard.html"
            write_dashboard(loaded, dashboard_path)
            self.assertTrue(dashboard_path.exists())
            raw = dashboard_path.read_text(encoding="utf-8")
            encoded = raw.split("<script id=\"payload\" type=\"application/json\">", 1)[1].split("</script>", 1)[0].strip()
            payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
            self.assertEqual(len(payload["rows"]), 2)
            self.assertEqual(payload["rows"][0]["raw_answer"], "proof_1")
            self.assertIn("View output", raw)
            self.assertIn("LLM Output", raw)
            self.assertIn("Lean Diagnostics", raw)
            self.assertIn("Failure Profile", raw)
            summary = summarize(loaded)
            self.assertIn("llm_baseline", summary)
            self.assertIn("react", summary)
