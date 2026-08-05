import unittest

from proofbench.agents.registry import create_agents, registered_agent_names
from proofbench.agents.self_consistency import SelfConsistencyLeanAgent
from proofbench.agents.ultimatum import UltimatumLeanAgent, repair_class
from proofbench.agents.search_common import SearchStats, check_candidate
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
        self.prompts = []

    def generate(self, prompt: str) -> ModelResponse:
        self.prompts.append(prompt)
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
        self.assertIn("ultimatum", names)

    def test_registered_search_agents_return_agent_results(self):
        agents = create_agents(
            ["self_consistency", "tree_of_thoughts", "graph_of_thoughts", "lats", "ultimatum"],
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

    def test_ultimatum_preserves_checked_candidate_after_empty_repair(self):
        agent = UltimatumLeanAgent(
            self.check_tool,
            max_iters=2,
            initial_candidates=1,
            include_informal=False,
        )

        result = agent.run(self.task, SequenceModel([INVALID_PROOF, ""]))

        self.assertEqual(result.raw_answer, "")
        self.assertNotIn("sorry", result.raw_answer.lower())
        decisions = [event for event in result.trace if event.get("type") == "decision"]
        self.assertEqual(decisions[-1]["reason"], "empty_model_response")

    def test_ultimatum_uses_portfolio_modes_and_rejects_placeholder_final(self):
        agent = UltimatumLeanAgent(
            self.check_tool,
            max_iters=5,
            initial_candidates=4,
            include_informal=False,
        )

        result = agent.run(self.task, SequenceModel([INVALID_PROOF] * 5))

        modes = [event["mode"] for event in result.trace if event.get("phase") == "generate"]
        self.assertEqual(
            modes,
            ["direct_tactic", "explicit_lemma_induction", "arithmetic_normalization", "conservative_repair"],
        )
        self.assertEqual(result.raw_answer, "")
        self.assertTrue(any(event.get("reason") == "placeholder_candidate" for event in result.trace))

    def test_ultimatum_retains_and_repairs_best_candidate(self):
        agent = create_agents(
            ["ultimatum"],
            check_tool=self.check_tool,
            max_iters=2,
            include_informal=False,
        )[0]

        model = SequenceModel([INVALID_PROOF, VALID_PROOF])
        result = agent.run(self.task, model)

        self.assertEqual(result.agent_name, "ultimatum")
        self.assertIn("by trivial", result.raw_answer)
        self.assertEqual(result.model_calls, 2)
        self.assertEqual(result.tool_calls, 2)
        self.assertIn("first_diagnostic_to_fix", model.prompts[1])
        tool_events = [event for event in result.trace if event.get("type") == "tool"]
        self.assertTrue(tool_events[-1]["passed"])

    def test_ultimatum_repairs_single_seed_using_diagnostics(self):
        agent = UltimatumLeanAgent(
            self.check_tool,
            max_iters=2,
            initial_candidates=1,
            include_informal=False,
        )

        result = agent.run(self.task, SequenceModel([INVALID_PROOF, VALID_PROOF]))

        self.assertIn("by trivial", result.raw_answer)
        self.assertEqual(result.model_calls, 2)
        self.assertEqual(result.tool_calls, 2)

    def test_ultimatum_repair_prompt_is_error_class_aware_and_stateful(self):
        agent = UltimatumLeanAgent(self.check_tool, include_informal=False)
        candidate = agent.run(self.task, SequenceModel([INVALID_PROOF])).trace
        tool_event = next(event for event in candidate if event.get("type") == "tool")
        self.assertTrue(tool_event["failure_profile"]["placeholder"])

        checked = check_candidate(
            task=self.task,
            check_tool=self.check_tool,
            raw_answer=INVALID_PROOF,
            label="seed",
            stats=SearchStats(),
            trace=[],
        )
        self.assertEqual(repair_class(checked), "placeholder")
        prompt = agent._repair_prompt("BASE", checked, 0)
        self.assertIn("Repair class: placeholder", prompt)
        self.assertIn("current_candidate:", prompt)
        self.assertIn("proof_completion:", prompt)
        self.assertIn("Remove every sorry", prompt)


if __name__ == "__main__":
    unittest.main()
