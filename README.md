# Entropy-DeepWide

Research workspace for uncertainty-aware control of deep-and-wide web search.

The repository currently contains:

- `survey.md`: literature survey and novelty audit;
- `plan.md`: evidence-gated research and implementation plan;
- `scripts/`: baseline generation and official-evaluation adapters;
- `data/deepwidesearch/`: the public DeepWideSearch query file used by the baseline;
- `results/`: compact, credential-free aggregate result artifacts;
- the original proposal PDF for provenance.

Large generated runs, virtual environments, credentials, and third-party source mirrors are intentionally excluded from Git. See `plan.md` for the current project status and reproducibility requirements.

## Current conclusions

As of 2026-07-30 04:25 UTC, the frozen R1 run is at `129/220` terminal tasks (`23` completed, `106` failed, `91` remaining). The released evaluator has not run, so there is no official DeepWideBench score, Avg@4 result, leaderboard improvement, or SOTA claim.

The literature review rules out broad novelty claims based only on entropy, information gain, dynamic deep/wide routing, coverage maps, denominator discovery, or information-weighted credit assignment. The narrower hypothesis still worth testing is a **calibrated four-layer open-world belief** over anchors, unseen mass/scope, row eligibility, and cell values, used to choose actions by expected task-risk reduction per cost and source dependence.

Entropy reduction alone is not valid credit: it can reward confident mistakes, duplicated evidence, or action-correlated uncertainty changes. Any training-time credit should therefore be validated with same-state counterfactuals, evidence provenance, cost/overlap controls, and an outcome or terminal-harm gate. This remains a preregistered research hypothesis, not an observed benchmark gain. The live execution order and exact evidence gates are recorded at the top of [`plan.md`](plan.md); the novelty audit is in [`survey.md`](survey.md).
