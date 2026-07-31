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

As of 2026-07-31 16:28 UTC, the frozen R1 run is at `175/220` terminal tasks (`35` completed, `140` failed, `45` remaining). This is terminal progress, not a benchmark score. The released evaluator has not run, so there is no official DeepWideBench score, Avg@4 result, leaderboard improvement, or SOTA claim.

V2.42.11 implements the label-blind entropy/VOC decision kernel and a real action-to-state runtime bridge for three contexts and nine context-action pairs. V2.42.12/13 freeze the selected entropy-component publisher over 18 decisions and 14 unique parent byte graphs. V2.42.12 failed closed on an upstream field-name mismatch without opening selected content or launching any API/benchmark work; V2.42.13 uses a new namespace and is now safely waiting for the search parent and Gate-2A to become terminal. It has not opened the selected model/report, acquired the shared lease, built a joint package, or authorized a benchmark launch. The active R1 and all healthy watchers remain untouched.

The latest literature audit keeps a deduplicated set of 156 papers and rechecks WebSwarm from its arXiv v1, full text, ablations, limitations, and public repository. Recursive atom/deep/wide/entity-collect delegation, web-structure probing, and sibling experience reuse are prior work, not the contribution here. The remaining candidate contribution is narrower: calibrated four-layer open-world task risk plus outcome-verified, provenance-aware credit, evaluated on a fresh exact-220 run after selected publication, joint-package, dev64, capacity, and single-owner launch gates open.

The literature review rules out broad novelty claims based only on entropy, information gain, dynamic deep/wide routing, coverage maps, denominator discovery, or information-weighted credit assignment. The narrower hypothesis still worth testing is a **calibrated four-layer open-world belief** over anchors, unseen mass/scope, row eligibility, and cell values, used to choose actions by expected task-risk reduction per cost and source dependence.

Entropy reduction alone is not valid credit: it can reward confident mistakes, duplicated evidence, or action-correlated uncertainty changes. Any training-time credit should therefore be validated with same-state counterfactuals, evidence provenance, cost/overlap controls, and an outcome or terminal-harm gate. This remains a preregistered research hypothesis, not an observed benchmark gain. The live execution order and exact evidence gates are recorded at the top of [`plan.md`](plan.md); the novelty audit is in [`survey.md`](survey.md).

The next full evaluation remains exact all-220. After R1 naturally releases the shared endpoint, the frozen `1/2/4/8/12 × 3 waves` neutral capacity ladder selects the highest continuously safe concurrency. A single owner must then run fresh `52/52/52/64` shards at fixed concurrency with no resume and failures counted as zero; no subset or completed-only result can replace this evaluation.
