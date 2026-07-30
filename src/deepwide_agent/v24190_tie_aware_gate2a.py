"""Tie-aware successor to the frozen V2.41.61 strict Gate-2A.

V2.41.61 correctly moved action ranking to complete, same-checkpoint,
equal-cost three-action groups.  Its top-2 random baseline nevertheless uses a
constant ``2/3`` and its model top-2 sets use a deterministic action-order
tie-break.  Both are exact only when the terminal contribution has one best
action and the model has no tie across the top-2 boundary.

True-continuation contribution is a rounded difference of evaluator losses,
so ties are ordinary data rather than a pathological corner case.  This
module leaves every frozen V2.41.61 validation and non-top-2 gate unchanged,
then replaces the three paired top-2 tests with their exact expected values:

* the random baseline samples two of three actions uniformly and accounts for
  the number of tied true-best actions;
* a model score tie crossing the top-2 boundary is broken uniformly, so action
  declaration order cannot create credit;
* paired differences are computed checkpoint-by-checkpoint and bootstrapped
  by opaque task cluster, as in the parent strict gate.

The module is post-terminal and offline only.  It has no model, search,
network, credential, forward, or controller execution surface.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Callable

from .v2409_interventions import CONTEXT_ACTIONS
from .v24123_release import phase_bundles, validate_replicate_aggregate
from .v24161_strict_gate2a import (
    DEFAULT_SETTINGS,
    _finite,
    _mean,
    _stable_checkpoint_group,
    _validate_features,
    _validate_prediction_seal,
    cluster_bootstrap,
    evaluate_strict_gate2a,
    heuristic_score,
)


TOP_K = 2


def uniform_topk_hit_probability(
    *, action_count: int, best_count: int, top_k: int = TOP_K
) -> float:
    """Probability that a uniform size-k action subset hits any true best."""

    if (
        isinstance(action_count, bool)
        or isinstance(best_count, bool)
        or isinstance(top_k, bool)
        or not all(isinstance(value, int) for value in (action_count, best_count, top_k))
        or action_count <= 0
        or not 1 <= best_count <= action_count
        or not 0 <= top_k <= action_count
    ):
        raise ValueError("V2.41.90 random top-k dimensions are invalid")
    if top_k == 0:
        return 0.0
    if top_k > action_count - best_count:
        return 1.0
    misses = math.comb(action_count - best_count, top_k)
    total = math.comb(action_count, top_k)
    return 1.0 - misses / total


def expected_topk_hit_probability(
    scores: dict[str, float],
    true_best: set[str],
    *,
    top_k: int = TOP_K,
) -> float:
    """Expected best-action hit under uniform boundary-tie breaking.

    Scores strictly above the cutoff are always selected.  If the cutoff
    score has more actions than remaining slots, those slots are sampled
    uniformly without replacement from the tied tier.
    """

    if (
        not isinstance(scores, dict)
        or not scores
        or not isinstance(true_best, set)
        or not true_best
        or not true_best.issubset(scores)
        or isinstance(top_k, bool)
        or not isinstance(top_k, int)
        or not 0 <= top_k <= len(scores)
    ):
        raise ValueError("V2.41.90 model top-k inputs are invalid")
    clean = {
        str(action): _finite(value, label="tie-aware top-k score")
        for action, value in scores.items()
    }
    if len(clean) != len(scores) or any(not action for action in clean):
        raise ValueError("V2.41.90 model top-k action identity is invalid")
    if top_k == 0:
        return 0.0
    if top_k == len(clean):
        return 1.0

    selected_above: set[str] = set()
    remaining = top_k
    for score in sorted(set(clean.values()), reverse=True):
        tier = {action for action, value in clean.items() if value == score}
        if len(tier) <= remaining:
            selected_above.update(tier)
            remaining -= len(tier)
            if remaining == 0:
                return 1.0 if selected_above & true_best else 0.0
            continue
        if selected_above & true_best:
            return 1.0
        best_in_tier = len(tier & true_best)
        if best_in_tier == 0:
            return 0.0
        misses = math.comb(len(tier) - best_in_tier, remaining)
        total = math.comb(len(tier), remaining)
        return 1.0 - misses / total
    raise RuntimeError("V2.41.90 top-k boundary was not reached")


def _lower(report: dict[str, Any]) -> float | None:
    return report["cluster_bootstrap_95ci"]["lower"]


def _method_scores(
    group: list[dict[str, Any]], key: str | Callable[[dict[str, Any]], float]
) -> dict[str, float]:
    if callable(key):
        return {str(row["action"]): float(key(row)) for row in group}
    return {str(row["action"]): float(row[key]) for row in group}


def evaluate_tie_aware_gate2a(
    manifest: dict[str, Any],
    aggregate_records: list[dict[str, Any]],
    prediction_seal: dict[str, Any],
    *,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay the parent strict gate and replace only its top-2 statistics."""

    config = dict(DEFAULT_SETTINGS)
    if settings is not None:
        if set(settings) != set(DEFAULT_SETTINGS):
            raise ValueError("V2.41.90 settings schema is not exact")
        config.update(settings)
    parent = evaluate_strict_gate2a(
        manifest,
        aggregate_records,
        prediction_seal,
        settings=config,
    )
    predictions = _validate_prediction_seal(manifest, prediction_seal)
    bundles = {row["bundle_sha256"]: row for row in manifest["bundles"]}
    records: dict[str, dict[str, Any]] = {}
    valid: dict[str, bool] = {}
    for record in aggregate_records:
        if not isinstance(record, dict):
            raise ValueError("V2.41.90 aggregate is not an object")
        bundle_sha = str(record.get("bundle_sha256", ""))
        bundle = bundles.get(bundle_sha)
        if bundle is None or bundle_sha in records:
            raise ValueError("V2.41.90 aggregate identity is outside or duplicated")
        valid[bundle_sha] = validate_replicate_aggregate(
            record,
            bundle,
            job_manifest_sha256=manifest["manifest_sha256"],
        )
        records[bundle_sha] = record
    if set(records) != set(bundles):
        raise ValueError("V2.41.90 aggregates do not exactly cover the manifest")

    audit = phase_bundles(manifest, audit=True)
    rows: list[dict[str, Any]] = []
    for bundle in audit:
        bundle_sha = bundle["bundle_sha256"]
        if not valid[bundle_sha]:
            continue
        prediction = predictions[bundle_sha]
        _validate_features(bundle.get("pre_action_features"))
        rows.append(
            {
                **bundle,
                "actual_contribution": _finite(
                    records[bundle_sha].get("mean_signed_task_contribution"),
                    label="actual contribution",
                ),
                "actual_action_tokens": _finite(
                    records[bundle_sha].get("mean_action_system_total_tokens"),
                    label="actual action cost",
                ),
                "full_prediction": float(prediction["predicted_task_contribution"]),
                "no_entropy_prediction": float(
                    prediction["no_entropy_predicted_task_contribution"]
                ),
                "heuristic_prediction": heuristic_score(bundle),
            }
        )

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[
            (
                str(row["task_cluster_ref_sha256"]),
                str(row["source_checkpoint_sha256"]),
                str(row["context"]),
            )
        ].append(row)

    metrics: dict[str, dict[str, list[float]]] = {
        name: defaultdict(list)
        for name in (
            "full",
            "no_entropy",
            "heuristic",
            "random",
            "full_minus_random",
            "full_minus_no_entropy",
            "full_minus_heuristic",
        )
    }
    actual_best_multiplicity: Counter[int] = Counter()
    boundary_ties: dict[str, Counter[int]] = {
        "full": Counter(),
        "no_entropy": Counter(),
        "heuristic": Counter(),
    }
    complete = 0
    comparable = 0
    unstable = 0
    out_of_cost = 0
    for (cluster, _, context), group in grouped.items():
        expected_actions = set(CONTEXT_ACTIONS[context])
        if (
            len(group) != len(expected_actions)
            or {row["action"] for row in group} != expected_actions
        ):
            continue
        complete += 1
        if not _stable_checkpoint_group(group):
            unstable += 1
            continue
        costs = [float(row["actual_action_tokens"]) for row in group]
        if (max(costs) - min(costs)) / max(1.0, min(costs)) > float(
            config["equal_cost_tolerance_fraction"]
        ):
            out_of_cost += 1
            continue
        comparable += 1
        best_value = max(float(row["actual_contribution"]) for row in group)
        true_best = {
            str(row["action"])
            for row in group
            if float(row["actual_contribution"]) == best_value
        }
        actual_best_multiplicity[len(true_best)] += 1
        method_scores = {
            "full": _method_scores(group, "full_prediction"),
            "no_entropy": _method_scores(group, "no_entropy_prediction"),
            "heuristic": _method_scores(group, "heuristic_prediction"),
        }
        hits = {
            name: expected_topk_hit_probability(scores, true_best)
            for name, scores in method_scores.items()
        }
        random_hit = uniform_topk_hit_probability(
            action_count=len(group), best_count=len(true_best)
        )
        for name, scores in method_scores.items():
            ordered = sorted(set(scores.values()), reverse=True)
            above = 0
            boundary_size = 0
            for score in ordered:
                tier_size = sum(value == score for value in scores.values())
                if above + tier_size >= TOP_K:
                    boundary_size = tier_size
                    break
                above += tier_size
            boundary_ties[name][boundary_size] += 1
            metrics[name][cluster].append(hits[name])
        metrics["random"][cluster].append(random_hit)
        metrics["full_minus_random"][cluster].append(hits["full"] - random_hit)
        metrics["full_minus_no_entropy"][cluster].append(
            hits["full"] - hits["no_entropy"]
        )
        metrics["full_minus_heuristic"][cluster].append(
            hits["full"] - hits["heuristic"]
        )

    if (
        complete != parent["complete_three_action_checkpoints"]
        or comparable != parent["comparable_equal_cost_checkpoints"]
        or unstable != parent["unstable_checkpoint_groups"]
        or out_of_cost != parent["out_of_cost_overlap_checkpoints"]
    ):
        raise RuntimeError("V2.41.90 parent comparable-set replay drifted")

    seed = int(config["bootstrap_seed"]) + 90
    resamples = int(config["bootstrap_resamples"])
    reports = {
        name: cluster_bootstrap(
            values,
            _mean,
            seed=seed + index,
            resamples=resamples,
        )
        for index, (name, values) in enumerate(metrics.items())
    }
    rank = parent["within_checkpoint_action_rank"]["full"]
    entropy_mae = parent["full_minus_no_entropy_same_action_mae_improvement"]
    identification = parent["entropy_increase_risk_decrease_identification"][
        "full_positive_direction_rate"
    ]
    evaluable = parent["status"] != "not_evaluable"
    non_top2_passed = bool(
        evaluable
        and rank["estimate"] is not None
        and rank["estimate"] >= float(config["within_checkpoint_spearman_minimum"])
        and _lower(rank) is not None
        and _lower(rank) > 0.0
        and _lower(entropy_mae) is not None
        and _lower(entropy_mae) > 0.0
        and identification["estimate"] is not None
        and identification["estimate"]
        >= float(config["entropy_increase_risk_decrease_direction_accuracy_minimum"])
        and _lower(identification) is not None
        and _lower(identification) > 0.0
    )
    tie_aware_top2_passed = all(
        _lower(reports[name]) is not None and _lower(reports[name]) > 0.0
        for name in (
            "full_minus_random",
            "full_minus_no_entropy",
            "full_minus_heuristic",
        )
    )
    passed = bool(evaluable and non_top2_passed and tie_aware_top2_passed)
    return {
        "gate": "v24190_tie_aware_true_continuation_gate2a",
        "status": "pass" if passed else "fail" if evaluable else "not_evaluable",
        "passed": passed,
        "development_only": True,
        "predictions_frozen_before_audit_outcomes": True,
        "same_checkpoint_true_terminal_contribution": True,
        "rank_and_bootstrap_contract_inherited_from_v24161": True,
        "parent_v24161_status_diagnostic_only": parent["status"],
        "parent_v24161_passed_diagnostic_only": parent["passed"],
        "parent_fixed_two_thirds_random_baseline_superseded": True,
        "parent_deterministic_prediction_tie_break_superseded": True,
        "tie_policy": {
            "true_best": "all actions exactly tied at the rounded maximum contribution",
            "model_boundary": "uniform sampling without replacement within the cutoff score tier",
            "random_baseline": "uniform size-2 subset from all three actions conditional on true-best multiplicity",
            "action_declaration_order_used_for_ties": False,
        },
        "comparable_equal_cost_checkpoints": comparable,
        "actual_best_multiplicity": {
            str(key): actual_best_multiplicity[key]
            for key in sorted(actual_best_multiplicity)
        },
        "prediction_boundary_tier_size": {
            name: {str(key): counts[key] for key in sorted(counts)}
            for name, counts in boundary_ties.items()
        },
        "tie_aware_top2": {
            "full_expected_hit_rate": reports["full"],
            "no_entropy_expected_hit_rate": reports["no_entropy"],
            "same_action_heuristic_expected_hit_rate": reports["heuristic"],
            "random_expected_hit_rate": reports["random"],
            "full_advantage_over_random": reports["full_minus_random"],
            "full_minus_no_entropy": reports["full_minus_no_entropy"],
            "full_minus_same_action_heuristic": reports[
                "full_minus_heuristic"
            ],
        },
        "non_top2_parent_conditions_passed": non_top2_passed,
        "tie_aware_top2_conditions_passed": tie_aware_top2_passed,
        "parent_strict_gate_replay": parent,
        "settings": config,
        "controller_design_authorized": passed,
        "controller_implementation_or_pilot_launch_authorized": False,
        "training_credit_authorized": False,
        "full220_controller_launch_authorized": False,
        "benchmark_or_sota_claim": False,
    }

