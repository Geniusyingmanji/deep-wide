"""Candidate single-process runtime boundary for V2.42.33/34 effects.

V2.42.33 charges a declared reservation before emitting a permit and V2.42.34
maps sanitized provider attempts into a typed settlement vector.  Neither
module owns the control flow around an actual provider attempt.  This module
closes that local ordering gap for a future runtime integration: it serializes
budget admission, invokes a caller-supplied *single-attempt* callback only
after the permit exists, and serializes settlement while allowing callbacks
for different permits to overlap.

The harness is deliberately not wired into the active DeepWide runner.  It is
not crash durable, has no cross-process compare-and-swap, provider timeout, or
retry backoff, and cannot prove that a callback's response hash, usage, byte
counts, or challenge echo came from the named provider.  A callback exception
or invalid/over-reservation observation leaves the already charged permit
pending and never authorizes an automatic whole-effect replay.
"""

from __future__ import annotations

import copy
import dataclasses
import math
import secrets
import threading
import time
from typing import Any, Callable, Mapping, Sequence

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24233_webswarm_effect_preauthorization import (
    PERMIT_KEYS,
    PERMIT_ROLE,
    validate_effect_preauthorization_state,
)
from deepwide_agent.v24234_provider_cost_meter import (
    build_provider_attempt,
    build_provider_cost_measurement,
    issue_metered_effect_permit,
    settle_metered_effect_permit,
    validate_provider_attempt,
    validate_provider_cost_measurement,
    validate_provider_meter_contract,
)


POLICY_ID = "v24235_preauthorized_effect_harness_v1"
ATTEMPT_INVOCATION_ROLE = "v24235_provider_attempt_invocation"
EXECUTION_RECEIPT_ROLE = "v24235_effect_execution_receipt"
FAILURE_RECEIPT_ROLE = "v24235_effect_failure_receipt"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

CALLER_SUPPLIED_SINGLE_ATTEMPT_CALLBACK_IMPLEMENTED = True
CALLER_SUPPLIED_EFFECT_CALLBACK_INVOCATION_AUTHORIZED = True
SINGLE_PROCESS_SERIAL_ADMISSION_AND_SETTLEMENT_IMPLEMENTED = True
CALLBACK_CONCURRENCY_BETWEEN_PERMITS_IMPLEMENTED = True
CROSS_PROCESS_COMPARE_AND_SWAP_IMPLEMENTED = False
CRASH_DURABLE_JOURNAL_IMPLEMENTED = False
CALLBACK_TIMEOUT_IMPLEMENTED = False
RETRY_BACKOFF_IMPLEMENTED = False
PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED = False
CALLBACK_SINGLE_PROVIDER_ATTEMPT_SEMANTICS_INDEPENDENTLY_VERIFIED = False
EXTERNAL_EFFECT_AFTER_PERMIT_INDEPENDENTLY_VERIFIED = False

RETRYABLE_OUTCOMES = frozenset(
    {
        "retryable_http",
        "key_local_http",
        "transport_error",
        "invalid_json",
        "empty_output",
    }
)
TERMINAL_OUTCOMES = frozenset(
    {"success", "terminal_http", "local_success", "local_error"}
)

OBSERVATION_KEYS = frozenset(
    {
        "execution_challenge_sha256",
        "attempt_ref_sha256",
        "local_counter_ref_sha256",
        "outcome",
        "http_status",
        "provider_response_ref_sha256",
        "token_usage_state",
        "input_tokens",
        "output_tokens",
        "provider_tool_usage_state",
        "provider_tool_calls",
        "request_body_bytes",
        "response_body_bytes",
    }
)
ATTEMPT_INVOCATION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_runtime",
        "meter_contract_sha256",
        "provider_kind",
        "effect_kind",
        "charge_kind",
        "invocation_ref_sha256",
        "permit_ref_sha256",
        "permit_sha256",
        "execution_challenge_sha256",
        "attempt_index",
        "max_attempts",
        "attempt_ref_sha256",
        "local_counter_ref_sha256",
        "callback_start_sequence",
        "raw_request_or_response_content_present",
        "credential_or_url_present",
        "benchmark_or_evaluator_metadata_present",
        "attempt_invocation_sha256",
    }
)
EXECUTION_RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_runtime",
        "meter_contract",
        "permit",
        "attempt_invocations",
        "measurement",
        "invocation_ref_sha256",
        "meter_contract_sha256",
        "provider_kind",
        "effect_kind",
        "charge_kind",
        "state_before_admission_sha256",
        "state_after_permit_sha256",
        "state_after_settlement_sha256",
        "permit_ref_sha256",
        "permit_sha256",
        "execution_challenge_sha256",
        "admission_sequence",
        "callback_start_sequences",
        "callback_complete_sequences",
        "settlement_sequence",
        "attempt_invocation_sha256s",
        "attempt_sha256s",
        "attempt_count",
        "logical_status",
        "measurement_sha256",
        "effect_receipt_sha256",
        "observed_cost_lower_bound",
        "settlement_cost",
        "reservation_fallback_dimensions",
        "reservation_fallback_applied",
        "settlement_eligible",
        "permit_committed_before_every_callback",
        "single_process_serial_admission_and_settlement",
        "callbacks_between_permits_may_overlap",
        "local_monotonic_callback_intervals_measured",
        "provider_response_authenticity_independently_verified",
        "local_counter_and_clock_independently_attested",
        "provider_challenge_consumption_independently_verified",
        "callback_single_provider_attempt_semantics_independently_verified",
        "external_effect_after_permit_independently_verified",
        "schema_resealing_without_secret_cryptographically_excluded",
        "cross_process_compare_and_swap_implemented",
        "crash_durable_journal_implemented",
        "callback_timeout_implemented",
        "retry_backoff_implemented",
        "automatic_whole_effect_replay_authorized",
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
        "meter_contract",
        "permit",
        "attempt_invocations",
        "attempts",
        "invocation_ref_sha256",
        "meter_contract_sha256",
        "provider_kind",
        "effect_kind",
        "charge_kind",
        "state_after_permit_sha256",
        "permit_ref_sha256",
        "permit_sha256",
        "execution_challenge_sha256",
        "admission_sequence",
        "callback_start_sequences",
        "callback_complete_sequences",
        "attempt_invocation_sha256s",
        "attempt_sha256s",
        "failure_phase",
        "callback_invoked",
        "completed_callback_count",
        "all_started_callbacks_completed",
        "provider_effect_may_have_occurred",
        "reservation_remains_charged",
        "permit_remains_pending",
        "automatic_whole_effect_replay_authorized",
        "raw_exception_message_persisted",
        "raw_provider_value_persisted_hashed_or_emitted",
        "raw_request_or_response_content_present",
        "credential_or_url_present",
        "benchmark_or_evaluator_metadata_present",
        "single_process_serial_admission_and_settlement",
        "cross_process_compare_and_swap_implemented",
        "crash_durable_journal_implemented",
        "callback_single_provider_attempt_semantics_independently_verified",
        "external_effect_after_permit_independently_verified",
        "schema_resealing_without_secret_cryptographically_excluded",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "failure_receipt_sha256",
    }
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
        raise ValueError(f"V2.42.35 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    if not _is_sha256(value.get(seal_key)):
        return False
    unsigned = dict(value)
    seal = unsigned.pop(seal_key)
    return seal == object_sha256(unsigned)


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


@dataclasses.dataclass(frozen=True)
class ProviderAttemptResult:
    """One provider attempt's sanitized observation plus ephemeral value."""

    observation: Mapping[str, Any]
    value: Any = None


@dataclasses.dataclass(frozen=True)
class EffectExecutionResult:
    """A settled receipt and the final callback value, never persisted here."""

    receipt: Mapping[str, Any]
    value: Any = None


class PreauthorizedEffectExecutionError(RuntimeError):
    """Safe failure carrying only a sealed content-free failure receipt."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        super().__init__("preauthorized provider effect did not reach settlement")
        self.receipt = _clone(dict(receipt))


def build_provider_attempt_observation(
    *,
    invocation: Mapping[str, Any],
    outcome: str,
    http_status: int | None,
    provider_response_ref_sha256: str | None,
    token_usage_state: str,
    input_tokens: int | None,
    output_tokens: int | None,
    provider_tool_usage_state: str,
    provider_tool_calls: int | None,
    request_body_bytes: int,
    response_body_bytes: int | None,
) -> dict[str, Any]:
    """Build the exact sanitized object a single-attempt callback returns."""

    source = _exact(
        invocation,
        keys=ATTEMPT_INVOCATION_KEYS,
        label="attempt invocation",
    )
    if not _sealed(source, seal_key="attempt_invocation_sha256"):
        raise ValueError("V2.42.35 attempt invocation seal drifted")
    return {
        "execution_challenge_sha256": source["execution_challenge_sha256"],
        "attempt_ref_sha256": source["attempt_ref_sha256"],
        "local_counter_ref_sha256": source["local_counter_ref_sha256"],
        "outcome": outcome,
        "http_status": http_status,
        "provider_response_ref_sha256": provider_response_ref_sha256,
        "token_usage_state": token_usage_state,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "provider_tool_usage_state": provider_tool_usage_state,
        "provider_tool_calls": provider_tool_calls,
        "request_body_bytes": request_body_bytes,
        "response_body_bytes": response_body_bytes,
    }


def _validate_attempt_graph_bindings(
    *,
    receipt: Mapping[str, Any],
    meter_contract: Mapping[str, Any],
    permit: Mapping[str, Any],
    invocations: Sequence[Mapping[str, Any]],
    attempts: Sequence[Mapping[str, Any]],
) -> None:
    starts = receipt.get("callback_start_sequences", [])
    completes = receipt.get("callback_complete_sequences", [])
    if (
        not isinstance(starts, list)
        or not isinstance(completes, list)
        or len(invocations) != len(starts)
        or len(attempts) > len(completes)
        or len(completes) > len(invocations)
        or len(invocations) < 1
        or len(invocations) > int(meter_contract["max_attempts"])
    ):
        raise ValueError("V2.42.35 embedded attempt graph cardinality drifted")
    for index, invocation in enumerate(invocations, start=1):
        if (
            invocation["meter_contract_sha256"]
            != meter_contract["contract_sha256"]
            or invocation["provider_kind"] != meter_contract["provider_kind"]
            or invocation["effect_kind"] != meter_contract["effect_kind"]
            or invocation["charge_kind"] != meter_contract["charge_kind"]
            or invocation["invocation_ref_sha256"]
            != receipt["invocation_ref_sha256"]
            or invocation["permit_ref_sha256"] != permit["permit_ref_sha256"]
            or invocation["permit_sha256"] != permit["permit_sha256"]
            or invocation["execution_challenge_sha256"]
            != receipt["execution_challenge_sha256"]
            or invocation["attempt_index"] != index
            or invocation["max_attempts"] != meter_contract["max_attempts"]
            or invocation["callback_start_sequence"] != starts[index - 1]
            or invocation["raw_request_or_response_content_present"] is not False
            or invocation["credential_or_url_present"] is not False
            or invocation["benchmark_or_evaluator_metadata_present"] is not False
        ):
            raise ValueError("V2.42.35 embedded attempt invocation drifted")
    for index, attempt in enumerate(attempts):
        invocation = invocations[index]
        if (
            attempt["attempt_index"] != index + 1
            or attempt["attempt_ref_sha256"]
            != invocation["attempt_ref_sha256"]
            or attempt["local_counter_ref_sha256"]
            != invocation["local_counter_ref_sha256"]
            or attempt["meter_contract_sha256"]
            != meter_contract["contract_sha256"]
            or attempt["provider_kind"] != meter_contract["provider_kind"]
            or attempt["effect_kind"] != meter_contract["effect_kind"]
        ):
            raise ValueError("V2.42.35 invocation-to-attempt binding drifted")
    sequence = [
        int(receipt["admission_sequence"]),
        *[int(item) for item in starts],
        *[int(item) for item in completes],
    ]
    if "settlement_sequence" in receipt:
        sequence.append(int(receipt["settlement_sequence"]))
    if len(sequence) != len(set(sequence)) or any(item < 1 for item in sequence):
        raise ValueError("V2.42.35 execution sequence is invalid")
    if not all(
        int(receipt["admission_sequence"]) < int(start) for start in starts
    ):
        raise ValueError("V2.42.35 callback precedes admission")
    if any(
        int(start) >= int(complete)
        for start, complete in zip(starts, completes)
    ):
        raise ValueError("V2.42.35 callback sequence is reversed")
    if any(
        int(completes[index]) >= int(starts[index + 1])
        for index in range(min(len(completes), len(starts) - 1))
    ):
        raise ValueError("V2.42.35 retry callback sequence overlaps itself")


def validate_effect_execution_receipt(value: Mapping[str, Any]) -> None:
    receipt = _exact(
        value,
        keys=EXECUTION_RECEIPT_KEYS,
        label="execution receipt",
    )
    try:
        meter_contract = dict(receipt.get("meter_contract"))
        permit = dict(receipt.get("permit"))
        invocations = [dict(item) for item in receipt.get("attempt_invocations", [])]
        measurement = dict(receipt.get("measurement"))
        validate_provider_meter_contract(meter_contract)
        _exact(permit, keys=PERMIT_KEYS, label="embedded permit")
        if not _sealed(permit, seal_key="permit_sha256"):
            raise ValueError("embedded permit seal drifted")
        for invocation in invocations:
            _exact(
                invocation,
                keys=ATTEMPT_INVOCATION_KEYS,
                label="embedded attempt invocation",
            )
            if not _sealed(invocation, seal_key="attempt_invocation_sha256"):
                raise ValueError("embedded invocation seal drifted")
        validate_provider_cost_measurement(
            measurement,
            contract=meter_contract,
            permit=permit,
        )
        _validate_attempt_graph_bindings(
            receipt=receipt,
            meter_contract=meter_contract,
            permit=permit,
            invocations=invocations,
            attempts=measurement["attempts"],
        )
    except (TypeError, ValueError):
        raise ValueError("V2.42.35 embedded execution graph drifted") from None
    if (
        receipt.get("role") != EXECUTION_RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("candidate_runtime") is not True
        or not _is_sha256(receipt.get("invocation_ref_sha256"))
        or not _is_sha256(receipt.get("meter_contract_sha256"))
        or not _is_sha256(receipt.get("permit_sha256"))
        or not _is_sha256(receipt.get("execution_challenge_sha256"))
        or not _is_sha256(receipt.get("measurement_sha256"))
        or not _is_sha256(receipt.get("effect_receipt_sha256"))
        or receipt.get("meter_contract_sha256")
        != meter_contract["contract_sha256"]
        or receipt.get("provider_kind") != meter_contract["provider_kind"]
        or receipt.get("effect_kind") != meter_contract["effect_kind"]
        or receipt.get("charge_kind") != meter_contract["charge_kind"]
        or receipt.get("permit_ref_sha256") != permit["permit_ref_sha256"]
        or receipt.get("permit_sha256") != permit["permit_sha256"]
        or receipt.get("attempt_count") != len(receipt.get("attempt_sha256s", []))
        or receipt.get("attempt_count")
        != len(receipt.get("attempt_invocation_sha256s", []))
        or receipt.get("attempt_count") != len(invocations)
        or receipt.get("attempt_count")
        != len(receipt.get("callback_start_sequences", []))
        or receipt.get("attempt_count")
        != len(receipt.get("callback_complete_sequences", []))
        or any(
            not _is_sha256(item)
            for item in receipt.get("attempt_sha256s", [])
        )
        or any(
            not _is_sha256(item)
            for item in receipt.get("attempt_invocation_sha256s", [])
        )
        or receipt.get("attempt_invocation_sha256s")
        != [item["attempt_invocation_sha256"] for item in invocations]
        or receipt.get("attempt_sha256s")
        != [item["attempt_sha256"] for item in measurement["attempts"]]
        or receipt.get("attempt_count") != measurement["attempt_count"]
        or receipt.get("logical_status") != measurement["logical_status"]
        or receipt.get("measurement_sha256") != measurement["measurement_sha256"]
        or receipt.get("effect_receipt_sha256")
        != measurement["effect_receipt_sha256"]
        or receipt.get("observed_cost_lower_bound")
        != measurement["observed_cost_lower_bound"]
        or receipt.get("settlement_cost") != measurement["settlement_cost"]
        or receipt.get("reservation_fallback_dimensions")
        != measurement["reservation_fallback_dimensions"]
        or receipt.get("reservation_fallback_applied")
        != measurement["reservation_fallback_applied"]
        or receipt.get("settlement_eligible") != measurement["settlement_eligible"]
        or receipt.get("settlement_eligible") is not True
        or receipt.get("permit_committed_before_every_callback") is not True
        or receipt.get("single_process_serial_admission_and_settlement") is not True
        or receipt.get("callbacks_between_permits_may_overlap") is not True
        or receipt.get("local_monotonic_callback_intervals_measured") is not True
        or receipt.get("provider_response_authenticity_independently_verified")
        is not False
        or receipt.get("local_counter_and_clock_independently_attested") is not False
        or receipt.get("provider_challenge_consumption_independently_verified")
        is not False
        or receipt.get(
            "callback_single_provider_attempt_semantics_independently_verified"
        )
        is not False
        or receipt.get("external_effect_after_permit_independently_verified")
        is not False
        or receipt.get(
            "schema_resealing_without_secret_cryptographically_excluded"
        )
        is not False
        or receipt.get("cross_process_compare_and_swap_implemented") is not False
        or receipt.get("crash_durable_journal_implemented") is not False
        or receipt.get("callback_timeout_implemented") is not False
        or receipt.get("retry_backoff_implemented") is not False
        or receipt.get("automatic_whole_effect_replay_authorized") is not False
        or receipt.get("raw_provider_value_persisted_hashed_or_emitted") is not False
        or receipt.get("raw_request_or_response_content_present") is not False
        or receipt.get("credential_or_url_present") is not False
        or receipt.get("benchmark_or_evaluator_metadata_present") is not False
        or receipt.get("active_forward_integration_authorized") is not False
        or receipt.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(receipt, seal_key="execution_receipt_sha256")
    ):
        raise ValueError("V2.42.35 execution receipt drifted")
    if not all(
        int(complete) < int(receipt["settlement_sequence"])
        for complete in receipt["callback_complete_sequences"]
    ):
        raise ValueError("V2.42.35 permit/callback/settlement order drifted")


def validate_effect_failure_receipt(value: Mapping[str, Any]) -> None:
    receipt = _exact(
        value,
        keys=FAILURE_RECEIPT_KEYS,
        label="failure receipt",
    )
    try:
        meter_contract = dict(receipt.get("meter_contract"))
        permit = dict(receipt.get("permit"))
        invocations = [dict(item) for item in receipt.get("attempt_invocations", [])]
        attempts = [dict(item) for item in receipt.get("attempts", [])]
        validate_provider_meter_contract(meter_contract)
        _exact(permit, keys=PERMIT_KEYS, label="embedded permit")
        if not _sealed(permit, seal_key="permit_sha256"):
            raise ValueError("embedded permit seal drifted")
        for invocation in invocations:
            _exact(
                invocation,
                keys=ATTEMPT_INVOCATION_KEYS,
                label="embedded attempt invocation",
            )
            if not _sealed(invocation, seal_key="attempt_invocation_sha256"):
                raise ValueError("embedded invocation seal drifted")
        for attempt in attempts:
            validate_provider_attempt(attempt, contract=meter_contract)
        _validate_attempt_graph_bindings(
            receipt=receipt,
            meter_contract=meter_contract,
            permit=permit,
            invocations=invocations,
            attempts=attempts,
        )
    except (TypeError, ValueError):
        raise ValueError("V2.42.35 embedded failure graph drifted") from None
    if (
        receipt.get("role") != FAILURE_RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("candidate_runtime") is not True
        or receipt.get("meter_contract_sha256")
        != meter_contract["contract_sha256"]
        or receipt.get("provider_kind") != meter_contract["provider_kind"]
        or receipt.get("effect_kind") != meter_contract["effect_kind"]
        or receipt.get("charge_kind") != meter_contract["charge_kind"]
        or receipt.get("permit_ref_sha256") != permit["permit_ref_sha256"]
        or receipt.get("permit_sha256") != permit["permit_sha256"]
        or receipt.get("attempt_invocation_sha256s")
        != [item["attempt_invocation_sha256"] for item in invocations]
        or receipt.get("attempt_sha256s")
        != [item["attempt_sha256"] for item in attempts]
        or receipt.get("failure_phase")
        not in {"callback_exception", "observation_validation", "settlement_validation", "cancellation"}
        or receipt.get("callback_invoked") is not bool(invocations)
        or receipt.get("completed_callback_count")
        != len(receipt.get("callback_complete_sequences", []))
        or receipt.get("all_started_callbacks_completed")
        is not (
            len(receipt.get("callback_start_sequences", []))
            == len(receipt.get("callback_complete_sequences", []))
        )
        or receipt.get("provider_effect_may_have_occurred") is not bool(invocations)
        or receipt.get("reservation_remains_charged") is not True
        or receipt.get("permit_remains_pending") is not True
        or receipt.get("automatic_whole_effect_replay_authorized") is not False
        or receipt.get("raw_exception_message_persisted") is not False
        or receipt.get("raw_provider_value_persisted_hashed_or_emitted") is not False
        or receipt.get("raw_request_or_response_content_present") is not False
        or receipt.get("credential_or_url_present") is not False
        or receipt.get("benchmark_or_evaluator_metadata_present") is not False
        or receipt.get("single_process_serial_admission_and_settlement") is not True
        or receipt.get("cross_process_compare_and_swap_implemented") is not False
        or receipt.get("crash_durable_journal_implemented") is not False
        or receipt.get(
            "callback_single_provider_attempt_semantics_independently_verified"
        )
        is not False
        or receipt.get("external_effect_after_permit_independently_verified")
        is not False
        or receipt.get(
            "schema_resealing_without_secret_cryptographically_excluded"
        )
        is not False
        or receipt.get("active_forward_integration_authorized") is not False
        or receipt.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(receipt, seal_key="failure_receipt_sha256")
    ):
        raise ValueError("V2.42.35 failure receipt drifted")


class PreauthorizedEffectHarness:
    """Own one V2.42.33 state with process-local serialized mutations."""

    def __init__(
        self,
        initial_state: Mapping[str, Any],
        *,
        guidance_contract: Mapping[str, Any],
        guidance_policy: Mapping[str, Any],
        guidance_arm: Mapping[str, Any],
        scouts: Sequence[Mapping[str, Any]],
        probe: Mapping[str, Any] | None,
        experience: Mapping[str, Any] | None,
    ) -> None:
        self._guidance_contract = _clone(dict(guidance_contract))
        self._guidance_policy = _clone(dict(guidance_policy))
        self._guidance_arm = _clone(dict(guidance_arm))
        self._scouts = _clone(list(scouts))
        self._probe = _clone(probe)
        self._experience = _clone(experience)
        validate_effect_preauthorization_state(
            initial_state,
            **self._shared(),
        )
        self._state = _clone(dict(initial_state))
        self._lock = threading.Lock()
        self._sequence = 0
        self._invocation_refs: set[str] = set()
        self._challenges: set[str] = set()
        self._execution_receipts: list[dict[str, Any]] = []
        self._failure_receipts: list[dict[str, Any]] = []

    def _shared(self) -> dict[str, Any]:
        return {
            "contract": self._guidance_contract,
            "guidance_policy": self._guidance_policy,
            "guidance_arm": self._guidance_arm,
            "scouts": self._scouts,
            "probe": self._probe,
            "experience": self._experience,
        }

    def _next_sequence_locked(self) -> int:
        self._sequence += 1
        return self._sequence

    def snapshot_state(self) -> dict[str, Any]:
        with self._lock:
            return _clone(self._state)

    def execution_receipts(self) -> list[dict[str, Any]]:
        with self._lock:
            return _clone(self._execution_receipts)

    def failure_receipts(self) -> list[dict[str, Any]]:
        with self._lock:
            return _clone(self._failure_receipts)

    def _new_challenge_locked(self, *, permit_sha256: str) -> str:
        for _ in range(4):
            challenge = object_sha256(
                {
                    "random_nonce": secrets.token_hex(32),
                    "permit_sha256": permit_sha256,
                }
            )
            if challenge not in self._challenges:
                self._challenges.add(challenge)
                return challenge
        raise RuntimeError("V2.42.35 could not allocate a unique challenge")

    @staticmethod
    def _permit(state: Mapping[str, Any], permit_ref_sha256: str) -> dict[str, Any]:
        matches = [
            dict(event)
            for event in state["events"]
            if event["role"] == PERMIT_ROLE
            and event["permit_ref_sha256"] == permit_ref_sha256
        ]
        if len(matches) != 1:
            raise RuntimeError("V2.42.35 admitted permit is not unique")
        return matches[0]

    def _build_invocation(
        self,
        *,
        meter_contract: Mapping[str, Any],
        permit: Mapping[str, Any],
        invocation_ref_sha256: str,
        execution_challenge_sha256: str,
        attempt_index: int,
        callback_start_sequence: int,
    ) -> dict[str, Any]:
        attempt_ref = object_sha256(
            {
                "policy_id": POLICY_ID,
                "invocation_ref_sha256": invocation_ref_sha256,
                "execution_challenge_sha256": execution_challenge_sha256,
                "attempt_index": attempt_index,
                "kind": "provider_attempt",
            }
        )
        counter_ref = object_sha256(
            {
                "policy_id": POLICY_ID,
                "invocation_ref_sha256": invocation_ref_sha256,
                "execution_challenge_sha256": execution_challenge_sha256,
                "callback_start_sequence": callback_start_sequence,
                "kind": "process_local_counter",
            }
        )
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": ATTEMPT_INVOCATION_ROLE,
            "policy_id": POLICY_ID,
            "candidate_runtime": True,
            "meter_contract_sha256": meter_contract["contract_sha256"],
            "provider_kind": meter_contract["provider_kind"],
            "effect_kind": meter_contract["effect_kind"],
            "charge_kind": meter_contract["charge_kind"],
            "invocation_ref_sha256": invocation_ref_sha256,
            "permit_ref_sha256": permit["permit_ref_sha256"],
            "permit_sha256": permit["permit_sha256"],
            "execution_challenge_sha256": execution_challenge_sha256,
            "attempt_index": attempt_index,
            "max_attempts": meter_contract["max_attempts"],
            "attempt_ref_sha256": attempt_ref,
            "local_counter_ref_sha256": counter_ref,
            "callback_start_sequence": callback_start_sequence,
            "raw_request_or_response_content_present": False,
            "credential_or_url_present": False,
            "benchmark_or_evaluator_metadata_present": False,
        }
        value["attempt_invocation_sha256"] = object_sha256(value)
        return value

    def _failure(
        self,
        *,
        meter_contract: Mapping[str, Any],
        permit: Mapping[str, Any],
        invocation_ref_sha256: str,
        execution_challenge_sha256: str,
        state_after_permit_sha256: str,
        admission_sequence: int,
        callback_start_sequences: Sequence[int],
        callback_complete_sequences: Sequence[int],
        attempt_invocations: Sequence[Mapping[str, Any]],
        attempts: Sequence[Mapping[str, Any]],
        failure_phase: str,
    ) -> dict[str, Any]:
        with self._lock:
            pending = permit["permit_ref_sha256"] in self._state["pending_permit_refs"]
            if not pending:
                raise RuntimeError("V2.42.35 failed effect no longer has pending permit")
            value: dict[str, Any] = {
                "artifact_version": 1,
                "role": FAILURE_RECEIPT_ROLE,
                "policy_id": POLICY_ID,
                "candidate_runtime": True,
                "meter_contract": _clone(dict(meter_contract)),
                "permit": _clone(dict(permit)),
                "attempt_invocations": _clone(list(attempt_invocations)),
                "attempts": _clone(list(attempts)),
                "invocation_ref_sha256": invocation_ref_sha256,
                "meter_contract_sha256": meter_contract["contract_sha256"],
                "provider_kind": meter_contract["provider_kind"],
                "effect_kind": meter_contract["effect_kind"],
                "charge_kind": meter_contract["charge_kind"],
                "state_after_permit_sha256": state_after_permit_sha256,
                "permit_ref_sha256": permit["permit_ref_sha256"],
                "permit_sha256": permit["permit_sha256"],
                "execution_challenge_sha256": execution_challenge_sha256,
                "admission_sequence": admission_sequence,
                "callback_start_sequences": list(callback_start_sequences),
                "callback_complete_sequences": list(callback_complete_sequences),
                "attempt_invocation_sha256s": [
                    item["attempt_invocation_sha256"]
                    for item in attempt_invocations
                ],
                "attempt_sha256s": [item["attempt_sha256"] for item in attempts],
                "failure_phase": failure_phase,
                "callback_invoked": bool(callback_start_sequences),
                "completed_callback_count": len(callback_complete_sequences),
                "all_started_callbacks_completed": (
                    len(callback_start_sequences)
                    == len(callback_complete_sequences)
                ),
                "provider_effect_may_have_occurred": bool(callback_start_sequences),
                "reservation_remains_charged": True,
                "permit_remains_pending": True,
                "automatic_whole_effect_replay_authorized": False,
                "raw_exception_message_persisted": False,
                "raw_provider_value_persisted_hashed_or_emitted": False,
                "raw_request_or_response_content_present": False,
                "credential_or_url_present": False,
                "benchmark_or_evaluator_metadata_present": False,
                "single_process_serial_admission_and_settlement": True,
                "cross_process_compare_and_swap_implemented": False,
                "crash_durable_journal_implemented": False,
                "callback_single_provider_attempt_semantics_independently_verified": False,
                "external_effect_after_permit_independently_verified": False,
                "schema_resealing_without_secret_cryptographically_excluded": False,
                "active_forward_integration_authorized": False,
                "benchmark_forward_or_evaluator_authorized": False,
            }
            value["failure_receipt_sha256"] = object_sha256(value)
            validate_effect_failure_receipt(value)
            self._failure_receipts.append(value)
            return _clone(value)

    def run_effect(
        self,
        *,
        meter_contract: Mapping[str, Any],
        invocation_ref_sha256: str,
        permit_ref_sha256: str,
        charge_ref_sha256: str,
        callback: Callable[[Mapping[str, Any]], ProviderAttemptResult],
    ) -> EffectExecutionResult:
        """Admit, execute bounded single attempts, measure, and settle once."""

        validate_provider_meter_contract(meter_contract)
        if not all(
            _is_sha256(value)
            for value in (
                invocation_ref_sha256,
                permit_ref_sha256,
                charge_ref_sha256,
            )
        ):
            raise ValueError("V2.42.35 invocation identity is not SHA-256 bound")
        if not callable(callback):
            raise ValueError("V2.42.35 provider callback is not callable")

        with self._lock:
            if invocation_ref_sha256 in self._invocation_refs:
                raise ValueError("V2.42.35 duplicate invocation reference rejected")
            validate_effect_preauthorization_state(self._state, **self._shared())
            before_sha = str(self._state["state_sha256"])
            admitted = issue_metered_effect_permit(
                self._state,
                contract=meter_contract,
                guidance_contract=self._guidance_contract,
                guidance_policy=self._guidance_policy,
                guidance_arm=self._guidance_arm,
                scouts=self._scouts,
                probe=self._probe,
                experience=self._experience,
                permit_ref_sha256=permit_ref_sha256,
                charge_ref_sha256=charge_ref_sha256,
            )
            self._state = admitted
            self._invocation_refs.add(invocation_ref_sha256)
            permit = self._permit(self._state, permit_ref_sha256)
            after_permit_sha = str(self._state["state_sha256"])
            challenge = self._new_challenge_locked(
                permit_sha256=str(permit["permit_sha256"])
            )
            admission_sequence = self._next_sequence_locked()

        attempts: list[dict[str, Any]] = []
        attempt_invocations: list[dict[str, Any]] = []
        invocation_hashes: list[str] = []
        callback_starts: list[int] = []
        callback_completes: list[int] = []
        final_value: Any = None

        for attempt_index in range(1, int(meter_contract["max_attempts"]) + 1):
            with self._lock:
                callback_start = self._next_sequence_locked()
            invocation = self._build_invocation(
                meter_contract=meter_contract,
                permit=permit,
                invocation_ref_sha256=invocation_ref_sha256,
                execution_challenge_sha256=challenge,
                attempt_index=attempt_index,
                callback_start_sequence=callback_start,
            )
            callback_starts.append(callback_start)
            attempt_invocations.append(invocation)
            invocation_hashes.append(str(invocation["attempt_invocation_sha256"]))
            started_ns = time.monotonic_ns()
            try:
                callback_result = callback(_clone(invocation))
            except (KeyboardInterrupt, SystemExit, GeneratorExit):
                self._failure(
                    meter_contract=meter_contract,
                    permit=permit,
                    invocation_ref_sha256=invocation_ref_sha256,
                    execution_challenge_sha256=challenge,
                    state_after_permit_sha256=after_permit_sha,
                    admission_sequence=admission_sequence,
                    callback_start_sequences=callback_starts,
                    callback_complete_sequences=callback_completes,
                    attempt_invocations=attempt_invocations,
                    attempts=attempts,
                    failure_phase="cancellation",
                )
                raise
            except Exception:
                receipt = self._failure(
                    meter_contract=meter_contract,
                    permit=permit,
                    invocation_ref_sha256=invocation_ref_sha256,
                    execution_challenge_sha256=challenge,
                    state_after_permit_sha256=after_permit_sha,
                    admission_sequence=admission_sequence,
                    callback_start_sequences=callback_starts,
                    callback_complete_sequences=callback_completes,
                    attempt_invocations=attempt_invocations,
                    attempts=attempts,
                    failure_phase="callback_exception",
                )
                raise PreauthorizedEffectExecutionError(receipt) from None
            elapsed_ms = max(
                1,
                int(math.ceil((time.monotonic_ns() - started_ns) / 1_000_000)),
            )
            with self._lock:
                callback_complete = self._next_sequence_locked()
            callback_completes.append(callback_complete)
            try:
                if not isinstance(callback_result, ProviderAttemptResult):
                    raise ValueError("callback result type is invalid")
                observation = _exact(
                    callback_result.observation,
                    keys=OBSERVATION_KEYS,
                    label="provider attempt observation",
                )
                if (
                    observation["execution_challenge_sha256"] != challenge
                    or observation["attempt_ref_sha256"]
                    != invocation["attempt_ref_sha256"]
                    or observation["local_counter_ref_sha256"]
                    != invocation["local_counter_ref_sha256"]
                ):
                    raise ValueError("provider observation binding drifted")
                attempt = build_provider_attempt(
                    contract=meter_contract,
                    attempt_index=attempt_index,
                    attempt_ref_sha256=str(observation["attempt_ref_sha256"]),
                    local_counter_ref_sha256=str(
                        observation["local_counter_ref_sha256"]
                    ),
                    outcome=str(observation["outcome"]),
                    http_status=observation["http_status"],
                    provider_response_ref_sha256=observation[
                        "provider_response_ref_sha256"
                    ],
                    token_usage_state=str(observation["token_usage_state"]),
                    input_tokens=observation["input_tokens"],
                    output_tokens=observation["output_tokens"],
                    provider_tool_usage_state=str(
                        observation["provider_tool_usage_state"]
                    ),
                    provider_tool_calls=observation["provider_tool_calls"],
                    wall_milliseconds=elapsed_ms,
                    request_body_bytes=observation["request_body_bytes"],
                    response_body_bytes=observation["response_body_bytes"],
                )
            except Exception:
                receipt = self._failure(
                    meter_contract=meter_contract,
                    permit=permit,
                    invocation_ref_sha256=invocation_ref_sha256,
                    execution_challenge_sha256=challenge,
                    state_after_permit_sha256=after_permit_sha,
                    admission_sequence=admission_sequence,
                    callback_start_sequences=callback_starts,
                    callback_complete_sequences=callback_completes,
                    attempt_invocations=attempt_invocations,
                    attempts=attempts,
                    failure_phase="observation_validation",
                )
                raise PreauthorizedEffectExecutionError(receipt) from None
            attempts.append(attempt)
            final_value = callback_result.value
            outcome = str(attempt["outcome"])
            if outcome in TERMINAL_OUTCOMES:
                break
            if outcome not in RETRYABLE_OUTCOMES:
                receipt = self._failure(
                    meter_contract=meter_contract,
                    permit=permit,
                    invocation_ref_sha256=invocation_ref_sha256,
                    execution_challenge_sha256=challenge,
                    state_after_permit_sha256=after_permit_sha,
                    admission_sequence=admission_sequence,
                    callback_start_sequences=callback_starts,
                    callback_complete_sequences=callback_completes,
                    attempt_invocations=attempt_invocations,
                    attempts=attempts,
                    failure_phase="observation_validation",
                )
                raise PreauthorizedEffectExecutionError(receipt)

        try:
            measurement = build_provider_cost_measurement(
                contract=meter_contract,
                permit=permit,
                measurement_ref_sha256=object_sha256(
                    {
                        "policy_id": POLICY_ID,
                        "invocation_ref_sha256": invocation_ref_sha256,
                        "execution_challenge_sha256": challenge,
                        "attempt_sha256s": [
                            item["attempt_sha256"] for item in attempts
                        ],
                    }
                ),
                attempts=attempts,
            )
            validate_provider_cost_measurement(
                measurement,
                contract=meter_contract,
                permit=permit,
            )
            with self._lock:
                settled = settle_metered_effect_permit(
                    self._state,
                    meter_contract=meter_contract,
                    measurement=measurement,
                    guidance_contract=self._guidance_contract,
                    guidance_policy=self._guidance_policy,
                    guidance_arm=self._guidance_arm,
                    scouts=self._scouts,
                    probe=self._probe,
                    experience=self._experience,
                )
                settlement_sequence = self._next_sequence_locked()
                value: dict[str, Any] = {
                    "artifact_version": 1,
                    "role": EXECUTION_RECEIPT_ROLE,
                    "policy_id": POLICY_ID,
                    "candidate_runtime": True,
                    "meter_contract": _clone(dict(meter_contract)),
                    "permit": _clone(dict(permit)),
                    "attempt_invocations": _clone(attempt_invocations),
                    "measurement": _clone(measurement),
                    "invocation_ref_sha256": invocation_ref_sha256,
                    "meter_contract_sha256": meter_contract["contract_sha256"],
                    "provider_kind": meter_contract["provider_kind"],
                    "effect_kind": meter_contract["effect_kind"],
                    "charge_kind": meter_contract["charge_kind"],
                    "state_before_admission_sha256": before_sha,
                    "state_after_permit_sha256": after_permit_sha,
                    "state_after_settlement_sha256": settled["state_sha256"],
                    "permit_ref_sha256": permit["permit_ref_sha256"],
                    "permit_sha256": permit["permit_sha256"],
                    "execution_challenge_sha256": challenge,
                    "admission_sequence": admission_sequence,
                    "callback_start_sequences": list(callback_starts),
                    "callback_complete_sequences": list(callback_completes),
                    "settlement_sequence": settlement_sequence,
                    "attempt_invocation_sha256s": list(invocation_hashes),
                    "attempt_sha256s": [
                        item["attempt_sha256"] for item in attempts
                    ],
                    "attempt_count": len(attempts),
                    "logical_status": measurement["logical_status"],
                    "measurement_sha256": measurement["measurement_sha256"],
                    "effect_receipt_sha256": measurement[
                        "effect_receipt_sha256"
                    ],
                    "observed_cost_lower_bound": measurement[
                        "observed_cost_lower_bound"
                    ],
                    "settlement_cost": measurement["settlement_cost"],
                    "reservation_fallback_dimensions": measurement[
                        "reservation_fallback_dimensions"
                    ],
                    "reservation_fallback_applied": measurement[
                        "reservation_fallback_applied"
                    ],
                    "settlement_eligible": measurement["settlement_eligible"],
                    "permit_committed_before_every_callback": True,
                    "single_process_serial_admission_and_settlement": True,
                    "callbacks_between_permits_may_overlap": True,
                    "local_monotonic_callback_intervals_measured": True,
                    "provider_response_authenticity_independently_verified": False,
                    "local_counter_and_clock_independently_attested": False,
                    "provider_challenge_consumption_independently_verified": False,
                    "callback_single_provider_attempt_semantics_independently_verified": False,
                    "external_effect_after_permit_independently_verified": False,
                    "schema_resealing_without_secret_cryptographically_excluded": False,
                    "cross_process_compare_and_swap_implemented": False,
                    "crash_durable_journal_implemented": False,
                    "callback_timeout_implemented": False,
                    "retry_backoff_implemented": False,
                    "automatic_whole_effect_replay_authorized": False,
                    "raw_provider_value_persisted_hashed_or_emitted": False,
                    "raw_request_or_response_content_present": False,
                    "credential_or_url_present": False,
                    "benchmark_or_evaluator_metadata_present": False,
                    "active_forward_integration_authorized": False,
                    "benchmark_forward_or_evaluator_authorized": False,
                }
                value["execution_receipt_sha256"] = object_sha256(value)
                validate_effect_execution_receipt(value)
                self._state = settled
                self._execution_receipts.append(value)
                receipt = _clone(value)
        except PreauthorizedEffectExecutionError:
            raise
        except Exception:
            failure = self._failure(
                meter_contract=meter_contract,
                permit=permit,
                invocation_ref_sha256=invocation_ref_sha256,
                execution_challenge_sha256=challenge,
                state_after_permit_sha256=after_permit_sha,
                admission_sequence=admission_sequence,
                callback_start_sequences=callback_starts,
                callback_complete_sequences=callback_completes,
                attempt_invocations=attempt_invocations,
                attempts=attempts,
                failure_phase="settlement_validation",
            )
            raise PreauthorizedEffectExecutionError(failure) from None
        return EffectExecutionResult(receipt=receipt, value=final_value)
