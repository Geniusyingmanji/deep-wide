"""Abstain-aware successor to the frozen V2.41.91 policy-value Gate-2A.

V2.41.91 replays the frozen Gate-3A value-per-token action ranking and stop
rule, but it does not replay Gate-3A's branch-specific missing-signal rule.
The true-continuation capture is stage-based and may therefore contain an
anchor checkpoint with no entropy (or another context with no required risk
signal).  Canonical zero plus an availability bit is valid model input, but
the online controller must abstain rather than rank actions in that state.

This evaluator replays V2.41.91 unchanged, then evaluates each policy branch
as ``action``, ``stop``, or ``abstain``:

* anchor/full requires both anchor risk and anchor entropy;
* anchor/no-entropy and the fixed heuristic require anchor risk;
* late_0 requires coverage risk;
* late_1 requires row-eligibility or cell-value risk;
* stop and abstain both execute no intervention and have checkpoint
  contribution zero, but remain separately counted;
* every checkpoint remains in the task-cluster-weighted estimand, so excessive
  abstention is penalized instead of silently dropped.

The module is post-terminal and offline only.  It has no model, search,
network, credential, forward, controller, or training execution surface.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .v2409_interventions import CONTEXT_ACTIONS
from .v24123_release import phase_bundles, validate_replicate_aggregate
from .v24161_strict_gate2a import (
    DEFAULT_SETTINGS,
    _finite,
    _stable_checkpoint_group,
    _validate_features,
    _validate_prediction_seal,
    heuristic_score,
)
from .v24191_policy_value_gate2a import (
    DEFAULT_POLICY_SETTINGS,
    VALUE_ADVANTAGES,
    _report,
    _shared_simultaneous_bootstrap,
    evaluate_policy_value_gate2a,
    select_deployment_action,
)


DEFAULT_ABSTAIN_SETTINGS = {
    "minimum_comparable_checkpoints": DEFAULT_SETTINGS[
        "minimum_comparable_checkpoints"
    ],
    "minimum_independent_task_clusters": DEFAULT_SETTINGS[
        "minimum_independent_task_clusters"
    ],
    "minimum_full_signal_available_checkpoints": DEFAULT_SETTINGS[
        "minimum_comparable_checkpoints"
    ],
    "minimum_full_signal_available_task_clusters": DEFAULT_SETTINGS[
        "minimum_independent_task_clusters"
    ],
    "bootstrap_seed": 24192,
    "bootstrap_resamples": DEFAULT_SETTINGS["bootstrap_resamples"],
    "simultaneous_lower_quantile": 0.025,
    "require_parent_v24190_pass": True,
    "retain_missing_signal_checkpoints_in_primary_estimand": True,
    "require_positive_actual_cost_for_all_tested_actions": True,
    "require_positive_predicted_cost_only_when_branch_ranks_actions": True,
    "require_simultaneous_value_advantage_ci_lower_strictly_positive": True,
}


def required_signal_available(
    features: dict[str, Any], *, context: str, branch: str
) -> bool:
    """Return the exact frozen Gate-3A branch availability decision."""

    clean = _validate_features(features)
    if branch not in {"full", "no_entropy", "heuristic"}:
        raise ValueError("V2.41.92 policy branch is invalid")
    if context == "anchor":
        risk = clean["anchor_risk_available"] == 1.0
        if branch == "full":
            return risk and clean["anchor_entropy_available"] == 1.0
        return risk
    if context == "late_0":
        return clean["coverage_risk_available"] == 1.0
    if context == "late_1":
        return bool(
            clean["row_eligibility_risk_available"] == 1.0
            or clean["cell_value_risk_available"] == 1.0
        )
    raise ValueError("V2.41.92 context is outside the frozen policy")


def branch_decision(
    scores: dict[str, float],
    predicted_tokens: dict[str, int],
    features: dict[str, Any],
    *,
    context: str,
    branch: str,
    action_order: tuple[str, ...] | list[str],
) -> tuple[str, str | None]:
    """Return ``(kind, action)`` for action, stop, or abstain."""

    if not required_signal_available(features, context=context, branch=branch):
        return "abstain", None
    action = select_deployment_action(
        scores,
        predicted_tokens,
        action_order=action_order,
    )
    return ("stop", None) if action is None else ("action", action)


def evaluate_abstain_aware_gate2a(
    manifest: dict[str, Any],
    aggregate_records: list[dict[str, Any]],
    prediction_seal: dict[str, Any],
    no_entropy_predicted_tokens: dict[str, int],
    *,
    parent_settings: dict[str, Any] | None = None,
    policy_settings: dict[str, Any] | None = None,
    abstain_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay V2.41.91 and replace its missing-signal deployment semantics."""

    parent_config = dict(DEFAULT_SETTINGS)
    if parent_settings is not None:
        if set(parent_settings) != set(DEFAULT_SETTINGS):
            raise ValueError("V2.41.92 parent settings schema is not exact")
        parent_config.update(parent_settings)
    policy_config = dict(DEFAULT_POLICY_SETTINGS)
    if policy_settings is not None:
        if set(policy_settings) != set(DEFAULT_POLICY_SETTINGS):
            raise ValueError("V2.41.92 policy settings schema is not exact")
        policy_config.update(policy_settings)
    config = dict(DEFAULT_ABSTAIN_SETTINGS)
    if abstain_settings is not None:
        if set(abstain_settings) != set(DEFAULT_ABSTAIN_SETTINGS):
            raise ValueError("V2.41.92 abstain settings schema is not exact")
        config.update(abstain_settings)
    required_true = (
        "require_parent_v24190_pass",
        "retain_missing_signal_checkpoints_in_primary_estimand",
        "require_positive_actual_cost_for_all_tested_actions",
        "require_positive_predicted_cost_only_when_branch_ranks_actions",
        "require_simultaneous_value_advantage_ci_lower_strictly_positive",
    )
    integer_positive = (
        "minimum_comparable_checkpoints",
        "minimum_independent_task_clusters",
        "minimum_full_signal_available_checkpoints",
        "minimum_full_signal_available_task_clusters",
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
        or isinstance(config["bootstrap_seed"], bool)
        or not isinstance(config["bootstrap_seed"], int)
        or isinstance(config["simultaneous_lower_quantile"], bool)
        or not isinstance(config["simultaneous_lower_quantile"], (int, float))
        or not 0.0 < float(config["simultaneous_lower_quantile"]) < 0.5
    ):
        raise ValueError("V2.41.92 settings are invalid")

    parent = evaluate_policy_value_gate2a(
        manifest,
        aggregate_records,
        prediction_seal,
        no_entropy_predicted_tokens,
        parent_settings=parent_config,
        policy_settings=policy_config,
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
        raise ValueError("V2.41.92 no-entropy predicted costs are not exact")
    bundles = {row["bundle_sha256"]: row for row in manifest["bundles"]}
    records: dict[str, dict[str, Any]] = {}
    valid: dict[str, bool] = {}
    for record in aggregate_records:
        if not isinstance(record, dict):
            raise ValueError("V2.41.92 aggregate is not an object")
        bundle_sha = str(record.get("bundle_sha256", ""))
        bundle = bundles.get(bundle_sha)
        if bundle is None or bundle_sha in records:
            raise ValueError("V2.41.92 aggregate identity is outside or duplicated")
        valid[bundle_sha] = validate_replicate_aggregate(
            record,
            bundle,
            job_manifest_sha256=manifest["manifest_sha256"],
        )
        records[bundle_sha] = record
    if set(records) != set(bundles):
        raise ValueError("V2.41.92 aggregates do not exactly cover the manifest")

    rows: list[dict[str, Any]] = []
    for bundle in phase_bundles(manifest, audit=True):
        bundle_sha = bundle["bundle_sha256"]
        if not valid[bundle_sha]:
            continue
        prediction = predictions[bundle_sha]
        features = _validate_features(bundle.get("pre_action_features"))
        rows.append(
            {
                **bundle,
                "pre_action_features": features,
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

    metric_names = (
        "full_selected_value",
        "no_entropy_selected_value",
        "heuristic_selected_value",
        "full_availability_matched_uniform_random_action_value",
        "unconstrained_oracle_action_or_no_intervention_value",
        "full_availability_matched_oracle_value",
        "no_entropy_availability_matched_oracle_value",
        "heuristic_availability_matched_oracle_value",
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
        "full_action_predicted_token_relative_error_when_ranked",
        "no_entropy_action_predicted_token_relative_error_when_ranked",
        "full_required_signal_available",
        "no_entropy_required_signal_available",
        "heuristic_required_signal_available",
        "full_abstained",
        "no_entropy_abstained",
        "heuristic_abstained",
        *VALUE_ADVANTAGES,
    )
    metrics: dict[str, dict[str, list[float]]] = {
        name: defaultdict(list) for name in metric_names
    }
    full_available_advantages: dict[str, dict[str, list[float]]] = {
        name: defaultdict(list) for name in VALUE_ADVANTAGES
    }
    decision_counts: dict[str, Counter[str]] = {
        "full": Counter(),
        "no_entropy": Counter(),
        "heuristic": Counter(),
    }
    missing_patterns: Counter[str] = Counter()
    complete = 0
    stable_equal_cost = 0
    policy_comparable = 0
    unstable = 0
    out_of_cost = 0
    nonpositive_actual_cost = 0
    nonpositive_required_predicted_cost = 0
    full_available_checkpoints = 0
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
        if any(cost <= 0.0 for cost in actual_costs.values()):
            nonpositive_actual_cost += 1
            continue
        features = group[0]["pre_action_features"]
        available = {
            name: required_signal_available(
                features,
                context=context,
                branch=name,
            )
            for name in ("full", "no_entropy", "heuristic")
        }
        if available["full"]:
            full_available_checkpoints += 1
        missing_patterns[
            f"{context}/full={int(available['full'])}/no_entropy={int(available['no_entropy'])}"
        ] += 1
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
            nonpositive_required_predicted_cost += 1
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
        decisions = {
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
        values = {
            name: 0.0 if action is None else actual[action]
            for name, (_, action) in decisions.items()
        }
        unconstrained_random_value = sum(actual.values()) / len(actual)
        random_value = unconstrained_random_value if available["full"] else 0.0
        unconstrained_oracle_value = max(0.0, max(actual.values()))
        oracle_actions = {
            action
            for action, value in actual.items()
            if value == unconstrained_oracle_value
        }
        random_oracle_hit = (
            len(oracle_actions) / len(actual) if available["full"] else 1.0
        )
        for name, (kind, action) in decisions.items():
            branch_oracle_value = (
                unconstrained_oracle_value if available[name] else 0.0
            )
            decision_counts[name][kind if action is None else action] += 1
            metrics[f"{name}_required_signal_available"][cluster].append(
                float(available[name])
            )
            metrics[f"{name}_abstained"][cluster].append(float(kind == "abstain"))
            metrics[f"{name}_selected_value"][cluster].append(values[name])
            metrics[f"{name}_oracle_regret"][cluster].append(
                branch_oracle_value - values[name]
            )
            hit = bool(
                (action is None and branch_oracle_value == 0.0)
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
        metrics["full_availability_matched_uniform_random_action_value"][
            cluster
        ].append(random_value)
        metrics["unconstrained_oracle_action_or_no_intervention_value"][
            cluster
        ].append(unconstrained_oracle_value)
        for name in ("full", "no_entropy", "heuristic"):
            metrics[f"{name}_availability_matched_oracle_value"][cluster].append(
                unconstrained_oracle_value if available[name] else 0.0
            )
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
        if available["full"]:
            full_available_advantages["full_selected_value_over_stop"][
                cluster
            ].append(values["full"])
            full_available_advantages[
                "full_minus_uniform_random_action_value"
            ][cluster].append(values["full"] - random_value)
            full_available_advantages[
                "full_minus_no_entropy_policy_value"
            ][cluster].append(values["full"] - values["no_entropy"])
            full_available_advantages[
                "full_minus_same_action_heuristic_policy_value"
            ][cluster].append(values["full"] - values["heuristic"])
        if available["full"]:
            for action in action_order:
                metrics[
                    "full_action_predicted_token_relative_error_when_ranked"
                ][cluster].append(
                    abs(predicted_tokens["full"][action] - actual_costs[action])
                    / actual_costs[action]
                )
        if available["no_entropy"]:
            for action in action_order:
                metrics[
                    "no_entropy_action_predicted_token_relative_error_when_ranked"
                ][cluster].append(
                    abs(
                        predicted_tokens["no_entropy"][action]
                        - actual_costs[action]
                    )
                    / actual_costs[action]
                )

    strict_parent = parent["parent_v24190_gate_replay"]["parent_strict_gate_replay"]
    if (
        complete != strict_parent["complete_three_action_checkpoints"]
        or stable_equal_cost != strict_parent["comparable_equal_cost_checkpoints"]
        or unstable != strict_parent["unstable_checkpoint_groups"]
        or out_of_cost != strict_parent["out_of_cost_overlap_checkpoints"]
    ):
        raise RuntimeError("V2.41.92 parent comparable-set replay drifted")

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
    full_available_simultaneous = _shared_simultaneous_bootstrap(
        full_available_advantages,
        seed=seed + 200,
        resamples=resamples,
        lower_quantile=float(config["simultaneous_lower_quantile"]),
    )
    cluster_count = simultaneous["task_clusters"]
    available_cluster_count = full_available_simultaneous["task_clusters"]
    parent_v90_passed = bool(parent["parent_v24190_gate_replay"]["passed"])
    evaluable = bool(
        policy_comparable >= int(config["minimum_comparable_checkpoints"])
        and cluster_count >= int(config["minimum_independent_task_clusters"])
        and full_available_checkpoints
        >= int(config["minimum_full_signal_available_checkpoints"])
        and available_cluster_count
        >= int(config["minimum_full_signal_available_task_clusters"])
        and unstable == 0
        and out_of_cost == 0
        and nonpositive_actual_cost == 0
        and nonpositive_required_predicted_cost == 0
    )
    joint_lower = simultaneous["shared_cluster_bootstrap_minimum_95ci"]["lower"]
    available_joint_lower = full_available_simultaneous[
        "shared_cluster_bootstrap_minimum_95ci"
    ]["lower"]
    policy_value_passed = bool(
        evaluable
        and joint_lower is not None
        and joint_lower > 0.0
        and available_joint_lower is not None
        and available_joint_lower > 0.0
    )
    passed = bool(evaluable and parent_v90_passed and policy_value_passed)
    return {
        "gate": "v24192_abstain_aware_true_continuation_gate2a",
        "status": "pass" if passed else "fail" if evaluable else "not_evaluable",
        "passed": passed,
        "development_only": True,
        "predictions_frozen_before_audit_outcomes": True,
        "same_checkpoint_true_terminal_contribution": True,
        "single_checkpoint_gate3a_action_stop_abstain_replayed_exactly": True,
        "multi_context_closed_loop_policy_value_claimed": False,
        "missing_signal_checkpoints_retained_in_primary_estimand": True,
        "decision_contract": {
            "action_value": "sealed terminal contribution of selected action",
            "stop_value": 0.0,
            "abstain_value": 0.0,
            "stop_and_abstain_distinguished_in_reporting": True,
            "full_required_signal": {
                "anchor": "anchor risk and anchor entropy",
                "late_0": "coverage risk",
                "late_1": "row-eligibility or cell-value risk",
            },
            "no_entropy_and_heuristic_required_signal": {
                "anchor": "anchor risk",
                "late_0": "coverage risk",
                "late_1": "row-eligibility or cell-value risk",
            },
            "ranking_when_available": "strictly-positive predicted contribution / branch-specific predicted tokens",
        },
        "task_cluster_equal_weighting": True,
        "complete_three_action_checkpoints": complete,
        "stable_equal_realized_cost_checkpoints": stable_equal_cost,
        "policy_comparable_checkpoints": policy_comparable,
        "independent_policy_task_clusters": cluster_count,
        "full_signal_available_checkpoints": full_available_checkpoints,
        "full_signal_available_task_clusters": available_cluster_count,
        "unstable_checkpoint_groups": unstable,
        "out_of_cost_overlap_checkpoints": out_of_cost,
        "nonpositive_actual_cost_checkpoints": nonpositive_actual_cost,
        "nonpositive_required_predicted_cost_checkpoints": (
            nonpositive_required_predicted_cost
        ),
        "decision_counts": {
            name: {key: counts[key] for key in sorted(counts)}
            for name, counts in decision_counts.items()
        },
        "missing_signal_patterns": {
            key: missing_patterns[key] for key in sorted(missing_patterns)
        },
        "availability_and_abstention": {
            name: reports[name]
            for name in (
                "full_required_signal_available",
                "no_entropy_required_signal_available",
                "heuristic_required_signal_available",
                "full_abstained",
                "no_entropy_abstained",
                "heuristic_abstained",
            )
        },
        "policy_value": {
            name: reports[name]
            for name in (
                "full_selected_value",
                "no_entropy_selected_value",
                "heuristic_selected_value",
                "full_availability_matched_uniform_random_action_value",
                "unconstrained_oracle_action_or_no_intervention_value",
                "full_availability_matched_oracle_value",
                "no_entropy_availability_matched_oracle_value",
                "heuristic_availability_matched_oracle_value",
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
                "full_action_predicted_token_relative_error_when_ranked",
                "no_entropy_action_predicted_token_relative_error_when_ranked",
            )
        },
        "simultaneous_policy_value_advantage": simultaneous,
        "full_signal_available_simultaneous_action_value_advantage": (
            full_available_simultaneous
        ),
        "parent_v24191_status_diagnostic_only": parent["status"],
        "parent_v24191_passed_diagnostic_only": parent["passed"],
        "parent_v24190_passed_required": True,
        "parent_v24191_gate_replay": parent,
        "abstain_settings": config,
        "policy_settings": policy_config,
        "parent_settings": parent_config,
        "policy_value_conditions_passed": policy_value_passed,
        "controller_design_authorized": passed,
        "controller_implementation_or_pilot_launch_authorized": False,
        "training_credit_authorized": False,
        "full220_controller_launch_authorized": False,
        "benchmark_or_sota_claim": False,
    }
