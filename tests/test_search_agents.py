import unittest

from proofbench.agents.registry import create_agents, registered_agent_names
from proofbench.agents.self_consistency import SelfConsistencyLeanAgent
from proofbench.evaluators.lean import ProofVerifier
from proofbench.models.base import ModelResponse
from proofbench.tasks.base import ProofTask
from proofbench.tools.lean_check import LeanCheckTool


VALID_PROOF = "```lean\ntheorem sample_task : True := by trivial\n```"
INVALID_PROOF = "```lean\ntheorem sample_task : True := by sorry\n```"


class SequenceModel:
    name = "sequence-model"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate(self, prompt: str) -> ModelResponse:
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        text = self.responses[index]
        return ModelResponse(
            text=text,
            input_tokens=max(1, len(prompt.split())),
            output_tokens=max(1, len(text.split())),
            latency_s=0.0,
            model_name=self.name,
        )


class SearchAgentTests(unittest.TestCase):
    def setUp(self):
        self.task = ProofTask(
            task_id="sample_task",
            split="test",
            proof_system="lean3",
            source_ref="local",
            formal_statement="theorem sample_task : True := by trivial",
        )
        self.check_tool = LeanCheckTool(ProofVerifier(mode="static"))

    def test_new_search_agents_are_registered(self):
        names = registered_agent_names()

        self.assertIn("self_consistency", names)
        self.assertIn("tree_of_thoughts", names)
        self.assertIn("graph_of_thoughts", names)
        self.assertIn("lats", names)

    def test_registered_search_agents_return_agent_results(self):
        agents = create_agents(
            ["self_consistency", "tree_of_thoughts", "graph_of_thoughts", "lats"],
            check_tool=self.check_tool,
            max_iters=1,
            include_informal=False,
            search_samples=1,
            search_width=1,
            search_depth=1,
            lats_rollouts=1,
        )

        for agent in agents:
            result = agent.run(self.task, SequenceModel([VALID_PROOF]))
            self.assertEqual(result.task_id, "sample_task")
            self.assertEqual(result.agent_name, agent.name)
            self.assertIn("theorem sample_task", result.raw_answer)
            self.assertGreaterEqual(result.model_calls, 1)
            self.assertGreaterEqual(result.tool_calls, 1)

    def test_self_consistency_selects_verified_candidate(self):
        agent = SelfConsistencyLeanAgent(
            self.check_tool,
            samples=2,
            include_informal=False,
        )

        result = agent.run(self.task, SequenceModel([INVALID_PROOF, VALID_PROOF]))

        self.assertIn("by trivial", result.raw_answer)
        self.assertEqual(result.model_calls, 2)
        self.assertEqual(result.tool_calls, 2)


if __name__ == "__main__":
    unittest.main()

