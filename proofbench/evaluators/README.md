# Evaluators

ProofBench evaluators measure three axes required for agent-design comparisons:

- accuracy through Lean compiler acceptance when available,
- proof quality through continuous verifier-derived progress signals,
- efficiency through token, model-call, and tool-call counts,
- speed through wall-clock and component latency.

`static` verification is only a smoke-test mode. Use `lean` for workshop results.

## Accuracy

The primary accuracy signal is still binary proof-assistant acceptance:

```text
accuracy = 1.0 if Lean accepts the completed proof, otherwise 0.0
```

This follows the dominant convention in formal theorem-proving benchmarks. miniF2F evaluates whether a generated formal proof is accepted in systems such as Lean, Isabelle, HOL Light, and Metamath. GPT-f, HyperTree Proof Search, LeanDojo/ReProver, Baldur, ProofNet, and related systems likewise report theorem-proving success, proving accuracy, or pass@k as the central correctness statistic. The reason is methodological: a proof assistant gives a small trusted kernel or verifier boundary, while natural-language plausibility and reference-proof similarity can both be misleading. A failed formal proof is not mathematically correct, even if it resembles a human proof.

ProofBench therefore keeps `accuracy` as the objective workshop comparison metric. Any continuous score is secondary and should be read as progress or repairability, not as partial mathematical truth.

## Continuous Proof Quality

The evaluator also records:

```text
proof_quality_score
proof_progress
failure_profile
proof_quality_metrics
```

`proof_quality_score` is a continuous value in `[0.0, 1.0]`. A Lean-accepted proof receives `1.0`. A failed proof is capped below `1.0`, because only the verifier can certify correctness. The score combines available compiler-grounded signals:

```text
0.20 * formal_wellformedness
+ 0.30 * verified_prefix_progress
+ 0.20 * goal_progress
+ 0.15 * premise_grounding
+ 0.15 * repairability
```

`formal_wellformedness` measures whether the answer has a theorem declaration, proof delimiter, proof-like body, import context, and no placeholders. This is a shallow signal and must not be interpreted as proof correctness.

`verified_prefix_progress` estimates how far Lean got before the first diagnostic line. This approximates a proof-state progress signal using only batch compiler output. It is weaker than an interactive Lean environment, but it is reproducible and cheap.

`goal_progress` uses verifier diagnostics to distinguish failures such as unsolved goals, type errors, parser errors, and unknown identifiers. This is inspired by proof-state-oriented systems such as LeanDojo and progress-prediction work such as LeanProgress, where the central question is not only whether a theorem is solved, but how far a search state is from a completed proof.

`premise_grounding` penalizes missing imports and unknown identifiers. This reflects the finding that premise selection and library grounding are major bottlenecks in neural theorem proving, emphasized by LeanDojo/ReProver, and that hallucinated library references are a common failure mode in newer mathematical-analysis benchmarks.

`repairability` estimates how local and actionable the failure is. This follows the repair framing used by Baldur, where failed proof attempts plus compiler feedback are useful artifacts for a repair model. Unsolved goals are treated as more repairable than parser failures or unavailable verifiers.

`proof_plan_alignment` is present in `proof_quality_metrics` but currently marked unavailable. ProofBench does not vendor miniF2F reference proofs, and reference-proof edit distance would be a poor default anyway: many correct proofs can be structurally unrelated. A future evaluator may compute proof-plan alignment from evaluator-only sketches, supporting subtheorems, or informal proof milestones, following Draft, Sketch, and Prove, ProofNet, and TheoremBench-style structured theorem decompositions.

## Failure Profile

`failure_profile` is a structured diagnostic summary. It currently records:

```text
passed
verifier_unavailable
placeholder
timeout
parse_error
type_error
unknown_identifier
missing_import
unsolved_goals
compilation_error
```

These labels are intended for analysis, dashboards, and agent debugging. They are not independent ground-truth labels; they are derived from Lean output and should be interpreted as best-effort diagnostic categories.

## Efficiency

Efficiency measures how much agent work was required to produce an answer:

```text
model_calls
input_tokens
output_tokens
total_tokens
tool_calls
```

This axis is separate from accuracy because theorem-proving agents can trade compute for success. Search-based systems such as GPT-f, HTPS, LeanDojo/ReProver, and HunyuanProver report success under search budgets, pass@k, or guided tree-search settings. For workshop comparisons, an agent that obtains the same Lean acceptance rate with fewer model calls, fewer tokens, or fewer tool calls is materially different from one that spends a much larger search budget.

## Speed

Speed measures latency:

```text
agent_elapsed_s
model_latency_s
verification_elapsed_s
total_elapsed_s
```

This is reported separately from efficiency because token/tool counts and elapsed time are not equivalent. A tactic-search agent may be token-efficient but slow due to many verifier calls; a whole-proof generator may be fast but brittle; a repair loop may improve accuracy while increasing wall-clock time. Baldur's whole-proof plus repair framing and tree-search theorem provers such as HTPS motivate reporting wall-clock and verifier cost alongside success.

## Interpretation

For workshop results, report all evaluator axes:

- Accuracy: Lean compiler acceptance rate.
- Continuous quality: proof-quality score, proof progress, and failure profile.
- Efficiency: model calls, tokens, and tool calls.
- Speed: total runtime, model latency, and verification time.

The rigorous ordering is:

```text
Lean acceptance > continuous proof quality > static smoke checks
```

Continuous quality is useful for understanding near misses and agent behavior, especially during development, but it never overrides Lean acceptance.

## References

- Kunhao Zheng, Jesse Michael Han, Stanislas Polu. "miniF2F: a cross-system benchmark for formal Olympiad-level mathematics." arXiv:2109.00110, 2021. https://arxiv.org/abs/2109.00110
- Stanislas Polu, Ilya Sutskever. "Generative Language Modeling for Automated Theorem Proving." arXiv:2009.03393, 2020. https://arxiv.org/abs/2009.03393
- Guillaume Lample, Marie-Anne Lachaux, Thibaut Lavril, Xavier Martinet, Amaury Hayat, Gabriel Ebner, Aurelien Rodriguez, Timothee Lacroix. "HyperTree Proof Search for Neural Theorem Proving." arXiv:2205.11491, 2022. https://arxiv.org/abs/2205.11491
- Kaiyu Yang, Aidan M. Swope, Alex Gu, Rahul Chalamala, Peiyang Song, Shixing Yu, Saad Godil, Ryan Prenger, Anima Anandkumar. "LeanDojo: Theorem Proving with Retrieval-Augmented Language Models." arXiv:2306.15626, 2023. https://arxiv.org/abs/2306.15626
- Emily First, Markus N. Rabe, Talia Ringer, Yuriy Brun. "Baldur: Whole-Proof Generation and Repair with Large Language Models." arXiv:2303.04910, 2023. https://arxiv.org/abs/2303.04910
- Albert Q. Jiang, Sean Welleck, Jin Peng Zhou, Wenda Li, Jiacheng Liu, Mateja Jamnik, Timothee Lacroix, Yuhuai Wu, Guillaume Lample. "Draft, Sketch, and Prove: Guiding Formal Theorem Provers with Informal Proofs." arXiv:2210.12283, 2022. https://arxiv.org/abs/2210.12283
- Zhangir Azerbayev, Bartosz Piotrowski, Hailey Schoelkopf, Edward W. Ayers, Dragomir Radev, Jeremy Avigad. "ProofNet: Autoformalizing and Formally Proving Undergraduate-Level Mathematics." arXiv:2302.12433, 2023. https://arxiv.org/abs/2302.12433
- Suozhi Huang, Peiyang Song, Robert Joseph George, Anima Anandkumar. "LeanProgress: Guiding Search for Neural Theorem Proving via Proof Progress Prediction." arXiv:2502.17925, 2025. https://arxiv.org/abs/2502.17925
- Lushi Pu, Weiming Zhang, Xinheng Xie, Zixuan Fu, Bingxiang He, Hongya Lyu, Xin Li, Jie Zhou, Yudong Wang. "MA-ProofBench: A Two-Tiered Evaluation of LLMs for Theorem Proving in Mathematical Analysis." arXiv:2606.13782, 2026. https://arxiv.org/abs/2606.13782
- QuocViet Pham, Elvir Karimov, Andrey Galichin, Ivan Oseledets. "TheoremBench: Evaluating LLMs on Theorem Proving in Formal Mathematics." arXiv:2606.09450, 2026. https://arxiv.org/abs/2606.09450
- Yang Li, Dong Du, Linfeng Song, Chen Li, Weikang Wang, Tao Yang, Haitao Mi. "HunyuanProver: A Scalable Data Synthesis Framework and Guided Tree Search for Automated Theorem Proving." arXiv:2412.20735, 2024. https://arxiv.org/abs/2412.20735
