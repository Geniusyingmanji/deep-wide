# U-DeepWide Research And Implementation Plan

## 1. Project Goal

Build and evaluate **U-DeepWide**, a training-free search-agent controller for DeepWide web-to-table tasks. The core claim is:

> DeepWide failures come from two separable runtime uncertainties: whether the candidate set is complete enough (**width uncertainty**) and whether each discovered entity's attributes are evidence-grounded enough (**depth uncertainty**). A controller that estimates both can allocate search budget better than fixed wide-then-deep, generic ReAct, or subjective LLM planner policies.

The project should avoid claiming that uncertainty, verification, or stopping are individually new. The defensible novelty is the **task-specific coupling**:

- Open-world candidate coverage uncertainty.
- Cell-level evidence credibility uncertainty.
- Dynamic budget routing between discovery, verification, counter-evidence search, and stopping.
- Evaluation on DeepWide-style structured table outputs with explicit cost-quality trade-offs.

## 2. Research Questions

1. **RQ1: Performance**
   Does U-DeepWide improve Row F1, Item F1, Column F1, and Success Rate on DeepWideSearch compared with strong search-agent and web-to-table baselines?

2. **RQ2: Cost Efficiency**
   Does uncertainty-aware routing reach the same or better Item F1 with fewer tool calls, tokens, wall-clock time, and API cost?

3. **RQ3: Width Uncertainty Quality**
   Does width uncertainty predict remaining undiscovered gold rows or low row recall?

4. **RQ4: Depth Uncertainty Quality**
   Does depth uncertainty predict wrong, unsupported, or contradicted table cells?

5. **RQ5: Mechanism**
   Which component matters most: width uncertainty, depth uncertainty, counter-evidence verification, or marginal coverage stopping?

## 3. Related Work Positioning

### 3.1 Closest Work

- **DeepWideSearch** (`arXiv:2510.20168`): benchmark showing current agents struggle with simultaneous depth and width. Reported best Avg@4 SR around 2.39% in the paper's main table.
- **Table-as-Search** (`arXiv:2602.06724`): reformulates long-horizon information seeking as table completion, with row expansion and cell population. U-DeepWide must beat or clearly differ from TaS by using calibrated uncertainty signals instead of only planner judgment.
- **Web2BigTable** (`arXiv:2604.27221`): strong web-to-table system, reports WideSearch Avg@4 SR 38.50. It is a key wide-search baseline.
- **A-MapReduce** (`arXiv:2602.01331`): very close to the target setup, reports WideSearch/DeepWideSearch cost-performance improvements and DeepWideSearch SR around 4.43. It must be treated as a strong baseline if reproducible.
- **Agentic Uncertainty Quantification** (`arXiv:2601.15703`): turns agent uncertainty into runtime control signals. U-DeepWide should position itself as a DeepWide/table-specific specialization.
- **WebUncertainty** (`arXiv:2604.17821`): dual-level uncertainty for web agents, focused on planning/action uncertainty and MCTS. U-DeepWide's uncertainty axes are different: candidate coverage and cell evidence credibility.
- **Asymmetric Verification** (`arXiv:2510.06135`), **FineVerify** (`arXiv:2606.00660`), **Marco DeepResearch** (`arXiv:2603.28376`): verification-centric deep search. U-DeepWide's verifier should be framed as cell-level counter-evidence verification, not generic self-verification.
- **AutoSearch** (`arXiv:2604.17337`) and **SlimSearcher** (`arXiv:2606.07074`): adaptive search depth and cost-aware search. U-DeepWide's stopping should focus on open-world entity enumeration and coverage saturation.
- **TreeSeeker** (`arXiv:2606.11662`): tree-structured uncertainty/risk/value control for deep search. U-DeepWide can borrow the idea of explicit operation utilities but applies it to table state.

### 3.2 Differentiation Statement

U-DeepWide differs from prior work by making the **table itself the uncertainty state**:

- Width state is measured over discovered canonical rows and recent discovery yield.
- Depth state is measured over evidence clusters for each table cell.
- The controller chooses operations by estimated uncertainty reduction per cost.
- Stopping is triggered by coverage saturation and cell credibility, not by fixed steps or final-answer confidence alone.

## 4. System Overview

### 4.1 High-Level Flow

1. Parse user task into a target table schema.
2. Initialize an external workboard/table state.
3. Repeatedly choose one operation:
   - `discover_entities`: broad search for new candidate rows.
   - `verify_cell`: find supporting evidence for a missing or uncertain cell.
   - `falsify_cell`: actively search for counter-evidence against a proposed cell value.
   - `backfill_missing`: fill cells for rows with known entities but missing attributes.
   - `stop_and_finalize`: emit final normalized table.
4. After every operation, update evidence, uncertainty, cost, and trace logs.
5. Stop when width uncertainty and depth uncertainty are below thresholds, or when marginal value is lower than budget-adjusted cost.

### 4.2 Proposed Repository Layout

```text
deep/
  plan.md
  src/udeepwide/
    __init__.py
    cli.py
    config.py
    schema.py
    state.py
    search_tools.py
    extraction.py
    verification.py
    uncertainty.py
    controller.py
    finalizer.py
    logging.py
    evaluators/
      deepwide.py
      widesearch.py
      browsecomp.py
  configs/
    default.yaml
    deepwide.yaml
    widesearch.yaml
    ablations/
  prompts/
    schema_builder.md
    entity_discovery.md
    cell_extractor.md
    counter_evidence.md
    cell_judge.md
    finalizer.md
  scripts/
    run_task.py
    run_benchmark.py
    summarize_runs.py
    plot_pareto.py
  outputs/
    runs/
    reports/
  tests/
    test_uncertainty.py
    test_controller.py
    test_dedup.py
    test_metrics.py
```

## 5. Core Data Structures

### 5.1 Query State

```python
@dataclass
class QueryState:
    query_id: str
    user_query: str
    schema: TableSchema
    rows: dict[str, EntityRow]
    issued_queries: list[SearchQuery]
    operation_log: list[OperationTrace]
    token_cost: int
    api_cost_usd: float
    remaining_budget: Budget
    width_uncertainty: float
    max_depth_uncertainty: float
```

### 5.2 Table Schema

```python
@dataclass
class TableSchema:
    entity_key: str
    required_columns: list[str]
    constraint_columns: list[str]
    optional_columns: list[str]
    output_format: str = "markdown_table"
```

### 5.3 Entity Row

```python
@dataclass
class EntityRow:
    row_id: str
    canonical_name: str
    aliases: list[str]
    discovery_evidence: list[Evidence]
    cells: dict[str, CellState]
    row_confidence: float
    row_status: Literal["candidate", "valid", "rejected", "duplicate", "needs_review"]
```

### 5.4 Cell State

```python
@dataclass
class CellState:
    column: str
    value: str | None
    support: list[Evidence]
    contradict: list[Evidence]
    not_found_queries: list[SearchQuery]
    semantic_clusters: list[ClaimCluster]
    depth_uncertainty: float
    status: Literal["missing", "proposed", "supported", "contradicted", "not_found", "verified"]
```

### 5.5 Evidence

```python
@dataclass
class Evidence:
    url: str
    title: str
    snippet: str
    retrieved_at: str
    source_type: Literal["official", "primary", "secondary", "aggregator", "unknown"]
    relation: Literal["supports", "contradicts", "mentions", "irrelevant"]
    extractor_confidence: float
```

## 6. Uncertainty Modeling

### 6.1 Width Uncertainty `Uw`

Purpose: estimate whether enough candidate entities have been discovered.

Signals:

- **Marginal discovery yield**: new canonical entities per search query or per 1k tokens.
- **Recent saturation**: fraction of recent discovery queries returning only already-known entities.
- **Query diversity**: coverage of source families, languages, time windows, synonyms, and domain-specific terms.
- **Source diversity**: whether discoveries come from multiple independent source types.
- **Constraint survival**: how many discovered entities survive row-level constraints.
- **Optional unseen-mass estimate**: Good-Turing/capture-recapture style estimate over entity mentions from independent query families.

Initial practical formula:

```text
new_yield_t = new_entities_t / max(tokens_t / 1000, 1)
yield_ma = moving_average(new_yield, window=K)
saturation = duplicate_entities_recent / max(total_entities_recent, 1)
source_gap = 1 - normalized_source_family_coverage
query_gap = 1 - normalized_query_family_coverage

Uw = clip(
  w1 * exp(-alpha * yield_ma)
  + w2 * source_gap
  + w3 * query_gap
  + w4 * constraint_survival_uncertainty
  - w5 * saturation,
  0,
  1
)
```

Interpretation:

- High `Uw`: continue broad discovery.
- Low `Uw`: likely coverage saturation, unless row constraints changed or new query families are unexplored.

Important caveat:

- No-new-entities does not prove completeness. To avoid query bias, saturation must be measured across diverse query families, not just repeated similar queries.

### 6.2 Depth Uncertainty `Ud`

Purpose: estimate whether a cell value is accurate and sufficiently evidence-grounded.

Signals:

- **Semantic disagreement**: different search paths extract semantically incompatible values.
- **Support strength**: number and quality of independent supporting evidence items.
- **Counter-evidence strength**: whether falsification queries find explicit contradictions.
- **Not-found ambiguity**: repeated failure to find evidence for a claim.
- **Source reliability**: official/primary sources reduce uncertainty more than aggregators.
- **Internal-knowledge penalty**: any value without cited external evidence remains high uncertainty.
- **Freshness requirement**: if the query is time-sensitive, stale sources carry less weight.

Initial practical formula:

```text
conflict = semantic_entropy_or_cluster_disagreement(cell.claim_clusters)
support_score = sum(source_weight(e) for e in cell.support)
contradict_score = sum(source_weight(e) for e in cell.contradict)
not_found_penalty = min(len(cell.not_found_queries) / N, 1) * beta
unsupported_penalty = 1 if value_exists_without_support else 0

Ud = clip(
  a1 * conflict
  + a2 * sigmoid(contradict_score)
  + a3 * unsupported_penalty
  + a4 * not_found_penalty
  - a5 * sigmoid(support_score),
  0,
  1
)
```

Cell status policy:

- `verified`: strong support, no strong contradiction, low `Ud`.
- `supported`: enough evidence for F1 output, but weaker than verified.
- `contradicted`: contradiction stronger than support.
- `not_found`: no evidence found after sufficient targeted retrieval.
- `missing`: no value proposed.

### 6.3 Aggregate Depth Uncertainty

```text
Ud_row = max_or_weighted_mean(Ud(cell) for required cells in row)
Ud_table = max(top_m(Ud_row), missing_cell_rate, contradicted_cell_rate)
```

Use max/top-k rather than mean, because a small number of wrong cells can destroy exact table success.

## 7. Controller And Routing

### 7.1 Candidate Operations

At each step, generate candidate operations:

1. Broad discovery query for unexplored query family.
2. Focused discovery query for a suspected coverage gap.
3. Support query for a high-`Ud` cell.
4. Falsification query for a proposed cell value.
5. Backfill query for missing cells in otherwise valid rows.
6. Stop and finalize.

### 7.2 Utility Model

Each operation receives an expected value per cost:

```text
U(discover) = E[delta_row_recall | state] / E[cost]
U(verify) = E[delta_cell_precision + delta_item_f1 | state] / E[cost]
U(falsify) = E[reduction_in_false_positive_risk | state] / E[cost]
U(backfill) = E[delta_item_recall | state] / E[cost]
U(stop) = E[final_score | current_state] - risk_penalty(Uw, Ud_table)
```

MVP implementation can use deterministic heuristics:

```text
if Uw > tau_w and marginal_gain > min_gain_threshold:
    discover_entities
elif max_cell_Ud > tau_d:
    if cell_has_support and not yet falsified:
        falsify_cell
    else:
        verify_cell
elif missing_cell_rate > tau_missing:
    backfill_missing
else:
    stop_and_finalize
```

Full implementation can replace hard rules with a contextual bandit or textual UCB-style operation selector:

```text
score(op) = value_estimate(op) + c * uncertainty_estimate(op) - risk_penalty(op) - cost_penalty(op)
```

### 7.3 Budget-Aware Marginal Coverage Stopping

Avoid calling this "optimal stopping" unless a formal bound is added. Use:

> Budget-aware marginal coverage stopping.

Stop broad discovery when:

```text
moving_avg(new_entities_per_1k_tokens) < dynamic_cost_threshold
AND query_family_coverage >= min_query_family_coverage
AND source_family_coverage >= min_source_family_coverage
AND no_required_constraint_gap_detected
```

Dynamic threshold:

```text
dynamic_cost_threshold = lambda_cost * expected_value_per_entity(remaining_budget, task_size_estimate)
```

Stop whole task when:

```text
Uw < tau_w_stop
AND max_required_cell_Ud < tau_d_stop
AND missing_required_cell_rate < tau_missing_stop
AND final_table_schema_valid
```

Emergency stop:

- Remaining budget below minimum cost of one full discovery/verification loop.
- Repeated tool failures across independent sources.
- Context or runtime cap reached; emit best table with uncertainty annotations in logs, not final answer.

## 8. Counter-Evidence Verification

### 8.1 Purpose

Reduce confirmation bias and internal-knowledge hallucinations by actively looking for evidence that would make a proposed cell value false.

### 8.2 Procedure

For each proposed high-value or high-risk cell:

1. Convert claim into a checkable statement.
2. Generate 2-4 counter-evidence queries:
   - direct negation,
   - exclusion criteria,
   - alternative value,
   - official-source query.
3. Retrieve and read sources.
4. Judge evidence as `supports`, `contradicts`, `not_found`, or `irrelevant`.
5. Update `Ud`.

Example:

```text
Claim: Clinical trial A allows patients with brain metastases.
Counter-evidence queries:
- "Clinical trial A exclusion criteria brain metastases"
- "Clinical trial A excluded CNS metastases"
- site:clinicaltrials.gov "Clinical trial A" "brain metastases" "exclusion"
```

Policy:

- "No contradiction found" lowers `Ud` only if search covered strong source families.
- It does not prove the claim true.
- Internal model explanations are never evidence.

## 9. Implementation Milestones

### Milestone 0: Environment And Minimal Tooling

Deliverables:

- Python package skeleton under `src/udeepwide`.
- Config loader.
- Search/read abstraction wrapping available web search and page reader tools.
- JSONL trace logger.
- Minimal Markdown table finalizer.

Success criteria:

- One task can run end-to-end with traces and final table.

### Milestone 1: Table State And Schema Builder

Deliverables:

- `TableSchema`, `EntityRow`, `CellState`, `Evidence` dataclasses.
- Prompt for schema extraction.
- Entity canonicalization and deduplication.
- Table validation: required columns, duplicate rows, empty cells.

Success criteria:

- Given a DeepWide-style query, system creates a valid schema and maintains table state across operations.

### Milestone 2: Discovery And Extraction

Deliverables:

- Entity discovery prompt and parser.
- Query family generator:
  - official source,
  - aggregator/list source,
  - time-window query,
  - synonym/alias query,
  - multilingual query when relevant.
- Cell extractor with evidence snippets.
- Dedup and alias merge.

Success criteria:

- On a small manual set, row discovery recall increases over repeated diverse queries.

### Milestone 3: Depth Verification

Deliverables:

- Support-evidence retrieval.
- Counter-evidence query generation.
- Cell-level evidence judge.
- `Ud` computation and status transitions.

Success criteria:

- Unsupported model-filled cells remain high uncertainty.
- Contradicted cells are flagged and either repaired or left blank.

### Milestone 4: Width Uncertainty And Stopping

Deliverables:

- `Uw` computation from discovery yield, saturation, query diversity, and source diversity.
- Budget-aware marginal coverage stopping.
- Coverage diagnostics in trace logs.

Success criteria:

- On tasks with small known entity sets, system stops earlier than fixed-step search without large recall loss.
- On tasks with large entity sets, system continues broad discovery rather than prematurely stopping.

### Milestone 5: Full Controller

Deliverables:

- Rule-based controller.
- Optional textual UCB controller.
- Operation utility logging.
- Configurable thresholds.

Success criteria:

- Controller visibly alternates between discovery and verification based on state, rather than using fixed phases.

### Milestone 6: Evaluation Harness

Deliverables:

- DeepWideSearch runner.
- WideSearch runner.
- BrowseComp/XBench-DeepSearch runner if formats are available.
- Metric parser for SR, Row F1, Item F1, Column F1, CE Acc.
- Cost metrics:
  - prompt tokens,
  - completion tokens,
  - tool calls,
  - pages read,
  - wall-clock time,
  - estimated API cost.
- Pareto plot script.

Success criteria:

- Runs produce aggregate JSON, Markdown report, and cost-performance plots.

## 10. Benchmarks

### 10.1 Primary Benchmark

#### DeepWideSearch

Use for the main paper claim.

Metrics:

- Success Rate.
- Row F1.
- Item F1.
- Column F1.
- Core Entity Accuracy.
- Avg@N and Pass@N if multiple attempts are run.
- Token/tool/cost metrics.

Subsets:

- Wide2Deep.
- Deep2Wide.
- Topic/domain breakdown if provided by benchmark metadata, only for offline analysis after predictions are complete.

Important leakage rule:

- Ground truth tables, labels, topic categories, and evaluator-only metadata must never be visible to runtime prompts, routing, memory retrieval, or verifier logic.

### 10.2 Secondary Benchmark

#### WideSearch

Purpose:

- Isolate broad candidate discovery and table construction.

Metrics:

- Success Rate.
- Row F1.
- Item F1.
- Cost per successful table.
- New entities per 1k tokens.

Expected finding:

- U-DeepWide should be competitive, but may not beat Web2BigTable/A-MapReduce on pure wide search unless width stopping and dedup are strong.

### 10.3 Depth-Oriented Benchmark

#### BrowseComp / BrowseComp-Plus / XBench-DeepSearch

Purpose:

- Test whether cell-level verification and counter-evidence search help on deep single-answer or multi-hop tasks.

Metrics:

- Accuracy.
- Evidence recall if available.
- Verification cost.

Expected finding:

- U-DeepWide may be less specialized here. Use as diagnostic, not main claim.

### 10.4 Optional Domain Stress Test

Clinical-trial matching or business-development scouting tasks.

Purpose:

- Demonstrate real-world DeepWide motivation.

Requirements:

- Manually curated small gold tables.
- Clear source policy.
- No protected/private data.

## 11. Baselines

### 11.1 Core Baselines

1. **Direct LLM**
   - Single prompt with no tools or limited browsing.
   - Purpose: measure internal-knowledge hallucination and table formatting baseline.

2. **ReAct Search Agent**
   - Standard reason-act-observe loop.
   - Same model and same max budget as U-DeepWide.
   - Purpose: compare against unstructured search.

3. **Fixed Wide-Then-Deep**
   - First spend fixed percentage of budget on entity discovery, then verify/fill cells.
   - Purpose: isolate benefit of dynamic routing.

4. **Fixed Deep-Then-Wide**
   - Verify seed/core entities first, then expand.
   - Purpose: compare against opposite phase ordering.

5. **Table-as-Search**
   - If code is available, run official implementation.
   - If not, implement faithful local baseline using table state and LLM planner without uncertainty scores.

6. **A-MapReduce**
   - Strong closest baseline if reproducible.
   - If official code is unavailable, implement an approximate MapReduce baseline:
     - coverage-oriented discovery,
     - parallel batch workers,
     - merge/reduce,
     - repair/backfill.

7. **Web2BigTable**
   - Strong wide-search/web-to-table baseline if code or API is available.
   - If not available, cite reported numbers separately and compare only where setup matches.

### 11.2 Verification Baselines

8. **Repeat-Search Verification**
   - Re-query support evidence only.
   - No falsification/counter-evidence queries.

9. **FineVerify-Style Cell Verification**
   - Decompose table requirements into checkable statements and verify each with evidence.
   - No width uncertainty controller.

10. **Asymmetric Verification Best-of-N**
    - Generate N candidate tables or candidate answers, then verify/rank.
    - Purpose: compare routing against brute-force test-time scaling.

### 11.3 Efficiency Baselines

11. **Fixed Step Budget**
    - Same operation templates but fixed number of discovery and verification steps.

12. **AutoSearch-Style Adaptive Depth**
    - Stop based on self-generated intermediate answer sufficiency.
    - Purpose: compare generic adaptive depth with table-specific width/depth uncertainty.

13. **SlimSearcher-Style Cost Prompting**
    - Add instruction to minimize tokens/tool calls.
    - Purpose: test whether simple cost-awareness is enough.

### 11.4 Upper-Bound Oracles

Use only for analysis, not as normal baselines:

1. **Oracle Row Set**
   - Provide gold entity rows, then test depth verification/extraction only.

2. **Oracle Schema**
   - Provide gold columns, but not rows/cells.

3. **Oracle Stop**
   - Stop when no remaining gold rows/cells can be improved.

These quantify how much error comes from schema, width, depth, and stopping.

## 12. Ablation Studies

### 12.1 Component Ablations

1. `w/o Uw`
   - Disable width uncertainty.
   - Use fixed discovery budget.
   - Expected: lower Row F1 or higher cost.

2. `w/o Ud`
   - Disable depth uncertainty.
   - Verify cells in fixed order.
   - Expected: lower Item precision and more hallucinated cells.

3. `w/o counter-evidence`
   - Replace falsification with support-only verification.
   - Expected: higher false positives, especially in exclusion/eligibility tasks.

4. `w/o marginal coverage stopping`
   - Use fixed step stop.
   - Expected: higher token cost and over-search on small entity sets.

5. `w/o query diversity`
   - Measure saturation only from recent duplicate returns.
   - Expected: premature stopping from query bias.

6. `w/o source reliability`
   - Treat all sources equally.
   - Expected: more incorrect cells from aggregators or stale pages.

7. `single trajectory only`
   - No multi-query semantic clusters.
   - Expected: worse `Ud` calibration.

### 12.2 Threshold Sensitivity

Vary:

- `tau_w_stop`.
- `tau_d_stop`.
- marginal gain threshold.
- query diversity minimum.
- counter-evidence query count.
- max verification attempts per cell.

Report:

- F1/SR.
- token cost.
- calibration metrics.
- premature stop rate.
- over-search rate.

## 13. Evaluation Metrics

### 13.1 Task Metrics

- Success Rate: exact table match after normalization.
- Row Precision / Recall / F1.
- Item Precision / Recall / F1.
- Column F1.
- Core Entity Accuracy.
- Missing required cell rate.
- Contradicted cell rate.
- Unsupported cell rate.

### 13.2 Cost Metrics

- Total tokens.
- Search calls.
- Page reads.
- Verification calls.
- Wall-clock time.
- API cost.
- Cost per correct item.
- Cost per Row F1 point.

### 13.3 Uncertainty Metrics

For `Uw`:

- Correlation with remaining undiscovered gold rows.
- AUROC for low row recall after stopping.
- Calibration curve: predicted coverage vs actual row recall.
- Premature stopping rate.

For `Ud`:

- AUROC for incorrect cells.
- AUROC for unsupported cells.
- ECE/Brier if mapped to probability of correctness.
- Risk-coverage curve: abstain/blank high-`Ud` cells and measure precision.

### 13.4 Pareto Analysis

Plot:

- Item F1 vs tokens.
- Row F1 vs tokens.
- Success Rate vs cost.
- Item F1 vs wall-clock time.

Main claim should be on the Pareto frontier, not only absolute score.

## 14. Experimental Protocol

### 14.1 Fairness Controls

- Same model backbone where possible.
- Same search API and page reader.
- Same max tokens/tool calls/runtime.
- Same number of attempts for Avg@N.
- Same normalization/evaluator.
- No ground truth, labels, score files, or benchmark categories in runtime prompts.

### 14.2 Run Settings

Recommended tiers:

1. **Smoke**
   - 5 DeepWideSearch tasks.
   - 3 WideSearch tasks.
   - Low budget.

2. **Pilot**
   - 30 DeepWideSearch tasks.
   - 30 WideSearch tasks.
   - 2 attempts each.

3. **Main**
   - Full DeepWideSearch.
   - Full WideSearch if cost allows.
   - Avg@4 for comparability with reported papers.

4. **Stress**
   - Long-tail topics.
   - High row-count tasks.
   - Time-sensitive tasks.

### 14.3 Logging Requirements

Each run writes:

```text
outputs/runs/<run_id>/
  config.yaml
  task_inputs.jsonl
  predictions.jsonl
  traces.jsonl
  table_states/
  evidence/
  uncertainty_timeseries.jsonl
  cost_summary.json
  metrics.json
  report.md
```

Trace fields:

- operation type.
- query text.
- retrieved URLs.
- new entities.
- duplicate entities.
- changed cells.
- `Uw` before/after.
- top `Ud` cells before/after.
- token/tool/cost.
- controller reason.

## 15. Paper Contribution Plan

### 15.1 Main Contributions

1. **Two-dimensional DeepWide uncertainty formulation**
   - Candidate coverage uncertainty and cell credibility uncertainty.

2. **Training-free uncertainty-aware controller**
   - Routes budget between discovery, support verification, counter-evidence verification, and stopping.

3. **Cell-level counter-evidence verification**
   - Explicitly searches for contradictions to reduce confirmation bias and unsupported internal-knowledge fills.

4. **Cost-quality evaluation**
   - Shows Pareto improvements on DeepWideSearch and diagnostic improvements on WideSearch/deep-search benchmarks.

### 15.2 Claims To Avoid

Avoid:

- "First uncertainty-aware web agent."
- "First verification-based deep search agent."
- "Provably optimal stopping" unless formal proof is added.
- "SOTA SR improvement" unless A-MapReduce/Web2BigTable/TaS are handled fairly.

Use:

- "DeepWide-specific uncertainty state."
- "Budget-aware marginal coverage stopping."
- "Training-free controller."
- "Cell-level counter-evidence verification."

## 16. Risks And Mitigations

### Risk 1: Width Saturation Is Query-Biased

Mitigation:

- Require query-family diversity before lowering `Uw`.
- Track source-family coverage.
- Add multilingual and domain-specific query templates.
- Use unseen-mass estimate as auxiliary signal.

### Risk 2: Falsification Search Misses Hidden Evidence

Mitigation:

- Treat not-found as uncertainty reduction only under strong source coverage.
- Do not convert absence of contradiction into proof.
- Keep high-risk cells as `supported`, not `verified`.

### Risk 3: Strong Baselines Already Solve Part Of The Problem

Mitigation:

- Compare against A-MapReduce/TaS/Web2BigTable where possible.
- Emphasize calibration, mechanism, and Pareto frontier.
- Use oracle and ablation analysis to show where gains come from.

### Risk 4: Exact Success Rate Remains Low

Mitigation:

- Make Item F1, Row F1, and cost Pareto primary.
- Analyze exact-match failures.
- Report SR but avoid overpromising.

### Risk 5: Evaluation Cost Is High

Mitigation:

- Build offline cache for search/page reads where benchmark rules permit.
- Run smoke/pilot before full benchmark.
- Use lower-cost model for extraction/judging and stronger model only for planning/finalization.

## 17. Timeline

### Week 1: Prototype

- Build state schema, search abstraction, trace logger.
- Implement basic discovery and extraction.
- Run 5 manual tasks.

### Week 2: Verification And Uncertainty

- Implement `Ud`.
- Implement counter-evidence verification.
- Add cell judge and evidence status.
- Unit test uncertainty updates.

### Week 3: Width And Controller

- Implement `Uw`.
- Implement routing policy.
- Implement marginal coverage stopping.
- Run DeepWideSearch smoke.

### Week 4: Benchmark Harness

- Add DeepWideSearch evaluator integration.
- Add WideSearch evaluator integration.
- Implement baselines:
  - ReAct,
  - fixed wide-then-deep,
  - support-only verification,
  - no-uncertainty TaS-like table planner.

### Week 5: Pilot Experiments

- Run 30-task pilot.
- Tune thresholds only on pilot/dev tasks.
- Generate first Pareto plots.
- Identify failure modes.

### Week 6: Strong Baselines And Ablations

- Add or reproduce A-MapReduce/TaS/Web2BigTable if code is available.
- Run component ablations.
- Run threshold sensitivity.

### Week 7: Full Evaluation

- Full DeepWideSearch.
- Full or sampled WideSearch.
- Optional BrowseComp/XBench diagnostic.
- Generate final metrics and reports.

### Week 8: Paper Draft

- Write method section.
- Write related work and positioning.
- Write experiments and ablations.
- Prepare figures:
  - architecture,
  - uncertainty time series,
  - Pareto frontier,
  - calibration curves,
  - failure analysis.

## 18. Minimum Viable Experiment

If time or budget is limited, the smallest publishable experiment is:

1. Implement rule-based U-DeepWide.
2. Evaluate on a 50-task DeepWideSearch subset.
3. Compare against:
   - ReAct,
   - fixed wide-then-deep,
   - TaS-like table planner without uncertainty,
   - support-only verification.
4. Run ablations:
   - no `Uw`,
   - no `Ud`,
   - no counter-evidence,
   - no marginal stopping.
5. Report:
   - Row F1,
   - Item F1,
   - SR,
   - token cost,
   - `Uw`/`Ud` calibration diagnostics.

This MVP is enough to validate whether the central hypothesis is real before investing in full SOTA comparisons.

## 19. Concrete Next Steps

1. Decide benchmark access:
   - locate or clone DeepWideSearch evaluator and data,
   - locate or clone WideSearch evaluator and data.
2. Choose model/search stack:
   - planner model,
   - extractor/verifier model,
   - search API,
   - page reader.
3. Build package skeleton.
4. Implement state and logging before agent logic.
5. Run 3 manually inspected examples and verify trace quality.
6. Add baselines only after U-DeepWide trace format is stable.
