"""Build-only TRIAGE-style role-typed credit baseline.

TRIAGE adds a bounded role-conditioned correction to a verifier-derived
trajectory advantage.  This module implements that comparison baseline while
keeping the two information sources separate:

* the role judge receives only a hashed visible-prompt/local-context
  projection with at most five prior and five future action-observation pairs;
* the outcome receipt is created only after a terminal verifier join and is
  unavailable to the role judge; and
* the combined record is training-only and is never imported by the active
  benchmark forward path.

The four constants follow TRIAGE v3 exactly: decisive progress ``1.0``, useful
exploration ``0.5``, no-progress infrastructure ``-0.1``, and regression
``-0.5``.  Unlike V2.42.23, this is an additive baseline and may reverse the
sign of a small outcome advantage.  A role label is a semantic judgment, not a
causal identification result.  Hashes prove binding and schema integrity, not
judge correctness.  Production and credit-training authority therefore remain
frozen false.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence


POLICY_ID = "v24225_triage_role_typed_credit_baseline_v1"
POLICY_ROLE = "v24225_triage_role_typed_credit_policy"
JUDGMENT_ROLE = "v24225_triage_role_judgment"
OUTCOME_ROLE = "v24225_terminal_outcome_advantage_receipt"
CREDIT_ROLE = "v24225_triage_role_typed_credit_record"
BATCH_ROLE = "v24225_triage_role_typed_credit_batch"

ROLE_CONSTANTS = {
    "decisive_progress": 1.0,
    "useful_exploration": 0.5,
    "no_progress_infrastructure": -0.1,
    "regression": -0.5,
}
ROLE_NAMES = frozenset(ROLE_CONSTANTS)
MAX_CONTEXT_PAIRS_PER_SIDE = 5
WHITENING_EPSILON = 1e-8
MIXING_WEIGHT_SELECTION_SCOPE = (
    "preregistered_training_split_only_before_heldout_evaluation"
)
PRODUCTION_PACKAGE_AUTHORIZED = False
CREDIT_TRAINING_AUTHORIZED = False

FORBIDDEN_ROLE_JUDGE_METADATA_KEYS = frozenset(
    {
        "answer",
        "answer_key",
        "benchmark_category",
        "benchmark_subset",
        "category",
        "correctness",
        "evaluator",
        "evaluator_output",
        "evaluator_score",
        "final_outcome",
        "gold",
        "ground_truth",
        "mapping",
        "outcome_advantage",
        "question_type",
        "results.csv",
        "reward",
        "score",
        "split",
        "task_category",
        "verifier_outcome",
    }
)

POLICY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_only",
        "selection_protocol_sha256",
        "role_constants",
        "mixing_weight",
        "mixing_weight_selection_scope",
        "test_or_benchmark_outcome_used_for_selection",
        "judge_context_previous_pair_limit",
        "judge_context_future_pair_limit",
        "batch_whitening",
        "whitening_epsilon",
        "runtime_label_routing_used",
        "production_package_authorized",
        "credit_training_authorized",
        "policy_sha256",
    }
)
JUDGMENT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_only",
        "segment_ref_sha256",
        "trajectory_ref_sha256",
        "visible_task_prompt_projection_sha256",
        "judge_context_projection_sha256",
        "judge_model_sha256",
        "rubric_sha256",
        "previous_action_observation_pair_count",
        "future_action_observation_pair_count",
        "assigned_role",
        "judge_input_tokens",
        "judge_output_tokens",
        "judge_call_count",
        "final_verifier_outcome_available_to_judge",
        "evaluator_gold_mapping_category_question_type_or_score_available_to_judge",
        "question_or_raw_observation_embedded",
        "judgment_sha256",
    }
)
OUTCOME_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "training_only",
        "segment_ref_sha256",
        "trajectory_ref_sha256",
        "group_ref_sha256",
        "verifier_protocol_sha256",
        "verifier_outcome_ref_sha256",
        "outcome_advantage",
        "trajectory_terminal",
        "verifier_joined_post_terminal",
        "role_judgment_or_role_label_available_to_verifier",
        "outcome_reward_or_evaluator_payload_available_to_role_judge",
        "benchmark_metadata_available_to_forward",
        "raw_verifier_payload_embedded",
        "receipt_sha256",
    }
)
CREDIT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_only",
        "policy_sha256",
        "segment_ref_sha256",
        "trajectory_ref_sha256",
        "judgment_sha256",
        "outcome_receipt_sha256",
        "assigned_role",
        "role_constant",
        "mixing_weight",
        "role_correction",
        "outcome_advantage",
        "unwhitened_role_typed_credit",
        "verifier_direction_preserved",
        "judge_and_verifier_sources_separated",
        "role_typing_is_causal_identification",
        "judge_cost",
        "runtime_forward_evaluator_or_training_authorized",
        "record_sha256",
    }
)
WHITENED_RECORD_KEYS = frozenset(
    {
        "segment_ref_sha256",
        "record_sha256",
        "unwhitened_role_typed_credit",
        "whitened_role_typed_credit",
    }
)
BATCH_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "training_baseline_only",
        "policy_sha256",
        "batch_ref_sha256",
        "record_sha256s",
        "record_count",
        "unwhitened_mean",
        "unwhitened_population_std",
        "whitening_epsilon",
        "whitened_records",
        "batch_whitening_applied",
        "runtime_forward_evaluator_or_training_authorized",
        "batch_sha256",
    }
)


def object_sha256(value: object) -> str:
    """Return the canonical SHA-256 used by all V2.42.25 artifacts."""

    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _is_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _exact_mapping(
    value: object, *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.25 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(seal_key, None)
    return _is_sha256(seal) and seal == object_sha256(unsigned)


def _finite(
    value: object, *, label: str, minimum: float, maximum: float
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.42.25 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"V2.42.25 {label} is outside [{minimum},{maximum}]")
    return number


def _nonnegative_integer(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.42.25 {label} is not a nonnegative integer")
    return value


def _sign(value: float, *, epsilon: float = 1e-12) -> int:
    if value > epsilon:
        return 1
    if value < -epsilon:
        return -1
    return 0


def reject_role_judge_privileged_metadata(value: object) -> None:
    """Reject evaluator-only metadata recursively from role-judge inputs."""

    if isinstance(value, Mapping):
        hits = {
            str(key).casefold() for key in value
        }.intersection(FORBIDDEN_ROLE_JUDGE_METADATA_KEYS)
        if hits:
            raise ValueError(
                "V2.42.25 role judge privileged metadata rejected: "
                + ",".join(sorted(hits))
            )
        for child in value.values():
            reject_role_judge_privileged_metadata(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            reject_role_judge_privileged_metadata(child)


def build_credit_policy(
    *, selection_protocol_sha256: str, mixing_weight: float
) -> dict[str, Any]:
    """Freeze one globally selected TRIAGE-style baseline policy."""

    if not _is_sha256(selection_protocol_sha256):
        raise ValueError("V2.42.25 selection protocol is not a SHA-256")
    weight = _finite(
        mixing_weight,
        label="mixing weight",
        minimum=0.0,
        maximum=1.0,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": POLICY_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "selection_protocol_sha256": selection_protocol_sha256,
        "role_constants": dict(ROLE_CONSTANTS),
        "mixing_weight": weight,
        "mixing_weight_selection_scope": MIXING_WEIGHT_SELECTION_SCOPE,
        "test_or_benchmark_outcome_used_for_selection": False,
        "judge_context_previous_pair_limit": MAX_CONTEXT_PAIRS_PER_SIDE,
        "judge_context_future_pair_limit": MAX_CONTEXT_PAIRS_PER_SIDE,
        "batch_whitening": "population_zscore_after_role_correction",
        "whitening_epsilon": WHITENING_EPSILON,
        "runtime_label_routing_used": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
    }
    value["policy_sha256"] = object_sha256(value)
    return value


def validate_credit_policy(value: Mapping[str, Any]) -> None:
    policy = _exact_mapping(value, keys=POLICY_KEYS, label="policy")
    if (
        policy.get("artifact_version") != 1
        or policy.get("role") != POLICY_ROLE
        or policy.get("policy_id") != POLICY_ID
        or policy.get("baseline_only") is not True
        or not _is_sha256(policy.get("selection_protocol_sha256"))
        or policy.get("role_constants") != ROLE_CONSTANTS
        or policy.get("mixing_weight_selection_scope")
        != MIXING_WEIGHT_SELECTION_SCOPE
        or policy.get("test_or_benchmark_outcome_used_for_selection") is not False
        or policy.get("judge_context_previous_pair_limit")
        != MAX_CONTEXT_PAIRS_PER_SIDE
        or policy.get("judge_context_future_pair_limit")
        != MAX_CONTEXT_PAIRS_PER_SIDE
        or policy.get("batch_whitening")
        != "population_zscore_after_role_correction"
        or policy.get("whitening_epsilon") != WHITENING_EPSILON
        or policy.get("runtime_label_routing_used") is not False
        or policy.get("production_package_authorized") is not False
        or policy.get("credit_training_authorized") is not False
        or not _sealed(policy, seal_key="policy_sha256")
    ):
        raise ValueError("V2.42.25 policy contract drifted")
    _finite(
        policy.get("mixing_weight"),
        label="mixing weight",
        minimum=0.0,
        maximum=1.0,
    )


def build_role_judgment(
    *,
    segment_ref_sha256: str,
    trajectory_ref_sha256: str,
    visible_task_prompt_projection_sha256: str,
    judge_context_projection_sha256: str,
    judge_model_sha256: str,
    rubric_sha256: str,
    previous_action_observation_pair_count: int,
    future_action_observation_pair_count: int,
    assigned_role: str,
    judge_input_tokens: int,
    judge_output_tokens: int,
) -> dict[str, Any]:
    """Record one bounded-context role judgment without verifier outcome."""

    hashes = (
        segment_ref_sha256,
        trajectory_ref_sha256,
        visible_task_prompt_projection_sha256,
        judge_context_projection_sha256,
        judge_model_sha256,
        rubric_sha256,
    )
    if not all(_is_sha256(value) for value in hashes):
        raise ValueError("V2.42.25 role judgment identity is not SHA-256 bound")
    previous = _nonnegative_integer(
        previous_action_observation_pair_count,
        label="previous context-pair count",
    )
    following = _nonnegative_integer(
        future_action_observation_pair_count,
        label="future context-pair count",
    )
    if previous > MAX_CONTEXT_PAIRS_PER_SIDE or following > MAX_CONTEXT_PAIRS_PER_SIDE:
        raise ValueError("V2.42.25 role judge context exceeds the frozen 5+5 window")
    if assigned_role not in ROLE_NAMES:
        raise ValueError("V2.42.25 role judgment uses an unknown role")
    input_tokens = _nonnegative_integer(judge_input_tokens, label="judge input tokens")
    output_tokens = _nonnegative_integer(
        judge_output_tokens, label="judge output tokens"
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": JUDGMENT_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "segment_ref_sha256": segment_ref_sha256,
        "trajectory_ref_sha256": trajectory_ref_sha256,
        "visible_task_prompt_projection_sha256": (
            visible_task_prompt_projection_sha256
        ),
        "judge_context_projection_sha256": judge_context_projection_sha256,
        "judge_model_sha256": judge_model_sha256,
        "rubric_sha256": rubric_sha256,
        "previous_action_observation_pair_count": previous,
        "future_action_observation_pair_count": following,
        "assigned_role": assigned_role,
        "judge_input_tokens": input_tokens,
        "judge_output_tokens": output_tokens,
        "judge_call_count": 1,
        "final_verifier_outcome_available_to_judge": False,
        "evaluator_gold_mapping_category_question_type_or_score_available_to_judge": False,
        "question_or_raw_observation_embedded": False,
    }
    value["judgment_sha256"] = object_sha256(value)
    return value


def validate_role_judgment(value: Mapping[str, Any]) -> None:
    judgment = _exact_mapping(value, keys=JUDGMENT_KEYS, label="role judgment")
    reject_role_judge_privileged_metadata(
        {
            "segment_ref_sha256": judgment.get("segment_ref_sha256"),
            "trajectory_ref_sha256": judgment.get("trajectory_ref_sha256"),
            "visible_task_prompt_projection_sha256": judgment.get(
                "visible_task_prompt_projection_sha256"
            ),
            "judge_context_projection_sha256": judgment.get(
                "judge_context_projection_sha256"
            ),
            "judge_model_sha256": judgment.get("judge_model_sha256"),
            "rubric_sha256": judgment.get("rubric_sha256"),
            "assigned_role": judgment.get("assigned_role"),
        }
    )
    hashes = (
        judgment.get("segment_ref_sha256"),
        judgment.get("trajectory_ref_sha256"),
        judgment.get("visible_task_prompt_projection_sha256"),
        judgment.get("judge_context_projection_sha256"),
        judgment.get("judge_model_sha256"),
        judgment.get("rubric_sha256"),
    )
    previous = _nonnegative_integer(
        judgment.get("previous_action_observation_pair_count"),
        label="previous context-pair count",
    )
    following = _nonnegative_integer(
        judgment.get("future_action_observation_pair_count"),
        label="future context-pair count",
    )
    _nonnegative_integer(judgment.get("judge_input_tokens"), label="judge input tokens")
    _nonnegative_integer(
        judgment.get("judge_output_tokens"), label="judge output tokens"
    )
    if (
        judgment.get("artifact_version") != 1
        or judgment.get("role") != JUDGMENT_ROLE
        or judgment.get("policy_id") != POLICY_ID
        or judgment.get("baseline_only") is not True
        or not all(_is_sha256(item) for item in hashes)
        or previous > MAX_CONTEXT_PAIRS_PER_SIDE
        or following > MAX_CONTEXT_PAIRS_PER_SIDE
        or judgment.get("assigned_role") not in ROLE_NAMES
        or judgment.get("judge_call_count") != 1
        or judgment.get("final_verifier_outcome_available_to_judge") is not False
        or judgment.get(
            "evaluator_gold_mapping_category_question_type_or_score_available_to_judge"
        )
        is not False
        or judgment.get("question_or_raw_observation_embedded") is not False
        or not _sealed(judgment, seal_key="judgment_sha256")
    ):
        raise ValueError("V2.42.25 role judgment contract drifted")


def build_outcome_advantage_receipt(
    *,
    segment_ref_sha256: str,
    trajectory_ref_sha256: str,
    group_ref_sha256: str,
    verifier_protocol_sha256: str,
    verifier_outcome_ref_sha256: str,
    outcome_advantage: float,
) -> dict[str, Any]:
    """Bind a post-terminal verifier advantage without exposing its payload."""

    hashes = (
        segment_ref_sha256,
        trajectory_ref_sha256,
        group_ref_sha256,
        verifier_protocol_sha256,
        verifier_outcome_ref_sha256,
    )
    if not all(_is_sha256(value) for value in hashes):
        raise ValueError("V2.42.25 outcome receipt identity is not SHA-256 bound")
    advantage = _finite(
        outcome_advantage,
        label="outcome advantage",
        minimum=-100.0,
        maximum=100.0,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": OUTCOME_ROLE,
        "policy_id": POLICY_ID,
        "training_only": True,
        "segment_ref_sha256": segment_ref_sha256,
        "trajectory_ref_sha256": trajectory_ref_sha256,
        "group_ref_sha256": group_ref_sha256,
        "verifier_protocol_sha256": verifier_protocol_sha256,
        "verifier_outcome_ref_sha256": verifier_outcome_ref_sha256,
        "outcome_advantage": advantage,
        "trajectory_terminal": True,
        "verifier_joined_post_terminal": True,
        "role_judgment_or_role_label_available_to_verifier": False,
        "outcome_reward_or_evaluator_payload_available_to_role_judge": False,
        "benchmark_metadata_available_to_forward": False,
        "raw_verifier_payload_embedded": False,
    }
    value["receipt_sha256"] = object_sha256(value)
    return value


def validate_outcome_advantage_receipt(value: Mapping[str, Any]) -> None:
    receipt = _exact_mapping(value, keys=OUTCOME_KEYS, label="outcome receipt")
    hashes = (
        receipt.get("segment_ref_sha256"),
        receipt.get("trajectory_ref_sha256"),
        receipt.get("group_ref_sha256"),
        receipt.get("verifier_protocol_sha256"),
        receipt.get("verifier_outcome_ref_sha256"),
    )
    _finite(
        receipt.get("outcome_advantage"),
        label="outcome advantage",
        minimum=-100.0,
        maximum=100.0,
    )
    if (
        receipt.get("artifact_version") != 1
        or receipt.get("role") != OUTCOME_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("training_only") is not True
        or not all(_is_sha256(item) for item in hashes)
        or receipt.get("trajectory_terminal") is not True
        or receipt.get("verifier_joined_post_terminal") is not True
        or receipt.get("role_judgment_or_role_label_available_to_verifier")
        is not False
        or receipt.get("outcome_reward_or_evaluator_payload_available_to_role_judge")
        is not False
        or receipt.get("benchmark_metadata_available_to_forward") is not False
        or receipt.get("raw_verifier_payload_embedded") is not False
        or not _sealed(receipt, seal_key="receipt_sha256")
    ):
        raise ValueError("V2.42.25 outcome receipt contract drifted")


def build_role_typed_credit(
    *,
    policy: Mapping[str, Any],
    judgment: Mapping[str, Any],
    outcome_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Combine separated role and outcome sources using the frozen formula."""

    validate_credit_policy(policy)
    validate_role_judgment(judgment)
    validate_outcome_advantage_receipt(outcome_receipt)
    if (
        judgment["segment_ref_sha256"]
        != outcome_receipt["segment_ref_sha256"]
        or judgment["trajectory_ref_sha256"]
        != outcome_receipt["trajectory_ref_sha256"]
    ):
        raise ValueError("V2.42.25 judgment and outcome identities differ")
    assigned_role = str(judgment["assigned_role"])
    role_constant = ROLE_CONSTANTS[assigned_role]
    weight = float(policy["mixing_weight"])
    advantage = float(outcome_receipt["outcome_advantage"])
    correction = weight * role_constant
    credit = advantage + correction
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CREDIT_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "policy_sha256": policy["policy_sha256"],
        "segment_ref_sha256": judgment["segment_ref_sha256"],
        "trajectory_ref_sha256": judgment["trajectory_ref_sha256"],
        "judgment_sha256": judgment["judgment_sha256"],
        "outcome_receipt_sha256": outcome_receipt["receipt_sha256"],
        "assigned_role": assigned_role,
        "role_constant": role_constant,
        "mixing_weight": weight,
        "role_correction": correction,
        "outcome_advantage": advantage,
        "unwhitened_role_typed_credit": credit,
        "verifier_direction_preserved": _sign(credit) == _sign(advantage),
        "judge_and_verifier_sources_separated": True,
        "role_typing_is_causal_identification": False,
        "judge_cost": {
            "calls": judgment["judge_call_count"],
            "input_tokens": judgment["judge_input_tokens"],
            "output_tokens": judgment["judge_output_tokens"],
        },
        "runtime_forward_evaluator_or_training_authorized": False,
    }
    value["record_sha256"] = object_sha256(value)
    return value


def validate_role_typed_credit(
    value: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    judgment: Mapping[str, Any],
    outcome_receipt: Mapping[str, Any],
) -> None:
    _exact_mapping(value, keys=CREDIT_KEYS, label="credit record")
    expected = build_role_typed_credit(
        policy=policy,
        judgment=judgment,
        outcome_receipt=outcome_receipt,
    )
    if dict(value) != expected or not _sealed(value, seal_key="record_sha256"):
        raise ValueError("V2.42.25 role-typed credit contract drifted")


def _validate_standalone_credit(
    value: Mapping[str, Any], *, policy: Mapping[str, Any]
) -> None:
    record = _exact_mapping(value, keys=CREDIT_KEYS, label="credit record")
    validate_credit_policy(policy)
    assigned_role = record.get("assigned_role")
    advantage = _finite(
        record.get("outcome_advantage"),
        label="outcome advantage",
        minimum=-100.0,
        maximum=100.0,
    )
    if assigned_role not in ROLE_NAMES:
        raise ValueError("V2.42.25 credit record uses an unknown role")
    role_constant = ROLE_CONSTANTS[str(assigned_role)]
    weight = float(policy["mixing_weight"])
    correction = weight * role_constant
    credit = advantage + correction
    judge_cost = record.get("judge_cost")
    if not isinstance(judge_cost, Mapping) or set(judge_cost) != {
        "calls",
        "input_tokens",
        "output_tokens",
    }:
        raise ValueError("V2.42.25 judge cost schema drifted")
    for key in ("calls", "input_tokens", "output_tokens"):
        _nonnegative_integer(judge_cost.get(key), label=f"judge cost {key}")
    if (
        record.get("artifact_version") != 1
        or record.get("role") != CREDIT_ROLE
        or record.get("policy_id") != POLICY_ID
        or record.get("baseline_only") is not True
        or record.get("policy_sha256") != policy["policy_sha256"]
        or not all(
            _is_sha256(record.get(key))
            for key in (
                "segment_ref_sha256",
                "trajectory_ref_sha256",
                "judgment_sha256",
                "outcome_receipt_sha256",
            )
        )
        or record.get("role_constant") != role_constant
        or record.get("mixing_weight") != weight
        or record.get("role_correction") != correction
        or record.get("unwhitened_role_typed_credit") != credit
        or record.get("verifier_direction_preserved")
        is not (_sign(credit) == _sign(advantage))
        or record.get("judge_and_verifier_sources_separated") is not True
        or record.get("role_typing_is_causal_identification") is not False
        or record.get("runtime_forward_evaluator_or_training_authorized") is not False
        or not _sealed(record, seal_key="record_sha256")
    ):
        raise ValueError("V2.42.25 standalone credit contract drifted")


def build_whitened_credit_batch(
    *,
    policy: Mapping[str, Any],
    batch_ref_sha256: str,
    credit_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply TRIAGE's within-batch whitening to frozen credit records."""

    validate_credit_policy(policy)
    if not _is_sha256(batch_ref_sha256):
        raise ValueError("V2.42.25 batch reference is not a SHA-256")
    if isinstance(credit_records, (str, bytes)) or len(credit_records) < 2:
        raise ValueError("V2.42.25 whitening requires at least two records")
    ordered = sorted(
        (dict(record) for record in credit_records),
        key=lambda record: str(record.get("segment_ref_sha256", "")),
    )
    for record in ordered:
        _validate_standalone_credit(record, policy=policy)
    segment_refs = [str(record["segment_ref_sha256"]) for record in ordered]
    record_refs = [str(record["record_sha256"]) for record in ordered]
    if len(set(segment_refs)) != len(segment_refs) or len(set(record_refs)) != len(
        record_refs
    ):
        raise ValueError("V2.42.25 whitening records are duplicated")
    raw = [float(record["unwhitened_role_typed_credit"]) for record in ordered]
    mean = sum(raw) / len(raw)
    population_std = math.sqrt(
        sum((number - mean) ** 2 for number in raw) / len(raw)
    )
    whitened = [
        {
            "segment_ref_sha256": record["segment_ref_sha256"],
            "record_sha256": record["record_sha256"],
            "unwhitened_role_typed_credit": number,
            "whitened_role_typed_credit": (
                (number - mean) / (population_std + WHITENING_EPSILON)
            ),
        }
        for record, number in zip(ordered, raw)
    ]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": BATCH_ROLE,
        "policy_id": POLICY_ID,
        "training_baseline_only": True,
        "policy_sha256": policy["policy_sha256"],
        "batch_ref_sha256": batch_ref_sha256,
        "record_sha256s": record_refs,
        "record_count": len(ordered),
        "unwhitened_mean": mean,
        "unwhitened_population_std": population_std,
        "whitening_epsilon": WHITENING_EPSILON,
        "whitened_records": whitened,
        "batch_whitening_applied": True,
        "runtime_forward_evaluator_or_training_authorized": False,
    }
    value["batch_sha256"] = object_sha256(value)
    return value


def validate_whitened_credit_batch(
    value: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    batch_ref_sha256: str,
    credit_records: Sequence[Mapping[str, Any]],
) -> None:
    batch = _exact_mapping(value, keys=BATCH_KEYS, label="whitened batch")
    rows = batch.get("whitened_records")
    if not isinstance(rows, list) or any(
        not isinstance(row, Mapping) or set(row) != WHITENED_RECORD_KEYS
        for row in rows
    ):
        raise ValueError("V2.42.25 whitened-record schema is not exact")
    expected = build_whitened_credit_batch(
        policy=policy,
        batch_ref_sha256=batch_ref_sha256,
        credit_records=credit_records,
    )
    if dict(value) != expected or not _sealed(batch, seal_key="batch_sha256"):
        raise ValueError("V2.42.25 whitened batch contract drifted")
