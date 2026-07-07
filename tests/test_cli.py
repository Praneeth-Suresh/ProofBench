import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from proofbench.agents.registry import registered_agent_names
from proofbench.cli import (
    _default_rapid_profile,
    _load_dotenv_file,
    _prompt_rapid_run_selections,
    _run_selections_from_args,
)
from proofbench.config import DEFAULT_TASK_IDS


class CliPromptTests(unittest.TestCase):
    def test_agent_options_are_single_agents(self):
        for name in registered_agent_names():
            self.assertNotIn(",", name)

    @patch("proofbench.cli._default_rapid_profile", return_value=("mock", None, "static"))
    @patch("builtins.input", side_effect=["react", "2"])
    def test_rapid_prompt_only_needs_agents_and_task_count(self, _input, _profile):
        selections = _prompt_rapid_run_selections()

        self.assertEqual(selections["agents"], ["react"])
        self.assertEqual(selections["tasks"], list(DEFAULT_TASK_IDS[:2]))
        self.assertEqual(selections["model_provider"], "mock")
        self.assertEqual(selections["verifier"], "static")
        self.assertTrue(selections["dashboard"])

    def test_run_selections_from_args_supports_direct_agents_and_tasks(self):
        args = type(
            "Args",
            (),
            {
                "agents": "llm_baseline,react",
                "tasks": "aime_1988_p8,algebra_9onxpypzleqsum2onxpy",
                "task_count": None,
                "model_provider": "mock-react",
                "model_name": None,
                "verifier": "static",
                "minif2f_ref": "main",
                "minif2f_local": None,
                "lean_root": None,
                "results_dir": "smoke",
                "max_iters": 5,
                "include_informal": True,
                "dashboard": False,
            },
        )()

        selections = _run_selections_from_args(args)

        self.assertEqual(selections["agents"], ["llm_baseline", "react"])
        self.assertEqual(
            selections["tasks"],
            ["aime_1988_p8", "algebra_9onxpypzleqsum2onxpy"],
        )
        self.assertEqual(selections["model_provider"], "mock-react")
        self.assertEqual(selections["verifier"], "static")
        self.assertEqual(selections["results_dir"], "smoke")
        self.assertEqual(selections["max_iters"], 5)
        self.assertFalse(selections["dashboard"])

    def test_run_selections_from_args_supports_task_count_shortcut(self):
        args = type(
            "Args",
            (),
            {
                "agents": "react",
                "tasks": None,
                "task_count": 2,
                "model_provider": "mock",
                "model_name": None,
                "verifier": "static",
                "minif2f_ref": "main",
                "minif2f_local": None,
                "lean_root": None,
                "results_dir": None,
                "max_iters": 3,
                "include_informal": False,
                "dashboard": True,
            },
        )()

        selections = _run_selections_from_args(args)

        self.assertEqual(selections["agents"], ["react"])
        self.assertEqual(selections["tasks"], list(DEFAULT_TASK_IDS[:2]))
        self.assertFalse(selections["include_informal"])

    def test_run_selections_from_args_rejects_unknown_agents(self):
        args = type(
            "Args",
            (),
            {
                "agents": "missing_agent",
                "tasks": None,
                "task_count": 1,
                "model_provider": "mock",
                "model_name": None,
                "verifier": "static",
                "minif2f_ref": "main",
                "minif2f_local": None,
                "lean_root": None,
                "results_dir": None,
                "max_iters": 3,
                "include_informal": True,
                "dashboard": True,
            },
        )()

        with self.assertRaisesRegex(ValueError, "Unknown agent"):
            _run_selections_from_args(args)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}, clear=False)
    def test_default_rapid_profile_requires_llm_credentials(self):
        with self.assertRaisesRegex(
            RuntimeError, "No LLM credentials found for rapid mode"
        ):
            _default_rapid_profile()


class CliEnvTests(unittest.TestCase):
    def test_load_dotenv_file_sets_missing_env_vars(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("FOO=bar\nBAZ=\"bee\"\n", encoding="utf-8")

            original_foo = os.getenv("FOO")
            original_baz = os.getenv("BAZ")

            _load_dotenv_file(env_path)

            self.assertEqual(os.getenv("FOO"), "bar")
            self.assertEqual(os.getenv("BAZ"), "bee")

            if original_foo is None:
                os.environ.pop("FOO", None)
            else:
                os.environ["FOO"] = original_foo
            if original_baz is None:
                os.environ.pop("BAZ", None)
            else:
                os.environ["BAZ"] = original_baz


if __name__ == "__main__":
    unittest.main()
