"""Build-only shared-total-budget ledger for the V2.42.31 baseline.

The V2.42.31 guidance controls bind every arm to one total-budget contract,
but deliberately do not implement an executor that enforces the contract.
This module supplies the missing pure accounting primitive.  It validates a
V2.42.31 arm, debits probe/extractor overhead as the first immutable charge,
and rejects duplicate, zero, post-stop, or over-cap charges before returning a
new ledger.

The module has no file, environment, network, model, search, fetch, process,
benchmark, or evaluator capability.  Accepting a charge does not authorize an
external side effect.  A future runtime wrapper must charge before execution
and must independently attest that ordering; neither property is claimed here.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from deepwide_agent.v24231_webswarm_guidance_baseline import (
    ARM_KEYS as GUIDANCE_ARM_KEYS,
    ARMS as GUIDANCE_ARMS,
    POLICY_ID as GUIDANCE_POLICY_ID,
    object_sha256 as guidance_object_sha256,
    validate_guidance_ablation_bundle,
    validate_guidance_arm,
    validate_guidance_policy,
)


POLICY_ID = "v24232_webswarm_shared_total_budget_v1"
CONTRACT_ROLE = "v24232_webswarm_shared_total_budget_contract"
CHARGE_ROLE = "v24232_webswarm_budget_charge"
LEDGER_ROLE = "v24232_webswarm_budget_ledger"
BUNDLE_ROLE = "v24232_webswarm_budget_start_bundle"

MAX_COST = 1_000_000_000_000_000
MAX_CHARGES = 1_000_000

COST_DIMENSIONS = (
    "model_calls",
    "model_attempts",
    "search_calls",
    "fetch_calls",
    "other_tool_calls",
    "orchestrator_calls",
    "input_tokens",
    "output_tokens",
    "wall_milliseconds",
)
COST_KEYS = frozenset(COST_DIMENSIONS)
EXECUTION_CHARGE_KINDS = frozenset(
    {
        "scout_execution",
        "fanout_execution",
        "orchestrator",
        "renderer",
        "other_tool",
    }
)
ALL_CHARGE_KINDS = EXECUTION_CHARGE_KINDS | {"method_overhead"}

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

CONTRACT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "guidance_policy_id",
        "arm_names",
        "caps",
        "cost_dimensions",
        "wall_unit",
        "wall_rounding",
        "exact_charge_schema",
        "method_overhead_is_first_charge",
        "duplicate_charge_refs_rejected",
        "hard_stop_when_any_cap_reached",
        "charge_acceptance_authorizes_external_side_effect",
        "pre_side_effect_ordering_independently_verified",
        "caller_reported_execution_cost_independently_verified",
        "method_overhead_attempts_extra_tools_independently_verified",
        "runtime_budget_wrapper_implemented",
        "runtime_label_routing_used",
        "production_package_authorized",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "dev64_or_exact220_launch_authorized",
        "shared_api_lease_acquire_authorized",
        "leaderboard_submission_or_sota_claim_authorized",
        "contract_sha256",
    }
)
CHARGE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "contract_sha256",
        "arm_name",
        "arm_sha256",
        "sequence_index",
        "previous_charge_sha256",
        "charge_kind",
        "charge_ref_sha256",
        "source_cost_sha256",
        "cost",
        "method_specific_overhead",
        "external_side_effect_observed",
        "charge_acceptance_authorizes_external_side_effect",
        "charge_sha256",
    }
)
SOURCE_BINDING_KEYS = frozenset({"scouts", "probe", "experience"})
LEDGER_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "contract_sha256",
        "guidance_policy_sha256",
        "arm_name",
        "arm_sha256",
        "charges",
        "charge_count",
        "totals",
        "remaining",
        "method_overhead_charged_first",
        "duplicate_charge_ref_present",
        "budget_exceeded",
        "hard_stop_required",
        "external_side_effect_observed",
        "runtime_enforcement_integrated",
        "benchmark_forward_authorized",
        "ledger_sha256",
    }
)
BUNDLE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "contract_sha256",
        "guidance_policy_sha256",
        "guidance_bundle_sha256",
        "arm_names",
        "ledger_sha256s",
        "exact_arm_set",
        "identical_caps_across_arms",
        "method_overhead_charged_first_for_all_arms",
        "all_ledgers_within_cap",
        "all_ledgers_have_post_overhead_capacity",
        "runtime_budget_enforcement_integrated",
        "benchmark_forward_or_evaluator_authorized",
        "dev64_or_exact220_launch_authorized",
        "shared_api_lease_acquire_authorized",
        "leaderboard_submission_or_sota_claim_authorized",
        "bundle_sha256",
    }
)


def object_sha256(value: object) -> str:
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


def _exact(
    value: Mapping[str, Any], *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.32 {label} schema is not exact")
    return value


def _integer(value: object, *, label: str, minimum: int = 0) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > MAX_COST
    ):
        raise ValueError(f"V2.42.32 {label} is outside the frozen range")
    return value


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    if not _is_sha256(value.get(seal_key)):
        return False
    unsigned = dict(value)
    seal = unsigned.pop(seal_key)
    return seal == object_sha256(unsigned)


def _cost(value: Mapping[str, Any], *, positive: bool) -> dict[str, int]:
    cost = _exact(value, keys=COST_KEYS, label="cost")
    output = {
        dimension: _integer(cost.get(dimension), label=dimension)
        for dimension in COST_DIMENSIONS
    }
    if output["model_attempts"] < output["model_calls"]:
        raise ValueError("V2.42.32 model attempts are below successful calls")
    if positive and not any(output.values()):
        raise ValueError("V2.42.32 zero-cost charges are forbidden")
    return output


def build_cost_vector(
    *,
    model_calls: int,
    model_attempts: int,
    search_calls: int,
    fetch_calls: int,
    other_tool_calls: int,
    orchestrator_calls: int,
    input_tokens: int,
    output_tokens: int,
    wall_milliseconds: int,
) -> dict[str, int]:
    return _cost(
        {
            "model_calls": model_calls,
            "model_attempts": model_attempts,
            "search_calls": search_calls,
            "fetch_calls": fetch_calls,
            "other_tool_calls": other_tool_calls,
            "orchestrator_calls": orchestrator_calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "wall_milliseconds": wall_milliseconds,
        },
        positive=False,
    )


def build_shared_total_budget_contract(
    *,
    model_calls: int,
    model_attempts: int,
    search_calls: int,
    fetch_calls: int,
    other_tool_calls: int,
    orchestrator_calls: int,
    input_tokens: int,
    output_tokens: int,
    wall_milliseconds: int,
) -> dict[str, Any]:
    caps = build_cost_vector(
        model_calls=model_calls,
        model_attempts=model_attempts,
        search_calls=search_calls,
        fetch_calls=fetch_calls,
        other_tool_calls=other_tool_calls,
        orchestrator_calls=orchestrator_calls,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        wall_milliseconds=wall_milliseconds,
    )
    if any(value < 1 for value in caps.values()):
        raise ValueError("V2.42.32 every shared budget cap must be positive")
    if caps["model_attempts"] < caps["model_calls"]:
        raise ValueError("V2.42.32 attempt cap is below model-call cap")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CONTRACT_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "guidance_policy_id": GUIDANCE_POLICY_ID,
        "arm_names": list(GUIDANCE_ARMS),
        "caps": caps,
        "cost_dimensions": list(COST_DIMENSIONS),
        "wall_unit": "integer_milliseconds",
        "wall_rounding": "ceil_each_source_charge",
        "exact_charge_schema": True,
        "method_overhead_is_first_charge": True,
        "duplicate_charge_refs_rejected": True,
        "hard_stop_when_any_cap_reached": True,
        "charge_acceptance_authorizes_external_side_effect": False,
        "pre_side_effect_ordering_independently_verified": False,
        "caller_reported_execution_cost_independently_verified": False,
        "method_overhead_attempts_extra_tools_independently_verified": False,
        "runtime_budget_wrapper_implemented": False,
        "runtime_label_routing_used": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "active_forward_integration_authorized": ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
        "dev64_or_exact220_launch_authorized": DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
        "shared_api_lease_acquire_authorized": SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
        "leaderboard_submission_or_sota_claim_authorized": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    }
    value["contract_sha256"] = object_sha256(value)
    return value


def validate_shared_total_budget_contract(value: Mapping[str, Any]) -> None:
    contract = _exact(value, keys=CONTRACT_KEYS, label="budget contract")
    caps = _cost(contract.get("caps"), positive=False)
    expected = build_shared_total_budget_contract(**caps)
    if dict(contract) != expected or not _sealed(
        contract, seal_key="contract_sha256"
    ):
        raise ValueError("V2.42.32 shared total budget contract drifted")


def _milliseconds(seconds: object) -> int:
    if (
        isinstance(seconds, bool)
        or not isinstance(seconds, (int, float))
        or not math.isfinite(float(seconds))
        or float(seconds) < 0.0
    ):
        raise ValueError("V2.42.32 source wall seconds are invalid")
    milliseconds = math.ceil(float(seconds) * 1000.0)
    return _integer(milliseconds, label="wall milliseconds")


def _method_overhead_wall_milliseconds(
    *,
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
) -> int:
    total = 0
    if probe is not None:
        total += _milliseconds(probe["probe_wall_seconds"])
    if experience is not None:
        total += _milliseconds(experience["extractor_wall_seconds"])
    return total


def _build_charge(
    *,
    contract: Mapping[str, Any],
    arm_name: str,
    arm_sha256: str,
    sequence_index: int,
    previous_charge_sha256: str | None,
    charge_kind: str,
    charge_ref_sha256: str,
    source_cost_sha256: str,
    cost: Mapping[str, Any],
    method_specific_overhead: bool,
) -> dict[str, Any]:
    validate_shared_total_budget_contract(contract)
    if arm_name not in GUIDANCE_ARMS or not _is_sha256(arm_sha256):
        raise ValueError("V2.42.32 charge arm identity is invalid")
    index = _integer(sequence_index, label="charge sequence", minimum=1)
    if index > MAX_CHARGES:
        raise ValueError("V2.42.32 charge sequence exceeds the frozen cap")
    if charge_kind not in ALL_CHARGE_KINDS:
        raise ValueError("V2.42.32 charge kind is invalid")
    if (index == 1 and previous_charge_sha256 is not None) or (
        index > 1 and not _is_sha256(previous_charge_sha256)
    ):
        raise ValueError("V2.42.32 previous charge binding is invalid")
    if not _is_sha256(charge_ref_sha256) or not _is_sha256(source_cost_sha256):
        raise ValueError("V2.42.32 charge provenance is not SHA-256 bound")
    if not isinstance(method_specific_overhead, bool):
        raise ValueError("V2.42.32 method-overhead marker is invalid")
    if (charge_kind == "method_overhead") is not method_specific_overhead:
        raise ValueError("V2.42.32 method-overhead charge marker drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CHARGE_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "contract_sha256": contract["contract_sha256"],
        "arm_name": arm_name,
        "arm_sha256": arm_sha256,
        "sequence_index": index,
        "previous_charge_sha256": previous_charge_sha256,
        "charge_kind": charge_kind,
        "charge_ref_sha256": charge_ref_sha256,
        "source_cost_sha256": source_cost_sha256,
        "cost": _cost(cost, positive=not method_specific_overhead),
        "method_specific_overhead": method_specific_overhead,
        "external_side_effect_observed": False,
        "charge_acceptance_authorizes_external_side_effect": False,
    }
    value["charge_sha256"] = object_sha256(value)
    return value


def validate_budget_charge(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    expected_arm_name: str,
    expected_arm_sha256: str,
) -> None:
    charge = _exact(value, keys=CHARGE_KEYS, label="budget charge")
    expected = _build_charge(
        contract=contract,
        arm_name=str(charge.get("arm_name")),
        arm_sha256=str(charge.get("arm_sha256")),
        sequence_index=charge.get("sequence_index"),
        previous_charge_sha256=charge.get("previous_charge_sha256"),
        charge_kind=str(charge.get("charge_kind")),
        charge_ref_sha256=str(charge.get("charge_ref_sha256")),
        source_cost_sha256=str(charge.get("source_cost_sha256")),
        cost=charge.get("cost"),
        method_specific_overhead=charge.get("method_specific_overhead"),
    )
    if (
        dict(charge) != expected
        or not _sealed(charge, seal_key="charge_sha256")
        or charge["arm_name"] != expected_arm_name
        or charge["arm_sha256"] != expected_arm_sha256
    ):
        raise ValueError("V2.42.32 budget charge contract drifted")


def _build_ledger(
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    arm_name: str,
    arm_sha256: str,
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
    charges: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    validate_shared_total_budget_contract(contract)
    validate_guidance_policy(guidance_policy)
    if (
        guidance_policy["total_budget_contract_sha256"]
        != contract["contract_sha256"]
    ):
        raise ValueError("V2.42.32 guidance policy budget binding differs")
    if arm_name not in GUIDANCE_ARMS or not _is_sha256(arm_sha256):
        raise ValueError("V2.42.32 ledger arm identity is invalid")
    validate_guidance_arm(
        guidance_arm,
        policy=guidance_policy,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    arm = _exact(
        guidance_arm,
        keys=GUIDANCE_ARM_KEYS,
        label="guidance arm",
    )
    unsigned_arm = dict(arm)
    arm_seal = unsigned_arm.pop("arm_sha256")
    if (
        arm.get("arm_name") != arm_name
        or arm_seal != arm_sha256
        or guidance_object_sha256(unsigned_arm) != arm_sha256
        or arm.get("policy_sha256") != guidance_policy["policy_sha256"]
        or arm.get("shared_total_budget_contract_sha256")
        != contract["contract_sha256"]
        or arm.get("method_specific_overhead_counted") is not True
        or arm.get("method_specific_overhead_debited_from_shared_total_cap")
        is not True
    ):
        raise ValueError("V2.42.32 guidance arm budget binding drifted")
    if isinstance(charges, (str, bytes)) or not isinstance(charges, Sequence):
        raise ValueError("V2.42.32 charges must be a sequence")
    if not 1 <= len(charges) <= MAX_CHARGES:
        raise ValueError("V2.42.32 ledger charge count is invalid")
    normalized: list[dict[str, Any]] = []
    for expected_index, source in enumerate(charges, start=1):
        charge = dict(source)
        validate_budget_charge(
            charge,
            contract=contract,
            expected_arm_name=arm_name,
            expected_arm_sha256=arm_sha256,
        )
        normalized_charge = _build_charge(
            contract=contract,
            arm_name=str(charge.get("arm_name")),
            arm_sha256=str(charge.get("arm_sha256")),
            sequence_index=charge.get("sequence_index"),
            previous_charge_sha256=charge.get("previous_charge_sha256"),
            charge_kind=str(charge.get("charge_kind")),
            charge_ref_sha256=str(charge.get("charge_ref_sha256")),
            source_cost_sha256=str(charge.get("source_cost_sha256")),
            cost=charge.get("cost"),
            method_specific_overhead=charge.get("method_specific_overhead"),
        )
        if normalized_charge["sequence_index"] != expected_index:
            raise ValueError("V2.42.32 charge sequence is not contiguous")
        expected_previous = (
            None if expected_index == 1 else normalized[-1]["charge_sha256"]
        )
        if normalized_charge["previous_charge_sha256"] != expected_previous:
            raise ValueError("V2.42.32 charge hash chain drifted")
        normalized.append(normalized_charge)
    refs = [str(charge["charge_ref_sha256"]) for charge in normalized]
    if len(refs) != len(set(refs)):
        raise ValueError("V2.42.32 duplicate charge reference rejected")
    if (
        normalized[0]["charge_kind"] != "method_overhead"
        or normalized[0]["method_specific_overhead"] is not True
        or any(
            charge["method_specific_overhead"] is not False
            or charge["charge_kind"] == "method_overhead"
            for charge in normalized[1:]
        )
    ):
        raise ValueError("V2.42.32 method overhead must be exactly the first charge")
    first_cost = normalized[0]["cost"]
    guidance_cost = arm["probe_extractor_cost"]
    expected_known_cost = {
        "model_calls": int(guidance_cost["model_calls"]),
        "search_calls": int(guidance_cost["search_calls"]),
        "fetch_calls": int(guidance_cost["fetch_calls"]),
        "input_tokens": int(guidance_cost["input_tokens"]),
        "output_tokens": int(guidance_cost["output_tokens"]),
        "wall_milliseconds": _method_overhead_wall_milliseconds(
            probe=probe,
            experience=experience,
        ),
    }
    if any(first_cost[key] != expected for key, expected in expected_known_cost.items()):
        raise ValueError("V2.42.32 method overhead differs from the guidance arm")
    expected_source_cost_sha256 = object_sha256(
        {
            "guidance_probe_extractor_cost": guidance_cost,
            "method_overhead_model_attempts": first_cost["model_attempts"],
            "method_overhead_other_tool_calls": first_cost["other_tool_calls"],
            "method_overhead_orchestrator_calls": first_cost[
                "orchestrator_calls"
            ],
            "wall_rounding": contract["wall_rounding"],
        }
    )
    if normalized[0]["source_cost_sha256"] != expected_source_cost_sha256:
        raise ValueError("V2.42.32 method overhead source binding drifted")
    caps = contract["caps"]
    totals = {dimension: 0 for dimension in COST_DIMENSIONS}
    for charge_index, charge in enumerate(normalized):
        if charge_index > 0 and any(
            totals[dimension] == caps[dimension]
            for dimension in COST_DIMENSIONS
        ):
            raise ValueError("V2.42.32 charge follows a hard stop")
        for dimension in COST_DIMENSIONS:
            totals[dimension] += int(charge["cost"][dimension])
            if totals[dimension] > MAX_COST:
                raise ValueError("V2.42.32 cumulative budget overflowed")
    exceeded = any(totals[key] > caps[key] for key in COST_DIMENSIONS)
    if exceeded:
        raise ValueError("V2.42.32 shared total budget cap exceeded")
    remaining = {
        dimension: int(caps[dimension]) - totals[dimension]
        for dimension in COST_DIMENSIONS
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": LEDGER_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "contract_sha256": contract["contract_sha256"],
        "guidance_policy_sha256": guidance_policy["policy_sha256"],
        "arm_name": arm_name,
        "arm_sha256": arm_sha256,
        "charges": normalized,
        "charge_count": len(normalized),
        "totals": totals,
        "remaining": remaining,
        "method_overhead_charged_first": True,
        "duplicate_charge_ref_present": False,
        "budget_exceeded": False,
        "hard_stop_required": any(value == 0 for value in remaining.values()),
        "external_side_effect_observed": False,
        "runtime_enforcement_integrated": False,
        "benchmark_forward_authorized": False,
    }
    value["ledger_sha256"] = object_sha256(value)
    return value


def initialize_arm_budget_ledger(
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
    charge_ref_sha256: str,
    method_overhead_model_attempts: int,
    method_overhead_other_tool_calls: int,
    method_overhead_orchestrator_calls: int,
) -> dict[str, Any]:
    validate_guidance_arm(
        arm,
        policy=guidance_policy,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    validate_shared_total_budget_contract(contract)
    if (
        arm["shared_total_budget_contract_sha256"]
        != contract["contract_sha256"]
        or guidance_policy["total_budget_contract_sha256"]
        != contract["contract_sha256"]
    ):
        raise ValueError("V2.42.32 arm shared total budget binding differs")
    source = arm["probe_extractor_cost"]
    full_cost = build_cost_vector(
        model_calls=source["model_calls"],
        model_attempts=method_overhead_model_attempts,
        search_calls=source["search_calls"],
        fetch_calls=source["fetch_calls"],
        other_tool_calls=method_overhead_other_tool_calls,
        orchestrator_calls=method_overhead_orchestrator_calls,
        input_tokens=source["input_tokens"],
        output_tokens=source["output_tokens"],
        wall_milliseconds=_method_overhead_wall_milliseconds(
            probe=probe,
            experience=experience,
        ),
    )
    source_cost_sha256 = object_sha256(
        {
            "guidance_probe_extractor_cost": source,
            "method_overhead_model_attempts": method_overhead_model_attempts,
            "method_overhead_other_tool_calls": method_overhead_other_tool_calls,
            "method_overhead_orchestrator_calls": method_overhead_orchestrator_calls,
            "wall_rounding": contract["wall_rounding"],
        }
    )
    first = _build_charge(
        contract=contract,
        arm_name=str(arm["arm_name"]),
        arm_sha256=str(arm["arm_sha256"]),
        sequence_index=1,
        previous_charge_sha256=None,
        charge_kind="method_overhead",
        charge_ref_sha256=charge_ref_sha256,
        source_cost_sha256=source_cost_sha256,
        cost=full_cost,
        method_specific_overhead=True,
    )
    return _build_ledger(
        contract=contract,
        guidance_policy=guidance_policy,
        arm_name=str(arm["arm_name"]),
        arm_sha256=str(arm["arm_sha256"]),
        guidance_arm=arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
        charges=[first],
    )


def validate_arm_budget_ledger(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
) -> None:
    ledger = _exact(value, keys=LEDGER_KEYS, label="budget ledger")
    expected = _build_ledger(
        contract=contract,
        guidance_policy=guidance_policy,
        arm_name=str(guidance_arm.get("arm_name")),
        arm_sha256=str(guidance_arm.get("arm_sha256")),
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
        charges=ledger.get("charges"),
    )
    if dict(ledger) != expected or not _sealed(
        ledger, seal_key="ledger_sha256"
    ):
        raise ValueError("V2.42.32 arm budget ledger contract drifted")


def apply_budget_charge(
    previous: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
    charge_kind: str,
    charge_ref_sha256: str,
    source_cost_sha256: str,
    cost: Mapping[str, Any],
) -> dict[str, Any]:
    validate_arm_budget_ledger(
        previous,
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    if previous["hard_stop_required"] is True:
        raise ValueError("V2.42.32 budget already reached a hard stop")
    if charge_kind not in EXECUTION_CHARGE_KINDS:
        raise ValueError("V2.42.32 execution charge kind is invalid")
    if charge_ref_sha256 in {
        charge["charge_ref_sha256"] for charge in previous["charges"]
    }:
        raise ValueError("V2.42.32 duplicate charge reference rejected")
    charge = _build_charge(
        contract=contract,
        arm_name=str(guidance_arm.get("arm_name")),
        arm_sha256=str(guidance_arm.get("arm_sha256")),
        sequence_index=int(previous["charge_count"]) + 1,
        previous_charge_sha256=str(previous["charges"][-1]["charge_sha256"]),
        charge_kind=charge_kind,
        charge_ref_sha256=charge_ref_sha256,
        source_cost_sha256=source_cost_sha256,
        cost=cost,
        method_specific_overhead=False,
    )
    return _build_ledger(
        contract=contract,
        guidance_policy=guidance_policy,
        arm_name=str(guidance_arm.get("arm_name")),
        arm_sha256=str(guidance_arm.get("arm_sha256")),
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
        charges=[*previous["charges"], charge],
    )


def validate_budget_transition(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
    charge_kind: str,
    charge_ref_sha256: str,
    source_cost_sha256: str,
    cost: Mapping[str, Any],
) -> None:
    expected = apply_budget_charge(
        previous,
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
        charge_kind=charge_kind,
        charge_ref_sha256=charge_ref_sha256,
        source_cost_sha256=source_cost_sha256,
        cost=cost,
    )
    if dict(current) != expected:
        raise ValueError("V2.42.32 budget transition drifted")


def build_budget_start_bundle(
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_bundle: Mapping[str, Any],
    guidance_bundle_ref_sha256: str,
    guidance_arms: Sequence[Mapping[str, Any]],
    guidance_sources: Mapping[str, Mapping[str, Any]],
    ledgers: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    validate_shared_total_budget_contract(contract)
    validate_guidance_ablation_bundle(
        guidance_bundle,
        policy=guidance_policy,
        bundle_ref_sha256=guidance_bundle_ref_sha256,
        arms=guidance_arms,
    )
    if isinstance(ledgers, (str, bytes)) or not isinstance(ledgers, Sequence):
        raise ValueError("V2.42.32 ledgers must be a sequence")
    if len(ledgers) != len(GUIDANCE_ARMS):
        raise ValueError("V2.42.32 start bundle requires four ledgers")
    arms_by_name = {str(arm["arm_name"]): arm for arm in guidance_arms}
    ledgers_by_name = {str(ledger.get("arm_name")): ledger for ledger in ledgers}
    if set(arms_by_name) != set(GUIDANCE_ARMS) or set(ledgers_by_name) != set(
        GUIDANCE_ARMS
    ):
        raise ValueError("V2.42.32 start bundle arm set is not exact")
    if not isinstance(guidance_sources, Mapping) or set(guidance_sources) != set(
        GUIDANCE_ARMS
    ):
        raise ValueError("V2.42.32 guidance source map is not exact")
    for name in GUIDANCE_ARMS:
        source = _exact(
            guidance_sources[name],
            keys=SOURCE_BINDING_KEYS,
            label="guidance source binding",
        )
        validate_arm_budget_ledger(
            ledgers_by_name[name],
            contract=contract,
            guidance_policy=guidance_policy,
            guidance_arm=arms_by_name[name],
            scouts=source["scouts"],
            probe=source["probe"],
            experience=source["experience"],
        )
        if ledgers_by_name[name]["hard_stop_required"] is True:
            raise ValueError("V2.42.32 method overhead exhausts a shared cap")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": BUNDLE_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "contract_sha256": contract["contract_sha256"],
        "guidance_policy_sha256": guidance_policy["policy_sha256"],
        "guidance_bundle_sha256": guidance_bundle["bundle_sha256"],
        "arm_names": list(GUIDANCE_ARMS),
        "ledger_sha256s": {
            name: str(ledgers_by_name[name]["ledger_sha256"])
            for name in GUIDANCE_ARMS
        },
        "exact_arm_set": True,
        "identical_caps_across_arms": True,
        "method_overhead_charged_first_for_all_arms": True,
        "all_ledgers_within_cap": True,
        "all_ledgers_have_post_overhead_capacity": True,
        "runtime_budget_enforcement_integrated": False,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
        "dev64_or_exact220_launch_authorized": DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
        "shared_api_lease_acquire_authorized": SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
        "leaderboard_submission_or_sota_claim_authorized": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    }
    value["bundle_sha256"] = object_sha256(value)
    return value


def validate_budget_start_bundle(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_bundle: Mapping[str, Any],
    guidance_bundle_ref_sha256: str,
    guidance_arms: Sequence[Mapping[str, Any]],
    guidance_sources: Mapping[str, Mapping[str, Any]],
    ledgers: Sequence[Mapping[str, Any]],
) -> None:
    bundle = _exact(value, keys=BUNDLE_KEYS, label="budget start bundle")
    hashes = bundle.get("ledger_sha256s")
    if not isinstance(hashes, Mapping) or set(hashes) != set(GUIDANCE_ARMS):
        raise ValueError("V2.42.32 ledger-hash map is not exact")
    expected = build_budget_start_bundle(
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_bundle=guidance_bundle,
        guidance_bundle_ref_sha256=guidance_bundle_ref_sha256,
        guidance_arms=guidance_arms,
        guidance_sources=guidance_sources,
        ledgers=ledgers,
    )
    if dict(bundle) != expected or not _sealed(
        bundle, seal_key="bundle_sha256"
    ):
        raise ValueError("V2.42.32 budget start bundle contract drifted")
