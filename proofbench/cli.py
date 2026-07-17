from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from dataclasses import asdict

from proofbench.agents.registry import create_agents, registered_agent_names
from proofbench.config import DEFAULT_TASK_IDS, ProofBenchConfig
from proofbench.evaluators.accuracy import success_score
from proofbench.evaluators.lean import ProofVerifier
from proofbench.evaluators.runner import EvaluationRunner, metric_validity
from proofbench.logging.dashboard import write_dashboard
from proofbench.logging.excel_export import write_excel
from proofbench.logging.result_store import ResultStore, load_results, summarize
from proofbench.preflight import run_preflight
from proofbench.models.registry import create_model
from proofbench.tasks.minif2f import extract_candidate_lean
from proofbench.tasks.registry import load_tasks, resolve_task_ids
from proofbench.tools.lean_check import LeanCheckTool


AGENT_LABELS = {
    "llm_baseline": "LLM baseline",
    "react": "ReAct Lean-checking agent",
    "self_consistency": "Self-Consistency proof sampler",
    "tree_of_thoughts": "Tree of Thoughts proof search",
    "graph_of_thoughts": "Graph of Thoughts proof search",
    "lats": "Language Agent Tree Search",
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
    run_p.add_argument("--agents", help="Comma-separated registered agents to run, for example llm_baseline,react.")
    run_p.add_argument("--tasks", help="Comma-separated miniF2F theorem ids, or all for the default task set.")
    run_p.add_argument("--task-count", type=int, help="Run the first N default tasks without prompting.")
    run_p.add_argument(
        "--model-provider",
        choices=[option[0] for option in MODEL_PROVIDER_OPTIONS],
        help="Model provider for a non-interactive run. Defaults to gemini when credentials exist.",
    )
    run_p.add_argument("--model-name", help="Provider-specific model name override.")
    run_p.add_argument(
        "--verifier",
        choices=[option[0] for option in VERIFIER_OPTIONS],
        help="Verifier for a non-interactive run. Defaults to auto.",
    )
    run_p.add_argument("--minif2f-local", help="Path to a local miniF2F checkout.")
    run_p.add_argument("--minif2f-ref", default="main", help="miniF2F git ref, default main.")
    run_p.add_argument("--lean-root", help="Path to miniF2F checkout root for Lean.")
    run_p.add_argument("--results-dir", help="Results directory or run slug.")
    run_p.add_argument("--max-iters", type=int, default=3, help="ReAct max tool-repair iterations.")
    run_p.add_argument("--search-samples", type=int, default=3, help="Self-Consistency proof samples.")
    run_p.add_argument("--search-width", type=int, default=2, help="Tree/graph/LATS branching width.")
    run_p.add_argument("--search-depth", type=int, default=2, help="Tree/LATS search depth.")
    run_p.add_argument("--lats-rollouts", type=int, default=4, help="Language Agent Tree Search rollouts.")
    prompt_group = run_p.add_mutually_exclusive_group()
    prompt_group.add_argument("--include-informal", dest="include_informal", action="store_true", default=True)
    prompt_group.add_argument("--formal-only", dest="include_informal", action="store_false")
    dashboard_group = run_p.add_mutually_exclusive_group()
    dashboard_group.add_argument(
        "--dashboard",
        nargs="?",
        const="dashboard.html",
        default=None,
        metavar="PATH",
        help="Generate HTML dashboard at path. Defaults to dashboard.html when omitted.",
    )
    dashboard_group.add_argument("--no-dashboard", dest="dashboard", action="store_false")

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

    export_p = sub.add_parser("export", help="Export result JSONL files to an Excel workbook.")
    export_p.add_argument("paths", nargs="*", default=[str(ProofBenchConfig().results_dir)])
    export_p.add_argument("--output", default=str(ProofBenchConfig().results_dir / "proofbench-results.xlsx"))

    reverify_p = sub.add_parser(
        "reverify",
        help="Re-run verifier/dashboard/export from existing results without model calls.",
    )
    reverify_p.add_argument("paths", nargs="*", default=[str(ProofBenchConfig().results_dir)])
    reverify_p.add_argument("--verifier", choices=[option[0] for option in VERIFIER_OPTIONS], default="lean")
    reverify_p.add_argument("--lean-root", help="Path to miniF2F checkout root for Lean.")
    reverify_p.add_argument("--minif2f-local", help="Path to a local miniF2F checkout.")
    reverify_p.add_argument("--minif2f-ref", default="main", help="miniF2F git ref, default main.")
    reverify_p.add_argument("--results-dir", default="reverified", help="Directory or run slug for reverified rows.")
    reverify_p.add_argument("--dashboard", default="dashboard.html", help="HTML dashboard output path.")
    reverify_p.add_argument("--no-dashboard", action="store_true", help="Skip dashboard generation.")

    sub.add_parser("list-tasks", help="List the default miniF2F theorem ids.")

    args = parser.parse_args(argv)
    if args.command == "run":
        return _run(args)
    if args.command == "summarize":
        return _summarize(args)
    if args.command == "dashboard":
        return _dashboard(args)
    if args.command == "export":
        return _export(args)
    if args.command == "reverify":
        return _reverify(args)
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
    try:
        selections = (
            _run_selections_from_args(args)
            if _has_run_args(args)
            else _prompt_run_selections()
            if args.advanced
            else _prompt_rapid_run_selections()
        )
    except (RuntimeError, ValueError) as exc:
        print("LLM is not available:")
        print(f"  {exc}")
        print("No benchmark tasks were run.")
        print(
            "If you want smoke mode, run with --advanced and pick a mock provider; "
            "otherwise set GEMINI_API_KEY (or GOOGLE_API_KEY) and retry."
        )
        return 1
    config = ProofBenchConfig.from_env(
        minif2f_ref=selections["minif2f_ref"],
        minif2f_local=selections["minif2f_local"],
        lean_root=selections["lean_root"],
        results_dir=selections["results_dir"],
    )
    if selections["verifier"] == "lean":
        _require_lean_root(config.lean_root)
    try:
        model = create_model(selections["model_provider"], selections["model_name"])
    except RuntimeError as exc:
        print("LLM is not available:")
        print(f"  {exc}")
        print("No benchmark tasks were run.")
        print(
            "If you want smoke mode, run with --advanced and pick a mock provider; "
            "otherwise set GEMINI_API_KEY (or GOOGLE_API_KEY) and retry."
        )
        return 1
    task_ids = resolve_task_ids(selections["tasks"])
    tasks = load_tasks(config, task_ids)
    verifier = ProofVerifier(mode=selections["verifier"], lean_root=config.lean_root)
    check_tool = LeanCheckTool(verifier)
    agents = create_agents(
        selections["agents"],
        check_tool=check_tool,
        max_iters=selections["max_iters"],
        include_informal=selections["include_informal"],
        search_samples=selections["search_samples"],
        search_width=selections["search_width"],
        search_depth=selections["search_depth"],
        lats_rollouts=selections["lats_rollouts"],
    )
    store = ResultStore(config.results_dir)
    rows = EvaluationRunner(verifier=verifier, result_store=store).run(
        agents=agents,
        tasks=tasks,
        model=model,
    )
    print(f"Wrote results to {store.path}")
    print(json.dumps(summarize(rows), indent=2))
    all_rows = load_results([config.results_dir])
    excel_path = write_excel(all_rows, config.results_dir / "proofbench-results.xlsx")
    print(f"Wrote Excel export to {excel_path}")
    dashboard_output = selections["dashboard"]
    if dashboard_output is True:
        dashboard_output = "dashboard.html"
    if dashboard_output:
        dashboard_path = write_dashboard(all_rows, Path(dashboard_output))
        print(f"Wrote dashboard to {dashboard_path}")
    return 0


def _has_run_args(args: argparse.Namespace) -> bool:
    return any(
        getattr(args, name) is not None
        for name in (
            "agents",
            "tasks",
            "task_count",
            "model_provider",
            "model_name",
            "verifier",
            "minif2f_local",
            "lean_root",
            "results_dir",
        )
    ) or args.max_iters != 3 or not args.include_informal or args.dashboard is False or (
        getattr(args, "search_samples", 3) != 3
        or getattr(args, "search_width", 2) != 2
        or getattr(args, "search_depth", 2) != 2
        or getattr(args, "lats_rollouts", 4) != 4
    )


def _run_selections_from_args(args: argparse.Namespace) -> dict:
    agents = _parse_agents(args.agents or DEFAULT_RAPID_AGENTS)
    tasks = _tasks_from_args(tasks=args.tasks, task_count=args.task_count)
    search_samples = _positive_int(getattr(args, "search_samples", 3), "--search-samples")
    search_width = _positive_int(getattr(args, "search_width", 2), "--search-width")
    search_depth = _positive_int(getattr(args, "search_depth", 2), "--search-depth")
    lats_rollouts = _positive_int(getattr(args, "lats_rollouts", 4), "--lats-rollouts")
    model_provider = args.model_provider
    model_name = args.model_name
    verifier = args.verifier
    if model_provider is None or verifier is None:
        default_provider, default_model, default_verifier = _default_profile_for_args()
        model_provider = model_provider or default_provider
        model_name = model_name or default_model
        verifier = verifier or default_verifier
    return {
        "agents": agents,
        "tasks": tasks,
        "model_provider": model_provider,
        "model_name": model_name,
        "verifier": verifier,
        "lean_root": args.lean_root,
        "minif2f_local": args.minif2f_local,
        "minif2f_ref": args.minif2f_ref,
        "results_dir": args.results_dir,
        "max_iters": args.max_iters,
        "search_samples": search_samples,
        "search_width": search_width,
        "search_depth": search_depth,
        "lats_rollouts": lats_rollouts,
        "include_informal": args.include_informal,
        "dashboard": args.dashboard if args.dashboard is not None else "dashboard.html",
    }


def _parse_agents(raw: str) -> list[str]:
    valid_names = set(registered_agent_names())
    agents = [part.strip() for part in raw.split(",") if part.strip()]
    unknown = [agent for agent in agents if agent not in valid_names]
    if not agents:
        raise ValueError("Enter at least one agent.")
    if unknown:
        raise ValueError(f"Unknown agent(s): {', '.join(unknown)}")
    return agents


def _tasks_from_args(*, tasks: str | None, task_count: int | None) -> list[str]:
    if tasks and task_count is not None:
        raise ValueError("Use --tasks or --task-count, not both.")
    if tasks:
        return resolve_task_ids([tasks])
    if task_count is not None:
        if not 1 <= task_count <= len(DEFAULT_TASK_IDS):
            raise ValueError(f"--task-count must be between 1 and {len(DEFAULT_TASK_IDS)}")
        return list(DEFAULT_TASK_IDS[:task_count])
    return ["all"]


def _positive_int(value: int, flag: str) -> int:
    if value < 1:
        raise ValueError(f"{flag} must be at least 1")
    return value


def _default_profile_for_args() -> tuple[str, str | None, str]:
    try:
        return _default_rapid_profile()
    except RuntimeError:
        return ("mock", None, "static")


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
        "search_samples": 3,
        "search_width": 2,
        "search_depth": 2,
        "lats_rollouts": 4,
        "include_informal": include_informal,
        "dashboard": "dashboard.html" if dashboard else False,
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
        "search_samples": 3,
        "search_width": 2,
        "search_depth": 2,
        "lats_rollouts": 4,
        "include_informal": True,
        "dashboard": "dashboard.html",
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
    if not has_gemini_key:
        raise RuntimeError(
            "No LLM credentials found for rapid mode. Set GEMINI_API_KEY (or GOOGLE_API_KEY) "
            "before running `proofbench run`, or use --advanced with a mock provider."
        )
    lean_ready = bool(lean_root and Path(lean_root).expanduser().exists() and _lean_available())
    if lean_ready:
        return ("gemini", "gemini-3.1-flash-lite", "lean")
    return ("gemini", "gemini-3.1-flash-lite", "auto")


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
    write_excel(rows, Path(args.output).parent / "proofbench-results.xlsx")
    output = write_dashboard(rows, Path(args.output))
    print(f"Wrote dashboard to {output}")
    return 0


def _export(args: argparse.Namespace) -> int:
    rows = load_results([Path(path) for path in args.paths])
    output = write_excel(rows, Path(args.output))
    print(f"Wrote Excel export to {output}")
    return 0


def _reverify(args: argparse.Namespace) -> int:
    input_rows = load_results([Path(path) for path in args.paths])
    config = ProofBenchConfig.from_env(
        minif2f_ref=args.minif2f_ref,
        minif2f_local=args.minif2f_local,
        lean_root=args.lean_root,
        results_dir=args.results_dir,
    )
    if args.verifier == "lean":
        _require_lean_root(config.lean_root)
    verifier = ProofVerifier(mode=args.verifier, lean_root=config.lean_root)
    store = ResultStore(config.results_dir)
    rows = _reverify_rows(input_rows, config=config, verifier=verifier, store=store)
    print(f"Reverified {len(rows)} existing result rows without model calls.")
    print(f"Wrote results to {store.path}")
    print(json.dumps(summarize(rows), indent=2))
    all_rows = load_results([config.results_dir])
    excel_path = write_excel(all_rows, config.results_dir / "proofbench-results.xlsx")
    print(f"Wrote Excel export to {excel_path}")
    if not args.no_dashboard:
        dashboard_path = write_dashboard(all_rows, Path(args.dashboard))
        print(f"Wrote dashboard to {dashboard_path}")
    return 0


def _reverify_rows(
    input_rows: list[dict],
    *,
    config: ProofBenchConfig,
    verifier: ProofVerifier,
    store: ResultStore,
) -> list[dict]:
    task_cache = {}
    output_rows = []
    for original in input_rows:
        task_id = original["task_id"]
        if task_id not in task_cache:
            task_cache[task_id] = load_tasks(config, [task_id])[0]
        task = task_cache[task_id]
        best_raw_answer = ""
        best_verification = None
        for raw_answer in _existing_answer_candidates(original):
            candidate = extract_candidate_lean(task, raw_answer)
            verification = verifier.verify(candidate)
            if best_verification is None or (
                verification.passed,
                verification.proof_completion,
                verification.repairability_score,
            ) > (
                best_verification.passed,
                best_verification.proof_completion,
                best_verification.repairability_score,
            ):
                best_raw_answer = raw_answer
                best_verification = verification
        if best_verification is None:
            best_raw_answer = original.get("raw_answer", "")
            candidate = extract_candidate_lean(task, best_raw_answer)
            best_verification = verifier.verify(candidate)
        verification = best_verification
        row = {
            **_without_legacy_metrics(original),
            "source_ref": config.minif2f_ref,
            "source_urls": task.source_urls,
            "metric_validity": metric_validity(verification, original.get("model", "unknown")),
            "solved": verification.passed,
            "success_score": success_score(verification),
            "proof_completion": verification.proof_completion,
            "verified_prefix_ratio": verification.verified_prefix_ratio,
            "repairability_score": verification.repairability_score,
            "failure_profile": verification.failure_profile,
            "completion_metrics": verification.completion_metrics,
            "verification": asdict(verification),
            "raw_answer": best_raw_answer,
            "reverified_from": original.get("created_at"),
            "reverified_without_model_calls": True,
        }
        row["speed"] = {
            **original.get("speed", {}),
            "verification_elapsed_s": verification.elapsed_s,
            "total_elapsed_s": float(original.get("speed", {}).get("agent_elapsed_s", 0.0)) + verification.elapsed_s,
        }
        store.append(row)
        output_rows.append(row)
    return output_rows


def _without_legacy_metrics(row: dict) -> dict:
    legacy_keys = {
        "accuracy",
        "proof_quality_score",
        "proof_progress",
        "proof_quality_metrics",
    }
    return {key: value for key, value in row.items() if key not in legacy_keys}


def _existing_answer_candidates(row: dict) -> list[str]:
    candidates = []
    raw_answer = row.get("raw_answer", "")
    if raw_answer:
        candidates.append(raw_answer)
    for event in row.get("trace", []):
        if not isinstance(event, dict):
            continue
        response = event.get("response")
        if response and response not in candidates:
            candidates.append(response)
    return candidates


def _preflight(args: argparse.Namespace) -> int:
    config = ProofBenchConfig.from_env(
        minif2f_ref=args.minif2f_ref,
        minif2f_local=args.minif2f_local,
        lean_root=args.lean_root,
    )
    return run_preflight(config=config, task_ids=args.tasks, require_lean=not args.skip_lean)


def _require_lean_root(lean_root: Path | None) -> None:
    if lean_root is None:
        raise SystemExit(
            "Lean root is required for --verifier lean. Set PROOFBENCH_MINIF2F_LEAN_ROOT "
            "or pass --lean-root /path/to/miniF2F."
        )
    if not lean_root.exists():
        raise SystemExit(f"Lean root path does not exist: {lean_root}")


if __name__ == "__main__":
    raise SystemExit(main())
