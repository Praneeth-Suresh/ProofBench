import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from proofbench.agents.registry import registered_agent_names
from proofbench.cli import _load_dotenv_file, _prompt_rapid_run_selections
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
