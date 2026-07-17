# Evaluators

ProofBench evaluators measure four separate questions:

- Did the agent solve the theorem?
- How much verifier-grounded proof progress did the candidate make?
- How repairable was the failure?
- How much time and compute did the agent spend?

These axes intentionally replace vague "proof accuracy" and blended "proof quality" reporting. A proof is either accepted by Lean or it is not, but a failed attempt can still carry useful progress and repair information.

`static` verification is only a smoke-test mode. Use `lean` for theorem-proving results.

## Evaluation Flow

`EvaluationRunner` receives a registered agent, a task, a model, a verifier, and a result store. For each agent/task pair it:

1. runs `agent.run(task, model)`,
2. extracts the Lean candidate from the raw answer,
3. verifies the candidate with `ProofVerifier`,
4. records solve status, proof-completion diagnostics, failure profile, efficiency, speed, raw output, and trace,
5. writes the row through `ResultStore`.

JSONL result rows are the source of truth. Dashboards and Excel files are generated views over those rows.

## Core Metrics

Future result rows use these top-level metrics:

```text
metric_validity
solved
success_score
proof_completion
verified_prefix_ratio
repairability_score
failure_profile
efficiency
speed
```

`solved` is the boolean proof-assistant result.

`success_score` is `1.0` when the verifier accepts the proof and `0.0` otherwise. Agent summaries average it as `success_rate`, which is the percentage of attempted tasks solved.

`proof_completion` estimates how much formal proof work was completed before failure. For accepted proofs it is `1.0`. For failed proofs it is capped below `1.0` and derived from compiler-grounded signals: verified prefix position, failure type, and whether the candidate has enough formal structure to make the diagnostic meaningful.

`verified_prefix_ratio` estimates how far Lean got before the first diagnostic line. This is not a semantic proof-state percentage, but it is a deterministic lower-level signal available from batch compiler output.

`repairability_score` estimates how local and actionable the failure is. Unsolved goals are more repairable than type errors; type errors are more repairable than parser failures; unavailable verifiers receive no repairability credit.

`failure_profile` records structured diagnostic labels such as `placeholder`, `parse_error`, `type_error`, `unknown_identifier`, `missing_import`, `unsolved_goals`, and `timeout`.

## Metric Validity

Every row includes `metric_validity`:

```text
lean          Real Lean-backed proof metric.
static_smoke  Static theorem-shape smoke check only.
mock_smoke    Mock model smoke run only.
unavailable   Verifier was unavailable.
```

Summaries average `proof_completion` and `verified_prefix_ratio` only over rows with `metric_validity == "lean"`. They also report `proof_metric_coverage`, the fraction of rows that have real Lean-backed proof metrics. This prevents mock/static runs from producing authoritative-looking proof-completion charts.

Operational metrics such as tokens, model calls, tool calls, and runtime remain useful in smoke runs because they measure framework behavior, not proof correctness.

## Success Rate

The headline solve metric is:

```text
success_rate = solved_tasks / attempted_tasks
```

This is the rigorous replacement for vague "accuracy." It follows the dominant convention in formal theorem-proving benchmarks: a generated formal proof must be accepted by a proof assistant. Natural-language plausibility, reference-proof similarity, and model preference can all be misleading.

## Proof Completion

`proof_completion` answers a different question from success rate: if the proof failed, did Lean validate any meaningful prefix before the failure?

The current implementation is conservative:

```text
passed proof              -> 1.0
verifier unavailable      -> 0.0
placeholder/missing import -> 0.0
failed proof              -> max(verified_prefix_ratio, diagnostic_floor * formal_structure_score), capped at 0.95
```

The diagnostic floor depends on failure class. Unsolved goals receive more completion credit than parser errors because they indicate that Lean reached a meaningful proof state. Parser errors receive little credit because the candidate did not form a valid proof object.

This is still an estimate. A future interactive Lean evaluator could compute stronger proof-state metrics such as discharged goals over total generated goals, but batch Lean output cannot reliably provide that for every proof.

## Repairability

`repairability_score` is intentionally separate from `proof_completion`.

A proof can fail late but be hard to repair if it depends on hallucinated identifiers. A proof can fail early but be easy to repair if the remaining issue is an unsolved goal with useful context. Keeping repairability separate helps compare agents that are good at generating repairable attempts against agents that produce invalid or ungrounded code.

## Efficiency

Efficiency measures how much agent work was required:

```text
model_calls
input_tokens
output_tokens
total_tokens
tool_calls
```

This axis is separate from success because search agents can buy higher solve rates with more calls. ProofBench exposes the cost so users can compare designs under the same model and task set.

## Speed

Speed measures latency:

```text
agent_elapsed_s
model_latency_s
verification_elapsed_s
total_elapsed_s
```

Speed is separate from efficiency because token count and wall-clock time are not equivalent. A proof-search agent may use few tokens but spend significant time in verifier calls.

## Interpretation

For workshop results, report:

- `success_rate`: percentage of tasks solved.
- `proof_metric_coverage`: fraction of rows with Lean-backed proof metrics.
- `avg_proof_completion`: average completion estimate over Lean-valid rows.
- `avg_verified_prefix_ratio`: average verified prefix over Lean-valid rows.
- `avg_repairability_score`: average repairability diagnostic.
- efficiency and speed metrics.

The rigorous ordering is:

```text
Lean success > Lean-backed completion diagnostics > smoke checks
```

Smoke checks prove plumbing. They do not prove theorem-solving behavior.

## References

- Kunhao Zheng, Jesse Michael Han, Stanislas Polu. "miniF2F: a cross-system benchmark for formal Olympiad-level mathematics." arXiv:2109.00110, 2021. https://arxiv.org/abs/2109.00110
- Stanislas Polu, Ilya Sutskever. "Generative Language Modeling for Automated Theorem Proving." arXiv:2009.03393, 2020. https://arxiv.org/abs/2009.03393
- Guillaume Lample, Marie-Anne Lachaux, Thibaut Lavril, Xavier Martinet, Amaury Hayat, Gabriel Ebner, Aurelien Rodriguez, Timothee Lacroix. "HyperTree Proof Search for Neural Theorem Proving." arXiv:2205.11491, 2022. https://arxiv.org/abs/2205.11491
- Kaiyu Yang, Aidan M. Swope, Alex Gu, Shixing Yu, Saad Godil, Ryan Prenger, Anima Anandkumar. "LeanDojo: Theorem Proving with Retrieval-Augmented Language Models." arXiv:2306.15626, 2023. https://arxiv.org/abs/2306.15626
- Emily First, Markus N. Rabe, Talia Ringer, Yuriy Brun. "Baldur: Whole-Proof Generation and Repair with Large Language Models." arXiv:2303.04910, 2023. https://arxiv.org/abs/2303.04910
- Albert Q. Jiang, Sean Welleck, Jin Peng Zhou, Wenda Li, Jiacheng Liu, Mateja Jamnik, Timothee Lacroix, Yuhuai Wu, Guillaume Lample. "Draft, Sketch, and Prove: Guiding Formal Theorem Provers with Informal Proofs." arXiv:2210.12283, 2022. https://arxiv.org/abs/2210.12283
- Zhangir Azerbayev, Bartosz Piotrowski, Hailey Schoelkopf, Edward W. Ayers, Dragomir Radev, Jeremy Avigad. "ProofNet: Autoformalizing and Formally Proving Undergraduate-Level Mathematics." arXiv:2302.12433, 2023. https://arxiv.org/abs/2302.12433
- Suozhi Huang, Peiyang Song, Robert Joseph George, Anima Anandkumar. "LeanProgress: Guiding Search for Neural Theorem Proving via Proof Progress Prediction." arXiv:2502.17925, 2025. https://arxiv.org/abs/2502.17925
- Yang Li, Dong Du, Linfeng Song, Chen Li, Weikang Wang, Tao Yang, Haitao Mi. "HunyuanProver: A Scalable Data Synthesis Framework and Guided Tree Search for Automated Theorem Proving." arXiv:2412.20735, 2024. https://arxiv.org/abs/2412.20735
