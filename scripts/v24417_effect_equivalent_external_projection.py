"""Content-free projection for V2.44.15 effect-equivalent envelopes.

The structured uncertainty mechanism algebra was frozen in V2.44.11.  This
adapter first validates the stronger V2.44.15 envelope, including both
content-free receipt snapshots and the V2.44.13 effect-equivalence
attestation.  It then constructs an in-memory compatibility view of the same
recovery result and post-recovery terminal receipts for the frozen V2.44.11
projector.  No task-private field is copied into the public projection.

The adapter adds only four content-free invariants to each task and aggregate:
effect-equivalence validity, nonincreasing remaining time, monotonic model
deadline state, and monotonic transport deadline state.  It performs no file,
environment, network, model, search, fetch, process, benchmark, evaluator,
reward, or score access.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256
from deepwide_agent.v24409_structured_uncertainty_runner import (
    ENVELOPE_ROLE as COMPAT_ROLE,
    POLICY_ID as COMPAT_POLICY,
    PRIVATE_SCOPE,
    build_envelope as _unused_compat_builder,
)
from deepwide_agent.v24407_structured_uncertainty_recovery import (
    POLICY_ID as RECOVERY_POLICY_ID,
)
from deepwide_agent.v24415_effect_equivalent_structured_runner import (
    validate_envelope as validate_effect_equivalent_envelope,
)
from deepwide_agent.v24413_effect_equivalence import (
    validate_effect_equivalence_receipt,
)
from scripts import v24411_structured_uncertainty_external_projection as base


del _unused_compat_builder
SELECTED = base.SELECTED
MODEL_SLOT_CAP = base.MODEL_SLOT_CAP
COMPLETION_KINDS = base.COMPLETION_KINDS
EQUIVALENCE_FIELDS = (
    "effect_equivalence_valid",
    "model_remaining_seconds_nonincreasing",
    "model_deadline_state_monotonic",
    "transport_deadline_state_monotonic",
)
TASK_CHECK_NAMES = (*base.TASK_CHECK_NAMES, "effect_equivalence_attested")
TASK_KEYS = frozenset({*base.TASK_KEYS, *EQUIVALENCE_FIELDS})
AGGREGATE_CHECK_NAMES = (*base.AGGREGATE_CHECK_NAMES, "all_effect_equivalence_attested")
AGGREGATE_KEYS = frozenset(
    {
        *base.AGGREGATE_KEYS,
        "effect_equivalent_tasks",
        "all_model_remaining_seconds_nonincreasing",
        "all_model_deadline_states_monotonic",
        "all_transport_deadline_states_monotonic",
        "all_effect_equivalence_attested",
    }
)

_BASE_TASK_DERIVED_KEYS = frozenset({"checks", "passed"})
_BASE_AGGREGATE_DERIVED_KEYS = frozenset({"checks", "passed"})


def _base_task_view(value: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild the V2.44.11 view without reading not-yet-derived fields."""
    required = base.TASK_KEYS - _BASE_TASK_DERIVED_KEYS
    if not required <= set(value):
        raise RuntimeError("V2.44.17 base task fields are incomplete")
    projected = {key: copy.deepcopy(value[key]) for key in required}
    projected["checks"] = base.task_checks(projected)
    projected["passed"] = all(projected["checks"].values())
    return projected


def _base_aggregate_view(
    value: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, Any]:
    """Rebuild the V2.44.11 aggregate before its derived fields exist."""
    required = base.AGGREGATE_KEYS - _BASE_AGGREGATE_DERIVED_KEYS
    if not required <= set(value):
        raise RuntimeError("V2.44.17 base aggregate fields are incomplete")
    projected = {key: copy.deepcopy(value[key]) for key in required}
    projected["checks"] = base.aggregate_checks(projected, gates)
    projected["passed"] = all(projected["checks"].values())
    return projected


def _compat_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    validated = validate_effect_equivalent_envelope(value)
    compat = {
        "artifact_version": 1,
        "role": COMPAT_ROLE,
        "policy_id": COMPAT_POLICY,
        "recovery_policy_id": RECOVERY_POLICY_ID,
        "result": copy.deepcopy(validated["result"]),
        "model_slot_receipt": copy.deepcopy(validated["model_slot_receipt"]),
        "transport_health": copy.deepcopy(validated["transport_health"]),
        "search_single_shot_receipt": copy.deepcopy(
            validated["search_single_shot_receipt"]
        ),
        "private_task_content_present": True,
        "private_task_content_scope": list(PRIVATE_SCOPE),
        "private_task_content_emitted_to_public_aggregate": False,
        "credential_or_privileged_evaluator_content_present": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    compat["envelope_payload_sha256"] = payload_sha256(compat)
    return compat


def task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    base_value = _base_task_view(value)
    checks = {
        **base.task_checks(base_value),
        "effect_equivalence_attested": all(
            value.get(name) is True for name in EQUIVALENCE_FIELDS
        ),
    }
    if tuple(checks) != TASK_CHECK_NAMES:
        raise RuntimeError("V2.44.17 task check order drifted")
    return checks


def task_projection(
    ordinal: int,
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        raise ValueError("V2.44.17 successful parent is missing its envelope")
    validated = validate_effect_equivalent_envelope(envelope)
    equivalence = validate_effect_equivalence_receipt(
        validated["effect_equivalence_receipt"]
    )
    legacy = base.task_projection(ordinal, parent, _compat_envelope(validated))
    legacy.pop("checks")
    legacy.pop("passed")
    value = {
        **legacy,
        "effect_equivalence_valid": True,
        "model_remaining_seconds_nonincreasing": equivalence[
            "model_remaining_seconds_nonincreasing"
        ],
        "model_deadline_state_monotonic": equivalence[
            "model_deadline_state_monotonic"
        ],
        "transport_deadline_state_monotonic": equivalence[
            "transport_deadline_state_monotonic"
        ],
    }
    value["checks"] = task_checks(value)
    value["passed"] = all(value["checks"].values())
    validate_task_projection(value)
    return value


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    checks = value.get("checks")
    base_value = _base_task_view(value)
    base.validate_task_projection(base_value)
    if (
        set(value) != TASK_KEYS
        or any(not isinstance(value.get(name), bool) for name in EQUIVALENCE_FIELDS)
        or not isinstance(checks, Mapping)
        or tuple(checks) != TASK_CHECK_NAMES
        or dict(checks) != task_checks(value)
        or value.get("passed") is not all(checks.values())
    ):
        raise RuntimeError("V2.44.17 task projection drifted")
    return copy.deepcopy(dict(value))


def local_failure(ordinal: int) -> dict[str, Any]:
    legacy = base.local_failure(ordinal)
    legacy.pop("checks")
    legacy.pop("passed")
    value = {**legacy, **{name: False for name in EQUIVALENCE_FIELDS}}
    value["checks"] = task_checks(value)
    value["passed"] = False
    validate_task_projection(value)
    return value


def aggregate_checks(
    summary: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, bool]:
    base_value = _base_aggregate_view(summary, gates)
    checks = {
        **base.aggregate_checks(base_value, gates),
        "all_effect_equivalence_attested": (
            summary.get("effect_equivalent_tasks") == summary.get("selected")
            and summary.get("all_model_remaining_seconds_nonincreasing") is True
            and summary.get("all_model_deadline_states_monotonic") is True
            and summary.get("all_transport_deadline_states_monotonic") is True
            and summary.get("all_effect_equivalence_attested") is True
        ),
    }
    if tuple(checks) != AGGREGATE_CHECK_NAMES:
        raise RuntimeError("V2.44.17 aggregate check order drifted")
    return checks


def aggregate_tasks(
    tasks: Sequence[Mapping[str, Any]],
    batch_wall_seconds: float,
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    values = sorted(
        (validate_task_projection(item) for item in tasks),
        key=lambda item: item["ordinal"],
    )
    base_values = []
    for item in values:
        base_values.append(_base_task_view(item))
    legacy = base.aggregate_tasks(base_values, batch_wall_seconds, gates)
    legacy.pop("checks")
    legacy.pop("passed")
    summary = {
        **legacy,
        "effect_equivalent_tasks": sum(
            item["effect_equivalence_valid"] for item in values
        ),
        "all_model_remaining_seconds_nonincreasing": all(
            item["model_remaining_seconds_nonincreasing"] for item in values
        ),
        "all_model_deadline_states_monotonic": all(
            item["model_deadline_state_monotonic"] for item in values
        ),
        "all_transport_deadline_states_monotonic": all(
            item["transport_deadline_state_monotonic"] for item in values
        ),
        "all_effect_equivalence_attested": all(
            item["checks"]["effect_equivalence_attested"] for item in values
        ),
    }
    summary["checks"] = aggregate_checks(summary, gates)
    summary["passed"] = all(summary["checks"].values())
    validate_aggregate(summary, gates)
    return summary


def validate_aggregate(
    value: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, Any]:
    checks = value.get("checks")
    base_value = _base_aggregate_view(value, gates)
    base.validate_aggregate(base_value, gates)
    if (
        set(value) != AGGREGATE_KEYS
        or isinstance(value.get("effect_equivalent_tasks"), bool)
        or not isinstance(value.get("effect_equivalent_tasks"), int)
        or not 0 <= value["effect_equivalent_tasks"] <= value["selected"]
        or any(
            not isinstance(value.get(name), bool)
            for name in (
                "all_model_remaining_seconds_nonincreasing",
                "all_model_deadline_states_monotonic",
                "all_transport_deadline_states_monotonic",
                "all_effect_equivalence_attested",
            )
        )
        or not isinstance(checks, Mapping)
        or tuple(checks) != AGGREGATE_CHECK_NAMES
        or dict(checks) != aggregate_checks(value, gates)
        or value.get("passed") is not all(checks.values())
    ):
        raise RuntimeError("V2.44.17 aggregate drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "AGGREGATE_KEYS",
    "TASK_KEYS",
    "aggregate_checks",
    "aggregate_tasks",
    "local_failure",
    "task_checks",
    "task_projection",
    "validate_aggregate",
    "validate_task_projection",
]
