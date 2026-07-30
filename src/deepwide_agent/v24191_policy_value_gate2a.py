"""Policy-value successor to the frozen V2.41.90 tie-aware Gate-2A.

V2.41.90 makes the top-2 retrieval diagnostic statistically tie-aware, but a
deployed controller executes one action (or stops).  A model can therefore
pass rank and top-2 tests while its actual argmax policy is worse than a
uniform random action.  The frozen Gate-3A design also ranks positive
predictions by predicted contribution per predicted token, whereas V2.41.90
ranks raw contribution and never exercises the stop decision.

This module replays V2.41.90 unchanged, then evaluates the exact frozen
deployment rule on the same complete, equal-realized-cost checkpoints:

* execute only a strictly-positive prediction, otherwise stop with value 0;
* rank by predicted contribution / predicted action tokens, then contribution,
  lower tokens, and the preregistered context action order;
* score the actually selected action with sealed terminal contribution;
* compare full entropy policy value with stop, uniform random action,
  no-entropy policy, and the fixed same-action heuristic;
* weight opaque task clusters equally and use one shared cluster bootstrap for
  a simultaneous minimum-advantage lower bound.

The evaluator is post-terminal and offline only.  It has no model, search,
network, credential, forward, controller, or training execution surface.
"""

from __future__ import annotations

import copy
import random
from collections import Counter, defaultdict
from typing import Any

from .v2409_interventions import CONTEXT_ACTIONS
from .v24123_release import (
    ACTION_MODEL_ROLE,
    _predict_action_branch,
    _validate_feature_vector,
    object_sha256,
    phase_bundles,
    validate_job_manifest,
    validate_replicate_aggregate,
)
from .v24161_strict_gate2a import (
    DEFAULT_SETTINGS,
    _finite,
    _mean,
    _percentile,
    _stable_checkpoint_group,
    _validate_features,
    _validate_prediction_seal,
    cluster_bootstrap,
    heuristic_score,
)
from .v24190_tie_aware_gate2a import evaluate_tie_aware_gate2a


DEFAULT_POLICY_SETTINGS = {
    "minimum_comparable_checkpoints": DEFAULT_SETTINGS[
        "minimum_comparable_checkpoints"
    ],
    "minimum_independent_task_clusters": DEFAULT_SETTINGS[
        "minimum_independent_task_clusters"
    ],
    "bootstrap_seed": 24191,
    "bootstrap_resamples": DEFAULT_SETTINGS["bootstrap_resamples"],
    "simultaneous_lower_quantile": 0.025,
    "require_parent_v24190_pass": True,
    "require_all_predicted_and_actual_action_costs_strictly_positive": True,
    "require_simultaneous_value_advantage_ci_lower_strictly_positive": True,
}

VALUE_ADVANTAGES = (
    "full_selected_value_over_stop",
    "full_minus_uniform_random_action_value",
    "full_minus_no_entropy_policy_value",
    "full_minus_same_action_heuristic_policy_value",
)


def derive_no_entropy_predicted_tokens(
    manifest: dict[str, Any], model: dict[str, Any]
) -> dict[str, int]:
    """Replay the frozen no-entropy cost branch for every audit bundle.

    V2.41.23 fits separate full and no-entropy models for both contribution and
    log action cost, but its prediction seal serializes only the full cost.
    The sealed pre-outcome model therefore remains the authoritative source for
    the no-entropy branch-specific deployment cost.
    """

    validate_job_manifest(manifest)
    unsigned = copy.deepcopy(model)
    seal = unsigned.pop("model_sha256", None)
    if (
        model.get("role") != ACTION_MODEL_ROLE
        or model.get("job_manifest_sha256") != manifest["manifest_sha256"]
        or model.get("model_ready") is not True
        or model.get("audit_outcomes_read") is not False
        or seal != object_sha256(unsigned)
        or not isinstance(model.get("no_entropy_baseline"), dict)
    ):
        raise ValueError("V2.41.91 frozen action model is invalid")
    output: dict[str, int] = {}
    for bundle in phase_bundles(manifest, audit=True):
        features = _validate_feature_vector(bundle["pre_action_features"])
        prediction = _predict_action_branch(
            model["no_entropy_baseline"],
            context=bundle["context"],
            action=bundle["action"],
            features=features,
        )
        bundle_sha = str(bundle["bundle_sha256"])
        tokens = prediction["predicted_action_system_tokens"]
        if (
            bundle_sha in output
            or isinstance(tokens, bool)
            or not isinstance(tokens, int)
            or tokens < 0
        ):
            raise ValueError("V2.41.91 no-entropy cost replay is invalid")
        output[bundle_sha] = tokens
    return output


def select_deployment_action(
    scores: dict[str, float],
    predicted_tokens: dict[str, int],
    *,
    action_order: tuple[str, ...] | list[str],
) -> str | None:
    """Apply the frozen Gate-3A one-action ranking rule.

    ``None`` is the explicit stop decision.  Declaration order is used only as
    the already-preregistered final deployment tie-break, never as a hidden
    outcome-dependent tie resolver.
    """

    order = tuple(action_order)
    if (
        not isinstance(scores, dict)
        or not isinstance(predicted_tokens, dict)
        or not order
        or len(set(order)) != len(order)
        or set(scores) != set(order)
        or set(predicted_tokens) != set(order)
    ):
        raise ValueError("V2.41.91 deployment action slate is invalid")
    clean_scores = {
        action: _finite(scores[action], label="policy score") for action in order
    }
    clean_tokens: dict[str, int] = {}
    for action in order:
        value = predicted_tokens[action]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("V2.41.91 predicted action tokens are not positive")
        clean_tokens[action] = value
    available = [action for action in order if clean_scores[action] > 0.0]
    if not available:
        return None
    rank = {action: index for index, action in enumerate(order)}
    return min(
        available,
        key=lambda action: (
            -clean_scores[action] / clean_tokens[action],
            -clean_scores[action],
            clean_tokens[action],
            rank[action],
        ),
    )


def _cluster_means(
    checkpoint_values: dict[str, list[float]],
) -> dict[str, list[float]]:
    return {
        cluster: [float(value)]
        for cluster, rows in checkpoint_values.items()
        if (value := _mean(rows)) is not None
    }


def _shared_simultaneous_bootstrap(
    advantages: dict[str, dict[str, list[float]]],
    *,
    seed: int,
    resamples: int,
    lower_quantile: float,
) -> dict[str, Any]:
    if set(advantages) != set(VALUE_ADVANTAGES):
        raise ValueError("V2.41.91 simultaneous advantage family is not exact")
    cluster_means = {name: _cluster_means(rows) for name, rows in advantages.items()}
    cluster_sets = {name: set(rows) for name, rows in cluster_means.items()}
    if len({frozenset(rows) for rows in cluster_sets.values()}) != 1:
        raise ValueError("V2.41.91 advantage metrics do not share task clusters")
    clusters = sorted(next(iter(cluster_sets.values()), set()))
    observed = {
        name: _mean([rows[cluster][0] for cluster in clusters])
        for name, rows in cluster_means.items()
    }
    minima: list[float] = []
    if clusters:
        generator = random.Random(seed)
        for _ in range(resamples):
            drawn = [generator.choice(clusters) for _ in clusters]
            estimates = [
                sum(cluster_means[name][cluster][0] for cluster in drawn)
                / len(drawn)
                for name in VALUE_ADVANTAGES
            ]
            minima.append(min(estimates))
    lower = _percentile(minima, lower_quantile)
    upper = _percentile(minima, 1.0 - lower_quantile)
    return {
        "family": list(VALUE_ADVANTAGES),
        "task_clusters": len(clusters),
        "cluster_weighting": "one mean per opaque task cluster",
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
        "shared_cluster_bootstrap_minimum_95ci": {
            "requested_resamples": resamples,
            "valid_resamples": len(minima),
            "seed": seed,
            "lower_quantile": lower_quantile,
            "lower": round(lower, 12) if lower is not None else None,
            "upper": round(upper, 12) if upper is not None else None,
        },
    }


def _report(
    values: dict[str, list[float]], *, seed: int, resamples: int
) -> dict[str, Any]:
    return cluster_bootstrap(
        _cluster_means(values),
        _mean,
        seed=seed,
        resamples=resamples,
    )


def evaluate_policy_value_gate2a(
    manifest: dict[str, Any],
    aggregate_records: list[dict[str, Any]],
    prediction_seal: dict[str, Any],
    no_entropy_predicted_tokens: dict[str, int],
    *,
    parent_settings: dict[str, Any] | None = None,
    policy_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay V2.41.90 and add an exact one-action policy-value gate."""

    parent_config = dict(DEFAULT_SETTINGS)
    if parent_settings is not None:
        if set(parent_settings) != set(DEFAULT_SETTINGS):
            raise ValueError("V2.41.91 parent settings schema is not exact")
        parent_config.update(parent_settings)
    config = dict(DEFAULT_POLICY_SETTINGS)
    if policy_settings is not None:
        if set(policy_settings) != set(DEFAULT_POLICY_SETTINGS):
            raise ValueError("V2.41.91 policy settings schema is not exact")
        config.update(policy_settings)
    if (
        config["require_parent_v24190_pass"] is not True
        or config[
            "require_all_predicted_and_actual_action_costs_strictly_positive"
        ]
        is not True
        or config[
            "require_simultaneous_value_advantage_ci_lower_strictly_positive"
        ]
        is not True
        or isinstance(config["minimum_comparable_checkpoints"], bool)
        or not isinstance(config["minimum_comparable_checkpoints"], int)
        or int(config["minimum_comparable_checkpoints"]) <= 0
        or isinstance(config["minimum_independent_task_clusters"], bool)
        or not isinstance(config["minimum_independent_task_clusters"], int)
        or int(config["minimum_independent_task_clusters"]) <= 0
        or isinstance(config["bootstrap_seed"], bool)
        or not isinstance(config["bootstrap_seed"], int)
        or isinstance(config["bootstrap_resamples"], bool)
        or not isinstance(config["bootstrap_resamples"], int)
        or int(config["bootstrap_resamples"]) <= 0
        or isinstance(config["simultaneous_lower_quantile"], bool)
        or not isinstance(config["simultaneous_lower_quantile"], (int, float))
        or not 0.0
        < float(config["simultaneous_lower_quantile"])
        < 0.5
    ):
        raise ValueError("V2.41.91 bootstrap settings are invalid")

    parent = evaluate_tie_aware_gate2a(
        manifest,
        aggregate_records,
        prediction_seal,
        settings=parent_config,
    )
    predictions = _validate_prediction_seal(manifest, prediction_seal)
    if (
        not isinstance(no_entropy_predicted_tokens, dict)
        or set(no_entropy_predicted_tokens) != set(predictions)
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in no_entropy_predicted_tokens.values()
        )
    ):
        raise ValueError("V2.41.91 no-entropy predicted costs are not exact")
    bundles = {row["bundle_sha256"]: row for row in manifest["bundles"]}
    records: dict[str, dict[str, Any]] = {}
    valid: dict[str, bool] = {}
    for record in aggregate_records:
        if not isinstance(record, dict):
            raise ValueError("V2.41.91 aggregate is not an object")
        bundle_sha = str(record.get("bundle_sha256", ""))
        bundle = bundles.get(bundle_sha)
        if bundle is None or bundle_sha in records:
            raise ValueError("V2.41.91 aggregate identity is outside or duplicated")
        valid[bundle_sha] = validate_replicate_aggregate(
            record,
            bundle,
            job_manifest_sha256=manifest["manifest_sha256"],
        )
        records[bundle_sha] = record
    if set(records) != set(bundles):
        raise ValueError("V2.41.91 aggregates do not exactly cover the manifest")

    rows: list[dict[str, Any]] = []
    for bundle in phase_bundles(manifest, audit=True):
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

    metrics: dict[str, dict[str, list[float]]] = {
        name: defaultdict(list)
        for name in (
            "full_selected_value",
            "no_entropy_selected_value",
            "heuristic_selected_value",
            "uniform_random_action_value",
            "oracle_action_or_stop_value",
            "full_oracle_regret",
            "no_entropy_oracle_regret",
            "heuristic_oracle_regret",
            "full_top1_oracle_hit",
            "no_entropy_top1_oracle_hit",
            "heuristic_top1_oracle_hit",
            "uniform_random_action_oracle_hit_probability",
            "full_selected_actual_value_per_1000_tokens",
            "no_entropy_selected_actual_value_per_1000_tokens",
            "heuristic_selected_actual_value_per_1000_tokens",
            "full_action_predicted_token_relative_error",
            "no_entropy_action_predicted_token_relative_error",
            *VALUE_ADVANTAGES,
        )
    }
    selection_counts: dict[str, Counter[str]] = {
        "full": Counter(),
        "no_entropy": Counter(),
        "heuristic": Counter(),
    }
    complete = 0
    stable_equal_cost = 0
    policy_comparable = 0
    unstable = 0
    out_of_cost = 0
    nonpositive_cost = 0
    for (cluster, _, context), group in grouped.items():
        action_order = tuple(CONTEXT_ACTIONS[context])
        if len(group) != len(action_order) or {row["action"] for row in group} != set(
            action_order
        ):
            continue
        complete += 1
        if not _stable_checkpoint_group(group):
            unstable += 1
            continue
        actual_costs = {
            str(row["action"]): float(row["actual_action_tokens"]) for row in group
        }
        if (max(actual_costs.values()) - min(actual_costs.values())) / max(
            1.0, min(actual_costs.values())
        ) > float(parent_config["equal_cost_tolerance_fraction"]):
            out_of_cost += 1
            continue
        stable_equal_cost += 1
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
        if any(
            cost <= 0
            for cost in (
                *actual_costs.values(),
                *[
                    value
                    for branch in predicted_tokens.values()
                    for value in branch.values()
                    if isinstance(value, (int, float)) and not isinstance(value, bool)
                ],
            )
        ) or any(
            isinstance(value, bool) or not isinstance(value, int)
            for branch in predicted_tokens.values()
            for value in branch.values()
        ):
            nonpositive_cost += 1
            continue
        policy_comparable += 1
        actual = {
            str(row["action"]): float(row["actual_contribution"]) for row in group
        }
        scores = {
            "full": {
                str(row["action"]): float(row["full_prediction"]) for row in group
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
        selected = {
            name: select_deployment_action(
                values,
                predicted_tokens[
                    "full" if name == "full" else "no_entropy"
                ],
                action_order=action_order,
            )
            for name, values in scores.items()
        }
        values = {
            name: 0.0 if action is None else actual[action]
            for name, action in selected.items()
        }
        random_value = sum(actual.values()) / len(actual)
        oracle_value = max(0.0, max(actual.values()))
        oracle_actions = {action for action, value in actual.items() if value == oracle_value}
        stop_is_oracle = oracle_value == 0.0
        random_oracle_hit = len(oracle_actions) / len(actual)
        for name, action in selected.items():
            selection_counts[name]["stop" if action is None else action] += 1
            metrics[f"{name}_selected_value"][cluster].append(values[name])
            metrics[f"{name}_oracle_regret"][cluster].append(
                oracle_value - values[name]
            )
            hit = bool(
                (action is None and stop_is_oracle)
                or (action is not None and action in oracle_actions)
            )
            metrics[f"{name}_top1_oracle_hit"][cluster].append(float(hit))
            value_per_tokens = (
                0.0
                if action is None
                else 1000.0 * values[name] / actual_costs[action]
            )
            metrics[f"{name}_selected_actual_value_per_1000_tokens"][
                cluster
            ].append(value_per_tokens)
        metrics["uniform_random_action_value"][cluster].append(random_value)
        metrics["oracle_action_or_stop_value"][cluster].append(oracle_value)
        metrics["uniform_random_action_oracle_hit_probability"][cluster].append(
            random_oracle_hit
        )
        metrics["full_selected_value_over_stop"][cluster].append(values["full"])
        metrics["full_minus_uniform_random_action_value"][cluster].append(
            values["full"] - random_value
        )
        metrics["full_minus_no_entropy_policy_value"][cluster].append(
            values["full"] - values["no_entropy"]
        )
        metrics["full_minus_same_action_heuristic_policy_value"][cluster].append(
            values["full"] - values["heuristic"]
        )
        for action in action_order:
            metrics["full_action_predicted_token_relative_error"][cluster].append(
                abs(predicted_tokens["full"][action] - actual_costs[action])
                / actual_costs[action]
            )
            metrics["no_entropy_action_predicted_token_relative_error"][
                cluster
            ].append(
                abs(predicted_tokens["no_entropy"][action] - actual_costs[action])
                / actual_costs[action]
            )

    if (
        complete != parent["parent_strict_gate_replay"][
            "complete_three_action_checkpoints"
        ]
        or stable_equal_cost
        != parent["parent_strict_gate_replay"]["comparable_equal_cost_checkpoints"]
        or unstable
        != parent["parent_strict_gate_replay"]["unstable_checkpoint_groups"]
        or out_of_cost
        != parent["parent_strict_gate_replay"]["out_of_cost_overlap_checkpoints"]
    ):
        raise RuntimeError("V2.41.91 parent comparable-set replay drifted")

    seed = int(config["bootstrap_seed"])
    resamples = int(config["bootstrap_resamples"])
    reports = {
        name: _report(rows, seed=seed + index, resamples=resamples)
        for index, (name, rows) in enumerate(metrics.items())
    }
    simultaneous = _shared_simultaneous_bootstrap(
        {name: metrics[name] for name in VALUE_ADVANTAGES},
        seed=seed + 100,
        resamples=resamples,
        lower_quantile=float(config["simultaneous_lower_quantile"]),
    )
    cluster_count = simultaneous["task_clusters"]
    evaluable = bool(
        parent["status"] != "not_evaluable"
        and policy_comparable >= int(config["minimum_comparable_checkpoints"])
        and cluster_count >= int(config["minimum_independent_task_clusters"])
        and unstable == 0
        and out_of_cost == 0
        and nonpositive_cost == 0
    )
    joint_lower = simultaneous["shared_cluster_bootstrap_minimum_95ci"]["lower"]
    policy_value_passed = bool(
        evaluable and joint_lower is not None and joint_lower > 0.0
    )
    parent_required = bool(config["require_parent_v24190_pass"])
    passed = bool(
        evaluable
        and policy_value_passed
        and (parent["passed"] or not parent_required)
    )
    return {
        "gate": "v24191_policy_value_true_continuation_gate2a",
        "status": "pass" if passed else "fail" if evaluable else "not_evaluable",
        "passed": passed,
        "development_only": True,
        "predictions_frozen_before_audit_outcomes": True,
        "same_checkpoint_true_terminal_contribution": True,
        "single_checkpoint_deployment_decision_replayed_exactly": True,
        "multi_context_closed_loop_policy_value_claimed": False,
        "deployment_policy": {
            "positive_prediction_required_to_act": True,
            "stop_value": 0.0,
            "ranking": "predicted contribution / predicted action tokens",
            "branch_specific_cost_prediction": {
                "full": "full entropy model cost output serialized in prediction seal",
                "no_entropy": "no-entropy model cost output replayed from frozen pre-outcome model",
                "fixed_heuristic": "shares no-entropy cost model, never full entropy cost",
            },
            "tie_break": [
                "larger predicted contribution",
                "lower predicted action tokens",
                "preregistered context action order",
            ],
            "maximum_actions_replayed_per_checkpoint": 1,
            "later_context_state_distribution_replayed": False,
        },
        "task_cluster_equal_weighting": True,
        "complete_three_action_checkpoints": complete,
        "stable_equal_realized_cost_checkpoints": stable_equal_cost,
        "policy_comparable_checkpoints": policy_comparable,
        "independent_policy_task_clusters": cluster_count,
        "unstable_checkpoint_groups": unstable,
        "out_of_cost_overlap_checkpoints": out_of_cost,
        "nonpositive_predicted_or_actual_cost_checkpoints": nonpositive_cost,
        "selection_counts": {
            name: {key: counts[key] for key in sorted(counts)}
            for name, counts in selection_counts.items()
        },
        "policy_value": {
            name: reports[name]
            for name in (
                "full_selected_value",
                "no_entropy_selected_value",
                "heuristic_selected_value",
                "uniform_random_action_value",
                "oracle_action_or_stop_value",
                *VALUE_ADVANTAGES,
            )
        },
        "oracle_regret": {
            name: reports[name]
            for name in (
                "full_oracle_regret",
                "no_entropy_oracle_regret",
                "heuristic_oracle_regret",
            )
        },
        "top1_oracle_hit": {
            name: reports[name]
            for name in (
                "full_top1_oracle_hit",
                "no_entropy_top1_oracle_hit",
                "heuristic_top1_oracle_hit",
                "uniform_random_action_oracle_hit_probability",
            )
        },
        "gain_per_cost_diagnostics": {
            name: reports[name]
            for name in (
                "full_selected_actual_value_per_1000_tokens",
                "no_entropy_selected_actual_value_per_1000_tokens",
                "heuristic_selected_actual_value_per_1000_tokens",
                "full_action_predicted_token_relative_error",
                "no_entropy_action_predicted_token_relative_error",
            )
        },
        "simultaneous_policy_value_advantage": simultaneous,
        "parent_v24190_status_diagnostic_only": parent["status"],
        "parent_v24190_passed_required": parent_required,
        "parent_v24190_gate_replay": parent,
        "policy_settings": config,
        "parent_settings": parent_config,
        "policy_value_conditions_passed": policy_value_passed,
        "controller_design_authorized": passed,
        "controller_implementation_or_pilot_launch_authorized": False,
        "training_credit_authorized": False,
        "full220_controller_launch_authorized": False,
        "benchmark_or_sota_claim": False,
    }
