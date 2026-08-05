# Agents

`moe_fused` is the only MoE design: `router.py` routes every task to exactly two existing experts, then the fused agent verifier-selects or repairs their candidate proofs.

This folder contains agent designs. `llm_baseline.py` performs one model call and is the control condition. `react_agent.py` adds a simple reasoning/action loop with Lean compiler feedback.

New agents should implement the `AgentResult` contract in `base.py` and be registered in `registry.py`.

## Analysis of the comparison results

The headline result is that ReAct produced the highest Lean-backed proof-completion score in the original comparison: about 0.874 averaged across the three tasks, compared with 0.339 for Graph of Thoughts and 0.286 for Tree of Thoughts. However, none of the original agents actually produced a Lean-accepted proof. Every agent's success rate was 0%.

That distinction matters. `proof_completion` is a compiler-grounded estimate of how far a failed proof got before its first error. It is useful for diagnosing progress, but it is not partial theorem correctness. Lean compiler acceptance remains the only objective solve signal.

### Why ReAct performed best

ReAct is the design most closely aligned with the actual failure mode of theorem proving:

1. Generate a proof.
2. Ask Lean to check it.
3. Read the compiler diagnostics.
4. Revise the proof.
5. Repeat.

The three ReAct iterations therefore form one coherent repair trajectory. On all three tasks it reached a proof that Lean largely understood but rejected at the final goal. The failures were mostly unsolved goals, which the evaluator treats as highly repairable. ReAct was not proving 85% of each theorem mathematically; it was producing structurally valid Lean programs that got close to the remaining obligation.

Its cost was moderate: three model calls and three compiler checks per task.

### Why Tree of Thoughts underperformed

Tree of Thoughts generated multiple branches, but the implementation mostly regenerated complete proofs rather than deeply refining a promising proof state. Later states retained thought descriptions more than verified Lean states.

This means the model spent budget generating alternate full proofs instead of fixing a known compiler error. Branch selection could also prefer a malformed proof with a longer valid prefix over a strategically better proof that failed earlier. It reached moderate partial progress on the algebra and AIME tasks, but number-theory attempts were often rejected because they contained placeholders.

### Why Graph of Thoughts was somewhat better

Graph of Thoughts generated independent candidates, improved failed candidates, and sometimes aggregated the strongest attempts. This explains its relatively strong algebra completion score: it found partially compatible algebraic fragments.

The limitation is that two failed Lean proofs are not necessarily compositional. Combining their text does not guarantee that their lemmas, types, or proof states fit together. Graph of Thoughts also used substantially more model and compiler calls, but that extra search did not produce an accepted proof.

### Why Self-Consistency scored zero

Self-Consistency samples independent proofs and selects the best candidate. That helps when several independent attempts have a reasonable chance of being correct. Here, the samples repeatedly contained `sorry`, `admit`, or placeholder-like material and were rejected before meaningful compilation.

More importantly, independent samples do not receive compiler feedback between attempts. If the model repeats the same Lean mistake, Self-Consistency simply produces several versions of that mistake.

### Why LATS did not benefit from search

LATS adds MCTS-style selection and self-reflection, but reflection produces a textual score and repair plan rather than a reliably checked revised proof. The search therefore selects among weak candidates instead of systematically repairing them.

Its reward signal also gives too much importance to model-generated judgments. Lean acceptance, remaining goals, verified prefixes, and error repairability should dominate the reward. The observed LATS candidates often contained placeholders or malformed proof fragments, so the search machinery could not compensate.

### What happened with `moe_fused`

The fused agent routes each task to two experts, runs both, and optionally asks the model to fuse their candidates. It selected combinations involving ReAct, Graph of Thoughts, and the baseline. Its completion scores were similar to ReAct, but no proof passed Lean.

Fusion is expensive and difficult when both expert candidates fail in different ways. The model must reconcile multiple incompatible proof states, not simply choose between two answers. A stronger version would pass verified fragments and diagnostics between specialists rather than fusing two final failed proofs.

### Why Ultimatum still could not reach 100%

Ultimatum combined the most promising ideas: a portfolio of direct tactics, explicit lemmas or induction, arithmetic normalization, conservative repair, error-class-aware prompts, placeholder rejection, and preservation of the strongest compiler-tested candidate. It was developed through five iterations and evaluated with eight model calls and eight Lean checks per task.

The final run improved partial progress but still solved 0/3 tasks:

- Algebra: 0.556 proof completion, failing on algebraic normalization.
- AIME 1988 P8: 0.350 completion, failing on a type or rewrite mismatch.
- Number theory: 0.875 completion, but the final goal remained unresolved.

There are several reasons this was not enough:

- The model often identified the right mathematical idea but translated it into invalid Lean syntax, unavailable theorem names, or incorrect coercions.
- Compiler feedback identifies what Lean rejects, but it does not automatically supply the missing mathematical lemma or the correct proof strategy.
- Repeated repair prompts can preserve a flawed proof structure. A verified prefix may be syntactically valid while the remaining goal requires a fundamentally different argument.
- The hardest tasks require domain-specific reasoning: induction and recurrence manipulation for AIME, and number-theoretic factorization or parity arguments for the number-theory task. Generic repair modes cannot guarantee those discoveries.
- More model calls increase opportunities for repair, but they also increase opportunities for regression, hallucinated lemmas, and placeholder output.

The final Ultimatum result therefore demonstrates improved proof progress, not perfect proving ability. Achieving 100% would likely require stronger theorem/lemma retrieval, explicit Lean environment awareness, structured goal-state editing, and task-specific mathematical planning. The current agent architecture can provide those capabilities, but bounded prompting and compiler feedback alone were insufficient on this three-task sample.

### Overall conclusion

The comparison supports a specific conclusion: compiler-guided serial repair was more valuable than unstructured breadth, graph organization, or self-reported search scoring. ReAct was strongest because it kept one proof trajectory coherent and used Lean feedback immediately. Ultimatum improved the search and repair discipline and reached higher partial completion on the final run, but its 0% success rate shows that compiler diagnostics are necessary without being sufficient for correct formal proofs.
