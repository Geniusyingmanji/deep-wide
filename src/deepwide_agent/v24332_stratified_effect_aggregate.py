"""Append-only stratified effect accounting for total forward results.

Complete task receipts obey exact conservation.  Incomplete total-fallback
receipts expose independently observed effect lower bounds only; they are not
summed into a false global equality and never recover a semantic last stage.
This module is pure, benchmark-external, content-free, and performs no I/O.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


ROLE = "v24332_stratified_effect_aggregate"
POLICY_ID = "v24332_complete_conservation_incomplete_independent_bounds_v1"
DEFAULT_MAXIMUM_INCOMPLETE_TASKS = 0
COMPLETE_FIELDS = (
    "logical_model_admissions",
    "provider_model_requests",
    "provider_model_attempts",
    "pre_provider_model_rejections",
    "slot_acquisitions",
    "slot_timeouts",
)
INCOMPLETE_FIELDS = (
    "slot_acquisitions",
    "slot_timeouts",
    "provider_deadline_failures",
    "hosted_search_attempts",
    "hosted_search_deadline_failures",
    "hard_fetch_helper_calls",
    "hard_fetch_deadline_failures",
    "fetch_helper_failures",
    "fetch_deadline_rejections",
    "deadline_exhausted_tasks",
    "unattributed_model_effects_lower_bound",
    "unattributed_model_attempts_lower_bound",
    "unattributed_search_effects_lower_bound",
    "unattributed_fetch_effects_lower_bound",
)
TASK_KEYS = frozenset(
    {
        "terminal_kind",
        "effect_accounting_complete",
        *COMPLETE_FIELDS,
        *INCOMPLETE_FIELDS,
    }
)
TERMINAL_KINDS = frozenset(
    {"complete_success", "complete_fallback", "incomplete_fallback"}
)
AGGREGATE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "selected_tasks",
        "terminal_kinds",
        "complete_tasks",
        "incomplete_tasks",
        "complete_task_totals",
        "incomplete_task_independent_lower_bounds",
        "complete_subset_conservation_verified",
        "incomplete_lower_bounds_verified",
        "incomplete_semantic_last_stage_available",
        "incomplete_stage_inferred_or_imputed",
        "global_equality_asserted_across_incomplete_lower_bounds",
        "maximum_incomplete_tasks",
        "promotion_checks",
        "promotion_passed",
        "aggregate_payload_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _count(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.43.32 {field} is not a nonnegative integer")
    return value


def validate_task_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    if set(value) != TASK_KEYS or value.get("terminal_kind") not in TERMINAL_KINDS:
        raise ValueError("V2.43.32 task receipt schema drifted")
    complete = value.get("effect_accounting_complete")
    if not isinstance(complete, bool):
        raise ValueError("V2.43.32 completion flag drifted")
    counts = {name: _count(value.get(name), field=name) for name in TASK_KEYS if name not in {"terminal_kind", "effect_accounting_complete"}}
    logical = counts["logical_model_admissions"]
    requests = counts["provider_model_requests"]
    attempts = counts["provider_model_attempts"]
    rejected = counts["pre_provider_model_rejections"]
    acquisitions = counts["slot_acquisitions"]
    timeouts = counts["slot_timeouts"]
    if complete:
        if value["terminal_kind"] == "incomplete_fallback":
            raise ValueError("V2.43.32 complete receipt claimed incomplete fallback")
        if (
            logical != requests + rejected
            or requests != acquisitions
            or rejected != timeouts
            or attempts < requests
            or any(counts[name] != 0 for name in INCOMPLETE_FIELDS if name.startswith("unattributed_"))
        ):
            raise ValueError("V2.43.32 complete receipt conservation drifted")
    else:
        if value["terminal_kind"] != "incomplete_fallback":
            raise ValueError("V2.43.32 incomplete receipt taxonomy drifted")
        if any(counts[name] != 0 for name in ("logical_model_admissions", "provider_model_requests", "provider_model_attempts", "pre_provider_model_rejections")):
            raise ValueError("V2.43.32 incomplete receipt claimed attributed model effects")
        if (
            counts["unattributed_model_effects_lower_bound"] < acquisitions
            or counts["unattributed_model_attempts_lower_bound"] < acquisitions
            or counts["unattributed_search_effects_lower_bound"]
            < counts["hosted_search_attempts"]
            or counts["unattributed_fetch_effects_lower_bound"]
            < counts["hard_fetch_helper_calls"]
        ):
            raise ValueError("V2.43.32 incomplete receipt lower bound drifted")
    return dict(value)


def build_task_receipt(
    *,
    terminal_kind: str,
    effect_accounting_complete: bool,
    logical_model_admissions: int = 0,
    provider_model_requests: int = 0,
    provider_model_attempts: int = 0,
    pre_provider_model_rejections: int = 0,
    slot_acquisitions: int = 0,
    slot_timeouts: int = 0,
    provider_deadline_failures: int = 0,
    hosted_search_attempts: int = 0,
    hosted_search_deadline_failures: int = 0,
    hard_fetch_helper_calls: int = 0,
    hard_fetch_deadline_failures: int = 0,
    fetch_helper_failures: int = 0,
    fetch_deadline_rejections: int = 0,
    deadline_exhausted_tasks: int = 0,
    unattributed_model_effects_lower_bound: int = 0,
    unattributed_model_attempts_lower_bound: int = 0,
    unattributed_search_effects_lower_bound: int = 0,
    unattributed_fetch_effects_lower_bound: int = 0,
) -> dict[str, Any]:
    value = {name: item for name, item in locals().items()}
    return validate_task_receipt(value)


def build_aggregate(
    receipts: Sequence[Mapping[str, Any]],
    *,
    maximum_incomplete_tasks: int = DEFAULT_MAXIMUM_INCOMPLETE_TASKS,
) -> dict[str, Any]:
    if isinstance(receipts, (str, bytes)) or not receipts:
        raise ValueError("V2.43.32 aggregate requires at least one task receipt")
    maximum = _count(maximum_incomplete_tasks, field="maximum incomplete tasks")
    validated = [validate_task_receipt(value) for value in receipts]
    complete = [value for value in validated if value["effect_accounting_complete"]]
    incomplete = [value for value in validated if not value["effect_accounting_complete"]]
    kinds = Counter(str(value["terminal_kind"]) for value in validated)
    complete_totals = {
        name: sum(int(value[name]) for value in complete) for name in COMPLETE_FIELDS
    }
    incomplete_totals = {
        name: sum(int(value[name]) for value in incomplete)
        for name in INCOMPLETE_FIELDS
    }
    complete_conservation = (
        complete_totals["logical_model_admissions"]
        == complete_totals["provider_model_requests"]
        + complete_totals["pre_provider_model_rejections"]
        and complete_totals["provider_model_requests"]
        == complete_totals["slot_acquisitions"]
        and complete_totals["pre_provider_model_rejections"]
        == complete_totals["slot_timeouts"]
        and complete_totals["provider_model_attempts"]
        >= complete_totals["provider_model_requests"]
    )
    lower_bounds = all(
        value["unattributed_model_effects_lower_bound"]
        >= value["slot_acquisitions"]
        and value["unattributed_model_attempts_lower_bound"]
        >= value["slot_acquisitions"]
        and value["unattributed_search_effects_lower_bound"]
        >= value["hosted_search_attempts"]
        and value["unattributed_fetch_effects_lower_bound"]
        >= value["hard_fetch_helper_calls"]
        for value in incomplete
    )
    checks = {
        "complete_subset_conservation": complete_conservation,
        "incomplete_lower_bounds": lower_bounds,
        "incomplete_task_count": len(incomplete) <= maximum,
    }
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "selected_tasks": len(validated),
        "terminal_kinds": dict(sorted(kinds.items())),
        "complete_tasks": len(complete),
        "incomplete_tasks": len(incomplete),
        "complete_task_totals": complete_totals,
        "incomplete_task_independent_lower_bounds": incomplete_totals,
        "complete_subset_conservation_verified": complete_conservation,
        "incomplete_lower_bounds_verified": lower_bounds,
        "incomplete_semantic_last_stage_available": False,
        "incomplete_stage_inferred_or_imputed": False,
        "global_equality_asserted_across_incomplete_lower_bounds": False,
        "maximum_incomplete_tasks": maximum,
        "promotion_checks": checks,
        "promotion_passed": all(checks.values()),
    }
    value["aggregate_payload_sha256"] = payload_sha256(value)
    validate_aggregate(value)
    return value


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("aggregate_payload_sha256", None)
    selected = _count(value.get("selected_tasks"), field="selected tasks")
    complete = _count(value.get("complete_tasks"), field="complete tasks")
    incomplete = _count(value.get("incomplete_tasks"), field="incomplete tasks")
    maximum = _count(
        value.get("maximum_incomplete_tasks"), field="maximum incomplete tasks"
    )
    kinds = value.get("terminal_kinds")
    complete_totals = value.get("complete_task_totals")
    lower_bounds = value.get("incomplete_task_independent_lower_bounds")
    checks = value.get("promotion_checks")
    if (
        set(value) != AGGREGATE_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(kinds, Mapping)
        or set(kinds).difference(TERMINAL_KINDS)
        or any(_count(item, field="terminal kind count") < 0 for item in kinds.values())
        or sum(int(item) for item in kinds.values()) != selected
        or complete + incomplete != selected
        or not isinstance(complete_totals, Mapping)
        or set(complete_totals) != set(COMPLETE_FIELDS)
        or not isinstance(lower_bounds, Mapping)
        or set(lower_bounds) != set(INCOMPLETE_FIELDS)
        or any(_count(item, field="complete total") < 0 for item in complete_totals.values())
        or any(_count(item, field="incomplete lower bound") < 0 for item in lower_bounds.values())
        or value.get("complete_subset_conservation_verified") is not True
        or value.get("incomplete_lower_bounds_verified") is not True
        or value.get("incomplete_semantic_last_stage_available") is not False
        or value.get("incomplete_stage_inferred_or_imputed") is not False
        or value.get("global_equality_asserted_across_incomplete_lower_bounds") is not False
        or checks
        != {
            "complete_subset_conservation": True,
            "incomplete_lower_bounds": True,
            "incomplete_task_count": incomplete <= maximum,
        }
        or value.get("promotion_passed") is not all(checks.values())
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.32 aggregate identity drifted")
    return dict(value)


__all__ = [
    "DEFAULT_MAXIMUM_INCOMPLETE_TASKS",
    "POLICY_ID",
    "ROLE",
    "build_aggregate",
    "build_task_receipt",
    "payload_sha256",
    "validate_aggregate",
    "validate_task_receipt",
]
