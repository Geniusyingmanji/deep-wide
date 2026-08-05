# Experiment synthesis and evidence ledger

Last evidence refresh: **2026-08-05 20:35 UTC**. This document separates measured quality, diagnostic evidence, implementation audits, and waiting control processes so that the large log collection is not mistaken for a large set of benchmark results.

## Executive conclusions

1. **There are two audited current full-220 single-rollout scores, but no SOTA or Avg@4 result.** The best remains V2.42.67: it froze all 220 predictions before evaluator access and reports 3.1818% whole-table success, 69.09% Entity accuracy, 20.19% Row F1, 34.68% Item F1, and 41.46% Column F1 with all 14 evaluator errors retained as zeros. V2.42.87 was worse at 5/220 and Composite 0.395991. These are consumed public-resource single rollouts, not held out and not directly equivalent to published Avg@4 results.
2. **Known R1 failures are dominated by validation, semantics, provenance, and output contracts.** At the latest snapshot, 200/220 tasks are terminal: 40 completed and 160 failed. At least 121 of the 160 failures are in explicitly named structural, semantic, provenance, or contract categories. Infrastructure abort and exhausted retryable model requests account for only 4 failures.
3. **Truncation is a major semantic-validation mechanism.** Of the 25 stage-semantic-validation failures, 21 had every terminal semantic attempt's primary output truncated. Fixing prompt/output budgeting and structured continuation is a higher-priority intervention than adding more downstream controllers.
4. **Retrieval and final entity selection are separate bottlenecks.** In the two-task anchor diagnostic, the official entity was present among candidates in 7 of 8 task-round observations, while exact final entity selection remained 0/8.
5. **The replays validate local invariants, not metric gains.** They show that alias canonicalization, mixed row domains, fixed-slot binding, membership predicates, attribute isolation, and column-fair query construction behave as intended on consumed states. They do not measure completion, F1, held-out generalization, cost reduction, or leaderboard improvement.
6. **V2.42.21–V2.42.44 are implementation/build audits.** They establish that specific modules or candidate adapters exist under tested contracts. They report no production runtime integration, real provider evaluation, benchmark score, quality/cost improvement, training improvement, or SOTA evidence.
7. **Host discovery is no longer the immediate mechanism bottleneck; independent verifier power is.** V2.43.61 completed 12/12 external tasks in 121.325s with exact two-batch discovery, no recursive split, no deadline/slot/helper failures, and a conserved ten-fetch cap. It unioned 317 registrable hosts, selected 120/120 sources, raised eligible parent support from 0 to two tasks/three sets, and naturally produced two parent candidates. Both candidates were reverted by the one-host hidden verifier, leaving zero utility-aligned retention and a strict NO-GO. The next same-budget intervention is 8 proposal + 2 hidden verifier hosts on a fresh external task vector; dev64/exact-220 remain unauthorized.
8. **The V2.45 collector repair is operationally valid, but title-validatable acquisition is still a strict mechanism NO-GO.** V2.45.87 ran one fresh 8-task/64-entity external wave after a 220/220 preactivation suite. It completed 8/8 workers and capabilities in 149.965s with no timeout, nonzero exit, recursive collector, lease, watcher, or post-audit finding. Pre-dedup preservation was active on all eight tasks and retained 195 same-source candidates; two tasks reached source-representative replacement. Yet all three observed title-surface hits belonged to excluded sources, leaving zero selected title hit and zero validator-aligned title replacement. V2.45.88 therefore authorizes only a query–validator alignment policy, not dev64 or exact-220. V2.45.89–93 implement that same-budget policy and pass a 72/72 clean-build audit; a fresh external protocol is not yet frozen or launched.

## Audited V2.42.67 exact-220 result

| Protocol | Whole-table success | Entity accuracy | Row F1 | Item F1 | Column F1 | Quality composite |
|---|---:|---:|---:|---:|---:|---:|
| V2.42.67, full 220, one cold rollout, failure-as-zero | 7/220 = 3.1818% | 69.0909% | 20.1856% | 34.6810% | 41.4591% | 0.413541 |

The forward produced 217 model-generated tables and three canonical fallbacks. The official evaluator returned 206 valid rows and 14 terminal errors; the denominator remains 220 and no error was selectively re-evaluated. The post-result audit reports no findings, no mapping/gold/evaluator access before the exact-220 prediction freeze, and no label-based routing.

Forward wall time was 3,655 seconds (60m55s). The subsequent evaluator took 3,031 seconds (50m31s), so that interval must not be described as search time. Aggregate per-task wall was 14,449.368 seconds; divided across four workers its ideal lower bound is 3,612.342 seconds, showing that outer scheduling was already about 98.8% efficient. The avoidable cost is inside each task: 1,744 logical searches, 3,600 fetch attempts, and 34.51M total tokens, of which 28.45M (82.45%) came from the search transport. The frozen efficiency diagnosis is `results/v24267_exact220_efficiency_diagnosis_v1_20260802.json`.

This single rollout improves over the repository's historical GPT-5.5 single-run reference, but it is below the published A-MapReduce full-220 Avg@4 result on all five official metrics. It therefore supports a reliable current baseline and several engineering conclusions, not a leaderboard or SOTA claim.

## Evidence hierarchy

| Tier | Evidence type | What it can support | What it cannot support |
|---|---|---|---|
| A | Frozen prediction plus released evaluator | Quality metrics under that exact protocol | Generalization beyond the protocol; SOTA without a valid comparison |
| B | Forward-only terminal run | Completion/failure census, resource use, mechanism prevalence | Accuracy, F1, leaderboard position |
| C | Deterministic consumed-state replay | Local transformation, validation, or query-plan behavior | Fresh-task quality or causal improvement |
| D | Build/test audit | Implementation availability and test-contract integrity | Runtime effectiveness, cost or quality improvement |
| E | Preregistration/waiting watcher | Intended ordering, isolation, and process liveness | Any experimental effect or score |

All claims below follow the highest applicable tier. In particular, `terminal`, `completed`, and `failed` describe forward states, whereas `success_rate` is an evaluator-derived quality metric.

## Quality and diagnostic results

| Artifact | Protocol | Whole-table success | Entity accuracy | Row F1 | Item F1 | Column F1 | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| `baseline_gpt55_20260623.json` | Historical public full set, n=220, one GPT-5.5 rollout | 5/220 = 2.27% | 67.73% | 19.48% | 34.14% | 41.03% | Diagnostic reference only; not strict current isolation, no contamination scan, not Avg@4 |
| `patched_dev8_v2191_20260720.json` | Public dev, n=8, conservative all-task accounting | 12.50% | 37.50% | 18.53% | 25.30% | 28.08% | Small engineering pilot; one resumed checkpoint and one evaluator-invalid task |
| same artifact, valid-only view | Public dev, n=7 | 14.29% | 42.86% | 21.17% | 28.92% | 32.09% | Descriptive valid-only view; excluding the invalid task does not make it held out |
| `anchor_replay_dev2_v2201_v2204_20260721.json` | Two reused public-dev tasks, four rounds | — | Exact entity 0/2 in every round | — | — | — | Candidate recall was 2/2 in rounds 1, 2, and 4 and 1/2 in round 3; selection remained wrong |

These rows must not be compared as a model-improvement sequence: the task sets, isolation boundaries, run counts, and validity rules differ.

The anchor diagnostic consumed 298,303 tokens, 24 search queries, 86 HTTP attempts with 6 failures, and 509.437 aggregate seconds. Those costs describe the diagnostic only and do not establish a quality/cost trade-off.

## Current V2.40.3 R1 failure census

Source: `outputs/full220_v2403_r1_failure_clusters.json`, created at 2026-08-01 07:45:17 UTC.

- Terminal: **200/220**
- Completed forward states: **40**
- Failed forward states: **160**
- Remaining: **20**
- Label-blind: **true**
- Mapping or gold read: **false**
- Prediction emitted by the census process: **false**

| Failure cluster | Count | Share of 160 failures |
|---|---:|---:|
| Candidate or merge validation | 41 | 25.6% |
| Other forward failure | 35 | 21.9% |
| Stage semantic validation | 25 | 15.6% |
| Anchor unresolved after bounded recovery | 18 | 11.3% |
| Row-enrichment batch validation | 13 | 8.1% |
| Open-world coverage gate | 8 | 5.0% |
| Visible-date output contract | 8 | 5.0% |
| Bridge entity unresolved | 3 | 1.9% |
| Candidate discovery empty | 3 | 1.9% |
| Retryable model requests exhausted | 3 | 1.9% |
| Malformed URL ingestion | 2 | 1.3% |
| Infrastructure abort fixed to zero | 1 | 0.6% |

The 121 count in the executive conclusion is the sum of named structural/semantic/provenance/contract clusters: candidate/merge validation, stage semantic validation, anchor and bridge resolution, candidate discovery, row-enrichment validation, coverage gate, visible-date contract, and malformed URL ingestion. It is a conservative classification; the 35 `other_forward_failure` cases are not reassigned. Validation-marker counts overlap and must not be summed as task counts.

### Resource accounting

The 200 terminal states accumulated:

- 512,330,207 system-total tokens;
- 18,315 search calls;
- 150,534 fetch calls, of which 38,131 failed;
- 595,638 aggregate task-wall seconds.

Aggregate task-wall seconds sum per-task durations and are **not** elapsed campaign time. The high fetch-failure count is operationally relevant, but the terminal failure taxonomy does not support attributing most task failures to infrastructure.

## Mechanism replay findings

| Replay | Observed behavior | Supported conclusion | Boundary |
|---|---|---|---|
| V2.39.3 visible-format/person-alias | Canonicalization reduced 25 candidate rows to 19 and correctly failed the visible lower bound `19 < 21` | Coverage and rendering can share a canonical row set and fail closed after alias merging | One consumed task; zero calls; no quality score |
| V2.39.4 mixed row domain | A country × fixed-year task materialized 6 rows to 24 and passed its structural gate; another task remained `44 < 54` | Deterministic fixed dimensions can repair a specific row-domain representation without indiscriminate promotion | Two consumed failed tasks; no cell correctness evidence |
| V2.39.8 fixed-slot entity | All 38/38 generated queries retained supported make/model/year bindings; unknown-row accounting changed 0 to 4 | Query binding and unknown-cell accounting are reachable and deterministic | One consumed state; no model/search/evaluator calls |
| V2.40.1 membership ledger | Two source states remained byte-identical; partial predicates were rejected; zero publishable rows failed even with lower bound zero | Membership eligibility and zero-row fail-closed invariants hold in replay | No fresh evidence or score |
| V2.40.2 attribute isolation | 14 and 119 membership-like fields were ignored while row and membership projections stayed unchanged | Attribute refinement can be isolated from membership state | Batch floors 2 and 13 versus historical 20 and 135 calls are theoretical, not measured savings |
| V2.40.3 column-fair/caption | Two consumed completed states passed output contracts; one task's 148 risk pairs were covered by 72 initial and 96 refinement queries | The query planner covers the declared column-risk pairs and preserves verified captions | Zero-call replay; no correctness or efficiency result |

## Build-only audits and waiting protocols

The V2.42.21–V2.42.44 artifacts should be read as one implementation stream rather than 24 benchmark experiments. They cover predicate/exhaustion baselines, sign-preserving and role-typed credit components, outer-target integrity primitives, WebSwarm guidance/budget/effect primitives, provider metering/adapters, durable effect journaling/co-ordination, retry deadlines, and strict settled-JSON parsing.

Across their own `claims` fields, these artifacts explicitly deny one or more of the following: production runtime integration, real provider execution, real independent intervention pairs, benchmark score, benchmark improvement, measured quality/cost effect, training improvement, leaderboard submission, and SOTA. The quarantined pre-freeze V2.42.24 artifact under `results/DO_NOT_USE_invalid_v24224_pre_freeze/` must not be cited.

The active successor chain is also pre-result:

`V2.42.13 component recovery → V2.42.15 joint package → V2.42.16 package gate → V2.42.17 capacity ladder → V2.42.18 fresh exact-220 → V2.42.19 contamination audit → V2.42.20 source-dependency audit`

At the evidence refresh, V2.42.13 was waiting on its search and Gate-2A parents; V2.42.16, V2.42.18, V2.42.19, and V2.42.20 were consequently waiting on upstream terminal states. Their state files report no benchmark forward/evaluator result. A live watcher proves only that the control process is present.

## What the evidence supports

- R1 is useful as a failure-distribution and cost census under a label-blind forward boundary.
- Validation/provenance/contract failures deserve priority over adding more speculative control modules.
- Semantic truncation requires a targeted mitigation and replay before another expensive full run.
- Candidate retrieval must be evaluated separately from final anchor selection.
- The local replays provide regression tests for narrow runtime invariants.
- The project has a substantial implementation and safety-control surface, but most recent artifacts remain upstream of empirical effectiveness testing.

## What the evidence does not support

- A current official DeepWideBench score, Avg@4, Max@4, or Pass@4 result.
- Improvement over the historical GPT-5.5 baseline or the patched dev pilot.
- A causal quality gain from entropy, OWIC/credit, WebSwarm, or any V2.42 build-only component.
- Measured cost reduction from theoretical batching floors or zero-call replays.
- Held-out generalization, leaderboard submission, or SOTA.
- Treating completed forward states as evaluator-defined whole-table successes.

## Recommended experiment order

1. Let R1 reach 220/220 only to close the forward failure census; preserve its no-gold boundary.
2. Triage the 41 candidate/merge failures and 25 semantic failures first. Add explicit tests for the dominant provenance markers and for continuation after truncated primary output.
3. Run a small, frozen, cold-start paired development ablation on the same opaque tasks, with identical model/search budgets, failure-as-zero accounting, and evaluator access only after both arms freeze.
4. Promote a candidate only if completion and quality gates pass without a material resource regression. Report all preregistered metrics, not only favorable subsets.
5. Run one fresh exact-220 evaluation under the isolated released evaluator. Do not resume, selectively retry, or remove contamination/dependency-sensitive tasks from the official denominator.
6. If the single rollout is competitive, run three additional independent rollouts before reporting Avg@4/Max@4/Pass@4.
7. Evaluate entropy/credit claims with same-state interventions and outcome verification; implementation tests alone are insufficient.

## Storage and update policy

- Compact, credential-free evidence summaries belong in `results/`.
- Human-readable cumulative conclusions belong in this file under `docs/`.
- Large task states, logs, caches, and prototype trees belong under ignored `outputs/`; they must not be committed.
- On 2026-08-01, 39 historical `deep-v*` prototype trees (about 68 MB) were moved from the `zyf/` root to `outputs/prototype_workspaces/`. Because frozen scripts and waiting protocols contain their original absolute paths, root-level `deep-v*` compatibility entries are symlinks only; all physical files now remain under `deep/`.
- Invalid artifacts stay in clearly named `DO_NOT_USE` or `TAINTED` directories.
- Each refresh must record a UTC snapshot time, source paths, protocol status, denominator, evaluator boundary, and limitations.
- Do not silently replace a snapshot with live values. Add or revise the dated statement and preserve the evidence artifact.

## Evidence index

- Historical quality reference: `results/baseline_gpt55_20260623.json`
- Historical status/limitations mirror: `results/historical_full220_gpt55_single_rollout_20260623.json`
- Patched public-dev pilot: `results/patched_dev8_v2191_20260720.json`
- Anchor diagnostic: `results/anchor_replay_dev2_v2201_v2204_20260721.json`
- R1 live failure census: `outputs/full220_v2403_r1_failure_clusters.json`
- Mechanism replays: `results/v2393_visible_format_person_alias_replay_20260723.json`, `results/v2394_mixed_row_domain_replay_20260723.json`, `results/v2398_fixed_slot_entity_replay_20260723.json`, `results/v2401_membership_ledger_replay_v2400_20260724.json`, `results/v2402_attribute_isolation_replay_v2401_20260725.json`, and `results/v2403_column_fair_caption_replay_v2402_20260725.json`
- Detailed chronological control history: `plan.md`
- Literature and novelty boundaries: `survey.md`
