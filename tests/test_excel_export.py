import tempfile
import unittest
import zipfile
from pathlib import Path

from proofbench.logging.excel_export import write_excel


class ExcelExportTests(unittest.TestCase):
    def test_write_excel_creates_summary_and_rows_sheets(self):
        rows = [
            {
                "created_at": "2026-07-10T00:00:00+00:00",
                "agent": "self_consistency",
                "task_id": "task_a",
                "split": "test",
                "proof_system": "lean3",
                "model": "mock",
                "metric_validity": "lean",
                "solved": True,
                "success_score": 1.0,
                "proof_completion": 1.0,
                "verified_prefix_ratio": 1.0,
                "repairability_score": 1.0,
                "failure_profile": {"passed": True},
                "verification": {"verifier": "static", "verifier_available": True},
                "efficiency": {
                    "model_calls": 3,
                    "input_tokens": 12,
                    "output_tokens": 8,
                    "total_tokens": 20,
                    "tool_calls": 3,
                },
                "speed": {
                    "agent_elapsed_s": 0.01,
                    "model_latency_s": 0.0,
                    "verification_elapsed_s": 0.01,
                    "total_elapsed_s": 0.02,
                },
            }
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "proofbench-results.xlsx"

            write_excel(rows, output)

            self.assertTrue(output.exists())
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                self.assertIn("xl/workbook.xml", names)
                self.assertIn("xl/worksheets/sheet1.xml", names)
                self.assertIn("xl/worksheets/sheet2.xml", names)
                summary = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
                details = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")
                self.assertIn("self_consistency", summary)
                self.assertIn("success_rate", summary)
                self.assertIn("proof_completion", details)
                self.assertIn("task_a", details)


if __name__ == "__main__":
    unittest.main()
