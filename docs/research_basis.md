# Research Basis

ProofBench uses miniF2F because formal proof benchmarks make correctness objective: a proof either compiles in the target proof assistant or it does not. The default implementation focuses on Lean 3 because miniF2F ships a Lean split with theorem statements and imports.

## Papers and Design Choices

- miniF2F: Zheng et al. introduced a cross-system formal Olympiad benchmark spanning Lean, Isabelle, Metamath, and other formalizations. ProofBench stores theorem IDs and retrieves statements at run time to avoid copying benchmark content. Source: https://github.com/facebookresearch/miniF2F
- AgentBench, arXiv:2308.03688: motivates evaluating agents as systems acting in environments, not only as single model calls. ProofBench therefore compares a single-call LLM baseline with a ReAct loop that can call a compiler-feedback tool. Source: https://arxiv.org/abs/2308.03688
- AI Agents That Matter, arXiv:2407.01502: emphasizes reproducible agent evaluation and accuracy-cost tradeoffs. ProofBench logs task IDs, source refs, model calls, tokens, tool calls, and runtime alongside correctness. Source: https://arxiv.org/abs/2407.01502
- Let's Verify Step by Step, arXiv:2305.20050: motivates process-aware evaluation and verifier feedback. ProofBench records traces and lets ReAct agents use compiler diagnostics as process feedback, while final accuracy remains compiler acceptance. Source: https://arxiv.org/abs/2305.20050
- ReAct: Yao et al. introduced interleaving reasoning and acting. ProofBench's starter `react` agent alternates model proposals with `lean_check` actions.
- LeanDojo and related neural theorem-proving work show that proof assistants can provide reliable feedback loops for automated theorem proving. ProofBench keeps this loop lightweight for workshop use.
- Gemini API pricing and API-key setup are documented by Google AI for Developers. ProofBench defaults to `gemini-3.1-flash-lite` because the official pricing page currently lists free input and output tokens for it. Sources: https://ai.google.dev/gemini-api/docs/pricing and https://ai.google.dev/gemini-api/docs/api-key

## Metric Mapping

- Accuracy: `1` only when the configured Lean verifier accepts a proof with no `sorry` or `admit`.
- Efficiency: model calls, input/output tokens, total tokens, and tool calls.
- Speed: agent wall time, model latency, verifier time, and total wall time.
