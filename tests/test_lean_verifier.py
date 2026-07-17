import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from proofbench.evaluators.lean import ProofVerifier


class LeanVerifierTests(unittest.TestCase):
    def test_lean_check_sets_lean_path_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / "src"
            src.mkdir()
            (src / "minif2f_import.lean").write_text("", encoding="utf-8")
            verifier = ProofVerifier(mode="lean", lean_root=root)

            captured = {}

            def fake_run(*args, **kwargs):
                if args[0][-1] == "--path":
                    return type(
                        "Completed",
                        (),
                        {
                            "returncode": 0,
                            "stdout": json.dumps({"path": ["/lean/library"]}),
                        },
                    )()
                captured["env"] = kwargs["env"]
                return type("Completed", (), {"returncode": 0, "stdout": ""})()

            with patch.dict(os.environ, {"LEAN_PATH": ""}, clear=False):
                with patch.object(verifier, "_lean_command", return_value=["lean"]):
                    with patch("proofbench.evaluators.lean.subprocess.run", side_effect=fake_run):
                        result = verifier.verify("import minif2f_import\n\ntheorem sample : True := by trivial")

            self.assertTrue(result.passed)
            self.assertEqual(captured["env"]["LEAN_PATH"], os.pathsep.join(["/lean/library", str(src)]))

    def test_lean_check_uses_leanpkg_path_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "lean" / "src").mkdir(parents=True)
            (root / "_target" / "deps" / "mathlib" / "src").mkdir(parents=True)
            (root / "lean" / "src" / "minif2f_import.lean").write_text("", encoding="utf-8")
            (root / "leanpkg.path").write_text(
                "builtin_path\npath _target/deps/mathlib/src\npath ./lean/src\n",
                encoding="utf-8",
            )
            verifier = ProofVerifier(mode="lean", lean_root=root)

            captured = {}

            def fake_run(*args, **kwargs):
                if args[0][-1] == "--path":
                    return type(
                        "Completed",
                        (),
                        {
                            "returncode": 0,
                            "stdout": json.dumps(
                                {
                                    "path": [
                                        "/lean/library",
                                        str(root / "_target" / "deps" / "mathlib" / "src"),
                                        str(root / "lean" / "src"),
                                    ]
                                }
                            ),
                        },
                    )()
                captured["env"] = kwargs["env"]
                return type("Completed", (), {"returncode": 0, "stdout": ""})()

            with patch.dict(os.environ, {"LEAN_PATH": ""}, clear=False):
                with patch.object(verifier, "_lean_command", return_value=["lean"]):
                    with patch("proofbench.evaluators.lean.subprocess.run", side_effect=fake_run):
                        verifier.verify("import minif2f_import\n\ntheorem sample : True := by trivial")

            expected = os.pathsep.join(
                [
                    "/lean/library",
                    str(root / "_target" / "deps" / "mathlib" / "src"),
                    str(root / "lean" / "src"),
                ]
            )
            self.assertEqual(captured["env"]["LEAN_PATH"], expected)


if __name__ == "__main__":
    unittest.main()
