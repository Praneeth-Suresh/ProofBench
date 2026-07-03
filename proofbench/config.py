from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parents[1]


DEFAULT_TASK_IDS = (
    "algebra_9onxpypzleqsum2onxpy",
    "aime_1988_p8",
    "numbertheory_exk2powkeqapb2mulbpa2_aeq1",
)


@dataclass(frozen=True)
class ProofBenchConfig:
    root: Path = PROJECT_ROOT
    cache_dir: Path = PROJECT_ROOT / ".cache"
    results_dir: Path = PROJECT_ROOT / "results"
    minif2f_repo: str = "facebookresearch/miniF2F"
    minif2f_ref: str = "main"
    minif2f_local: Path | None = None
    lean_root: Path | None = None

    @classmethod
    def from_env(
        cls,
        *,
        minif2f_ref: str | None = None,
        minif2f_local: str | None = None,
        lean_root: str | None = None,
        results_dir: str | None = None,
    ) -> "ProofBenchConfig":
        local = minif2f_local or os.getenv("PROOFBENCH_MINIF2F_LOCAL")
        lean = lean_root or os.getenv("PROOFBENCH_MINIF2F_LEAN_ROOT")
        results = results_dir or os.getenv("PROOFBENCH_RESULTS_DIR")
        return cls(
            minif2f_ref=minif2f_ref or os.getenv("PROOFBENCH_MINIF2F_REF", "main"),
            minif2f_local=Path(local).expanduser().resolve() if local else None,
            lean_root=Path(lean).expanduser().resolve() if lean else None,
            results_dir=_resolve_results_dir(results),
        )


_TIMESTAMP = "%Y%m%dT%H%M%SZ"


def _run_dir_like(name: str) -> bool:
    return bool(re.fullmatch(r"run_\d{8}T\d{6}Z(?:_[A-Za-z0-9._-]+)?", name))


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]", "_", value.strip())
    slug = slug.strip("._-")
    return slug or "run"


def _resolve_results_dir(results_dir: str | None) -> Path:
    if not results_dir:
        return PROJECT_ROOT / "results"

    raw = results_dir.strip()
    if not raw:
        return PROJECT_ROOT / "results"

    candidate = Path(raw).expanduser()

    # Keep explicit multi-segment paths (e.g. "results/run_x", "../scratch/results") as-is.
    if not candidate.is_absolute() and candidate.parent != Path("."):
        return (PROJECT_ROOT / candidate).resolve()

    token = _safe_slug(str(candidate))
    if token in {"results", "result", "run", ".", ".."}:
        return PROJECT_ROOT / "results"

    stamp = datetime.now(timezone.utc).strftime(_TIMESTAMP)
    if _run_dir_like(token):
        return PROJECT_ROOT / "results" / token

    return PROJECT_ROOT / "results" / f"run_{stamp}_{token}"
