"""Real-subprocess boundary for the V2.43.23 shared-prefix prototype.

The module is benchmark-external.  It binds two branch children to one sealed
prefix bundle, proves that neither branch repeats upstream plan/search/fetch
effects, and cross-checks the candidate context action against its entropy
admission receipt.  It contains no model, network, search, fetch, mapping, or
evaluator client.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from .v24323_shared_prefix_cell_entropy import (
    build_pair_contract,
    payload_sha256,
    validate_admission_receipt,
    validate_pair_contract,
    validate_shared_prefix_receipt,
)


POLICY_ID = "v24324_real_subprocess_shared_prefix_runner_v1"
BUNDLE_ROLE = "v24324_shared_prefix_bundle"
EFFECT_ROLE = "v24324_branch_effect_receipt"
TRANSPORT_ROLE = "v24324_no_external_transport_receipt"
BRANCH_ROLE = "v24324_shared_prefix_branch_envelope"
PAIR_ROLE = "v24324_shared_prefix_pair_envelope"
ARMS = ("baseline", "candidate")
EXTERNAL_EFFECTS = ("remote_network", "model_provider", "hosted_search", "fetch", "evaluator")


def _digest(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"V2.43.24 {label} is not a SHA-256 digest")
    return value


def _count(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.43.24 {label} is not a nonnegative integer")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def build_prefix_bundle(shared_prefix: Mapping[str, Any]) -> dict[str, Any]:
    prefix = validate_shared_prefix_receipt(shared_prefix)
    value = {
        "artifact_version": 1,
        "role": BUNDLE_ROLE,
        "policy_id": POLICY_ID,
        "shared_prefix": copy.deepcopy(prefix),
        "shared_prefix_receipt_sha256": str(prefix["receipt_sha256"]),
        "producer_execution_count": 1,
        "producer_effects": {
            "plan_model": int(prefix["plan_model_effects"]),
            "first_wave_search": int(prefix["first_wave_search_effects"]),
            "first_wave_fetch": int(prefix["first_wave_fetch_effects"]),
        },
        "bundle_created_before_branch_children": True,
        "bundle_read_only_for_branch_children": True,
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["bundle_payload_sha256"] = payload_sha256(value)
    validate_prefix_bundle(value)
    return value


def validate_prefix_bundle(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "shared_prefix",
        "shared_prefix_receipt_sha256",
        "producer_execution_count",
        "producer_effects",
        "bundle_created_before_branch_children",
        "bundle_read_only_for_branch_children",
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "bundle_payload_sha256",
    }
    prefix = value.get("shared_prefix")
    effects = value.get("producer_effects")
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != BUNDLE_ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(prefix, Mapping)
        or not isinstance(effects, Mapping)
        or set(effects) != {"plan_model", "first_wave_search", "first_wave_fetch"}
        or value.get("producer_execution_count") != 1
        or value.get("bundle_created_before_branch_children") is not True
        or value.get("bundle_read_only_for_branch_children") is not True
        or value.get(
            "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or not _sealed(value, "bundle_payload_sha256")
    ):
        raise ValueError("V2.43.24 prefix bundle drifted")
    prefix_value = validate_shared_prefix_receipt(prefix)
    if value.get("shared_prefix_receipt_sha256") != prefix_value["receipt_sha256"]:
        raise ValueError("V2.43.24 prefix receipt identity drifted")
    for name in effects:
        _count(effects[name], label=f"producer {name}")
    if effects != {
        "plan_model": prefix_value["plan_model_effects"],
        "first_wave_search": prefix_value["first_wave_search_effects"],
        "first_wave_fetch": prefix_value["first_wave_fetch_effects"],
    }:
        raise ValueError("V2.43.24 producer effect ledger drifted")
    return dict(value)


def build_branch_effect_receipt(
    arm: str,
    *,
    shared_prefix_receipt_sha256: str,
    repeated_plan_model_effects: int = 0,
    repeated_first_wave_search_effects: int = 0,
    repeated_first_wave_fetch_effects: int = 0,
    synthetic_synthesis_effects: int = 1,
) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError("V2.43.24 branch arm drifted")
    value = {
        "artifact_version": 1,
        "role": EFFECT_ROLE,
        "policy_id": POLICY_ID,
        "arm": arm,
        "shared_prefix_receipt_sha256": _digest(
            shared_prefix_receipt_sha256, label="effect prefix"
        ),
        "repeated_plan_model_effects": _count(
            repeated_plan_model_effects, label="repeated plan effects"
        ),
        "repeated_first_wave_search_effects": _count(
            repeated_first_wave_search_effects, label="repeated search effects"
        ),
        "repeated_first_wave_fetch_effects": _count(
            repeated_first_wave_fetch_effects, label="repeated fetch effects"
        ),
        "synthetic_synthesis_effects": _count(
            synthetic_synthesis_effects, label="synthetic synthesis effects"
        ),
        "external_provider_effects": 0,
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_branch_effect_receipt(value)
    return value


def validate_branch_effect_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "arm",
        "shared_prefix_receipt_sha256",
        "repeated_plan_model_effects",
        "repeated_first_wave_search_effects",
        "repeated_first_wave_fetch_effects",
        "synthetic_synthesis_effects",
        "external_provider_effects",
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != EFFECT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("arm") not in ARMS
        or value.get("external_provider_effects") != 0
        or value.get(
            "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or not _sealed(value, "receipt_sha256")
    ):
        raise ValueError("V2.43.24 branch effect receipt drifted")
    _digest(value.get("shared_prefix_receipt_sha256"), label="effect prefix")
    for name in (
        "repeated_plan_model_effects",
        "repeated_first_wave_search_effects",
        "repeated_first_wave_fetch_effects",
        "synthetic_synthesis_effects",
    ):
        _count(value.get(name), label=name)
    if (
        value["repeated_plan_model_effects"] != 0
        or value["repeated_first_wave_search_effects"] != 0
        or value["repeated_first_wave_fetch_effects"] != 0
        or value["synthetic_synthesis_effects"] != 1
    ):
        raise ValueError("V2.43.24 branch repeated an upstream effect")
    return dict(value)


def build_no_external_transport_receipt(arm: str) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError("V2.43.24 transport arm drifted")
    value = {
        "artifact_version": 1,
        "role": TRANSPORT_ROLE,
        "policy_id": POLICY_ID,
        "arm": arm,
        **{name: 0 for name in EXTERNAL_EFFECTS},
        "contains_content_identifier_or_credential": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_no_external_transport_receipt(value)
    return value


def validate_no_external_transport_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "arm",
        *EXTERNAL_EFFECTS,
        "contains_content_identifier_or_credential",
        "receipt_sha256",
    }
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != TRANSPORT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("arm") not in ARMS
        or any(value.get(name) != 0 for name in EXTERNAL_EFFECTS)
        or value.get("contains_content_identifier_or_credential") is not False
        or not _sealed(value, "receipt_sha256")
    ):
        raise ValueError("V2.43.24 transport receipt drifted")
    return dict(value)


def build_branch_envelope(
    *,
    arm: str,
    prefix_bundle: Mapping[str, Any],
    prefix_file_sha256_before: str,
    prefix_file_sha256_after: str,
    effect_receipt: Mapping[str, Any],
    transport_receipt: Mapping[str, Any],
    admission_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    bundle = validate_prefix_bundle(prefix_bundle)
    effect = validate_branch_effect_receipt(effect_receipt)
    transport = validate_no_external_transport_receipt(transport_receipt)
    if arm not in ARMS or effect["arm"] != arm or transport["arm"] != arm:
        raise ValueError("V2.43.24 branch arm cross-artifact drifted")
    prefix_sha = str(bundle["shared_prefix_receipt_sha256"])
    if effect["shared_prefix_receipt_sha256"] != prefix_sha:
        raise ValueError("V2.43.24 branch effect prefix drifted")
    if arm == "baseline":
        if admission_receipt is not None:
            raise ValueError("V2.43.24 baseline received reserve admission")
        action = "core_only"
        admission = None
    else:
        if not isinstance(admission_receipt, Mapping):
            raise ValueError("V2.43.24 candidate admission absent")
        admission = validate_admission_receipt(admission_receipt)
        action = str(admission["context_action"])
    value = {
        "artifact_version": 1,
        "role": BRANCH_ROLE,
        "policy_id": POLICY_ID,
        "arm": arm,
        "prefix_bundle_payload_sha256": str(bundle["bundle_payload_sha256"]),
        "shared_prefix_receipt_sha256": prefix_sha,
        "prefix_file_sha256_before": _digest(
            prefix_file_sha256_before, label="prefix file before"
        ),
        "prefix_file_sha256_after": _digest(
            prefix_file_sha256_after, label="prefix file after"
        ),
        "prefix_file_unchanged": prefix_file_sha256_before == prefix_file_sha256_after,
        "branch_effect_receipt_sha256": str(effect["receipt_sha256"]),
        "transport_receipt_sha256": str(transport["receipt_sha256"]),
        "admission_receipt": copy.deepcopy(admission),
        "context_action": action,
        "synthetic_output_sha256": payload_sha256(
            {"arm": arm, "prefix": prefix_sha, "context_action": action}
        ),
        "shared_upstream_effects_repeated": False,
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    validate_branch_envelope(
        value,
        prefix_bundle=bundle,
        effect_receipt=effect,
        transport_receipt=transport,
    )
    return value


def validate_branch_envelope(
    value: Mapping[str, Any],
    *,
    prefix_bundle: Mapping[str, Any],
    effect_receipt: Mapping[str, Any],
    transport_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "arm",
        "prefix_bundle_payload_sha256",
        "shared_prefix_receipt_sha256",
        "prefix_file_sha256_before",
        "prefix_file_sha256_after",
        "prefix_file_unchanged",
        "branch_effect_receipt_sha256",
        "transport_receipt_sha256",
        "admission_receipt",
        "context_action",
        "synthetic_output_sha256",
        "shared_upstream_effects_repeated",
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "envelope_payload_sha256",
    }
    bundle = validate_prefix_bundle(prefix_bundle)
    effect = validate_branch_effect_receipt(effect_receipt)
    transport = validate_no_external_transport_receipt(transport_receipt)
    arm = value.get("arm")
    admission = value.get("admission_receipt")
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != BRANCH_ROLE
        or value.get("policy_id") != POLICY_ID
        or arm not in ARMS
        or effect["arm"] != arm
        or transport["arm"] != arm
        or value.get("prefix_bundle_payload_sha256")
        != bundle["bundle_payload_sha256"]
        or value.get("shared_prefix_receipt_sha256")
        != bundle["shared_prefix_receipt_sha256"]
        or effect["shared_prefix_receipt_sha256"]
        != bundle["shared_prefix_receipt_sha256"]
        or value.get("prefix_file_sha256_before")
        != value.get("prefix_file_sha256_after")
        or value.get("prefix_file_unchanged") is not True
        or value.get("branch_effect_receipt_sha256") != effect["receipt_sha256"]
        or value.get("transport_receipt_sha256") != transport["receipt_sha256"]
        or value.get("shared_upstream_effects_repeated") is not False
        or value.get(
            "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or not _sealed(value, "envelope_payload_sha256")
    ):
        raise ValueError("V2.43.24 branch envelope drifted")
    _digest(value.get("prefix_file_sha256_before"), label="prefix file")
    _digest(value.get("synthetic_output_sha256"), label="synthetic output")
    if arm == "baseline":
        if admission is not None or value.get("context_action") != "core_only":
            raise ValueError("V2.43.24 baseline context drifted")
    else:
        if not isinstance(admission, Mapping):
            raise ValueError("V2.43.24 candidate admission absent")
        admitted = validate_admission_receipt(admission)
        if value.get("context_action") != admitted["context_action"]:
            raise ValueError("V2.43.24 candidate context/admission drifted")
    return dict(value)


def build_pair_envelope(
    *,
    prefix_bundle: Mapping[str, Any],
    baseline_branch: Mapping[str, Any],
    baseline_effect_receipt: Mapping[str, Any],
    baseline_transport_receipt: Mapping[str, Any],
    candidate_branch: Mapping[str, Any],
    candidate_effect_receipt: Mapping[str, Any],
    candidate_transport_receipt: Mapping[str, Any],
    synthesis_prompt_template_sha256: str,
    model_configuration_sha256: str,
) -> dict[str, Any]:
    bundle = validate_prefix_bundle(prefix_bundle)
    if baseline_branch.get("arm") != "baseline" or candidate_branch.get("arm") != "candidate":
        raise ValueError("V2.43.24 pair arm order drifted")
    baseline_effect = validate_branch_effect_receipt(baseline_effect_receipt)
    candidate_effect = validate_branch_effect_receipt(candidate_effect_receipt)
    baseline_transport = validate_no_external_transport_receipt(
        baseline_transport_receipt
    )
    candidate_transport = validate_no_external_transport_receipt(
        candidate_transport_receipt
    )
    validate_branch_envelope(
        baseline_branch,
        prefix_bundle=bundle,
        effect_receipt=baseline_effect,
        transport_receipt=baseline_transport,
    )
    validate_branch_envelope(
        candidate_branch,
        prefix_bundle=bundle,
        effect_receipt=candidate_effect,
        transport_receipt=candidate_transport,
    )
    admission = candidate_branch.get("admission_receipt")
    if not isinstance(admission, Mapping):
        raise ValueError("V2.43.24 pair candidate admission absent")
    pair = build_pair_contract(
        shared_prefix=bundle["shared_prefix"],
        baseline_prefix_sha256=str(baseline_branch["shared_prefix_receipt_sha256"]),
        candidate_prefix_sha256=str(candidate_branch["shared_prefix_receipt_sha256"]),
        synthesis_prompt_template_sha256=synthesis_prompt_template_sha256,
        model_configuration_sha256=model_configuration_sha256,
        candidate_admission=admission,
    )
    value = {
        "artifact_version": 1,
        "role": PAIR_ROLE,
        "policy_id": POLICY_ID,
        "prefix_bundle_payload_sha256": str(bundle["bundle_payload_sha256"]),
        "prefix_producer_execution_count": int(bundle["producer_execution_count"]),
        "baseline_branch_envelope_sha256": str(
            baseline_branch["envelope_payload_sha256"]
        ),
        "candidate_branch_envelope_sha256": str(
            candidate_branch["envelope_payload_sha256"]
        ),
        "v24323_pair_contract": pair,
        "shared_prefix_file_sha256": str(baseline_branch["prefix_file_sha256_before"]),
        "shared_prefix_file_unchanged_across_both_branches": (
            baseline_branch["prefix_file_sha256_before"]
            == baseline_branch["prefix_file_sha256_after"]
            == candidate_branch["prefix_file_sha256_before"]
            == candidate_branch["prefix_file_sha256_after"]
        ),
        "total_repeated_upstream_effects": sum(
            int(receipt[field])
            for receipt in (baseline_effect, candidate_effect)
            for field in (
                "repeated_plan_model_effects",
                "repeated_first_wave_search_effects",
                "repeated_first_wave_fetch_effects",
            )
        ),
        "external_effect_ledger": {
            name: int(baseline_transport[name]) + int(candidate_transport[name])
            for name in EXTERNAL_EFFECTS
        },
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    validate_pair_envelope(value)
    return value


def validate_pair_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "prefix_bundle_payload_sha256",
        "prefix_producer_execution_count",
        "baseline_branch_envelope_sha256",
        "candidate_branch_envelope_sha256",
        "v24323_pair_contract",
        "shared_prefix_file_sha256",
        "shared_prefix_file_unchanged_across_both_branches",
        "total_repeated_upstream_effects",
        "external_effect_ledger",
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "envelope_payload_sha256",
    }
    pair = value.get("v24323_pair_contract")
    ledger = value.get("external_effect_ledger")
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != PAIR_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("prefix_producer_execution_count") != 1
        or not isinstance(pair, Mapping)
        or not isinstance(ledger, Mapping)
        or set(ledger) != set(EXTERNAL_EFFECTS)
        or any(ledger[name] != 0 for name in EXTERNAL_EFFECTS)
        or value.get("shared_prefix_file_unchanged_across_both_branches") is not True
        or value.get("total_repeated_upstream_effects") != 0
        or value.get(
            "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or not _sealed(value, "envelope_payload_sha256")
    ):
        raise ValueError("V2.43.24 pair envelope drifted")
    validate_pair_contract(pair)
    for name in (
        "prefix_bundle_payload_sha256",
        "baseline_branch_envelope_sha256",
        "candidate_branch_envelope_sha256",
        "shared_prefix_file_sha256",
    ):
        _digest(value.get(name), label=name)
    return dict(value)


__all__ = [
    "ARMS",
    "build_branch_effect_receipt",
    "build_branch_envelope",
    "build_no_external_transport_receipt",
    "build_pair_envelope",
    "build_prefix_bundle",
    "validate_branch_effect_receipt",
    "validate_branch_envelope",
    "validate_no_external_transport_receipt",
    "validate_pair_envelope",
    "validate_prefix_bundle",
]
