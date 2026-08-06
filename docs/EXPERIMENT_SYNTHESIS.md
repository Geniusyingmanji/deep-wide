# Experiment synthesis and evidence ledger

Last evidence refresh: **2026-08-06 UTC**. This document separates measured quality, diagnostic evidence, implementation audits, and waiting control processes so that the large log collection is not mistaken for a large set of benchmark results.

## Executive conclusions

1. **The audited full-220 frontier is split, with no SOTA or Avg@4 result.** V2.42.67 has the best whole-table count, `7/220`, and Composite `0.413541`; V2.46.35 has the best Composite, `0.437892`, and `4/220` whole-table success. Both froze all 220 predictions before evaluator access. They are single rollouts on the consumed public task set, not held out and not directly equivalent to published Avg@4 results.
2. **The terminal R1 failure census is dominated by validation, semantics, provenance, and output contracts.** Its dated 2026-08-01 snapshot has 220/220 terminal tasks: 47 completed and 173 failed. At least 131 failures fall in explicitly named structural, semantic, provenance, or contract categories. Infrastructure abort and exhausted retryable model requests account for only four failures.
3. **Truncation is a major semantic-validation mechanism in R1.** Of the 28 stage-semantic-validation failures, 24 had every terminal semantic attempt's primary output truncated. Fixing prompt/output budgeting and structured continuation remains more directly supported than adding downstream controllers to that legacy pipeline.
4. **Retrieval and final entity selection are separate bottlenecks.** In the two-task anchor diagnostic, the official entity was present among candidates in 7 of 8 task-round observations, while exact final entity selection remained 0/8.
5. **The replays validate local invariants, not metric gains.** They show that alias canonicalization, mixed row domains, fixed-slot binding, membership predicates, attribute isolation, and column-fair query construction behave as intended on consumed states. They do not measure completion, F1, held-out generalization, cost reduction, or leaderboard improvement.
6. **V2.42.21–V2.42.44 are implementation/build audits.** They establish that specific modules or candidate adapters exist under tested contracts. They report no production runtime integration, real provider evaluation, benchmark score, quality/cost improvement, training improvement, or SOTA evidence.
7. **Host discovery is no longer the immediate mechanism bottleneck; independent verifier power is.** V2.43.61 completed 12/12 external tasks in 121.325s with exact two-batch discovery, no recursive split, no deadline/slot/helper failures, and a conserved ten-fetch cap. It unioned 317 registrable hosts, selected 120/120 sources, raised eligible parent support from 0 to two tasks/three sets, and naturally produced two parent candidates. Both candidates were reverted by the one-host hidden verifier, leaving zero utility-aligned retention and a strict NO-GO. The next same-budget intervention is 8 proposal + 2 hidden verifier hosts on a fresh external task vector; dev64/exact-220 remain unauthorized.
8. **V2.46.51–54 is the latest positive benchmark-external mechanism result, not a DeepWideBench score.** On 12 fresh ROR registry tasks, deterministic exact-name lookup against the authoritative registry changed exact-table success from `0/12` to `7/12`, Item F1 from `0.552083` to `0.927083`, and Composite from `0.888021` to `0.981771` under the same total fetch cap. The result supports identity- and target-bound structured recovery in that domain. It does not validate entropy credit or establish transfer to DeepWideBench.
9. **V2.46.79 is a complete fixed-denominator dev64 result and a strict NO-GO.** Its label-blind forward ran 64 fresh controls and eight fresh treated candidates in 305.128s; 56 untreated candidates reused their same-run controls exactly. All 72 children succeeded. The official post-freeze evaluator used 64 baseline judgments, seven changed-candidate judgments, and 57 prediction-identity reuses to score both arms on 64 tasks. Composite rose from 0.492059 to 0.492925, but whole-table success stayed 3/64, so the preregistered `+1` whole-table gate failed. The result does not authorize exact-220.
10. **The schema treatment reached the runtime but did not reliably reach task utility.** All eight treatment tasks applied the expanded schema, and seven predictions changed. Among those seven, the paired composite change was positive for one, zero for four, and negative for two; every whole-table and Entity score was unchanged. The parser is therefore a prerequisite for a future target-value intervention, not a standalone quality candidate. This historical dev64 population is not unseen, and independently sampled treated arms do not identify a pure parser effect.

## Audited V2.46.79 historical dev64 result

| Arm | Whole-table | Entity | Row F1 | Item F1 | Column F1 | Composite |
|---|---:|---:|---:|---:|---:|---:|
| Frozen parser control, n=64 | 3/64 | 0.718750 | 0.253472 | 0.448457 | 0.547557 | 0.492059 |
| Expanded-schema candidate, n=64 | 3/64 | 0.718750 | 0.256077 | 0.449156 | 0.547717 | 0.492925 |
| Candidate minus control | 0 | 0 | +0.002604 | +0.000699 | +0.000160 | +0.000866 |

The forward completed 72 real children in 305.128 seconds with zero runtime failure, fallback, or model-slot timeout. The evaluator completed in 177.119 seconds without selective re-evaluation. Three evaluator-invalid rows remained zeros in each fixed denominator. The paired composite 95% bootstrap interval was `[-0.001402, 0.004272]`; 61 task deltas were zero, one was positive, and two were negative. The only preregistered failed check was whole-table success `+1`.

The first launch attempt failed before lease acquisition or any child/API effect because the runner referenced an unbound `FORWARD_AUDIT` name. The zero-effect failure was sealed and the old execution-start revoked. An append-only recovery bound that name in a process-private namespace and reran the unchanged task, budget, child, and output contracts. Future launcher audits must include undefined-global checking and a pre-lease main-path dry run; import and function-level tests did not cover this defect.

## Audited full-220 frontier

| Protocol | Whole-table success | Entity accuracy | Row F1 | Item F1 | Column F1 | Quality composite |
|---|---:|---:|---:|---:|---:|---:|
| V2.42.67, full 220, one cold rollout, failure-as-zero | 7/220 = 3.1818% | 69.0909% | 20.1856% | 34.6810% | 41.4591% | 0.413541 |
| V2.46.35, full 220, one cold rollout, failure-as-zero | 4/220 = 1.8182% | 67.2727% | 22.4156% | 38.5078% | 46.9605% | 0.437892 |

V2.42.67 produced 217 model-generated tables and three canonical fallbacks. Its official evaluator returned 206 valid rows and 14 terminal errors. V2.46.35 produced 219 model-generated tables and one fallback; its evaluator returned 208 valid rows and 12 terminal errors. Each denominator remains 220, and neither run selectively re-evaluated errors. Their post-result audits report no findings, no mapping, gold, or evaluator access before prediction freeze, and no label-based routing.

V2.42.67 forward wall time was 3,655 seconds (60m55s), followed by 3,031 seconds (50m31s) for evaluation. V2.46.35 reduced these walls to 915.576 and 222.244 seconds. The earlier evaluator interval must not be described as search time. For V2.42.67, aggregate per-task wall was 14,449.368 seconds; divided across four workers its ideal lower bound is 3,612.342 seconds, showing that its outer scheduling was already about 98.8% efficient. Its avoidable cost was inside each task: 1,744 logical searches, 3,600 fetch attempts, and 34.51M total tokens, of which 28.45M (82.45%) came from the search transport. The frozen efficiency diagnosis is `results/v24267_exact220_efficiency_diagnosis_v1_20260802.json`.

V2.42.67 improves over the repository's historical GPT-5.5 single-run reference, but it is below the published A-MapReduce full-220 Avg@4 result on all five official metrics. It therefore supports a reliable current baseline and several engineering conclusions, not a leaderboard or SOTA claim.

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

## Terminal V2.40.3 R1 failure census

Source: `outputs/full220_v2403_r1_failure_clusters.json`, created at 2026-08-01 23:01:48 UTC.

- Terminal: **220/220**
- Completed forward states: **47**
- Failed forward states: **173**
- Remaining: **0**
- Label-blind: **true**
- Mapping or gold read: **false**
- Prediction emitted by the census process: **false**

| Failure cluster | Count | Share of 173 failures |
|---|---:|---:|
| Candidate or merge validation | 42 | 24.3% |
| Other forward failure | 38 | 22.0% |
| Stage semantic validation | 28 | 16.2% |
| Anchor unresolved after bounded recovery | 21 | 12.1% |
| Row-enrichment batch validation | 14 | 8.1% |
| Open-world coverage gate | 10 | 5.8% |
| Visible-date output contract | 8 | 4.6% |
| Bridge entity unresolved | 3 | 1.7% |
| Candidate discovery empty | 3 | 1.7% |
| Retryable model requests exhausted | 3 | 1.7% |
| Malformed URL ingestion | 2 | 1.2% |
| Infrastructure abort fixed to zero | 1 | 0.6% |

The 131 count in the executive conclusion is the sum of named structural, semantic, provenance, and contract clusters: candidate/merge validation, stage semantic validation, anchor and bridge resolution, candidate discovery, row-enrichment validation, coverage gate, visible-date contract, and malformed URL ingestion. It is a conservative classification; the 38 `other_forward_failure` cases are not reassigned. Validation-marker counts overlap and must not be summed as task counts.

### Resource accounting

The 220 terminal states accumulated:

- 569,880,181 system-total tokens;
- 20,468 search calls;
- 168,168 fetch calls, of which 43,027 failed;
- 650,591.274 aggregate task-wall seconds.

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

The legacy successor chain remains pre-result and is independent of the completed V2.46 results:

`V2.42.13 component recovery → V2.42.15 joint package → V2.42.16 package gate → V2.42.17 capacity ladder → V2.42.18 fresh exact-220 → V2.42.19 contamination audit → V2.42.20 source-dependency audit`

At this evidence refresh, protected V2.42.18 watcher PID `3061652` remains at `waiting_for_v24216_package_gate_terminal`; it has no execution-start, benchmark forward, evaluator result, or authority for the V2.46.79 candidate. A live watcher proves only that the control process is present and must not be restarted or duplicated.

## What the evidence supports

- R1 is a complete failure-distribution and cost census under a label-blind forward boundary.
- Validation/provenance/contract failures deserve priority over adding more speculative control modules.
- Semantic truncation requires a targeted mitigation and replay before another expensive full run.
- Candidate retrieval must be evaluated separately from final anchor selection.
- The local replays provide regression tests for narrow runtime invariants.
- The project has full-220, dev64, and benchmark-external quality evidence, while many implementation artifacts remain upstream of empirical effectiveness testing.

## What the evidence does not support

- Avg@4, Max@4, Pass@4, leaderboard submission, or SOTA.
- A single method that simultaneously exceeds the current `7/220` whole-table and `0.437892` Composite frontiers.
- A causal quality gain from entropy, OWIC/credit, WebSwarm, or any V2.42 build-only component.
- Measured cost reduction from theoretical batching floors or zero-call replays.
- Held-out generalization, leaderboard submission, or SOTA.
- Treating completed forward states as evaluator-defined whole-table successes.

## Recommended experiment order

1. Freeze the V2.46.35 parser and reliability pipeline as the control. Do not tune further on the consumed public 220 or rerun the V2.46.79 historical dev64.
2. On a fresh benchmark-external table population, compare three arms: frozen parser, expanded parser only, and expanded parser plus addressable target–value evidence, deterministic cell admission, and an independent completion check.
3. Require a strict whole-table gain and non-regression in Composite, Entity, Row F1, Item F1, and Column F1 under fixed denominators and failure-as-zero accounting. Treat entropy or information gain only as a shadow ranking signal after identity and target–value binding.
4. Promote a candidate to a separately preregistered DeepWideBench gate only if the external mechanism and quality gates both pass. Preserve the runtime boundary `{opaque_id, question}` and freeze both arms before any mapping or evaluator access.
5. Authorize a new exact-220 design only after that gate passes. The full run must include all 220 tasks, prohibit resume and selective retry, and report every preregistered metric.
6. If a single rollout clears both current frontiers, run three additional independent rollouts before reporting Avg@4, Max@4, or Pass@4. SOTA still requires a valid same-protocol external comparison or leaderboard evidence.
7. Evaluate entropy-credit claims with same-state intervention or post-freeze outer utility. Parser reachability, prediction change, and entropy reduction cannot determine a positive credit sign by themselves.

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
