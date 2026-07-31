"""Replicate-aware successor to the frozen V2.41.92 Gate-2A.

V2.41.92 propagates task-cluster sampling uncertainty but evaluates each
action from the mean of only three sealed continuation replicates.  A noisy
three-replicate mean can therefore look positive in every observed task and
produce a strictly positive cluster-bootstrap lower bound even though the
within-action continuation uncertainty still covers harmful outcomes.

This append-only evaluator replays V2.41.92 unchanged, then performs a
hierarchical bootstrap.  The outer level resamples opaque task clusters.  The
inner level independently resamples the three signed continuation
contributions of every action bundle and recomputes the already-frozen policy
comparisons.  A single inner draw is shared by full, no-entropy, heuristic,
random, and stop comparisons at that checkpoint.  Action selection itself is
never refit or changed after outcomes are opened.

The module is post-terminal and offline only.  It has no model, search,
network, credential, forward, controller, or training execution surface.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any

from .v2409_interventions import CONTEXT_ACTIONS
from .v24123_release import (
    REPLICATE_IDS,
    phase_bundles,
    validate_replicate_aggregate,
)
from .v24161_strict_gate2a import (
    DEFAULT_SETTINGS,
    _finite,
    _stable_checkpoint_group,
    _validate_features,
    _validate_prediction_seal,
    heuristic_score,
)
from .v24191_policy_value_gate2a import VALUE_ADVANTAGES
from .v24192_abstain_aware_gate2a import (
    DEFAULT_ABSTAIN_SETTINGS,
    branch_decision,
    evaluate_abstain_aware_gate2a,
    required_signal_available,
)


DEFAULT_REPLICATE_SETTINGS = {
    "minimum_independent_task_clusters": DEFAULT_ABSTAIN_SETTINGS[
        "minimum_independent_task_clusters"
    ],
    "minimum_full_signal_available_task_clusters": DEFAULT_ABSTAIN_SETTINGS[
        "minimum_full_signal_available_task_clusters"
    ],
    "required_replicates_per_action": len(REPLICATE_IDS),
    "bootstrap_seed": 24193,
    "bootstrap_resamples": DEFAULT_ABSTAIN_SETTINGS["bootstrap_resamples"],
    "simultaneous_lower_quantile": 0.025,
    "require_parent_v24192_pass": True,
    "require_both_hierarchical_minimum_lowers_strictly_positive": True,
    "resample_task_clusters_outer": True,
    "resample_action_continuations_inner": True,
    "share_inner_action_draws_across_policy_comparisons": True,
}


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("V2.41.93 cannot average an empty collection")
    return sum(values) / len(values)


def _percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (position - lower) * (
        ordered[upper] - ordered[lower]
    )


def _checkpoint_advantages(
    unit: dict[str, Any], actual: dict[str, float]
) -> dict[str, float]:
    decisions = unit["decisions"]
    values = {
        name: 0.0 if decisions[name] is None else actual[decisions[name]]
        for name in ("full", "no_entropy", "heuristic")
    }
    random_value = _mean(list(actual.values())) if unit["full_available"] else 0.0
    return {
        "full_selected_value_over_stop": values["full"],
        "full_minus_uniform_random_action_value": values["full"] - random_value,
        "full_minus_no_entropy_policy_value": (
            values["full"] - values["no_entropy"]
        ),
        "full_minus_same_action_heuristic_policy_value": (
            values["full"] - values["heuristic"]
        ),
    }


def _cluster_estimates(
    units_by_cluster: dict[str, list[dict[str, Any]]],
) -> dict[str, float | None]:
    cluster_means: dict[str, dict[str, float]] = {}
    for cluster, units in units_by_cluster.items():
        rows = {
            name: [] for name in VALUE_ADVANTAGES
        }
        for unit in units:
            actual = {
                action: _mean(list(values))
                for action, values in unit["replicate_contributions"].items()
            }
            advantages = _checkpoint_advantages(unit, actual)
            for name in VALUE_ADVANTAGES:
                rows[name].append(advantages[name])
        cluster_means[cluster] = {
            name: _mean(rows[name]) for name in VALUE_ADVANTAGES
        }
    return {
        name: (
            _mean([cluster_means[cluster][name] for cluster in sorted(cluster_means)])
            if cluster_means
            else None
        )
        for name in VALUE_ADVANTAGES
    }


def hierarchical_simultaneous_bootstrap(
    units: list[dict[str, Any]],
    *,
    seed: int,
    resamples: int,
    lower_quantile: float,
) -> dict[str, Any]:
    """Bootstrap task clusters outside and sealed continuations inside."""

    by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in units:
        by_cluster[str(unit["task_cluster_ref_sha256"])].append(unit)
    clusters = sorted(by_cluster)
    observed = _cluster_estimates(dict(by_cluster))
    minima: list[float] = []
    if clusters:
        generator = random.Random(seed)
        for _ in range(resamples):
            drawn_clusters = [generator.choice(clusters) for _ in clusters]
            sampled_cluster_rows: list[dict[str, float]] = []
            for cluster in drawn_clusters:
                checkpoint_rows = {
                    name: [] for name in VALUE_ADVANTAGES
                }
                for unit in by_cluster[cluster]:
                    actual: dict[str, float] = {}
                    for action in unit["action_order"]:
                        values = unit["replicate_contributions"][action]
                        actual[action] = _mean(
                            [generator.choice(values) for _ in REPLICATE_IDS]
                        )
                    advantages = _checkpoint_advantages(unit, actual)
                    for name in VALUE_ADVANTAGES:
                        checkpoint_rows[name].append(advantages[name])
                sampled_cluster_rows.append(
                    {
                        name: _mean(checkpoint_rows[name])
                        for name in VALUE_ADVANTAGES
                    }
                )
            estimates = [
                _mean([row[name] for row in sampled_cluster_rows])
                for name in VALUE_ADVANTAGES
            ]
            minima.append(min(estimates))
    lower = _percentile(minima, lower_quantile)
    upper = _percentile(minima, 1.0 - lower_quantile)
    return {
        "family": list(VALUE_ADVANTAGES),
        "task_clusters": len(clusters),
        "checkpoints": len(units),
        "replicates_per_action": len(REPLICATE_IDS),
        "outer_unit": "opaque task cluster",
        "inner_unit": "sealed signed continuation contribution within action bundle",
        "inner_action_draws_shared_across_policy_comparisons": True,
        "policy_selection_refit_in_bootstrap": False,
        "individual_estimates": {
            name: round(float(observed[name]), 12)
            if observed[name] is not None
            else None
            for name in VALUE_ADVANTAGES
        },
        "minimum_observed_advantage": (
            round(min(float(value) for value in observed.values()), 12)
            if observed and all(value is not None for value in observed.values())
            else None
        ),
        "hierarchical_shared_minimum_95ci": {
            "requested_resamples": resamples,
            "valid_resamples": len(minima),
            "seed": seed,
            "lower_quantile": lower_quantile,
            "lower": round(lower, 12) if lower is not None else None,
            "upper": round(upper, 12) if upper is not None else None,
        },
    }


def _validated_units(
    manifest: dict[str, Any],
    aggregate_records: list[dict[str, Any]],
    prediction_seal: dict[str, Any],
    no_entropy_predicted_tokens: dict[str, int],
    *,
    equal_cost_tolerance_fraction: float,
) -> list[dict[str, Any]]:
    predictions = _validate_prediction_seal(manifest, prediction_seal)
    bundles = {row["bundle_sha256"]: row for row in manifest["bundles"]}
    records: dict[str, dict[str, Any]] = {}
    valid: dict[str, bool] = {}
    for record in aggregate_records:
        if not isinstance(record, dict):
            raise ValueError("V2.41.93 aggregate is not an object")
        bundle_sha = str(record.get("bundle_sha256", ""))
        bundle = bundles.get(bundle_sha)
        if bundle is None or bundle_sha in records:
            raise ValueError("V2.41.93 aggregate identity is outside or duplicated")
        valid[bundle_sha] = validate_replicate_aggregate(
            record,
            bundle,
            job_manifest_sha256=manifest["manifest_sha256"],
        )
        records[bundle_sha] = record
    if set(records) != set(bundles):
        raise ValueError("V2.41.93 aggregates do not exactly cover the manifest")

    rows: list[dict[str, Any]] = []
    for bundle in phase_bundles(manifest, audit=True):
        bundle_sha = bundle["bundle_sha256"]
        if not valid[bundle_sha]:
            continue
        record = records[bundle_sha]
        prediction = predictions[bundle_sha]
        features = _validate_features(bundle.get("pre_action_features"))
        contributions = record.get("replicate_signed_task_contribution")
        if (
            not isinstance(contributions, list)
            or len(contributions) != len(REPLICATE_IDS)
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in contributions
            )
        ):
            raise ValueError("V2.41.93 sealed contribution vector is invalid")
        rows.append(
            {
                **bundle,
                "pre_action_features": features,
                "replicate_contributions": tuple(float(value) for value in contributions),
                "actual_action_tokens": _finite(
                    record.get("mean_action_system_total_tokens"),
                    label="actual action cost",
                ),
                "full_prediction": float(prediction["predicted_task_contribution"]),
                "no_entropy_prediction": float(
                    prediction["no_entropy_predicted_task_contribution"]
                ),
                "full_predicted_action_tokens": prediction[
                    "predicted_action_system_tokens"
                ],
                "no_entropy_predicted_action_tokens": no_entropy_predicted_tokens[
                    bundle_sha
                ],
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

    units: list[dict[str, Any]] = []
    for (cluster, checkpoint, context), group in grouped.items():
        action_order = tuple(CONTEXT_ACTIONS[context])
        if len(group) != len(action_order) or {
            row["action"] for row in group
        } != set(action_order):
            continue
        if not _stable_checkpoint_group(group):
            continue
        actual_costs = {
            str(row["action"]): float(row["actual_action_tokens"])
            for row in group
        }
        if (max(actual_costs.values()) - min(actual_costs.values())) / max(
            1.0, min(actual_costs.values())
        ) > equal_cost_tolerance_fraction:
            continue
        if any(cost <= 0.0 for cost in actual_costs.values()):
            continue
        features = group[0]["pre_action_features"]
        available = {
            name: required_signal_available(features, context=context, branch=name)
            for name in ("full", "no_entropy", "heuristic")
        }
        predicted_tokens = {
            "full": {
                str(row["action"]): row["full_predicted_action_tokens"]
                for row in group
            },
            "no_entropy": {
                str(row["action"]): row["no_entropy_predicted_action_tokens"]
                for row in group
            },
        }
        required_cost_failure = any(
            available[name]
            and any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
                for value in predicted_tokens[
                    "full" if name == "full" else "no_entropy"
                ].values()
            )
            for name in ("full", "no_entropy", "heuristic")
        )
        if required_cost_failure:
            continue
        scores = {
            "full": {
                str(row["action"]): float(row["full_prediction"])
                for row in group
            },
            "no_entropy": {
                str(row["action"]): float(row["no_entropy_prediction"])
                for row in group
            },
            "heuristic": {
                str(row["action"]): float(row["heuristic_prediction"])
                for row in group
            },
        }
        raw_decisions = {
            name: branch_decision(
                values,
                predicted_tokens[
                    "full" if name == "full" else "no_entropy"
                ],
                features,
                context=context,
                branch=name,
                action_order=action_order,
            )
            for name, values in scores.items()
        }
        units.append(
            {
                "task_cluster_ref_sha256": cluster,
                "source_checkpoint_sha256": checkpoint,
                "context": context,
                "action_order": action_order,
                "full_available": available["full"],
                "decisions": {
                    name: action for name, (_, action) in raw_decisions.items()
                },
                "replicate_contributions": {
                    str(row["action"]): row["replicate_contributions"]
                    for row in group
                },
            }
        )
    return units


def evaluate_replicate_aware_gate2a(
    manifest: dict[str, Any],
    aggregate_records: list[dict[str, Any]],
    prediction_seal: dict[str, Any],
    no_entropy_predicted_tokens: dict[str, int],
    *,
    parent_settings: dict[str, Any] | None = None,
    policy_settings: dict[str, Any] | None = None,
    abstain_settings: dict[str, Any] | None = None,
    replicate_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay V2.41.92 and propagate continuation measurement uncertainty."""

    config = dict(DEFAULT_REPLICATE_SETTINGS)
    if replicate_settings is not None:
        if set(replicate_settings) != set(DEFAULT_REPLICATE_SETTINGS):
            raise ValueError("V2.41.93 replicate settings schema is not exact")
        config.update(replicate_settings)
    required_true = (
        "require_parent_v24192_pass",
        "require_both_hierarchical_minimum_lowers_strictly_positive",
        "resample_task_clusters_outer",
        "resample_action_continuations_inner",
        "share_inner_action_draws_across_policy_comparisons",
    )
    integer_positive = (
        "minimum_independent_task_clusters",
        "minimum_full_signal_available_task_clusters",
        "required_replicates_per_action",
        "bootstrap_resamples",
    )
    if (
        any(config[key] is not True for key in required_true)
        or any(
            isinstance(config[key], bool)
            or not isinstance(config[key], int)
            or config[key] <= 0
            for key in integer_positive
        )
        or config["required_replicates_per_action"] != len(REPLICATE_IDS)
        or isinstance(config["bootstrap_seed"], bool)
        or not isinstance(config["bootstrap_seed"], int)
        or isinstance(config["simultaneous_lower_quantile"], bool)
        or not isinstance(config["simultaneous_lower_quantile"], (int, float))
        or not 0.0 < float(config["simultaneous_lower_quantile"]) < 0.5
    ):
        raise ValueError("V2.41.93 replicate settings are invalid")

    parent = evaluate_abstain_aware_gate2a(
        manifest,
        aggregate_records,
        prediction_seal,
        no_entropy_predicted_tokens,
        parent_settings=parent_settings,
        policy_settings=policy_settings,
        abstain_settings=abstain_settings,
    )
    parent_config = dict(DEFAULT_SETTINGS)
    if parent_settings is not None:
        parent_config.update(parent_settings)
    units = _validated_units(
        manifest,
        aggregate_records,
        prediction_seal,
        no_entropy_predicted_tokens,
        equal_cost_tolerance_fraction=float(
            parent_config["equal_cost_tolerance_fraction"]
        ),
    )
    full_available_units = [unit for unit in units if unit["full_available"]]
    if len(units) != parent["policy_comparable_checkpoints"] or len(
        full_available_units
    ) != parent["full_signal_available_checkpoints"]:
        raise RuntimeError("V2.41.93 parent checkpoint replay drifted")

    overall = hierarchical_simultaneous_bootstrap(
        units,
        seed=int(config["bootstrap_seed"]),
        resamples=int(config["bootstrap_resamples"]),
        lower_quantile=float(config["simultaneous_lower_quantile"]),
    )
    available = hierarchical_simultaneous_bootstrap(
        full_available_units,
        seed=int(config["bootstrap_seed"]) + 100,
        resamples=int(config["bootstrap_resamples"]),
        lower_quantile=float(config["simultaneous_lower_quantile"]),
    )
    parent_overall = parent["simultaneous_policy_value_advantage"][
        "individual_estimates"
    ]
    parent_available = parent[
        "full_signal_available_simultaneous_action_value_advantage"
    ]["individual_estimates"]
    for ours, theirs in (
        (overall["individual_estimates"], parent_overall),
        (available["individual_estimates"], parent_available),
    ):
        if any(
            ours[name] is None
            or theirs[name] is None
            or not math.isclose(
                float(ours[name]),
                float(theirs[name]),
                rel_tol=0.0,
                abs_tol=1e-10,
            )
            for name in VALUE_ADVANTAGES
        ):
            raise RuntimeError("V2.41.93 observed parent estimand replay drifted")

    overall_ci = overall["hierarchical_shared_minimum_95ci"]
    available_ci = available["hierarchical_shared_minimum_95ci"]
    evaluable = bool(
        parent["status"] != "not_evaluable"
        and overall["task_clusters"]
        >= int(config["minimum_independent_task_clusters"])
        and available["task_clusters"]
        >= int(config["minimum_full_signal_available_task_clusters"])
        and overall_ci["valid_resamples"] == int(config["bootstrap_resamples"])
        and available_ci["valid_resamples"] == int(config["bootstrap_resamples"])
    )
    hierarchical_conditions_passed = bool(
        evaluable
        and overall_ci["lower"] is not None
        and overall_ci["lower"] > 0.0
        and available_ci["lower"] is not None
        and available_ci["lower"] > 0.0
    )
    passed = bool(
        evaluable
        and parent["passed"]
        and hierarchical_conditions_passed
    )
    return {
        "gate": "v24193_replicate_aware_true_continuation_gate2a",
        "status": "pass" if passed else "fail" if evaluable else "not_evaluable",
        "passed": passed,
        "development_only": True,
        "predictions_frozen_before_audit_outcomes": True,
        "single_checkpoint_action_stop_abstain_policy_frozen": True,
        "task_cluster_outer_bootstrap": True,
        "action_continuation_inner_bootstrap": True,
        "replicates_are_repeated_measurements_not_independent_tasks": True,
        "policy_selection_refit_in_bootstrap": False,
        "multi_context_closed_loop_policy_value_claimed": False,
        "policy_comparable_checkpoints": len(units),
        "full_signal_available_checkpoints": len(full_available_units),
        "independent_policy_task_clusters": overall["task_clusters"],
        "full_signal_available_task_clusters": available["task_clusters"],
        "hierarchical_simultaneous_policy_value_advantage": overall,
        "full_signal_available_hierarchical_simultaneous_action_value_advantage": available,
        "parent_v24192_status_diagnostic_only_without_replicate_gate": parent[
            "status"
        ],
        "parent_v24192_passed_required": bool(
            config["require_parent_v24192_pass"]
        ),
        "parent_v24192_gate_replay": parent,
        "replicate_settings": config,
        "hierarchical_conditions_passed": hierarchical_conditions_passed,
        "controller_design_authorized": passed,
        "controller_implementation_or_pilot_launch_authorized": False,
        "training_credit_authorized": False,
        "full220_controller_launch_authorized": False,
        "benchmark_or_sota_claim": False,
    }
