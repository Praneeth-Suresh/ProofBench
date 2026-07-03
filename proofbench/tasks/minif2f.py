from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from proofbench.config import ProofBenchConfig
from proofbench.tasks.base import ProofTask


class MiniF2FRetrievalError(RuntimeError):
    pass


class MiniF2FRepository:
    """Runtime loader for miniF2F statements.

    The benchmark content is not vendored into ProofBench. It is loaded from a
    local miniF2F checkout when configured, otherwise fetched from GitHub raw
    URLs and cached for reproducibility.
    """

    def __init__(self, config: ProofBenchConfig):
        self.config = config
        self.cache_dir = config.cache_dir / "minif2f" / config.minif2f_ref
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load_task(self, task_id: str, *, split: str = "test") -> ProofTask:
        lean_source = self._read_text(
            relative_path=f"lean/src/{split}.lean",
            cache_name=f"lean_src_{split}.lean",
        )
        formal_statement = extract_theorem_statement(lean_source, task_id)
        informal = self._read_informal(task_id, split=split)
        urls = {
            "lean": self.raw_url(f"lean/src/{split}.lean"),
            "informal": self.raw_url(f"informal/{split}/{task_id}.json"),
        }
        return ProofTask(
            task_id=task_id,
            split=split,
            proof_system="lean3",
            source_ref=self.config.minif2f_ref,
            formal_statement=formal_statement,
            informal_statement=informal,
            source_urls=urls,
        )

    def raw_url(self, relative_path: str) -> str:
        return (
            "https://raw.githubusercontent.com/"
            f"{self.config.minif2f_repo}/{self.config.minif2f_ref}/{relative_path}"
        )

    def _read_informal(self, task_id: str, *, split: str) -> str | None:
        try:
            raw = self._read_text(
                relative_path=f"informal/{split}/{task_id}.json",
                cache_name=f"informal_{split}_{task_id}.json",
            )
        except MiniF2FRetrievalError:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data.get("informal_statement")

    def _read_text(self, *, relative_path: str, cache_name: str) -> str:
        if self.config.minif2f_local:
            path = self.config.minif2f_local / relative_path
            if not path.exists():
                raise MiniF2FRetrievalError(f"Missing miniF2F file: {path}")
            return path.read_text(encoding="utf-8")

        cached = self.cache_dir / cache_name
        if cached.exists():
            return cached.read_text(encoding="utf-8")

        url = self.raw_url(relative_path)
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                text = response.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - network-dependent
            raise MiniF2FRetrievalError(f"Could not retrieve {url}: {exc}") from exc
        cached.write_text(text, encoding="utf-8")
        return text


def extract_theorem_statement(lean_source: str, theorem_id: str) -> str:
    pattern = re.compile(
        rf"^theorem\s+{re.escape(theorem_id)}\b.*?(?=^theorem\s+\w|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(lean_source)
    if not match:
        raise MiniF2FRetrievalError(f"Theorem {theorem_id!r} was not found.")
    block = match.group(0).strip()
    if ":=" not in block:
        raise MiniF2FRetrievalError(f"Theorem {theorem_id!r} has no proof delimiter.")
    header = block.split(":=", 1)[0].rstrip()
    return f"{header} :=\nbegin\n  sorry\nend"


def extract_candidate_lean(task: ProofTask, raw_answer: str) -> str:
    answer = _strip_code_fence(raw_answer).strip()
    theorem_match = re.search(
        rf"theorem\s+{re.escape(task.task_id)}\b.*",
        answer,
        flags=re.DOTALL,
    )
    if theorem_match:
        return _ensure_import(theorem_match.group(0).strip())

    header = task.formal_statement.split(":=", 1)[0].rstrip()
    if answer.startswith("begin") or answer.startswith("by "):
        candidate = f"{header} :=\n{answer}"
    else:
        candidate = f"{header} :=\nbegin\n{answer}\nend"
    return _ensure_import(candidate)


def _strip_code_fence(text: str) -> str:
    fence = re.search(r"```(?:lean)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return fence.group(1) if fence else text


def _ensure_import(lean_code: str) -> str:
    if re.search(r"^\s*import\s+", lean_code, flags=re.MULTILINE):
        return lean_code
    return (
        "import minif2f_import\n\n"
        "open_locale big_operators\n"
        "open_locale nat\n"
        "open_locale real\n"
        "open_locale rat\n\n"
        f"{lean_code}"
    )

