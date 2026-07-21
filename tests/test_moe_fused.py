import unittest

from proofbench.agents.base import AgentResult
from proofbench.agents.moe_fused import GLaMTopTwoFusedAgent
from proofbench.agents.registry import EXPERT_AGENT_NAMES, create_agents, registered_agent_names
from proofbench.agents.router import AgentRouter
from proofbench.evaluators.lean import ProofVerifier
from proofbench.logging.comparison import paired_agent_comparison
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
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return ModelResponse(text=response, input_tokens=3, output_tokens=2, model_name=self.name)


class FixedExpert:
    def __init__(self, name, answer):
        self.name = name
        self.answer = answer

    def run(self, task, model):
        return AgentResult(agent_name=self.name, task_id=task.task_id, raw_answer=self.answer)


class MoeFusedAgentTests(unittest.TestCase):
    def setUp(self):
        self.task = ProofTask(task_id="sample_task", split="test", proof_system="lean3", source_ref="local", formal_statement="theorem sample_task : True := by trivial")
        self.check_tool = LeanCheckTool(ProofVerifier(mode="static"))

    def test_router_selects_exactly_two_distinct_registered_experts(self):
        decision = AgentRouter(EXPERT_AGENT_NAMES).route(self.task)
        self.assertEqual(len(decision.experts), 2)
        self.assertEqual(len(set(decision.experts)), 2)
        self.assertTrue(set(decision.experts).issubset(set(registered_agent_names())))
        self.assertAlmostEqual(sum(decision.weights), 1.0)
        self.assertIn("features", decision.trace_event())
        self.assertEqual(decision.fallback_reason, "no_usable_historical_rows; static_scores_used")

    def test_registered_moe_agent_returns_agent_result(self):
        agent = create_agents(["moe_fused"], check_tool=self.check_tool, max_iters=1, include_informal=False, search_samples=1, search_width=1, search_depth=1, lats_rollouts=1)[0]
        result = agent.run(self.task, SequenceModel([VALID_PROOF]))
        self.assertEqual(result.agent_name, "moe_fused")
        self.assertEqual(result.task_id, self.task.task_id)
        self.assertEqual(len(next(event for event in result.trace if event["type"] == "router")["selected_experts"]), 2)

    def test_fusion_prefers_verified_expert_candidate(self):
        agent = GLaMTopTwoFusedAgent(router=AgentRouter(("expert_one", "expert_two")), experts={"expert_one": FixedExpert("expert_one", INVALID_PROOF), "expert_two": FixedExpert("expert_two", VALID_PROOF)}, check_tool=self.check_tool, include_informal=False)
        result = agent.run(self.task, SequenceModel([INVALID_PROOF]))
        self.assertIn("by trivial", result.raw_answer)
        self.assertFalse(any(event.get("phase") == "fusion" for event in result.trace))

    def test_fusion_repairs_two_incomplete_candidates(self):
        agent = GLaMTopTwoFusedAgent(router=AgentRouter(("expert_one", "expert_two")), experts={"expert_one": FixedExpert("expert_one", INVALID_PROOF), "expert_two": FixedExpert("expert_two", INVALID_PROOF)}, check_tool=self.check_tool, include_informal=False)
        result = agent.run(self.task, SequenceModel([VALID_PROOF]))
        self.assertIn("by trivial", result.raw_answer)
        self.assertTrue(any(event.get("phase") == "fusion" for event in result.trace))

    def test_paired_comparison_enforces_lean_only_efficiency_gate(self):
        rows = [_lean_row("llm_baseline", 0.0, 100, 1.0), _lean_row("moe_fused", 1.0, 150, 1.5), {"agent": "moe_fused", "metric_validity": "static_smoke"}]
        report = paired_agent_comparison(rows, max_token_multiplier=2.0, max_time_multiplier=2.0)
        self.assertEqual(report["paired_tasks"], 1)
        self.assertEqual(report["solve_rate_delta"], 1.0)
        self.assertTrue(report["efficiency_gate"]["passed"])


def _lean_row(agent, success_score, tokens, elapsed):
    return {"created_at": "2026-07-21T00:00:00+00:00", "agent": agent, "task_id": "sample_task", "model": "gemini", "metric_validity": "lean", "success_score": success_score, "efficiency": {"total_tokens": tokens}, "speed": {"total_elapsed_s": elapsed}, "verification": {"verifier": "lean"}}
