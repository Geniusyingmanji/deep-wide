"""Checkpoint deadline and deterministic retry backoff for V2.42.42.

This candidate wraps, but does not modify, the frozen V2.42.42 durable effect
coordinator.  A monotonic deadline starts before durable admission.  Before
every caller-supplied provider callback, the wrapper checks that a declared
minimum attempt window remains.  Retry attempts additionally wait for a
deterministic capped exponential backoff inside the parent callback interval,
so a real sleeper is measured by V2.42.42/V2.42.34 and the entire deadline is
conservatively precovered by the V2.42.34 wall reservation.

The deadline is checkpoint enforcement, not asynchronous cancellation.  An
already-running arbitrary callback can outlive the deadline; when it returns,
the wrapper detects the overrun and fails closed with the durable reservation
still charged.  Requests-style per-call timeouts are not treated as a trusted
total deadline.  This module remains absent from active clients, runtime,
runner, launcher, benchmark, and evaluator paths.
"""

from __future__ import annotations

import copy
import dataclasses
import time
from typing import Any, Callable, Mapping, Sequence

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24234_provider_cost_meter import (
    validate_provider_meter_contract,
)
from deepwide_agent.v24235_preauthorized_effect_harness import (
    RETRYABLE_OUTCOMES,
    TERMINAL_OUTCOMES,
    ProviderAttemptResult,
)
from deepwide_agent.v24242_durable_effect_coordinator import (
    DurableEffectExecutionError,
    DurablePreauthorizedEffectCoordinator,
    validate_durable_effect_execution_receipt,
    validate_durable_effect_failure_receipt,
)


POLICY_ID = "v24243_retry_deadline_scheduler_v1"
CONTRACT_ROLE = "v24243_retry_deadline_contract"
SCHEDULE_RECORD_ROLE = "v24243_retry_attempt_schedule_record"
EXECUTION_RECEIPT_ROLE = "v24243_retry_deadline_execution_receipt"
FAILURE_RECEIPT_ROLE = "v24243_retry_deadline_failure_receipt"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

STRICT_RETRY_ADMISSION_DEADLINE_IMPLEMENTED = True
DETERMINISTIC_CAPPED_BACKOFF_IMPLEMENTED = True
BACKOFF_PREAUTHORIZED_IN_WALL_RESERVATION_IMPLEMENTED = True
INJECTABLE_MONOTONIC_CLOCK_AND_SLEEPER_IMPLEMENTED = True
POST_CALLBACK_DEADLINE_CHECK_IMPLEMENTED = True
ALREADY_RUNNING_CALLBACK_FORCE_CANCELLATION_IMPLEMENTED = False
TRUSTED_HARD_TOTAL_WALL_TIMEOUT_IMPLEMENTED = False
REQUESTS_PER_CALL_TIMEOUT_TREATED_AS_TOTAL_DEADLINE = False

MAX_MILLISECONDS = 1_000_000_000_000
MAX_BACKOFF_MULTIPLIER = 64
NANOSECONDS_PER_MILLISECOND = 1_000_000
MAX_MONOTONIC_NANOSECONDS = (1 << 63) - 1

CONTRACT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_runtime",
        "meter_contract_sha256",
        "max_attempts",
        "total_deadline_milliseconds",
        "minimum_attempt_window_milliseconds",
        "initial_backoff_milliseconds",
        "backoff_multiplier",
        "maximum_backoff_milliseconds",
        "retry_backoff_schedule_milliseconds",
        "maximum_cumulative_backoff_milliseconds",
        "wall_reservation_milliseconds",
        "minimum_required_wall_reservation_milliseconds",
        "deadline_scope",
        "retry_admission_policy",
        "backoff_accounting_policy",
        "clock_source",
        "clock_and_sleeper_injectable",
        "callback_force_cancellation_implemented",
        "already_running_callback_may_outlive_deadline",
        "requests_per_call_timeout_is_total_deadline",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "contract_sha256",
    }
)
SCHEDULE_RECORD_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "attempt_index",
        "required_backoff_milliseconds",
        "callback_entry_elapsed_nanoseconds",
        "sleep_started_elapsed_nanoseconds",
        "sleep_completed_elapsed_nanoseconds",
        "observed_sleep_nanoseconds",
        "remaining_before_provider_callback_nanoseconds",
        "provider_callback_started_elapsed_nanoseconds",
        "provider_callback_returned_elapsed_nanoseconds",
        "provider_callback_started",
        "provider_callback_returned",
        "outcome",
        "status",
        "record_sha256",
    }
)
EXECUTION_RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_runtime",
        "invocation_ref_sha256",
        "scheduler_contract",
        "scheduler_contract_sha256",
        "parent_execution_receipt",
        "parent_execution_receipt_sha256",
        "schedule_records",
        "attempt_count",
        "provider_callback_started_count",
        "provider_callback_returned_count",
        "required_backoff_total_milliseconds",
        "observed_backoff_total_nanoseconds",
        "total_elapsed_nanoseconds",
        "parent_measured_wall_milliseconds",
        "parent_logical_status",
        "strict_retry_admission_deadline_enforced",
        "post_callback_deadline_checked",
        "backoff_executed_inside_parent_callback_intervals",
        "wall_reservation_precovered_total_deadline",
        "callback_force_cancellation_implemented",
        "already_running_callback_may_outlive_deadline",
        "trusted_hard_total_wall_timeout_implemented",
        "requests_per_call_timeout_is_total_deadline",
        "raw_provider_value_persisted_hashed_or_emitted",
        "raw_request_or_response_content_present",
        "credential_or_url_present",
        "benchmark_or_evaluator_metadata_present",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "execution_receipt_sha256",
    }
)
FAILURE_RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_runtime",
        "invocation_ref_sha256",
        "scheduler_contract",
        "scheduler_contract_sha256",
        "parent_execution_receipt",
        "parent_failure_receipt",
        "schedule_records",
        "failure_reason",
        "provider_callback_started_count",
        "provider_callback_returned_count",
        "last_observed_elapsed_nanoseconds",
        "permit_durably_committed",
        "settlement_durably_committed",
        "reservation_remains_charged",
        "automatic_whole_effect_replay_authorized",
        "callback_force_cancellation_implemented",
        "already_running_callback_may_outlive_deadline",
        "raw_exception_message_persisted",
        "raw_provider_value_persisted_hashed_or_emitted",
        "raw_request_or_response_content_present",
        "credential_or_url_present",
        "benchmark_or_evaluator_metadata_present",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "failure_receipt_sha256",
    }
)

RECORD_STATUSES = frozenset(
    {
        "provider_callback_returned_before_deadline",
        "deadline_rejected_before_backoff",
        "deadline_rejected_before_provider_callback",
        "sleeper_exception",
        "backoff_clock_invalid",
        "backoff_incomplete",
        "provider_callback_exception",
        "callback_return_clock_invalid",
        "provider_callback_returned_at_or_after_deadline",
    }
)
FAILURE_REASONS = frozenset(
    {
        "deadline_before_backoff",
        "deadline_before_provider_callback",
        "sleeper_exception",
        "clock_invalid_during_backoff",
        "backoff_incomplete",
        "provider_callback_exception",
        "clock_invalid_after_provider_callback",
        "provider_callback_returned_at_or_after_deadline",
        "parent_execution_failure",
        "clock_invalid_after_parent_return",
        "parent_returned_at_or_after_deadline",
    }
)


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


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
        raise ValueError(f"V2.42.43 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, key: str) -> bool:
    seal = value.get(key)
    if not _is_sha256(seal):
        return False
    unsigned = dict(value)
    unsigned.pop(key)
    return seal == object_sha256(unsigned)


def _integer(
    value: object,
    *,
    label: str,
    minimum: int = 0,
    maximum: int = MAX_MILLISECONDS,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"V2.42.43 {label} is outside the frozen range")
    return value


def _optional_nonnegative_integer(value: object, *, label: str) -> int | None:
    if value is None:
        return None
    return _integer(
        value,
        label=label,
        maximum=MAX_MONOTONIC_NANOSECONDS,
    )


def _backoff_schedule(
    *,
    max_attempts: int,
    initial_backoff_milliseconds: int,
    backoff_multiplier: int,
    maximum_backoff_milliseconds: int,
) -> list[int]:
    schedule: list[int] = []
    current = initial_backoff_milliseconds
    for _ in range(max_attempts - 1):
        bounded = min(current, maximum_backoff_milliseconds)
        schedule.append(bounded)
        if bounded >= maximum_backoff_milliseconds:
            current = maximum_backoff_milliseconds
        else:
            current = min(
                maximum_backoff_milliseconds,
                bounded * backoff_multiplier,
            )
    return schedule


def build_retry_deadline_contract(
    *,
    meter_contract: Mapping[str, Any],
    total_deadline_milliseconds: int,
    minimum_attempt_window_milliseconds: int,
    initial_backoff_milliseconds: int,
    backoff_multiplier: int,
    maximum_backoff_milliseconds: int,
) -> dict[str, Any]:
    """Freeze a deterministic schedule already covered by meter wall budget."""

    meter = _clone(dict(meter_contract))
    validate_provider_meter_contract(meter)
    attempts = _integer(
        meter["max_attempts"],
        label="maximum attempts",
        minimum=1,
        maximum=64,
    )
    total = _integer(
        total_deadline_milliseconds,
        label="total deadline",
        minimum=1,
    )
    window = _integer(
        minimum_attempt_window_milliseconds,
        label="minimum attempt window",
        minimum=1,
    )
    initial = _integer(
        initial_backoff_milliseconds,
        label="initial backoff",
        minimum=1,
    )
    multiplier = _integer(
        backoff_multiplier,
        label="backoff multiplier",
        minimum=1,
        maximum=MAX_BACKOFF_MULTIPLIER,
    )
    maximum = _integer(
        maximum_backoff_milliseconds,
        label="maximum backoff",
        minimum=1,
    )
    reservation = _integer(
        meter["reserved_cost"]["wall_milliseconds"],
        label="wall reservation",
        minimum=1,
    )
    if maximum < initial:
        raise ValueError("V2.42.43 maximum backoff is below initial backoff")
    if total > reservation:
        raise ValueError("V2.42.43 deadline exceeds wall reservation")
    schedule = _backoff_schedule(
        max_attempts=attempts,
        initial_backoff_milliseconds=initial,
        backoff_multiplier=multiplier,
        maximum_backoff_milliseconds=maximum,
    )
    cumulative = sum(schedule)
    if cumulative > MAX_MILLISECONDS:
        raise ValueError("V2.42.43 cumulative backoff overflowed")
    if window > total or cumulative + window > total:
        raise ValueError("V2.42.43 schedule cannot fit its declared deadline")
    minimum_reservation = total + attempts - 1
    if minimum_reservation > MAX_MILLISECONDS:
        raise ValueError("V2.42.43 rounded wall reservation overflowed")
    if reservation < minimum_reservation:
        raise ValueError(
            "V2.42.43 wall reservation cannot cover per-attempt rounding"
        )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CONTRACT_ROLE,
        "policy_id": POLICY_ID,
        "candidate_runtime": True,
        "meter_contract_sha256": meter["contract_sha256"],
        "max_attempts": attempts,
        "total_deadline_milliseconds": total,
        "minimum_attempt_window_milliseconds": window,
        "initial_backoff_milliseconds": initial,
        "backoff_multiplier": multiplier,
        "maximum_backoff_milliseconds": maximum,
        "retry_backoff_schedule_milliseconds": schedule,
        "maximum_cumulative_backoff_milliseconds": cumulative,
        "wall_reservation_milliseconds": reservation,
        "minimum_required_wall_reservation_milliseconds": minimum_reservation,
        "deadline_scope": "before_parent_admission_through_parent_return_checkpoints",
        "retry_admission_policy": "minimum_window_before_every_provider_callback",
        "backoff_accounting_policy": "inside_parent_callback_interval_and_precovered_by_wall_reservation",
        "clock_source": "monotonic_nanoseconds",
        "clock_and_sleeper_injectable": True,
        "callback_force_cancellation_implemented": False,
        "already_running_callback_may_outlive_deadline": True,
        "requests_per_call_timeout_is_total_deadline": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["contract_sha256"] = object_sha256(value)
    return value


def validate_retry_deadline_contract(
    value: Mapping[str, Any], *, meter_contract: Mapping[str, Any]
) -> None:
    contract = _exact(value, keys=CONTRACT_KEYS, label="scheduler contract")
    meter = _clone(dict(meter_contract))
    validate_provider_meter_contract(meter)
    expected = build_retry_deadline_contract(
        meter_contract=meter,
        total_deadline_milliseconds=contract.get("total_deadline_milliseconds"),
        minimum_attempt_window_milliseconds=contract.get(
            "minimum_attempt_window_milliseconds"
        ),
        initial_backoff_milliseconds=contract.get(
            "initial_backoff_milliseconds"
        ),
        backoff_multiplier=contract.get("backoff_multiplier"),
        maximum_backoff_milliseconds=contract.get(
            "maximum_backoff_milliseconds"
        ),
    )
    if (
        dict(contract) != expected
        or contract.get("meter_contract_sha256") != meter["contract_sha256"]
        or not _sealed(contract, key="contract_sha256")
    ):
        raise ValueError("V2.42.43 scheduler contract drifted")


def _validate_schedule_record(
    value: Mapping[str, Any], *, contract: Mapping[str, Any]
) -> None:
    record = _exact(value, keys=SCHEDULE_RECORD_KEYS, label="schedule record")
    index = _integer(
        record.get("attempt_index"),
        label="record attempt index",
        minimum=1,
        maximum=int(contract["max_attempts"]),
    )
    expected_backoff = (
        0
        if index == 1
        else int(contract["retry_backoff_schedule_milliseconds"][index - 2])
    )
    optional_fields = (
        "callback_entry_elapsed_nanoseconds",
        "sleep_started_elapsed_nanoseconds",
        "sleep_completed_elapsed_nanoseconds",
        "observed_sleep_nanoseconds",
        "remaining_before_provider_callback_nanoseconds",
        "provider_callback_started_elapsed_nanoseconds",
        "provider_callback_returned_elapsed_nanoseconds",
    )
    normalized = {
        field: _optional_nonnegative_integer(record.get(field), label=field)
        for field in optional_fields
    }
    outcome = record.get("outcome")
    if outcome is not None and outcome not in RETRYABLE_OUTCOMES | TERMINAL_OUTCOMES:
        raise ValueError("V2.42.43 schedule record outcome is invalid")
    ordered_fields = (
        "callback_entry_elapsed_nanoseconds",
        "sleep_started_elapsed_nanoseconds",
        "sleep_completed_elapsed_nanoseconds",
        "provider_callback_started_elapsed_nanoseconds",
        "provider_callback_returned_elapsed_nanoseconds",
    )
    timeline = [
        normalized[field]
        for field in ordered_fields
        if normalized[field] is not None
    ]
    sleep_started = normalized["sleep_started_elapsed_nanoseconds"]
    sleep_completed = normalized["sleep_completed_elapsed_nanoseconds"]
    observed_sleep = normalized["observed_sleep_nanoseconds"]
    provider_started_at = normalized[
        "provider_callback_started_elapsed_nanoseconds"
    ]
    provider_returned_at = normalized[
        "provider_callback_returned_elapsed_nanoseconds"
    ]
    remaining = normalized["remaining_before_provider_callback_nanoseconds"]
    deadline_ns = (
        int(contract["total_deadline_milliseconds"])
        * NANOSECONDS_PER_MILLISECOND
    )
    minimum_window_ns = (
        int(contract["minimum_attempt_window_milliseconds"])
        * NANOSECONDS_PER_MILLISECOND
    )
    status = record.get("status")
    if (
        record.get("artifact_version") != 1
        or record.get("role") != SCHEDULE_RECORD_ROLE
        or record.get("policy_id") != POLICY_ID
        or record.get("required_backoff_milliseconds") != expected_backoff
        or status not in RECORD_STATUSES
        or normalized["callback_entry_elapsed_nanoseconds"] is None
        and status != "backoff_clock_invalid"
        or normalized["callback_entry_elapsed_nanoseconds"] is None
        and any(
            normalized[field] is not None
            for field in optional_fields
            if field != "callback_entry_elapsed_nanoseconds"
        )
        or timeline != sorted(timeline)
        or (sleep_started is None) != (observed_sleep is None)
        or sleep_completed is not None
        and sleep_started is None
        or sleep_started is not None
        and observed_sleep is not None
        and sleep_completed is not None
        and observed_sleep != sleep_completed - sleep_started
        or not isinstance(record.get("provider_callback_started"), bool)
        or not isinstance(record.get("provider_callback_returned"), bool)
        or record["provider_callback_returned"]
        and not record["provider_callback_started"]
        or record["provider_callback_started"]
        != (normalized["provider_callback_started_elapsed_nanoseconds"] is not None)
        or (
            record["provider_callback_returned"]
            != (
                normalized["provider_callback_returned_elapsed_nanoseconds"]
                is not None
            )
            and status != "callback_return_clock_invalid"
        )
        or status == "callback_return_clock_invalid"
        and (
            record.get("provider_callback_returned") is not True
            or normalized["provider_callback_returned_elapsed_nanoseconds"]
            is not None
        )
        or index == 1
        and any(
            normalized[field] is not None
            for field in (
                "sleep_started_elapsed_nanoseconds",
                "sleep_completed_elapsed_nanoseconds",
                "observed_sleep_nanoseconds",
            )
        )
        or index > 1
        and status
        not in {
            "deadline_rejected_before_backoff",
            "sleeper_exception",
            "backoff_clock_invalid",
        }
        and sleep_completed is None
        or record["provider_callback_started"]
        and (
            remaining is None
            or provider_started_at is None
            or remaining != max(0, deadline_ns - provider_started_at)
            or remaining < minimum_window_ns
        )
        or record["provider_callback_returned"]
        and provider_returned_at is not None
        and provider_started_at is not None
        and provider_returned_at < provider_started_at
        or status == "provider_callback_returned_before_deadline"
        and (
            record["provider_callback_returned"] is not True
            or provider_returned_at is None
            or provider_returned_at >= deadline_ns
        )
        or status == "provider_callback_returned_at_or_after_deadline"
        and (
            record["provider_callback_returned"] is not True
            or provider_returned_at is None
            or provider_returned_at < deadline_ns
        )
        or not _sealed(record, key="record_sha256")
    ):
        raise ValueError("V2.42.43 schedule record drifted")


def _record_totals(
    records: Sequence[Mapping[str, Any]], *, contract: Mapping[str, Any]
) -> dict[str, int]:
    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
        raise ValueError("V2.42.43 schedule records must be a sequence")
    normalized = [dict(item) for item in records]
    for expected_index, record in enumerate(normalized, start=1):
        _validate_schedule_record(record, contract=contract)
        if record["attempt_index"] != expected_index:
            raise ValueError("V2.42.43 attempt schedule is not contiguous")
        if expected_index > 1:
            previous_return = normalized[expected_index - 2][
                "provider_callback_returned_elapsed_nanoseconds"
            ]
            current_entry = record["callback_entry_elapsed_nanoseconds"]
            if previous_return is None or current_entry < previous_return:
                raise ValueError("V2.42.43 cross-attempt timeline drifted")
    return {
        "attempt_count": len(normalized),
        "started_count": sum(
            bool(record["provider_callback_started"]) for record in normalized
        ),
        "returned_count": sum(
            bool(record["provider_callback_returned"]) for record in normalized
        ),
        "required_backoff_milliseconds": sum(
            int(record["required_backoff_milliseconds"])
            for record in normalized
        ),
        "observed_backoff_nanoseconds": sum(
            int(record["observed_sleep_nanoseconds"] or 0)
            for record in normalized
        ),
    }


@dataclasses.dataclass(frozen=True)
class RetryDeadlineExecutionResult:
    """A content-free scheduler receipt and the parent's ephemeral value."""

    receipt: Mapping[str, Any]
    value: Any = None


class RetryDeadlineExecutionError(RuntimeError):
    """Fail-closed scheduler or parent failure after durable admission."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        super().__init__("retry deadline execution did not complete safely")
        self.receipt = _clone(dict(receipt))


class _SchedulerAbort(RuntimeError):
    pass


class _ClockInvalid(RuntimeError):
    pass


def validate_retry_deadline_execution_receipt(value: Mapping[str, Any]) -> None:
    receipt = _exact(
        value,
        keys=EXECUTION_RECEIPT_KEYS,
        label="execution receipt",
    )
    contract = dict(receipt["scheduler_contract"])
    parent = dict(receipt["parent_execution_receipt"])
    meter = dict(parent["meter_contract"])
    validate_retry_deadline_contract(contract, meter_contract=meter)
    validate_durable_effect_execution_receipt(parent)
    totals = _record_totals(receipt["schedule_records"], contract=contract)
    total_elapsed = _integer(
        receipt.get("total_elapsed_nanoseconds"),
        label="total elapsed nanoseconds",
        maximum=MAX_MONOTONIC_NANOSECONDS,
    )
    parent_wall = _integer(
        receipt.get("parent_measured_wall_milliseconds"),
        label="parent measured wall",
        minimum=1,
    )
    if (
        receipt.get("artifact_version") != 1
        or receipt.get("role") != EXECUTION_RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("candidate_runtime") is not True
        or receipt.get("invocation_ref_sha256")
        != parent.get("invocation_ref_sha256")
        or receipt.get("scheduler_contract_sha256")
        != contract.get("contract_sha256")
        or receipt.get("parent_execution_receipt_sha256")
        != parent.get("execution_receipt_sha256")
        or receipt.get("attempt_count") != totals["attempt_count"]
        or receipt.get("attempt_count") != parent.get("attempt_count")
        or [record["outcome"] for record in receipt["schedule_records"]]
        != [attempt["outcome"] for attempt in parent["measurement"]["attempts"]]
        or receipt.get("provider_callback_started_count")
        != totals["started_count"]
        or receipt.get("provider_callback_returned_count")
        != totals["returned_count"]
        or totals["started_count"] != totals["attempt_count"]
        or totals["returned_count"] != totals["attempt_count"]
        or receipt.get("required_backoff_total_milliseconds")
        != totals["required_backoff_milliseconds"]
        or receipt.get("observed_backoff_total_nanoseconds")
        != totals["observed_backoff_nanoseconds"]
        or total_elapsed
        >= int(contract["total_deadline_milliseconds"])
        * NANOSECONDS_PER_MILLISECOND
        or total_elapsed
        < int(
            receipt["schedule_records"][-1][
                "provider_callback_returned_elapsed_nanoseconds"
            ]
        )
        or parent_wall
        != parent["measurement"]["settlement_cost"]["wall_milliseconds"]
        or parent_wall > int(contract["wall_reservation_milliseconds"])
        or receipt.get("parent_logical_status") != parent.get("logical_status")
        or any(
            record["status"] != "provider_callback_returned_before_deadline"
            for record in receipt["schedule_records"]
        )
        or receipt.get("strict_retry_admission_deadline_enforced") is not True
        or receipt.get("post_callback_deadline_checked") is not True
        or receipt.get("backoff_executed_inside_parent_callback_intervals")
        is not True
        or receipt.get("wall_reservation_precovered_total_deadline") is not True
        or receipt.get("callback_force_cancellation_implemented") is not False
        or receipt.get("already_running_callback_may_outlive_deadline") is not True
        or receipt.get("trusted_hard_total_wall_timeout_implemented") is not False
        or receipt.get("requests_per_call_timeout_is_total_deadline") is not False
        or receipt.get("raw_provider_value_persisted_hashed_or_emitted") is not False
        or receipt.get("raw_request_or_response_content_present") is not False
        or receipt.get("credential_or_url_present") is not False
        or receipt.get("benchmark_or_evaluator_metadata_present") is not False
        or receipt.get("active_forward_integration_authorized") is not False
        or receipt.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(receipt, key="execution_receipt_sha256")
    ):
        raise ValueError("V2.42.43 execution receipt drifted")


def validate_retry_deadline_failure_receipt(value: Mapping[str, Any]) -> None:
    receipt = _exact(
        value,
        keys=FAILURE_RECEIPT_KEYS,
        label="failure receipt",
    )
    contract = dict(receipt["scheduler_contract"])
    parent_execution = receipt["parent_execution_receipt"]
    parent_failure = receipt["parent_failure_receipt"]
    if (parent_execution is None) == (parent_failure is None):
        raise ValueError("V2.42.43 failure needs exactly one parent receipt")
    if parent_execution is not None:
        parent = dict(parent_execution)
        validate_durable_effect_execution_receipt(parent)
        meter = dict(parent["meter_contract"])
        parent_count = int(parent["attempt_count"])
        settlement_committed = True
    else:
        parent = dict(parent_failure)
        validate_durable_effect_failure_receipt(parent)
        meter = dict(parent["meter_contract"])
        parent_count = len(parent["attempt_invocation_sha256s"])
        settlement_committed = bool(parent["settlement_durably_committed"])
    validate_retry_deadline_contract(contract, meter_contract=meter)
    totals = _record_totals(receipt["schedule_records"], contract=contract)
    _integer(
        receipt.get("last_observed_elapsed_nanoseconds"),
        label="last observed elapsed nanoseconds",
        maximum=MAX_MONOTONIC_NANOSECONDS,
    )
    last_status = receipt["schedule_records"][-1]["status"]
    compatible_failure_reasons = {
        "deadline_rejected_before_backoff": {
            "deadline_before_backoff",
            "parent_execution_failure",
        },
        "deadline_rejected_before_provider_callback": {
            "deadline_before_provider_callback"
        },
        "sleeper_exception": {"sleeper_exception"},
        "backoff_clock_invalid": {"clock_invalid_during_backoff"},
        "backoff_incomplete": {"backoff_incomplete"},
        "provider_callback_exception": {"provider_callback_exception"},
        "callback_return_clock_invalid": {
            "clock_invalid_after_provider_callback"
        },
        "provider_callback_returned_at_or_after_deadline": {
            "provider_callback_returned_at_or_after_deadline"
        },
        "provider_callback_returned_before_deadline": {
            "parent_execution_failure",
            "clock_invalid_after_parent_return",
            "parent_returned_at_or_after_deadline",
        },
    }
    if (
        receipt.get("artifact_version") != 1
        or receipt.get("role") != FAILURE_RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("candidate_runtime") is not True
        or receipt.get("invocation_ref_sha256")
        != parent.get("invocation_ref_sha256")
        or receipt.get("scheduler_contract_sha256")
        != contract.get("contract_sha256")
        or totals["attempt_count"] != parent_count
        or receipt.get("provider_callback_started_count")
        != totals["started_count"]
        or receipt.get("provider_callback_returned_count")
        != totals["returned_count"]
        or receipt.get("failure_reason") not in FAILURE_REASONS
        or receipt.get("failure_reason")
        not in compatible_failure_reasons[last_status]
        or receipt.get("permit_durably_committed") is not True
        or receipt.get("settlement_durably_committed") is not settlement_committed
        or receipt.get("reservation_remains_charged") is not True
        or receipt.get("automatic_whole_effect_replay_authorized") is not False
        or receipt.get("callback_force_cancellation_implemented") is not False
        or receipt.get("already_running_callback_may_outlive_deadline") is not True
        or receipt.get("raw_exception_message_persisted") is not False
        or receipt.get("raw_provider_value_persisted_hashed_or_emitted") is not False
        or receipt.get("raw_request_or_response_content_present") is not False
        or receipt.get("credential_or_url_present") is not False
        or receipt.get("benchmark_or_evaluator_metadata_present") is not False
        or receipt.get("active_forward_integration_authorized") is not False
        or receipt.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(receipt, key="failure_receipt_sha256")
    ):
        raise ValueError("V2.42.43 failure receipt drifted")


class RetryDeadlineEffectScheduler:
    """Apply checkpoint deadline admission to one durable coordinator."""

    def __init__(
        self,
        *,
        coordinator: DurablePreauthorizedEffectCoordinator,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not isinstance(coordinator, DurablePreauthorizedEffectCoordinator):
            raise ValueError("V2.42.43 parent coordinator type is invalid")
        if not callable(monotonic_ns) or not callable(sleeper):
            raise ValueError("V2.42.43 clock and sleeper must be callable")
        self._coordinator = coordinator
        self._monotonic_ns = monotonic_ns
        self._sleeper = sleeper

    def _read_clock(self, state: dict[str, Any]) -> int:
        try:
            value = self._monotonic_ns()
        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            raise
        except Exception:
            raise _ClockInvalid("clock callable failed") from None
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value > MAX_MONOTONIC_NANOSECONDS
            or state.get("last_ns") is not None
            and value < state["last_ns"]
        ):
            raise _ClockInvalid("monotonic clock is invalid")
        state["last_ns"] = value
        return value

    @staticmethod
    def _elapsed(state: Mapping[str, Any], now: int | None = None) -> int:
        current = int(state["last_ns"] if now is None else now)
        return max(0, current - int(state["started_ns"]))

    @staticmethod
    def _seal_record(record: dict[str, Any]) -> None:
        record.pop("record_sha256", None)
        record["record_sha256"] = object_sha256(record)

    def _failure_receipt(
        self,
        *,
        contract: Mapping[str, Any],
        invocation_ref_sha256: str,
        state: Mapping[str, Any],
        parent_execution_receipt: Mapping[str, Any] | None,
        parent_failure_receipt: Mapping[str, Any] | None,
        failure_reason: str,
    ) -> dict[str, Any]:
        parent_execution = (
            None
            if parent_execution_receipt is None
            else _clone(dict(parent_execution_receipt))
        )
        parent_failure = (
            None
            if parent_failure_receipt is None
            else _clone(dict(parent_failure_receipt))
        )
        settlement_committed = (
            True
            if parent_execution is not None
            else bool(parent_failure["settlement_durably_committed"])
        )
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": FAILURE_RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            "candidate_runtime": True,
            "invocation_ref_sha256": invocation_ref_sha256,
            "scheduler_contract": _clone(dict(contract)),
            "scheduler_contract_sha256": contract["contract_sha256"],
            "parent_execution_receipt": parent_execution,
            "parent_failure_receipt": parent_failure,
            "schedule_records": _clone(list(state["records"])),
            "failure_reason": failure_reason,
            "provider_callback_started_count": int(state["provider_started"]),
            "provider_callback_returned_count": int(state["provider_returned"]),
            "last_observed_elapsed_nanoseconds": self._elapsed(state),
            "permit_durably_committed": True,
            "settlement_durably_committed": settlement_committed,
            "reservation_remains_charged": True,
            "automatic_whole_effect_replay_authorized": False,
            "callback_force_cancellation_implemented": False,
            "already_running_callback_may_outlive_deadline": True,
            "raw_exception_message_persisted": False,
            "raw_provider_value_persisted_hashed_or_emitted": False,
            "raw_request_or_response_content_present": False,
            "credential_or_url_present": False,
            "benchmark_or_evaluator_metadata_present": False,
            "active_forward_integration_authorized": False,
            "benchmark_forward_or_evaluator_authorized": False,
        }
        value["failure_receipt_sha256"] = object_sha256(value)
        validate_retry_deadline_failure_receipt(value)
        return value

    def run_effect(
        self,
        *,
        meter_contract: Mapping[str, Any],
        scheduler_contract: Mapping[str, Any],
        invocation_ref_sha256: str,
        callback: Callable[[Mapping[str, Any]], ProviderAttemptResult],
        fault_hook: Callable[[str], None] | None = None,
    ) -> RetryDeadlineExecutionResult:
        """Run one parent effect with strict pre-callback deadline checks."""

        meter = _clone(dict(meter_contract))
        contract = _clone(dict(scheduler_contract))
        validate_retry_deadline_contract(contract, meter_contract=meter)
        if not _is_sha256(invocation_ref_sha256):
            raise ValueError("V2.42.43 invocation reference is not SHA-256 bound")
        if not callable(callback):
            raise ValueError("V2.42.43 provider callback is not callable")
        state: dict[str, Any] = {
            "started_ns": None,
            "last_ns": None,
            "records": [],
            "provider_started": 0,
            "provider_returned": 0,
            "previous_outcome": None,
            "failure_reason": None,
        }
        try:
            started = self._read_clock(state)
        except _ClockInvalid:
            raise ValueError("V2.42.43 initial monotonic clock is invalid") from None
        state["started_ns"] = started
        deadline_ns = started + (
            int(contract["total_deadline_milliseconds"])
            * NANOSECONDS_PER_MILLISECOND
        )
        if deadline_ns > MAX_MONOTONIC_NANOSECONDS:
            raise ValueError("V2.42.43 absolute monotonic deadline overflowed")
        minimum_window_ns = (
            int(contract["minimum_attempt_window_milliseconds"])
            * NANOSECONDS_PER_MILLISECOND
        )

        def abort(record: dict[str, Any], *, status: str, reason: str) -> None:
            record["status"] = status
            self._seal_record(record)
            state["failure_reason"] = reason
            raise _SchedulerAbort(reason)

        def scheduled_callback(
            invocation: Mapping[str, Any],
        ) -> ProviderAttemptResult:
            attempt_index = invocation.get("attempt_index")
            if (
                isinstance(attempt_index, bool)
                or not isinstance(attempt_index, int)
                or attempt_index != len(state["records"]) + 1
                or attempt_index < 1
                or attempt_index > int(contract["max_attempts"])
            ):
                state["failure_reason"] = "parent_execution_failure"
                raise _SchedulerAbort("unexpected parent attempt sequence")
            required_backoff = (
                0
                if attempt_index == 1
                else int(
                    contract["retry_backoff_schedule_milliseconds"][
                        attempt_index - 2
                    ]
                )
            )
            record: dict[str, Any] = {
                "artifact_version": 1,
                "role": SCHEDULE_RECORD_ROLE,
                "policy_id": POLICY_ID,
                "attempt_index": attempt_index,
                "required_backoff_milliseconds": required_backoff,
                "callback_entry_elapsed_nanoseconds": None,
                "sleep_started_elapsed_nanoseconds": None,
                "sleep_completed_elapsed_nanoseconds": None,
                "observed_sleep_nanoseconds": None,
                "remaining_before_provider_callback_nanoseconds": None,
                "provider_callback_started_elapsed_nanoseconds": None,
                "provider_callback_returned_elapsed_nanoseconds": None,
                "provider_callback_started": False,
                "provider_callback_returned": False,
                "outcome": None,
                "status": "deadline_rejected_before_provider_callback",
            }
            state["records"].append(record)
            try:
                now = self._read_clock(state)
            except _ClockInvalid:
                abort(
                    record,
                    status="backoff_clock_invalid",
                    reason="clock_invalid_during_backoff",
                )
            record["callback_entry_elapsed_nanoseconds"] = self._elapsed(state, now)
            if attempt_index > 1:
                if state["previous_outcome"] not in RETRYABLE_OUTCOMES:
                    state["failure_reason"] = "parent_execution_failure"
                    abort(
                        record,
                        status="deadline_rejected_before_backoff",
                        reason="parent_execution_failure",
                    )
                required_ns = required_backoff * NANOSECONDS_PER_MILLISECOND
                if now + required_ns + minimum_window_ns > deadline_ns:
                    abort(
                        record,
                        status="deadline_rejected_before_backoff",
                        reason="deadline_before_backoff",
                    )
                record["sleep_started_elapsed_nanoseconds"] = self._elapsed(
                    state, now
                )
                try:
                    self._sleeper(required_backoff / 1000.0)
                except (KeyboardInterrupt, SystemExit, GeneratorExit):
                    raise
                except Exception:
                    abort(
                        record,
                        status="sleeper_exception",
                        reason="sleeper_exception",
                    )
                try:
                    after_sleep = self._read_clock(state)
                except _ClockInvalid:
                    abort(
                        record,
                        status="backoff_clock_invalid",
                        reason="clock_invalid_during_backoff",
                    )
                observed_sleep = after_sleep - now
                record["sleep_completed_elapsed_nanoseconds"] = self._elapsed(
                    state, after_sleep
                )
                record["observed_sleep_nanoseconds"] = observed_sleep
                if observed_sleep < required_ns:
                    abort(
                        record,
                        status="backoff_incomplete",
                        reason="backoff_incomplete",
                    )
                now = after_sleep
            remaining = deadline_ns - now
            record["remaining_before_provider_callback_nanoseconds"] = max(
                0, remaining
            )
            if remaining < minimum_window_ns:
                abort(
                    record,
                    status="deadline_rejected_before_provider_callback",
                    reason="deadline_before_provider_callback",
                )
            record["provider_callback_started"] = True
            record["provider_callback_started_elapsed_nanoseconds"] = self._elapsed(
                state, now
            )
            state["provider_started"] += 1
            try:
                result = callback(_clone(dict(invocation)))
            except (KeyboardInterrupt, SystemExit, GeneratorExit):
                raise
            except Exception:
                abort(
                    record,
                    status="provider_callback_exception",
                    reason="provider_callback_exception",
                )
            record["provider_callback_returned"] = True
            state["provider_returned"] += 1
            try:
                returned = self._read_clock(state)
            except _ClockInvalid:
                abort(
                    record,
                    status="callback_return_clock_invalid",
                    reason="clock_invalid_after_provider_callback",
                )
            record["provider_callback_returned_elapsed_nanoseconds"] = self._elapsed(
                state, returned
            )
            if returned >= deadline_ns:
                abort(
                    record,
                    status="provider_callback_returned_at_or_after_deadline",
                    reason="provider_callback_returned_at_or_after_deadline",
                )
            if isinstance(result, ProviderAttemptResult) and isinstance(
                result.observation, Mapping
            ):
                outcome = result.observation.get("outcome")
                if outcome in RETRYABLE_OUTCOMES | TERMINAL_OUTCOMES:
                    record["outcome"] = outcome
                    state["previous_outcome"] = outcome
            record["status"] = "provider_callback_returned_before_deadline"
            self._seal_record(record)
            return result

        try:
            parent_result = self._coordinator.run_effect(
                meter_contract=meter,
                invocation_ref_sha256=invocation_ref_sha256,
                callback=scheduled_callback,
                fault_hook=fault_hook,
            )
        except DurableEffectExecutionError as error:
            reason = str(state["failure_reason"] or "parent_execution_failure")
            failure = self._failure_receipt(
                contract=contract,
                invocation_ref_sha256=invocation_ref_sha256,
                state=state,
                parent_execution_receipt=None,
                parent_failure_receipt=error.receipt,
                failure_reason=reason,
            )
            raise RetryDeadlineExecutionError(failure) from None

        try:
            returned_from_parent = self._read_clock(state)
        except _ClockInvalid:
            failure = self._failure_receipt(
                contract=contract,
                invocation_ref_sha256=invocation_ref_sha256,
                state=state,
                parent_execution_receipt=parent_result.receipt,
                parent_failure_receipt=None,
                failure_reason="clock_invalid_after_parent_return",
            )
            raise RetryDeadlineExecutionError(failure) from None
        if returned_from_parent >= deadline_ns:
            failure = self._failure_receipt(
                contract=contract,
                invocation_ref_sha256=invocation_ref_sha256,
                state=state,
                parent_execution_receipt=parent_result.receipt,
                parent_failure_receipt=None,
                failure_reason="parent_returned_at_or_after_deadline",
            )
            raise RetryDeadlineExecutionError(failure)

        parent_receipt = _clone(dict(parent_result.receipt))
        parent_wall = int(
            parent_receipt["measurement"]["settlement_cost"]["wall_milliseconds"]
        )
        totals = _record_totals(state["records"], contract=contract)
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": EXECUTION_RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            "candidate_runtime": True,
            "invocation_ref_sha256": invocation_ref_sha256,
            "scheduler_contract": _clone(contract),
            "scheduler_contract_sha256": contract["contract_sha256"],
            "parent_execution_receipt": parent_receipt,
            "parent_execution_receipt_sha256": parent_receipt[
                "execution_receipt_sha256"
            ],
            "schedule_records": _clone(list(state["records"])),
            "attempt_count": totals["attempt_count"],
            "provider_callback_started_count": totals["started_count"],
            "provider_callback_returned_count": totals["returned_count"],
            "required_backoff_total_milliseconds": totals[
                "required_backoff_milliseconds"
            ],
            "observed_backoff_total_nanoseconds": totals[
                "observed_backoff_nanoseconds"
            ],
            "total_elapsed_nanoseconds": self._elapsed(
                state, returned_from_parent
            ),
            "parent_measured_wall_milliseconds": parent_wall,
            "parent_logical_status": parent_receipt["logical_status"],
            "strict_retry_admission_deadline_enforced": True,
            "post_callback_deadline_checked": True,
            "backoff_executed_inside_parent_callback_intervals": True,
            "wall_reservation_precovered_total_deadline": True,
            "callback_force_cancellation_implemented": False,
            "already_running_callback_may_outlive_deadline": True,
            "trusted_hard_total_wall_timeout_implemented": False,
            "requests_per_call_timeout_is_total_deadline": False,
            "raw_provider_value_persisted_hashed_or_emitted": False,
            "raw_request_or_response_content_present": False,
            "credential_or_url_present": False,
            "benchmark_or_evaluator_metadata_present": False,
            "active_forward_integration_authorized": False,
            "benchmark_forward_or_evaluator_authorized": False,
        }
        value["execution_receipt_sha256"] = object_sha256(value)
        validate_retry_deadline_execution_receipt(value)
        return RetryDeadlineExecutionResult(
            receipt=value,
            value=parent_result.value,
        )
