from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from proofbench.config import DEFAULT_TASK_IDS, ProofBenchConfig
from proofbench.tasks.base import ProofTask
from proofbench.tasks.minif2f import MiniF2FRetrievalError, MiniF2FRepository
from proofbench.tasks.registry import resolve_task_ids


def run_preflight(
    config: ProofBenchConfig,
    task_ids: list[str] | None = None,
    require_lean: bool = True,
) -> int:
    tasks = resolve_task_ids(task_ids or list(DEFAULT_TASK_IDS))
    _check_tasks(config, tasks)
    if require_lean:
        _check_lean(config)
    print("Preflight checks passed.")
    return 0


def _check_tasks(config: ProofBenchConfig, task_ids: list[str]) -> None:
    print("Checking tasks...")
    repo = MiniF2FRepository(config)
    tasks: list[ProofTask] = []
    for task_id in task_ids:
        try:
            tasks.append(repo.load_task(task_id))
        except MiniF2FRetrievalError as exc:
            _fail(f"Task '{task_id}' is not available: {exc}")
    if not tasks:
        _fail("No tasks loaded; expected at least one test task.")


def _check_lean(config: ProofBenchConfig) -> None:
    print("Checking Lean availability...")
    lean_command = _lean_command()
    if not lean_command:
        _fail("Lean executable not found. Install Lean via elan and retry.")

    version = subprocess.run(
        [*lean_command, "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
        check=False,
    )
    if version.returncode != 0:
        _fail(f"Lean command {lean_command[0]} but `lean --version` failed: {version.stdout.strip()}")

    lean_root = config.lean_root
    if lean_root is None:
        _fail(
            "Lean root not set. Set PROOFBENCH_MINIF2F_LEAN_ROOT or use --lean-root "
            "when running preflight with Lean checks enabled."
        )
    if not lean_root.exists():
        _fail(f"Lean root path does not exist: {lean_root}")

    # miniF2F checkout root variants:
    # 1) .../miniF2F (lean files in ./lean/src)
    # 2) .../lean (legacy layout)
    if not (lean_root / "lean" / "src" / "minif2f_import.lean").exists() and not (
        lean_root / "src" / "minif2f_import.lean"
    ).exists():
        _fail(
            f"Could not find minif2f_import.lean under {lean_root}/lean/src or {lean_root}/src. "
            "Point Lean root at the miniF2F checkout root."
        )


def _lean_command() -> list[str] | None:
    override = os.getenv("PROOFBENCH_LEAN_EXE")
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file():
            return [str(candidate)]
    if lean_path := shutil.which("lean"):
        return [lean_path]
    if lake_path := shutil.which("lake"):
        return [lake_path, "env", "lean"]

    home_lean = Path.home() / ".elan" / "bin" / "lean"
    if home_lean.is_file():
        return [str(home_lean)]

    toolchains = Path.home() / ".elan" / "toolchains"
    if toolchains.is_dir():
        for toolchain_dir in sorted(toolchains.iterdir(), reverse=True):
            candidate = toolchain_dir / "bin" / "lean"
            if candidate.is_file():
                return [str(candidate)]

    elan_path = shutil.which("elan")
    if elan_path:
        try:
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


def _fail(message: str) -> None:
    print(f"Preflight failed: {message}", file=sys.stderr)
    raise SystemExit(1)
