from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from proofbench.agents.registry import create_agents, registered_agent_names
from proofbench.config import DEFAULT_TASK_IDS, ProofBenchConfig
from proofbench.evaluators.lean import ProofVerifier
from proofbench.evaluators.runner import EvaluationRunner
from proofbench.logging.dashboard import write_dashboard
from proofbench.logging.result_store import ResultStore, load_results, summarize
from proofbench.preflight import run_preflight
from proofbench.models.registry import create_model
from proofbench.tasks.registry import load_tasks, resolve_task_ids
from proofbench.tools.lean_check import LeanCheckTool


AGENT_LABELS = {
    "llm_baseline": "LLM baseline",
    "react": "ReAct Lean-checking agent",
}
DEFAULT_RAPID_AGENTS = "llm_baseline,react"

MODEL_PROVIDER_OPTIONS = [
    ("gemini", "Gemini API: real free-tier-friendly provider"),
    ("mock", "Mock model: local smoke test, no API key"),
    ("mock-react", "Mock ReAct model: exercises tool-call plumbing"),
]

VERIFIER_OPTIONS = [
    ("auto", "Auto: use Lean if configured, otherwise assign no proof credit"),
    ("lean", "Lean compiler: real proof-assistant grading"),
    ("static", "Static smoke check: not proof correctness"),
]


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(prog="proofbench")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run agents on miniF2F tasks.")
    run_p.add_argument(
        "--advanced",
        action="store_true",
        help="Use the full setup prompt instead of the two-question rapid path.",
    )

    pre_p = sub.add_parser("preflight", help="Verify tasks and Lean before a benchmark run.")
    pre_p.add_argument(
        "tasks",
        nargs="*",
        default=["all"],
        help="Task ids to validate; defaults to the three workshop tasks.",
    )
    pre_p.add_argument("--minif2f-local", default=None, help="Path to local miniF2F checkout.")
    pre_p.add_argument("--minif2f-ref", default=None, help="MiniF2F git ref, default main.")
    pre_p.add_argument("--lean-root", default=None, help="Path to miniF2F checkout root for Lean.")
    pre_p.add_argument(
        "--skip-lean",
        action="store_true",
        help="Skip Lean executable/root checks (tasks only).",
    )

    sum_p = sub.add_parser("summarize", help="Summarize result JSONL files.")
    sum_p.add_argument("paths", nargs="*", default=[str(ProofBenchConfig().results_dir)])

    dash_p = sub.add_parser("dashboard", help="Write a lightweight HTML dashboard.")
    dash_p.add_argument("paths", nargs="*", default=[str(ProofBenchConfig().results_dir)])
    dash_p.add_argument("--output", default=str(ProofBenchConfig().results_dir / "dashboard.html"))

    sub.add_parser("list-tasks", help="List the default miniF2F theorem ids.")

    args = parser.parse_args(argv)
    if args.command == "run":
        return _run(args)
    if args.command == "summarize":
        return _summarize(args)
    if args.command == "dashboard":
        return _dashboard(args)
    if args.command == "preflight":
        return _preflight(args)
    if args.command == "list-tasks":
        for task_id in DEFAULT_TASK_IDS:
            print(task_id)
        return 0
    return 1


def _load_dotenv() -> None:
    # Load common workspace variables if present so users can run `uv run proofbench ...`
    # without manually sourcing `.env` first.
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for path in candidates:
        if path.is_file():
            _load_dotenv_file(path)


def _load_dotenv_file(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if ((value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"'))):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _run(args: argparse.Namespace) -> int:
    selections = _prompt_run_selections() if args.advanced else _prompt_rapid_run_selections()
    config = ProofBenchConfig.from_env(
        minif2f_ref=selections["minif2f_ref"],
        minif2f_local=selections["minif2f_local"],
        lean_root=selections["lean_root"],
        results_dir=selections["results_dir"],
    )
    task_ids = resolve_task_ids(selections["tasks"])
    tasks = load_tasks(config, task_ids)
    verifier = ProofVerifier(mode=selections["verifier"], lean_root=config.lean_root)
    check_tool = LeanCheckTool(verifier)
    agents = create_agents(
        selections["agents"],
        check_tool=check_tool,
        max_iters=selections["max_iters"],
        include_informal=selections["include_informal"],
    )
    model = create_model(selections["model_provider"], selections["model_name"])
    store = ResultStore(config.results_dir)
    rows = EvaluationRunner(verifier=verifier, result_store=store).run(
        agents=agents,
        tasks=tasks,
        model=model,
    )
    print(f"Wrote results to {store.path}")
    print(json.dumps(summarize(rows), indent=2))
    if selections["dashboard"]:
        dashboard_path = write_dashboard(load_results([config.results_dir]), config.results_dir / "dashboard.html")
        print(f"Wrote dashboard to {dashboard_path}")
    return 0


def _prompt_run_selections() -> dict:
    print("ProofBench advanced run setup")
    agents = _prompt_agents(default=DEFAULT_RAPID_AGENTS)
    task_choice = _choice(
        "Tasks",
        [
            ("all", "Default three miniF2F tasks"),
            ("custom", "Enter miniF2F theorem IDs"),
        ],
        default=1,
    )
    tasks = ["all"]
    if task_choice == "custom":
        raw_tasks = _text(
            "Enter theorem IDs separated by commas",
            default=",".join(DEFAULT_TASK_IDS),
        )
        tasks = [part.strip() for part in raw_tasks.split(",") if part.strip()]

    model_provider = _choice("Model provider", MODEL_PROVIDER_OPTIONS, default=2)
    model_name = None
    if model_provider == "gemini":
        model_name = _text("Gemini model name", default="gemini-3.1-flash-lite")

    verifier = _choice("Verifier", VERIFIER_OPTIONS, default=3)
    source = _choice(
        "miniF2F source",
        [
            ("github", "Fetch from GitHub at run time"),
            ("local", "Use a local miniF2F checkout"),
        ],
        default=1,
    )
    minif2f_local = None
    if source == "local":
        minif2f_local = _optional_text("Path to local miniF2F checkout")

    minif2f_ref = _text("miniF2F Git ref", default="main")
    lean_root = None
    if verifier in {"auto", "lean"}:
        lean_root = _optional_text(
            "Lean root path, usually the miniF2F checkout root (for example /path/to/miniF2F); leave blank to use env/default"
        )

    max_iters = 3
    if "react" in agents:
        max_iters = int(
            _choice(
                "ReAct max iterations",
                [("1", "1 iteration"), ("3", "3 iterations"), ("5", "5 iterations")],
                default=2,
            )
        )
    include_informal = _yes_no("Include informal statement in prompts", default=True)
    dashboard = _yes_no("Generate/update HTML dashboard", default=True)
    results_dir = _optional_text("Results directory; leave blank for ./results")

    return {
        "agents": agents,
        "tasks": tasks,
        "model_provider": model_provider,
        "model_name": model_name,
        "verifier": verifier,
        "lean_root": lean_root,
        "minif2f_local": minif2f_local,
        "minif2f_ref": minif2f_ref,
        "results_dir": results_dir,
        "max_iters": max_iters,
        "include_informal": include_informal,
        "dashboard": dashboard,
    }


def _prompt_rapid_run_selections() -> dict:
    print("ProofBench rapid run setup")
    agents = _prompt_agents(default=DEFAULT_RAPID_AGENTS)
    task_count = _task_count_prompt(default=len(DEFAULT_TASK_IDS))
    model_provider, model_name, verifier = _default_rapid_profile()
    return {
        "agents": agents,
        "tasks": list(DEFAULT_TASK_IDS[:task_count]),
        "model_provider": model_provider,
        "model_name": model_name,
        "verifier": verifier,
        "lean_root": None,
        "minif2f_local": None,
        "minif2f_ref": "main",
        "results_dir": None,
        "max_iters": 3,
        "include_informal": True,
        "dashboard": True,
    }


def _prompt_agents(*, default: str) -> list[str]:
    valid_names = set(registered_agent_names())
    print("\nAvailable agents:")
    for name in registered_agent_names():
        print(f"  {name}: {AGENT_LABELS.get(name, name)}")
    while True:
        raw = _text("Agents to run, comma-separated", default=default)
        agents = [part.strip() for part in raw.split(",") if part.strip()]
        unknown = [agent for agent in agents if agent not in valid_names]
        if agents and not unknown:
            return agents
        if unknown:
            print(f"Unknown agent(s): {', '.join(unknown)}.")
        else:
            print("Enter at least one agent.")


def _task_count_prompt(*, default: int) -> int:
    max_tasks = len(DEFAULT_TASK_IDS)
    while True:
        raw = _text(f"Number of default tasks to run (1-{max_tasks})", default=str(default))
        if raw.isdigit():
            count = int(raw)
            if 1 <= count <= max_tasks:
                return count
        print(f"Enter a number from 1 to {max_tasks}.")


def _default_rapid_profile() -> tuple[str, str | None, str]:
    lean_root = os.getenv("PROOFBENCH_MINIF2F_LEAN_ROOT")
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    lean_ready = bool(lean_root and Path(lean_root).expanduser().exists() and _lean_available())
    if has_gemini_key and lean_ready:
        return ("gemini", "gemini-3.1-flash-lite", "lean")
    return ("mock", None, "static")


def _lean_available() -> bool:
    if shutil.which("lean") or shutil.which("lake"):
        return True
    if (Path.home() / ".elan" / "bin" / "lean").is_file():
        return True
    toolchains = Path.home() / ".elan" / "toolchains"
    if toolchains.is_dir():
        return any((toolchain / "bin" / "lean").is_file() for toolchain in toolchains.iterdir())
    return False


def _choice(title: str, options: list[tuple[str, str]], *, default: int) -> str:
    print(f"\n{title}:")
    for index, (_, label) in enumerate(options, start=1):
        suffix = " [default]" if index == default else ""
        print(f"  {index}. {label}{suffix}")
    while True:
        answer = _read_line(f"Select {title.lower()} [{default}]: ").strip()
        if not answer:
            return options[default - 1][0]
        if answer.isdigit():
            selected = int(answer)
            if 1 <= selected <= len(options):
                return options[selected - 1][0]
        print(f"Enter a number from 1 to {len(options)}.")


def _yes_no(prompt: str, *, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        answer = _read_line(f"{prompt} [{suffix}]: ").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Enter yes or no.")


def _text(prompt: str, *, default: str) -> str:
    answer = _read_line(f"{prompt} [{default}]: ").strip()
    return answer or default


def _optional_text(prompt: str) -> str | None:
    answer = _read_line(f"{prompt}: ").strip()
    return answer or None


def _read_line(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        print()
        return ""


def _summarize(args: argparse.Namespace) -> int:
    rows = load_results([Path(path) for path in args.paths])
    print(json.dumps(summarize(rows), indent=2))
    return 0


def _dashboard(args: argparse.Namespace) -> int:
    rows = load_results([Path(path) for path in args.paths])
    output = write_dashboard(rows, Path(args.output))
    print(f"Wrote dashboard to {output}")
    return 0


def _preflight(args: argparse.Namespace) -> int:
    config = ProofBenchConfig.from_env(
        minif2f_ref=args.minif2f_ref,
        minif2f_local=args.minif2f_local,
        lean_root=args.lean_root,
    )
    return run_preflight(config=config, task_ids=args.tasks, require_lean=not args.skip_lean)


if __name__ == "__main__":
    raise SystemExit(main())
