from __future__ import annotations

import os
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from proofbench.evaluators.accuracy import PLACEHOLDER_MARKERS, VerificationResult, enrich_verification


class ProofVerifier:
    def __init__(self, *, mode: str = "auto", lean_root: Path | None = None, timeout_s: int = 30):
        self.mode = mode
        self.lean_root = lean_root
        self.timeout_s = timeout_s

    def verify(self, lean_code: str) -> VerificationResult:
        if self.mode == "static":
            return self._static_check(lean_code)
        if self.mode == "lean":
            return self._lean_check(lean_code)
        if self._lean_command() and self.lean_root:
            return self._lean_check(lean_code)
        start = time.perf_counter()
        return self._result(
            lean_code,
            passed=False,
            verifier="auto",
            verifier_available=False,
            diagnostics=(
                "Lean verifier unavailable. Install/configure miniF2F Lean and rerun "
                "with the Lean compiler verifier and a /path/to/miniF2F/lean root. "
                "No proof-correctness credit was assigned."
            ),
            elapsed_s=time.perf_counter() - start,
        )

    def _static_check(self, lean_code: str) -> VerificationResult:
        start = time.perf_counter()
        lowered = lean_code.lower()
        has_placeholder = any(marker in lowered for marker in PLACEHOLDER_MARKERS)
        has_theorem = "theorem " in lean_code and ":=" in lean_code
        passed = has_theorem and not has_placeholder
        return self._result(
            lean_code,
            passed=passed,
            verifier="static",
            verifier_available=True,
            diagnostics=(
                "Static smoke check only; this is not proof-assistant grading. "
                f"has_theorem={has_theorem}; has_placeholder={has_placeholder}"
            ),
            elapsed_s=time.perf_counter() - start,
        )

    def _lean_check(self, lean_code: str) -> VerificationResult:
        start = time.perf_counter()
        lean_cmd = self._lean_command()
        if not lean_cmd:
            return self._result(
                lean_code,
                passed=False,
                verifier="lean",
                verifier_available=False,
                diagnostics="Could not find `lean` (`lake env lean` not available either).",
                elapsed_s=time.perf_counter() - start,
            )
        if not self.lean_root:
            return self._result(
                lean_code,
                passed=False,
                verifier="lean",
                verifier_available=False,
                diagnostics=(
                    "A Lean root is required. Enter it at the ProofBench prompt "
                    "or set PROOFBENCH_MINIF2F_LEAN_ROOT to the miniF2F checkout root."
                ),
                elapsed_s=time.perf_counter() - start,
            )
        if any(marker in lean_code.lower() for marker in PLACEHOLDER_MARKERS):
            return self._result(
                lean_code,
                passed=False,
                verifier="lean",
                verifier_available=True,
                diagnostics="Rejected before compilation because the proof contains sorry/admit.",
                elapsed_s=time.perf_counter() - start,
            )

        lean_path_dirs = self._lean_path_dirs(lean_cmd)
        env = os.environ.copy()
        lean_path = os.pathsep.join(str(path) for path in lean_path_dirs)
        if existing := env.get("LEAN_PATH"):
            env["LEAN_PATH"] = f"{lean_path}{os.pathsep}{existing}"
        else:
            env["LEAN_PATH"] = lean_path
        with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False, encoding="utf-8") as tmp:
            tmp.write(lean_code)
            tmp_path = Path(tmp.name)
        try:
            completed = subprocess.run(
                [*lean_cmd, "--make", str(tmp_path)],
                cwd=str(self.lean_root),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=self.timeout_s,
                check=False,
            )
            return self._result(
                lean_code,
                passed=completed.returncode == 0,
                verifier="lean",
                verifier_available=True,
                diagnostics=completed.stdout[-4000:] or "Lean accepted the proof.",
                elapsed_s=time.perf_counter() - start,
            )
        except subprocess.TimeoutExpired:
            return self._result(
                lean_code,
                passed=False,
                verifier="lean",
                verifier_available=True,
                diagnostics=f"Lean timed out after {self.timeout_s}s.",
                elapsed_s=time.perf_counter() - start,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    def _result(
        self,
        lean_code: str,
        *,
        passed: bool,
        verifier: str,
        verifier_available: bool,
        diagnostics: str,
        elapsed_s: float,
    ) -> VerificationResult:
        return enrich_verification(
            VerificationResult(
                passed=passed,
                verifier=verifier,
                verifier_available=verifier_available,
                diagnostics=diagnostics,
                elapsed_s=elapsed_s,
            ),
            lean_code,
        )

    def _lean_src_dir(self) -> Path:
        assert self.lean_root is not None
        if (self.lean_root / "src" / "minif2f_import.lean").exists():
            return self.lean_root / "src"
        if (self.lean_root / "lean" / "src" / "minif2f_import.lean").exists():
            return self.lean_root / "lean" / "src"
        return self.lean_root / "src"

    def _lean_path_dirs(self, lean_cmd: list[str]) -> list[Path]:
        assert self.lean_root is not None
        paths = self._lean_reported_paths(lean_cmd)
        lean_src = self._lean_src_dir()
        if paths:
            if lean_src not in paths:
                paths.append(lean_src)
            return paths
        leanpkg_path = self.lean_root / "leanpkg.path"
        if not leanpkg_path.exists():
            return [self._lean_src_dir()]
        paths = []
        for raw_line in leanpkg_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line.startswith("path "):
                continue
            raw_path = line.split(" ", 1)[1].strip()
            path = Path(raw_path)
            paths.append(path if path.is_absolute() else self.lean_root / path)
        return paths or [self._lean_src_dir()]

    def _lean_reported_paths(self, lean_cmd: list[str]) -> list[Path]:
        assert self.lean_root is not None
        env = os.environ.copy()
        env.pop("LEAN_PATH", None)
        try:
            completed = subprocess.run(
                [*lean_cmd, "--path"],
                cwd=str(self.lean_root),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=10,
                check=False,
            )
            if completed.returncode != 0:
                return []
            data = json.loads(completed.stdout)
        except Exception:
            return []
        return [Path(path) for path in data.get("path", [])]

    def _lean_command(self) -> list[str] | None:
        override = os.getenv("PROOFBENCH_LEAN_EXE")
        if override:
            candidate = Path(override).expanduser()
            if candidate.is_file():
                return [str(candidate)]
        if lean_exe := shutil.which("lean"):
            return [lean_exe]
        if lake_exe := shutil.which("lake"):
            return [lake_exe, "env", "lean"]
        return _lean_command_fallback()


def _lean_command_fallback() -> list[str] | None:
    home_lean = Path.home() / ".elan" / "bin" / "lean"
    if home_lean.is_file():
        return [str(home_lean)]

    toolchains = Path.home() / ".elan" / "toolchains"
    if toolchains.is_dir():
        for toolchain_dir in sorted(toolchains.iterdir(), reverse=True):
            candidate = toolchain_dir / "bin" / "lean"
            if candidate.is_file():
                return [str(candidate)]

    try:
        elan_path = shutil.which("elan")
        if elan_path:
            completed = subprocess.run(
                [elan_path, "which", "lean"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=10,
                check=False,
            )
            if completed.returncode == 0:
                candidate = Path(completed.stdout.strip().splitlines()[-1])
                if candidate.is_file():
                    return [str(candidate)]
    except Exception:
        return None
    return None
