import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from proofbench.config import ProofBenchConfig
from proofbench.preflight import run_preflight


class PreflightTests(unittest.TestCase):
    def _mock_repo(self, *, config, task_ids=("a",)):
        with patch("proofbench.preflight.MiniF2FRepository") as repo_cls:
            repo = MagicMock()
            repo.load_task.return_value = MagicMock()
            repo_cls.return_value = repo
            return run_preflight(config, task_ids=list(task_ids), require_lean=False)

    def test_preflight_without_lean_passes_when_skipped(self):
        config = ProofBenchConfig()
        result = self._mock_repo(config=config, task_ids=("x", "y"))
        self.assertEqual(result, 0)

    @patch("proofbench.preflight.subprocess.run")
    @patch("proofbench.preflight.shutil.which", return_value="/usr/bin/lean")
    @patch("proofbench.preflight.resolve_task_ids", return_value=["x"])
    @patch("proofbench.preflight.MiniF2FRepository")
    def test_preflight_fails_without_lean_root(
        self,
        repo_cls,
        _resolved_ids,
        _which,
        _run,
    ):
        repo_cls.return_value.load_task.return_value = MagicMock()
        _run.return_value = subprocess.CompletedProcess(["lean"], 0, stdout="lean 4")

        with self.assertRaises(SystemExit):
            run_preflight(ProofBenchConfig(), require_lean=True)

    @patch("proofbench.preflight.subprocess.run")
    @patch("proofbench.preflight.shutil.which", return_value="/usr/bin/lean")
    @patch("proofbench.preflight.resolve_task_ids", return_value=["x"])
    @patch("proofbench.preflight.MiniF2FRepository")
    def test_preflight_passes_with_lean_root(
        self,
        repo_cls,
        _resolved_ids,
        _which,
        _run,
    ):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "minif2f_import.lean").write_text("", encoding="utf-8")
            repo_cls.return_value.load_task.return_value = MagicMock()
            _run.return_value = subprocess.CompletedProcess(["lean"], 0, stdout="lean 4")
            config = ProofBenchConfig(lean_root=root)
            result = run_preflight(config, task_ids=["x"], require_lean=True)
            self.assertEqual(result, 0)
