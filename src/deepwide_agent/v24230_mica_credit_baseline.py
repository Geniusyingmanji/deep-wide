"""Build-only MICA-style multi-granularity credit baseline.

This module implements the equations in MICA v3 (arXiv:2603.06194v3) as a
strict comparison baseline:

* immediate IDR is ``phi_before - phi_after``;
* the Monte Carlo return is the discounted sum of future IDR values;
* returns are population-z-scored across trajectories for the same prompt and
  turn index;
* immediate IDR values are population-z-scored across every valid turn in the
  same prompt group; and
* the two normalized signals are combined with a frozen convex weight.

Only hashes, bounded scalars, and cost counts enter the module.  It has no
file, environment, network, model, search, evaluator, or process capability.
Dense feedback is training-only and may be wrong; a potential decrease is not
a causal contribution and is not an independent outer target.  The module is
therefore not connected to the active benchmark runtime and grants no
production, credit-training, evaluator, or leaderboard authority.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence


POLICY_ID = "v24230_mica_multi_granularity_credit_baseline_v1"
POLICY_ROLE = "v24230_mica_credit_policy"
TRANSITION_ROLE = "v24230_mica_potential_transition"
BATCH_ROLE = "v24230_mica_mixed_advantage_batch"
SOURCE_PAPER_ARXIV = "2603.06194"
SOURCE_PAPER_VERSION = 3

NORMALIZATION_EPSILON = 1e-8
MAX_POTENTIAL = 1_000_000.0
MAX_TRAJECTORIES = 64
MAX_TURNS_PER_TRAJECTORY = 256
MAX_TOKEN_COUNT = 1_000_000_000
MIXING_WEIGHT_SELECTION_SCOPE = (
    "preregistered_training_or_calibration_split_only_before_heldout_evaluation"
)
ALLOWED_DATA_SCOPES = frozenset(
    {"preregistered_training", "preregistered_calibration"}
)

PRODUCTION_PACKAGE_AUTHORIZED = False
CREDIT_TRAINING_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

FORBIDDEN_RUNTIME_METADATA_KEYS = frozenset(
    {
        "answer",
        "answerkey",
        "benchmarkcategory",
        "benchmarklabel",
        "benchmarksubset",
        "category",
        "correctness",
        "evaluator",
        "evaluatoroutput",
        "evaluatorpayload",
        "evaluatorscore",
        "finaloutcome",
        "gold",
        "groundtruth",
        "mapping",
        "officialmetrics",
        "prediction",
        "questiontype",
        "resultscsv",
        "reward",
        "score",
        "split",
        "taskcategory",
        "taskid",
        "verifieroutcome",
    }
)

POLICY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_only",
        "source_paper_arxiv",
        "source_paper_version",
        "selection_protocol_sha256",
        "potential_definition_sha256",
        "dense_feedback_protocol_sha256",
        "discount_factor",
        "turn_return_weight",
        "group_immediate_weight",
        "normalization_epsilon",
        "return_definition",
        "turn_normalization",
        "group_normalization",
        "mixing_weight_selection_scope",
        "test_or_benchmark_outcome_used_for_selection",
        "dense_feedback_scope",
        "runtime_label_routing_used",
        "production_package_authorized",
        "credit_training_authorized",
        "policy_sha256",
    }
)

TRANSITION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_only",
        "training_only",
        "policy_sha256",
        "prompt_group_ref_sha256",
        "trajectory_ref_sha256",
        "segment_ref_sha256",
        "turn_index",
        "state_before_projection_sha256",
        "state_after_projection_sha256",
        "potential_definition_sha256",
        "dense_feedback_protocol_sha256",
        "dense_feedback_receipt_sha256",
        "previous_potential",
        "current_potential",
        "immediate_idr",
        "dense_feedback_cost",
        "data_scope",
        "benchmark_evaluator_gold_mapping_category_question_type_or_score_used",
        "raw_prompt_state_observation_or_evaluator_payload_embedded",
        "dense_feedback_semantic_correctness_independently_verified",
        "transition_sha256",
    }
)

COST_KEYS = frozenset({"calls", "input_tokens", "output_tokens"})
TURN_STATISTIC_KEYS = frozenset(
    {
        "turn_index",
        "eligible_trajectory_count",
        "return_mean",
        "return_population_std",
    }
)
GROUP_STATISTIC_KEYS = frozenset(
    {
        "immediate_reward_count",
        "immediate_reward_mean",
        "immediate_reward_population_std",
    }
)
NORMALIZED_RECORD_KEYS = frozenset(
    {
        "segment_ref_sha256",
        "trajectory_ref_sha256",
        "turn_index",
        "transition_sha256",
        "immediate_idr",
        "monte_carlo_return",
        "turn_normalized_return_advantage",
        "group_normalized_immediate_advantage",
        "mixed_advantage",
    }
)
BATCH_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_only",
        "training_only",
        "policy_sha256",
        "batch_ref_sha256",
        "prompt_group_ref_sha256",
        "potential_definition_sha256",
        "dense_feedback_protocol_sha256",
        "data_scope",
        "discount_factor",
        "turn_return_weight",
        "group_immediate_weight",
        "normalization_epsilon",
        "trajectory_count",
        "transition_count",
        "trajectory_ref_sha256s",
        "transition_sha256s",
        "turn_statistics",
        "group_statistics",
        "normalized_records",
        "dense_feedback_cost",
        "variable_horizon_supported",
        "matched_state_rollout_used",
        "learned_critic_used",
        "dense_feedback_semantic_correctness_independently_verified",
        "potential_is_causal_state_value",
        "same_state_causal_identification",
        "independent_outer_target_used",
        "benchmark_metadata_available_to_forward",
        "runtime_forward_evaluator_or_credit_training_authorized",
        "batch_sha256",
    }
)


def object_sha256(value: object) -> str:
    """Return the canonical JSON SHA-256 used by every sealed object."""

    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _exact_mapping(
    value: Mapping[str, Any], *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.30 {label} schema is not exact")
    return value


def _finite(
    value: object,
    *,
    label: str,
    minimum: float,
    maximum: float,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"V2.42.30 {label} is not finite")
    number = float(value)
    if number < minimum or number > maximum:
        raise ValueError(f"V2.42.30 {label} is outside the frozen range")
    return 0.0 if number == 0.0 else number


def _integer(
    value: object, *, label: str, minimum: int, maximum: int
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"V2.42.30 {label} is outside the frozen range")
    return value


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    if not _is_sha256(value.get(seal_key)):
        return False
    unsigned = dict(value)
    seal = unsigned.pop(seal_key)
    return seal == object_sha256(unsigned)


def _normalized_metadata_key(value: object) -> str:
    return "".join(
        character for character in str(value).casefold() if character.isalnum()
    )


def reject_privileged_runtime_metadata(value: object) -> None:
    """Recursively reject evaluator-only keys from any future adapter input."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _normalized_metadata_key(key) in FORBIDDEN_RUNTIME_METADATA_KEYS:
                raise ValueError("V2.42.30 privileged runtime metadata rejected")
            reject_privileged_runtime_metadata(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            reject_privileged_runtime_metadata(nested)


def build_mica_policy(
    *,
    selection_protocol_sha256: str,
    potential_definition_sha256: str,
    dense_feedback_protocol_sha256: str,
    discount_factor: float,
    turn_return_weight: float,
) -> dict[str, Any]:
    """Freeze the faithful MICA equations before held-out evaluation."""

    hashes = (
        selection_protocol_sha256,
        potential_definition_sha256,
        dense_feedback_protocol_sha256,
    )
    if not all(_is_sha256(value) for value in hashes):
        raise ValueError("V2.42.30 policy identity is not SHA-256 bound")
    gamma = _finite(
        discount_factor,
        label="discount factor",
        minimum=0.0,
        maximum=1.0,
    )
    if gamma <= 0.0:
        raise ValueError("V2.42.30 discount factor must be positive")
    alpha = _finite(
        turn_return_weight,
        label="turn-return weight",
        minimum=0.0,
        maximum=1.0,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": POLICY_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "source_paper_arxiv": SOURCE_PAPER_ARXIV,
        "source_paper_version": SOURCE_PAPER_VERSION,
        "selection_protocol_sha256": selection_protocol_sha256,
        "potential_definition_sha256": potential_definition_sha256,
        "dense_feedback_protocol_sha256": dense_feedback_protocol_sha256,
        "discount_factor": gamma,
        "turn_return_weight": alpha,
        "group_immediate_weight": 1.0 - alpha,
        "normalization_epsilon": NORMALIZATION_EPSILON,
        "return_definition": "discounted_sum_of_future_immediate_idr",
        "turn_normalization": "same_prompt_same_turn_population_zscore",
        "group_normalization": "same_prompt_all_valid_turns_population_zscore",
        "mixing_weight_selection_scope": MIXING_WEIGHT_SELECTION_SCOPE,
        "test_or_benchmark_outcome_used_for_selection": False,
        "dense_feedback_scope": "training_environment_only",
        "runtime_label_routing_used": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
    }
    value["policy_sha256"] = object_sha256(value)
    return value


def validate_mica_policy(value: Mapping[str, Any]) -> None:
    policy = _exact_mapping(value, keys=POLICY_KEYS, label="policy")
    expected = build_mica_policy(
        selection_protocol_sha256=str(policy.get("selection_protocol_sha256")),
        potential_definition_sha256=str(policy.get("potential_definition_sha256")),
        dense_feedback_protocol_sha256=str(
            policy.get("dense_feedback_protocol_sha256")
        ),
        discount_factor=policy.get("discount_factor"),
        turn_return_weight=policy.get("turn_return_weight"),
    )
    if dict(policy) != expected or not _sealed(policy, seal_key="policy_sha256"):
        raise ValueError("V2.42.30 policy contract drifted")


def build_potential_transition(
    *,
    policy: Mapping[str, Any],
    prompt_group_ref_sha256: str,
    trajectory_ref_sha256: str,
    segment_ref_sha256: str,
    turn_index: int,
    state_before_projection_sha256: str,
    state_after_projection_sha256: str,
    dense_feedback_receipt_sha256: str,
    previous_potential: float,
    current_potential: float,
    dense_feedback_calls: int,
    dense_feedback_input_tokens: int,
    dense_feedback_output_tokens: int,
    data_scope: str,
) -> dict[str, Any]:
    """Bind one IDR transition without embedding raw state or evaluator data."""

    validate_mica_policy(policy)
    hashes = (
        prompt_group_ref_sha256,
        trajectory_ref_sha256,
        segment_ref_sha256,
        state_before_projection_sha256,
        state_after_projection_sha256,
        dense_feedback_receipt_sha256,
    )
    if not all(_is_sha256(value) for value in hashes):
        raise ValueError("V2.42.30 transition identity is not SHA-256 bound")
    turn = _integer(
        turn_index,
        label="turn index",
        minimum=1,
        maximum=MAX_TURNS_PER_TRAJECTORY,
    )
    before = _finite(
        previous_potential,
        label="previous potential",
        minimum=0.0,
        maximum=MAX_POTENTIAL,
    )
    after = _finite(
        current_potential,
        label="current potential",
        minimum=0.0,
        maximum=MAX_POTENTIAL,
    )
    calls = _integer(
        dense_feedback_calls,
        label="dense-feedback calls",
        minimum=0,
        maximum=MAX_TOKEN_COUNT,
    )
    input_tokens = _integer(
        dense_feedback_input_tokens,
        label="dense-feedback input tokens",
        minimum=0,
        maximum=MAX_TOKEN_COUNT,
    )
    output_tokens = _integer(
        dense_feedback_output_tokens,
        label="dense-feedback output tokens",
        minimum=0,
        maximum=MAX_TOKEN_COUNT,
    )
    if data_scope not in ALLOWED_DATA_SCOPES:
        raise ValueError("V2.42.30 transition data scope is not training/calibration")
    immediate = before - after
    immediate = 0.0 if immediate == 0.0 else immediate
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": TRANSITION_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "training_only": True,
        "policy_sha256": policy["policy_sha256"],
        "prompt_group_ref_sha256": prompt_group_ref_sha256,
        "trajectory_ref_sha256": trajectory_ref_sha256,
        "segment_ref_sha256": segment_ref_sha256,
        "turn_index": turn,
        "state_before_projection_sha256": state_before_projection_sha256,
        "state_after_projection_sha256": state_after_projection_sha256,
        "potential_definition_sha256": policy["potential_definition_sha256"],
        "dense_feedback_protocol_sha256": policy[
            "dense_feedback_protocol_sha256"
        ],
        "dense_feedback_receipt_sha256": dense_feedback_receipt_sha256,
        "previous_potential": before,
        "current_potential": after,
        "immediate_idr": immediate,
        "dense_feedback_cost": {
            "calls": calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
        "data_scope": data_scope,
        "benchmark_evaluator_gold_mapping_category_question_type_or_score_used": False,
        "raw_prompt_state_observation_or_evaluator_payload_embedded": False,
        "dense_feedback_semantic_correctness_independently_verified": False,
    }
    value["transition_sha256"] = object_sha256(value)
    return value


def validate_potential_transition(
    value: Mapping[str, Any], *, policy: Mapping[str, Any]
) -> None:
    transition = _exact_mapping(value, keys=TRANSITION_KEYS, label="transition")
    cost = transition.get("dense_feedback_cost")
    if not isinstance(cost, Mapping) or set(cost) != COST_KEYS:
        raise ValueError("V2.42.30 dense-feedback cost schema is not exact")
    expected = build_potential_transition(
        policy=policy,
        prompt_group_ref_sha256=str(transition.get("prompt_group_ref_sha256")),
        trajectory_ref_sha256=str(transition.get("trajectory_ref_sha256")),
        segment_ref_sha256=str(transition.get("segment_ref_sha256")),
        turn_index=transition.get("turn_index"),
        state_before_projection_sha256=str(
            transition.get("state_before_projection_sha256")
        ),
        state_after_projection_sha256=str(
            transition.get("state_after_projection_sha256")
        ),
        dense_feedback_receipt_sha256=str(
            transition.get("dense_feedback_receipt_sha256")
        ),
        previous_potential=transition.get("previous_potential"),
        current_potential=transition.get("current_potential"),
        dense_feedback_calls=cost.get("calls"),
        dense_feedback_input_tokens=cost.get("input_tokens"),
        dense_feedback_output_tokens=cost.get("output_tokens"),
        data_scope=str(transition.get("data_scope")),
    )
    if dict(transition) != expected or not _sealed(
        transition, seal_key="transition_sha256"
    ):
        raise ValueError("V2.42.30 potential transition contract drifted")


def _population_statistics(values: Sequence[float]) -> tuple[float, float]:
    mean = math.fsum(values) / len(values)
    variance = math.fsum((value - mean) ** 2 for value in values) / len(values)
    standard_deviation = math.sqrt(variance)
    return (
        0.0 if mean == 0.0 else mean,
        0.0 if standard_deviation == 0.0 else standard_deviation,
    )


def _normalized(value: float, mean: float, standard_deviation: float) -> float:
    result = (value - mean) / (standard_deviation + NORMALIZATION_EPSILON)
    return 0.0 if result == 0.0 else result


def _validated_ordered_transitions(
    *, policy: Mapping[str, Any], transitions: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    if isinstance(transitions, (str, bytes)) or not isinstance(transitions, Sequence):
        raise ValueError("V2.42.30 transitions must be a sequence")
    if any(not isinstance(transition, Mapping) for transition in transitions):
        raise ValueError("V2.42.30 every transition must be a mapping")
    if (
        len(transitions) < 2
        or len(transitions) > MAX_TRAJECTORIES * MAX_TURNS_PER_TRAJECTORY
    ):
        raise ValueError("V2.42.30 transition count is outside the frozen range")
    ordered = sorted(
        (dict(transition) for transition in transitions),
        key=lambda item: (
            str(item.get("trajectory_ref_sha256", "")),
            int(item.get("turn_index", 0))
            if isinstance(item.get("turn_index"), int)
            and not isinstance(item.get("turn_index"), bool)
            else 0,
            str(item.get("segment_ref_sha256", "")),
        ),
    )
    for transition in ordered:
        validate_potential_transition(transition, policy=policy)
    prompt_refs = {str(item["prompt_group_ref_sha256"]) for item in ordered}
    definition_refs = {str(item["potential_definition_sha256"]) for item in ordered}
    feedback_refs = {str(item["dense_feedback_protocol_sha256"]) for item in ordered}
    scopes = {str(item["data_scope"]) for item in ordered}
    if (
        len(prompt_refs) != 1
        or definition_refs != {str(policy["potential_definition_sha256"])}
        or feedback_refs != {str(policy["dense_feedback_protocol_sha256"])}
        or len(scopes) != 1
    ):
        raise ValueError("V2.42.30 batch mixes prompt, protocol, or data scope")
    segment_refs = [str(item["segment_ref_sha256"]) for item in ordered]
    transition_refs = [str(item["transition_sha256"]) for item in ordered]
    if len(set(segment_refs)) != len(segment_refs) or len(set(transition_refs)) != len(
        transition_refs
    ):
        raise ValueError("V2.42.30 batch contains duplicate segment/transition")

    by_trajectory: dict[str, list[dict[str, Any]]] = {}
    for transition in ordered:
        by_trajectory.setdefault(
            str(transition["trajectory_ref_sha256"]), []
        ).append(transition)
    if len(by_trajectory) < 2 or len(by_trajectory) > MAX_TRAJECTORIES:
        raise ValueError("V2.42.30 MICA batch requires two to sixty-four trajectories")
    initial_state_refs: set[str] = set()
    initial_potentials: set[float] = set()
    for trajectory in by_trajectory.values():
        indices = [int(item["turn_index"]) for item in trajectory]
        if indices != list(range(1, len(indices) + 1)):
            raise ValueError("V2.42.30 trajectory turn indices are not consecutive")
        if len(trajectory) > MAX_TURNS_PER_TRAJECTORY:
            raise ValueError("V2.42.30 trajectory exceeds the frozen horizon")
        initial_state_refs.add(str(trajectory[0]["state_before_projection_sha256"]))
        initial_potentials.add(float(trajectory[0]["previous_potential"]))
        for previous, current in zip(trajectory, trajectory[1:]):
            if (
                previous["state_after_projection_sha256"]
                != current["state_before_projection_sha256"]
                or previous["current_potential"] != current["previous_potential"]
            ):
                raise ValueError("V2.42.30 trajectory potential/state continuity failed")
    if len(initial_state_refs) != 1 or len(initial_potentials) != 1:
        raise ValueError("V2.42.30 repeated prompt trajectories have different starts")
    return ordered


def build_mica_mixed_advantage_batch(
    *,
    policy: Mapping[str, Any],
    batch_ref_sha256: str,
    transitions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compute faithful MICA return, normalization, and mixture records."""

    validate_mica_policy(policy)
    if not _is_sha256(batch_ref_sha256):
        raise ValueError("V2.42.30 batch reference is not SHA-256 bound")
    ordered = _validated_ordered_transitions(
        policy=policy,
        transitions=transitions,
    )
    by_trajectory: dict[str, list[dict[str, Any]]] = {}
    for transition in ordered:
        by_trajectory.setdefault(
            str(transition["trajectory_ref_sha256"]), []
        ).append(transition)

    gamma = float(policy["discount_factor"])
    returns_by_transition: dict[str, float] = {}
    for trajectory in by_trajectory.values():
        running = 0.0
        for transition in reversed(trajectory):
            running = float(transition["immediate_idr"]) + gamma * running
            returns_by_transition[str(transition["transition_sha256"])] = (
                0.0 if running == 0.0 else running
            )

    returns_by_turn: dict[int, list[float]] = {}
    for transition in ordered:
        returns_by_turn.setdefault(int(transition["turn_index"]), []).append(
            returns_by_transition[str(transition["transition_sha256"])]
        )
    turn_statistics: list[dict[str, Any]] = []
    turn_stats_by_index: dict[int, tuple[float, float]] = {}
    for turn_index in sorted(returns_by_turn):
        values = returns_by_turn[turn_index]
        mean, standard_deviation = _population_statistics(values)
        turn_stats_by_index[turn_index] = (mean, standard_deviation)
        turn_statistics.append(
            {
                "turn_index": turn_index,
                "eligible_trajectory_count": len(values),
                "return_mean": mean,
                "return_population_std": standard_deviation,
            }
        )

    immediate_values = [float(item["immediate_idr"]) for item in ordered]
    immediate_mean, immediate_standard_deviation = _population_statistics(
        immediate_values
    )
    alpha = float(policy["turn_return_weight"])
    beta = float(policy["group_immediate_weight"])
    normalized_records: list[dict[str, Any]] = []
    for transition in ordered:
        turn_index = int(transition["turn_index"])
        transition_ref = str(transition["transition_sha256"])
        monte_carlo_return = returns_by_transition[transition_ref]
        turn_mean, turn_standard_deviation = turn_stats_by_index[turn_index]
        turn_advantage = _normalized(
            monte_carlo_return,
            turn_mean,
            turn_standard_deviation,
        )
        group_advantage = _normalized(
            float(transition["immediate_idr"]),
            immediate_mean,
            immediate_standard_deviation,
        )
        mixed = alpha * turn_advantage + beta * group_advantage
        normalized_records.append(
            {
                "segment_ref_sha256": transition["segment_ref_sha256"],
                "trajectory_ref_sha256": transition["trajectory_ref_sha256"],
                "turn_index": turn_index,
                "transition_sha256": transition_ref,
                "immediate_idr": transition["immediate_idr"],
                "monte_carlo_return": monte_carlo_return,
                "turn_normalized_return_advantage": turn_advantage,
                "group_normalized_immediate_advantage": group_advantage,
                "mixed_advantage": 0.0 if mixed == 0.0 else mixed,
            }
        )

    total_cost = {
        key: sum(int(item["dense_feedback_cost"][key]) for item in ordered)
        for key in sorted(COST_KEYS)
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": BATCH_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "training_only": True,
        "policy_sha256": policy["policy_sha256"],
        "batch_ref_sha256": batch_ref_sha256,
        "prompt_group_ref_sha256": ordered[0]["prompt_group_ref_sha256"],
        "potential_definition_sha256": policy["potential_definition_sha256"],
        "dense_feedback_protocol_sha256": policy[
            "dense_feedback_protocol_sha256"
        ],
        "data_scope": ordered[0]["data_scope"],
        "discount_factor": gamma,
        "turn_return_weight": alpha,
        "group_immediate_weight": beta,
        "normalization_epsilon": NORMALIZATION_EPSILON,
        "trajectory_count": len(by_trajectory),
        "transition_count": len(ordered),
        "trajectory_ref_sha256s": sorted(by_trajectory),
        "transition_sha256s": [
            str(item["transition_sha256"]) for item in ordered
        ],
        "turn_statistics": turn_statistics,
        "group_statistics": {
            "immediate_reward_count": len(immediate_values),
            "immediate_reward_mean": immediate_mean,
            "immediate_reward_population_std": immediate_standard_deviation,
        },
        "normalized_records": normalized_records,
        "dense_feedback_cost": total_cost,
        "variable_horizon_supported": True,
        "matched_state_rollout_used": False,
        "learned_critic_used": False,
        "dense_feedback_semantic_correctness_independently_verified": False,
        "potential_is_causal_state_value": False,
        "same_state_causal_identification": False,
        "independent_outer_target_used": False,
        "benchmark_metadata_available_to_forward": False,
        "runtime_forward_evaluator_or_credit_training_authorized": False,
    }
    value["batch_sha256"] = object_sha256(value)
    return value


def validate_mica_mixed_advantage_batch(
    value: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    batch_ref_sha256: str,
    transitions: Sequence[Mapping[str, Any]],
) -> None:
    batch = _exact_mapping(value, keys=BATCH_KEYS, label="batch")
    turn_statistics = batch.get("turn_statistics")
    group_statistics = batch.get("group_statistics")
    normalized_records = batch.get("normalized_records")
    cost = batch.get("dense_feedback_cost")
    if not isinstance(turn_statistics, list) or any(
        not isinstance(row, Mapping) or set(row) != TURN_STATISTIC_KEYS
        for row in turn_statistics
    ):
        raise ValueError("V2.42.30 turn-statistic schema is not exact")
    if not isinstance(group_statistics, Mapping) or set(
        group_statistics
    ) != GROUP_STATISTIC_KEYS:
        raise ValueError("V2.42.30 group-statistic schema is not exact")
    if not isinstance(normalized_records, list) or any(
        not isinstance(row, Mapping) or set(row) != NORMALIZED_RECORD_KEYS
        for row in normalized_records
    ):
        raise ValueError("V2.42.30 normalized-record schema is not exact")
    if not isinstance(cost, Mapping) or set(cost) != COST_KEYS:
        raise ValueError("V2.42.30 batch cost schema is not exact")
    expected = build_mica_mixed_advantage_batch(
        policy=policy,
        batch_ref_sha256=batch_ref_sha256,
        transitions=transitions,
    )
    if dict(batch) != expected or not _sealed(batch, seal_key="batch_sha256"):
        raise ValueError("V2.42.30 MICA batch contract drifted")
