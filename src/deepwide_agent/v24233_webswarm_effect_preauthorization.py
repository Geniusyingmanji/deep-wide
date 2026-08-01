"""Build-only preauthorization journal for V2.42.32 budget charges.

V2.42.32 supplies an immutable shared-budget ledger, but a caller could still
perform an external effect before reporting its cost.  This module provides a
pure two-stage protocol: a declared upper bound is charged to the parent
ledger before an effect permit is emitted, and a later settlement may report
only an actual cost at or below that charged bound.  Unused reservation is not
refunded, so admitted effects cannot create capacity by optimistic reporting.

The module does not execute or authorize an external effect.  It has no file,
environment, network, model, search, fetch, process, benchmark, or evaluator
capability.  It also cannot prove that a caller used the permit before an
effect, serialized state updates with compare-and-swap, configured provider
limits to respect the reservation, or independently measured actual cost.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from deepwide_agent.v24232_webswarm_total_budget import (
    COST_DIMENSIONS,
    apply_budget_charge,
    build_cost_vector,
    object_sha256,
    validate_arm_budget_ledger,
    validate_budget_start_bundle,
    validate_shared_total_budget_contract,
)


POLICY_ID = "v24233_webswarm_effect_preauthorization_v1"
PERMIT_ROLE = "v24233_webswarm_effect_permit"
SETTLEMENT_ROLE = "v24233_webswarm_effect_settlement"
STATE_ROLE = "v24233_webswarm_effect_preauthorization_state"
BUNDLE_ROLE = "v24233_webswarm_effect_preauthorization_start_bundle"

MAX_EVENTS = 1_000_000
COST_KEYS = frozenset(COST_DIMENSIONS)

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

PERMIT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "contract_sha256",
        "guidance_policy_sha256",
        "arm_name",
        "arm_sha256",
        "sequence_index",
        "previous_event_sha256",
        "permit_ref_sha256",
        "charge_kind",
        "charge_ref_sha256",
        "estimate_source_sha256",
        "reserved_cost",
        "resulting_budget_ledger_sha256",
        "reserved_cost_declared_as_upper_bound",
        "upper_bound_charged_before_permit_emission",
        "single_use",
        "reserved_cost_independently_verified",
        "provider_limits_enforce_reservation_independently_verified",
        "external_side_effect_authorized",
        "effect_after_permit_independently_verified",
        "permit_sha256",
    }
)
SETTLEMENT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "contract_sha256",
        "guidance_policy_sha256",
        "arm_name",
        "arm_sha256",
        "sequence_index",
        "previous_event_sha256",
        "permit_ref_sha256",
        "permit_sha256",
        "effect_receipt_sha256",
        "actual_cost_source_sha256",
        "actual_cost",
        "unused_reservation",
        "actual_cost_within_declared_charged_upper_bound",
        "charged_budget_ledger_sha256_unchanged",
        "unused_reservation_refunded",
        "actual_cost_independently_measured",
        "external_side_effect_occurrence_independently_verified",
        "effect_after_permit_independently_verified",
        "resulting_budget_ledger_sha256",
        "settlement_sha256",
    }
)
STATE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "contract_sha256",
        "guidance_policy_sha256",
        "arm_name",
        "arm_sha256",
        "initial_budget_ledger",
        "initial_budget_ledger_sha256",
        "current_budget_ledger",
        "current_budget_ledger_sha256",
        "events",
        "event_count",
        "issued_permit_count",
        "settled_permit_count",
        "pending_permit_refs",
        "charged_upper_bound_totals",
        "settled_actual_totals",
        "settled_unused_reservation_totals",
        "pending_reserved_totals",
        "upper_bounds_charged_before_permit_emission",
        "single_use_settlement_enforced",
        "unused_reservation_refunded",
        "parallel_permits_supported_by_serial_admission",
        "single_writer_compare_and_swap_independently_verified",
        "reserved_cost_independently_verified",
        "actual_cost_independently_measured",
        "provider_limits_enforce_reservation_independently_verified",
        "external_cost_overrun_prevented_independently_verified",
        "effect_after_permit_independently_verified",
        "runtime_effect_wrapper_integrated",
        "external_side_effect_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "hard_stop_required",
        "state_sha256",
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
        "budget_start_bundle_sha256",
        "arm_names",
        "state_sha256s",
        "exact_arm_set",
        "identical_contract_across_arms",
        "all_states_begin_without_effect_events",
        "upper_bounds_charged_before_permit_emission",
        "runtime_effect_wrapper_integrated",
        "external_side_effect_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "dev64_or_exact220_launch_authorized",
        "shared_api_lease_acquire_authorized",
        "leaderboard_submission_or_sota_claim_authorized",
        "bundle_sha256",
    }
)


def _clone(value: object) -> Any:
    return json.loads(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


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
        raise ValueError(f"V2.42.33 {label} schema is not exact")
    return value


def _integer(value: object, *, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"V2.42.33 {label} is invalid")
    return value


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    if not _is_sha256(value.get(seal_key)):
        return False
    unsigned = dict(value)
    seal = unsigned.pop(seal_key)
    return seal == object_sha256(unsigned)


def _cost(value: Mapping[str, Any], *, positive: bool) -> dict[str, int]:
    source = _exact(value, keys=COST_KEYS, label="cost")
    cost = build_cost_vector(
        **{dimension: source.get(dimension) for dimension in COST_DIMENSIONS}
    )
    if positive and not any(cost.values()):
        raise ValueError("V2.42.33 reservation must have positive cost")
    return cost


def _zero_cost() -> dict[str, int]:
    return {dimension: 0 for dimension in COST_DIMENSIONS}


def _add_cost(total: dict[str, int], cost: Mapping[str, Any]) -> None:
    for dimension in COST_DIMENSIONS:
        total[dimension] += int(cost[dimension])


def _previous_event_sha256(event: Mapping[str, Any]) -> str:
    role = event.get("role")
    if role == PERMIT_ROLE:
        value = event.get("permit_sha256")
    elif role == SETTLEMENT_ROLE:
        value = event.get("settlement_sha256")
    else:
        raise ValueError("V2.42.33 event role is invalid")
    if not _is_sha256(value):
        raise ValueError("V2.42.33 event seal is invalid")
    return str(value)


def _build_effect_permit(
    *,
    ledger_before: Mapping[str, Any],
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
    sequence_index: int,
    previous_event_sha256: str | None,
    permit_ref_sha256: str,
    charge_kind: str,
    charge_ref_sha256: str,
    estimate_source_sha256: str,
    reserved_cost: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    index = _integer(sequence_index, label="event sequence", minimum=1)
    if index > MAX_EVENTS:
        raise ValueError("V2.42.33 event sequence exceeds the frozen cap")
    if (index == 1 and previous_event_sha256 is not None) or (
        index > 1 and not _is_sha256(previous_event_sha256)
    ):
        raise ValueError("V2.42.33 previous event binding is invalid")
    for label, value in (
        ("permit reference", permit_ref_sha256),
        ("charge reference", charge_ref_sha256),
        ("estimate source", estimate_source_sha256),
    ):
        if not _is_sha256(value):
            raise ValueError(f"V2.42.33 {label} is not SHA-256 bound")
    reserved = _cost(reserved_cost, positive=True)
    ledger_after = apply_budget_charge(
        ledger_before,
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
        charge_kind=charge_kind,
        charge_ref_sha256=charge_ref_sha256,
        source_cost_sha256=estimate_source_sha256,
        cost=reserved,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": PERMIT_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "contract_sha256": contract["contract_sha256"],
        "guidance_policy_sha256": guidance_policy["policy_sha256"],
        "arm_name": guidance_arm["arm_name"],
        "arm_sha256": guidance_arm["arm_sha256"],
        "sequence_index": index,
        "previous_event_sha256": previous_event_sha256,
        "permit_ref_sha256": permit_ref_sha256,
        "charge_kind": charge_kind,
        "charge_ref_sha256": charge_ref_sha256,
        "estimate_source_sha256": estimate_source_sha256,
        "reserved_cost": reserved,
        "resulting_budget_ledger_sha256": ledger_after["ledger_sha256"],
        "reserved_cost_declared_as_upper_bound": True,
        "upper_bound_charged_before_permit_emission": True,
        "single_use": True,
        "reserved_cost_independently_verified": False,
        "provider_limits_enforce_reservation_independently_verified": False,
        "external_side_effect_authorized": EXTERNAL_SIDE_EFFECT_AUTHORIZED,
        "effect_after_permit_independently_verified": False,
    }
    value["permit_sha256"] = object_sha256(value)
    return value, ledger_after


def _build_effect_settlement(
    *,
    permit: Mapping[str, Any],
    current_ledger: Mapping[str, Any],
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    sequence_index: int,
    previous_event_sha256: str | None,
    effect_receipt_sha256: str,
    actual_cost_source_sha256: str,
    actual_cost: Mapping[str, Any],
) -> dict[str, Any]:
    index = _integer(sequence_index, label="event sequence", minimum=1)
    if index > MAX_EVENTS or index < 2 or not _is_sha256(previous_event_sha256):
        raise ValueError("V2.42.33 settlement sequence binding is invalid")
    if not _is_sha256(effect_receipt_sha256) or not _is_sha256(
        actual_cost_source_sha256
    ):
        raise ValueError("V2.42.33 settlement provenance is not SHA-256 bound")
    actual = _cost(actual_cost, positive=False)
    reserved = _cost(permit.get("reserved_cost"), positive=True)
    if any(actual[key] > reserved[key] for key in COST_DIMENSIONS):
        raise ValueError("V2.42.33 actual cost exceeds the charged upper bound")
    unused = {
        dimension: reserved[dimension] - actual[dimension]
        for dimension in COST_DIMENSIONS
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": SETTLEMENT_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "contract_sha256": contract["contract_sha256"],
        "guidance_policy_sha256": guidance_policy["policy_sha256"],
        "arm_name": guidance_arm["arm_name"],
        "arm_sha256": guidance_arm["arm_sha256"],
        "sequence_index": index,
        "previous_event_sha256": previous_event_sha256,
        "permit_ref_sha256": permit["permit_ref_sha256"],
        "permit_sha256": permit["permit_sha256"],
        "effect_receipt_sha256": effect_receipt_sha256,
        "actual_cost_source_sha256": actual_cost_source_sha256,
        "actual_cost": actual,
        "unused_reservation": unused,
        "actual_cost_within_declared_charged_upper_bound": True,
        "charged_budget_ledger_sha256_unchanged": True,
        "unused_reservation_refunded": False,
        "actual_cost_independently_measured": False,
        "external_side_effect_occurrence_independently_verified": False,
        "effect_after_permit_independently_verified": False,
        "resulting_budget_ledger_sha256": current_ledger["ledger_sha256"],
    }
    value["settlement_sha256"] = object_sha256(value)
    return value


def _build_preauthorization_state(
    *,
    initial_budget_ledger: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
) -> dict[str, Any]:
    validate_shared_total_budget_contract(contract)
    validate_arm_budget_ledger(
        initial_budget_ledger,
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    if isinstance(events, (str, bytes)) or not isinstance(events, Sequence):
        raise ValueError("V2.42.33 events must be a sequence")
    if len(events) > MAX_EVENTS:
        raise ValueError("V2.42.33 event journal exceeds the frozen cap")

    current_ledger = _clone(initial_budget_ledger)
    normalized_events: list[dict[str, Any]] = []
    issued: dict[str, dict[str, Any]] = {}
    pending: dict[str, dict[str, Any]] = {}
    settled_effect_receipts: set[str] = set()
    charged_totals = _zero_cost()
    settled_actual_totals = _zero_cost()
    settled_unused_totals = _zero_cost()

    for expected_index, source in enumerate(events, start=1):
        if not isinstance(source, Mapping):
            raise ValueError("V2.42.33 event must be a mapping")
        event = dict(source)
        expected_previous = (
            None
            if expected_index == 1
            else _previous_event_sha256(normalized_events[-1])
        )
        if event.get("role") == PERMIT_ROLE:
            permit_ref = str(event.get("permit_ref_sha256"))
            if permit_ref in issued:
                raise ValueError("V2.42.33 duplicate permit reference rejected")
            expected, ledger_after = _build_effect_permit(
                ledger_before=current_ledger,
                contract=contract,
                guidance_policy=guidance_policy,
                guidance_arm=guidance_arm,
                scouts=scouts,
                probe=probe,
                experience=experience,
                sequence_index=event.get("sequence_index"),
                previous_event_sha256=event.get("previous_event_sha256"),
                permit_ref_sha256=permit_ref,
                charge_kind=str(event.get("charge_kind")),
                charge_ref_sha256=str(event.get("charge_ref_sha256")),
                estimate_source_sha256=str(event.get("estimate_source_sha256")),
                reserved_cost=event.get("reserved_cost"),
            )
            if (
                set(event) != PERMIT_KEYS
                or event != expected
                or event.get("sequence_index") != expected_index
                or event.get("previous_event_sha256") != expected_previous
                or not _sealed(event, seal_key="permit_sha256")
            ):
                raise ValueError("V2.42.33 effect permit drifted")
            normalized = expected
            current_ledger = ledger_after
            issued[permit_ref] = normalized
            pending[permit_ref] = normalized
            _add_cost(charged_totals, normalized["reserved_cost"])
        elif event.get("role") == SETTLEMENT_ROLE:
            permit_ref = str(event.get("permit_ref_sha256"))
            if permit_ref not in pending:
                raise ValueError(
                    "V2.42.33 settlement does not reference a pending permit"
                )
            effect_receipt = str(event.get("effect_receipt_sha256"))
            if effect_receipt in settled_effect_receipts:
                raise ValueError("V2.42.33 duplicate effect receipt rejected")
            permit = pending[permit_ref]
            expected = _build_effect_settlement(
                permit=permit,
                current_ledger=current_ledger,
                contract=contract,
                guidance_policy=guidance_policy,
                guidance_arm=guidance_arm,
                sequence_index=event.get("sequence_index"),
                previous_event_sha256=event.get("previous_event_sha256"),
                effect_receipt_sha256=effect_receipt,
                actual_cost_source_sha256=str(
                    event.get("actual_cost_source_sha256")
                ),
                actual_cost=event.get("actual_cost"),
            )
            if (
                set(event) != SETTLEMENT_KEYS
                or event != expected
                or event.get("sequence_index") != expected_index
                or event.get("previous_event_sha256") != expected_previous
                or event.get("permit_sha256") != permit["permit_sha256"]
                or not _sealed(event, seal_key="settlement_sha256")
            ):
                raise ValueError("V2.42.33 effect settlement drifted")
            normalized = expected
            _add_cost(settled_actual_totals, normalized["actual_cost"])
            _add_cost(settled_unused_totals, normalized["unused_reservation"])
            settled_effect_receipts.add(effect_receipt)
            del pending[permit_ref]
        else:
            raise ValueError("V2.42.33 event role is invalid")
        normalized_events.append(normalized)

    pending_reserved_totals = _zero_cost()
    for permit in pending.values():
        _add_cost(pending_reserved_totals, permit["reserved_cost"])
    initial = _clone(initial_budget_ledger)
    current = _clone(current_ledger)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STATE_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "contract_sha256": contract["contract_sha256"],
        "guidance_policy_sha256": guidance_policy["policy_sha256"],
        "arm_name": guidance_arm["arm_name"],
        "arm_sha256": guidance_arm["arm_sha256"],
        "initial_budget_ledger": initial,
        "initial_budget_ledger_sha256": initial["ledger_sha256"],
        "current_budget_ledger": current,
        "current_budget_ledger_sha256": current["ledger_sha256"],
        "events": normalized_events,
        "event_count": len(normalized_events),
        "issued_permit_count": len(issued),
        "settled_permit_count": len(issued) - len(pending),
        "pending_permit_refs": list(pending),
        "charged_upper_bound_totals": charged_totals,
        "settled_actual_totals": settled_actual_totals,
        "settled_unused_reservation_totals": settled_unused_totals,
        "pending_reserved_totals": pending_reserved_totals,
        "upper_bounds_charged_before_permit_emission": True,
        "single_use_settlement_enforced": True,
        "unused_reservation_refunded": False,
        "parallel_permits_supported_by_serial_admission": True,
        "single_writer_compare_and_swap_independently_verified": False,
        "reserved_cost_independently_verified": False,
        "actual_cost_independently_measured": False,
        "provider_limits_enforce_reservation_independently_verified": False,
        "external_cost_overrun_prevented_independently_verified": False,
        "effect_after_permit_independently_verified": False,
        "runtime_effect_wrapper_integrated": False,
        "external_side_effect_authorized": EXTERNAL_SIDE_EFFECT_AUTHORIZED,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
        "hard_stop_required": current["hard_stop_required"],
    }
    value["state_sha256"] = object_sha256(value)
    return value


def initialize_effect_preauthorization_state(
    *,
    initial_budget_ledger: Mapping[str, Any],
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return _build_preauthorization_state(
        initial_budget_ledger=initial_budget_ledger,
        events=[],
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )


def validate_effect_preauthorization_state(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
) -> None:
    state = _exact(value, keys=STATE_KEYS, label="preauthorization state")
    expected = _build_preauthorization_state(
        initial_budget_ledger=state.get("initial_budget_ledger"),
        events=state.get("events"),
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    if dict(state) != expected or not _sealed(state, seal_key="state_sha256"):
        raise ValueError("V2.42.33 preauthorization state drifted")


def issue_effect_permit(
    previous: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
    permit_ref_sha256: str,
    charge_kind: str,
    charge_ref_sha256: str,
    estimate_source_sha256: str,
    reserved_cost: Mapping[str, Any],
) -> dict[str, Any]:
    validate_effect_preauthorization_state(
        previous,
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    if previous["hard_stop_required"] is True:
        raise ValueError("V2.42.33 charged budget already reached a hard stop")
    if permit_ref_sha256 in {
        event["permit_ref_sha256"]
        for event in previous["events"]
        if event["role"] == PERMIT_ROLE
    }:
        raise ValueError("V2.42.33 duplicate permit reference rejected")
    previous_hash = (
        None
        if not previous["events"]
        else _previous_event_sha256(previous["events"][-1])
    )
    permit, _ = _build_effect_permit(
        ledger_before=previous["current_budget_ledger"],
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
        sequence_index=int(previous["event_count"]) + 1,
        previous_event_sha256=previous_hash,
        permit_ref_sha256=permit_ref_sha256,
        charge_kind=charge_kind,
        charge_ref_sha256=charge_ref_sha256,
        estimate_source_sha256=estimate_source_sha256,
        reserved_cost=reserved_cost,
    )
    return _build_preauthorization_state(
        initial_budget_ledger=previous["initial_budget_ledger"],
        events=[*previous["events"], permit],
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )


def settle_effect_permit(
    previous: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
    permit_ref_sha256: str,
    effect_receipt_sha256: str,
    actual_cost_source_sha256: str,
    actual_cost: Mapping[str, Any],
) -> dict[str, Any]:
    validate_effect_preauthorization_state(
        previous,
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    pending = {
        event["permit_ref_sha256"]: event
        for event in previous["events"]
        if event["role"] == PERMIT_ROLE
        and event["permit_ref_sha256"] in previous["pending_permit_refs"]
    }
    if permit_ref_sha256 not in pending:
        raise ValueError("V2.42.33 permit is absent or already settled")
    previous_hash = _previous_event_sha256(previous["events"][-1])
    settlement = _build_effect_settlement(
        permit=pending[permit_ref_sha256],
        current_ledger=previous["current_budget_ledger"],
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        sequence_index=int(previous["event_count"]) + 1,
        previous_event_sha256=previous_hash,
        effect_receipt_sha256=effect_receipt_sha256,
        actual_cost_source_sha256=actual_cost_source_sha256,
        actual_cost=actual_cost,
    )
    return _build_preauthorization_state(
        initial_budget_ledger=previous["initial_budget_ledger"],
        events=[*previous["events"], settlement],
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )


def validate_effect_preauthorization_transition(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
) -> None:
    validate_effect_preauthorization_state(
        previous,
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    validate_effect_preauthorization_state(
        current,
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    if (
        current["event_count"] != previous["event_count"] + 1
        or current["events"][:-1] != previous["events"]
    ):
        raise ValueError("V2.42.33 transition is not a one-event append")
    event = current["events"][-1]
    shared = {
        "contract": contract,
        "guidance_policy": guidance_policy,
        "guidance_arm": guidance_arm,
        "scouts": scouts,
        "probe": probe,
        "experience": experience,
    }
    if event["role"] == PERMIT_ROLE:
        expected = issue_effect_permit(
            previous,
            **shared,
            permit_ref_sha256=event["permit_ref_sha256"],
            charge_kind=event["charge_kind"],
            charge_ref_sha256=event["charge_ref_sha256"],
            estimate_source_sha256=event["estimate_source_sha256"],
            reserved_cost=event["reserved_cost"],
        )
    elif event["role"] == SETTLEMENT_ROLE:
        expected = settle_effect_permit(
            previous,
            **shared,
            permit_ref_sha256=event["permit_ref_sha256"],
            effect_receipt_sha256=event["effect_receipt_sha256"],
            actual_cost_source_sha256=event["actual_cost_source_sha256"],
            actual_cost=event["actual_cost"],
        )
    else:
        raise ValueError("V2.42.33 transition event role is invalid")
    if dict(current) != expected:
        raise ValueError("V2.42.33 preauthorization transition drifted")


def build_effect_preauthorization_start_bundle(
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_bundle: Mapping[str, Any],
    guidance_bundle_ref_sha256: str,
    guidance_arms: Sequence[Mapping[str, Any]],
    guidance_sources: Mapping[str, Mapping[str, Any]],
    budget_ledgers: Sequence[Mapping[str, Any]],
    budget_start_bundle: Mapping[str, Any],
    states: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    validate_budget_start_bundle(
        budget_start_bundle,
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_bundle=guidance_bundle,
        guidance_bundle_ref_sha256=guidance_bundle_ref_sha256,
        guidance_arms=guidance_arms,
        guidance_sources=guidance_sources,
        ledgers=budget_ledgers,
    )
    if isinstance(states, (str, bytes)) or not isinstance(states, Sequence):
        raise ValueError("V2.42.33 start states must be a sequence")
    arm_names = list(contract["arm_names"])
    arms = {str(arm["arm_name"]): arm for arm in guidance_arms}
    ledgers = {str(ledger["arm_name"]): ledger for ledger in budget_ledgers}
    state_map = {str(state.get("arm_name")): state for state in states}
    if (
        set(arms) != set(arm_names)
        or set(ledgers) != set(arm_names)
        or set(state_map) != set(arm_names)
        or len(states) != len(arm_names)
    ):
        raise ValueError("V2.42.33 start bundle arm set is not exact")
    for name in arm_names:
        source = guidance_sources[name]
        validate_effect_preauthorization_state(
            state_map[name],
            contract=contract,
            guidance_policy=guidance_policy,
            guidance_arm=arms[name],
            scouts=source["scouts"],
            probe=source["probe"],
            experience=source["experience"],
        )
        state = state_map[name]
        if (
            state["event_count"] != 0
            or state["initial_budget_ledger_sha256"]
            != ledgers[name]["ledger_sha256"]
            or state["current_budget_ledger_sha256"]
            != ledgers[name]["ledger_sha256"]
        ):
            raise ValueError("V2.42.33 start state is not pristine")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": BUNDLE_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "contract_sha256": contract["contract_sha256"],
        "guidance_policy_sha256": guidance_policy["policy_sha256"],
        "budget_start_bundle_sha256": budget_start_bundle["bundle_sha256"],
        "arm_names": arm_names,
        "state_sha256s": {
            name: state_map[name]["state_sha256"] for name in arm_names
        },
        "exact_arm_set": True,
        "identical_contract_across_arms": True,
        "all_states_begin_without_effect_events": True,
        "upper_bounds_charged_before_permit_emission": True,
        "runtime_effect_wrapper_integrated": False,
        "external_side_effect_authorized": EXTERNAL_SIDE_EFFECT_AUTHORIZED,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
        "dev64_or_exact220_launch_authorized": DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
        "shared_api_lease_acquire_authorized": SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
        "leaderboard_submission_or_sota_claim_authorized": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    }
    value["bundle_sha256"] = object_sha256(value)
    return value


def validate_effect_preauthorization_start_bundle(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_bundle: Mapping[str, Any],
    guidance_bundle_ref_sha256: str,
    guidance_arms: Sequence[Mapping[str, Any]],
    guidance_sources: Mapping[str, Mapping[str, Any]],
    budget_ledgers: Sequence[Mapping[str, Any]],
    budget_start_bundle: Mapping[str, Any],
    states: Sequence[Mapping[str, Any]],
) -> None:
    bundle = _exact(value, keys=BUNDLE_KEYS, label="start bundle")
    hashes = bundle.get("state_sha256s")
    if not isinstance(hashes, Mapping) or set(hashes) != set(
        contract["arm_names"]
    ):
        raise ValueError("V2.42.33 state hash map is not exact")
    expected = build_effect_preauthorization_start_bundle(
        contract=contract,
        guidance_policy=guidance_policy,
        guidance_bundle=guidance_bundle,
        guidance_bundle_ref_sha256=guidance_bundle_ref_sha256,
        guidance_arms=guidance_arms,
        guidance_sources=guidance_sources,
        budget_ledgers=budget_ledgers,
        budget_start_bundle=budget_start_bundle,
        states=states,
    )
    if dict(bundle) != expected or not _sealed(
        bundle, seal_key="bundle_sha256"
    ):
        raise ValueError("V2.42.33 start bundle drifted")
