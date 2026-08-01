"""Durable permit-before-callback coordinator for V2.42.34 effects.

V2.42.35 orders permit, callback, and settlement inside one process, while
V2.42.41 durably serializes V2.42.33 state transitions.  This candidate joins
those two boundaries without changing either frozen parent: every callback is
preceded by a durable permit generation, and every successful measurement is
followed by a durable settlement generation.

Invocation references deterministically derive permit and charge references.
Consequently, reopening the journal after a crash cannot issue the same
logical effect under a changed meter contract.  A pending permit found on
open, or left by a callback/observation/settlement failure, is never resumed or
replayed automatically.  Unrelated effects may still be admitted, so charged
uncertainty does not silently create budget capacity or force global serial
execution.

The journal contains only V2.42.33 permit and settlement events.  Attempt
invocations, measurements, callback values, credentials, URLs, and provider
content are not durably stored here.  This module does not implement a total
wall deadline, retry backoff, distributed lease, provider authenticity, or
malicious-writer protection.  It is not wired into the active clients,
runtime, runner, launcher, benchmark, or evaluator.
"""

from __future__ import annotations

import copy
import dataclasses
import math
import threading
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24233_webswarm_effect_preauthorization import (
    PERMIT_KEYS,
    PERMIT_ROLE,
    SETTLEMENT_KEYS,
    SETTLEMENT_ROLE,
    validate_effect_preauthorization_state,
)
from deepwide_agent.v24234_provider_cost_meter import (
    build_provider_attempt,
    build_provider_cost_measurement,
    issue_metered_effect_permit,
    settle_metered_effect_permit,
    validate_provider_cost_measurement,
    validate_provider_meter_contract,
)
from deepwide_agent.v24235_preauthorized_effect_harness import (
    ATTEMPT_INVOCATION_KEYS,
    ATTEMPT_INVOCATION_ROLE,
    OBSERVATION_KEYS,
    POLICY_ID as V24235_POLICY_ID,
    RETRYABLE_OUTCOMES,
    TERMINAL_OUTCOMES,
    ProviderAttemptResult,
)
from deepwide_agent.v24241_durable_preauthorization_journal import (
    POLICY_ID as V24241_POLICY_ID,
    DurableJournalCASConflict,
    DurablePreauthorizationJournal,
)


POLICY_ID = "v24242_durable_effect_coordinator_v1"
EXECUTION_RECEIPT_ROLE = "v24242_durable_effect_execution_receipt"
FAILURE_RECEIPT_ROLE = "v24242_durable_effect_failure_receipt"
RECOVERY_STATUS_ROLE = "v24242_durable_effect_recovery_status"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

DURABLE_PERMIT_BEFORE_CALLBACK_IMPLEMENTED = True
DURABLE_SETTLEMENT_AFTER_CALLBACK_IMPLEMENTED = True
DETERMINISTIC_INVOCATION_IDEMPOTENCY_BINDING_IMPLEMENTED = True
PREEXISTING_PENDING_PERMIT_AUTOMATIC_REPLAY_IMPLEMENTED = False
CALLBACK_OR_SETTLEMENT_FAILURE_AUTOMATIC_REPLAY_IMPLEMENTED = False
UNRELATED_EFFECT_ADMISSION_WITH_PENDING_PERMIT_IMPLEMENTED = True
CALLBACK_CONCURRENCY_BETWEEN_EFFECTS_IMPLEMENTED = True
CROSS_PROCESS_CAS_IMPLEMENTED = True
CALLER_SUPPLIED_EFFECT_CALLBACK_INVOCATION_AUTHORIZED = True
LOCAL_POSIX_CRASH_DURABLE_EFFECT_ORDERING_IMPLEMENTED = True
CALLBACK_TIMEOUT_IMPLEMENTED = False
RETRY_BACKOFF_IMPLEMENTED = False
TOTAL_WALL_DEADLINE_IMPLEMENTED = False
ATTEMPT_MEASUREMENT_DURABLY_PERSISTED = False
PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED = False
PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED = False
NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN = False

MAX_CAS_RETRIES = 64
FAILURE_PHASES = frozenset(
    {"callback_exception", "observation_validation", "settlement_validation"}
)

COMMIT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "journal_namespace_sha256",
        "generation",
        "previous_state_sha256",
        "resulting_state_sha256",
        "entry_sha256",
        "recovered_pending_file_count_before_commit",
        "cross_process_cas_for_cooperating_writers",
        "immutable_generation_file_created_no_clobber",
        "file_and_directory_fsync_attempted",
        "active_harness_durability_integrated",
        "external_side_effect_authorized",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
    }
)
EXECUTION_RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_runtime",
        "journal_namespace_sha256",
        "invocation_ref_sha256",
        "execution_challenge_sha256",
        "permit_ref_sha256",
        "charge_ref_sha256",
        "meter_contract",
        "meter_contract_sha256",
        "permit",
        "admission_commit",
        "attempt_invocations",
        "measurement",
        "settlement_event",
        "settlement_commit",
        "state_before_admission_sha256",
        "state_after_permit_sha256",
        "state_before_settlement_sha256",
        "state_after_settlement_sha256",
        "attempt_invocation_sha256s",
        "attempt_sha256s",
        "attempt_count",
        "logical_status",
        "measurement_sha256",
        "effect_receipt_sha256",
        "settlement_cost",
        "durable_permit_before_every_callback",
        "durable_settlement_after_all_callbacks",
        "deterministic_invocation_idempotency_binding",
        "automatic_whole_effect_replay_authorized",
        "callback_concurrency_between_effects",
        "cross_process_cas_used",
        "attempt_measurement_durably_persisted",
        "callback_timeout_implemented",
        "retry_backoff_implemented",
        "total_wall_deadline_implemented",
        "provider_challenge_consumption_independently_verified",
        "provider_response_authenticity_independently_verified",
        "network_or_distributed_filesystem_semantics_proven",
        "schema_resealing_without_secret_cryptographically_excluded",
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
        "journal_namespace_sha256",
        "invocation_ref_sha256",
        "permit_ref_sha256",
        "charge_ref_sha256",
        "meter_contract_sha256",
        "meter_contract",
        "permit_sha256",
        "permit",
        "admission_entry_sha256",
        "admission_commit",
        "state_before_admission_sha256",
        "state_after_permit_sha256",
        "attempt_invocation_sha256s",
        "attempt_sha256s",
        "failure_phase",
        "callback_started",
        "completed_callback_count",
        "provider_effect_may_have_occurred",
        "permit_durably_committed",
        "settlement_durably_committed",
        "reservation_remains_charged",
        "permit_may_remain_pending",
        "automatic_whole_effect_replay_authorized",
        "deterministic_invocation_idempotency_binding",
        "schema_resealing_without_secret_cryptographically_excluded",
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
RECOVERY_STATUS_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "journal_namespace_sha256",
        "generation",
        "current_state_sha256",
        "pending_permit_count",
        "owned_live_pending_permit_count",
        "quarantined_or_preexisting_pending_permit_count",
        "automatic_pending_effect_replay_authorized",
        "unrelated_new_effect_admission_authorized",
        "raw_provider_content_present",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "status_sha256",
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
        raise ValueError(f"V2.42.42 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, key: str) -> bool:
    seal = value.get(key)
    if not _is_sha256(seal):
        return False
    unsigned = dict(value)
    unsigned.pop(key)
    return seal == object_sha256(unsigned)


def derive_effect_references(
    *, journal_namespace_sha256: str, invocation_ref_sha256: str
) -> dict[str, str]:
    """Derive stable permit and charge identities from one logical invocation."""

    if not _is_sha256(journal_namespace_sha256) or not _is_sha256(
        invocation_ref_sha256
    ):
        raise ValueError("V2.42.42 effect identity is not SHA-256 bound")
    common = {
        "policy_id": POLICY_ID,
        "journal_namespace_sha256": journal_namespace_sha256,
        "invocation_ref_sha256": invocation_ref_sha256,
    }
    return {
        "permit_ref_sha256": object_sha256(
            {**common, "identity_kind": "durable_effect_permit"}
        ),
        "charge_ref_sha256": object_sha256(
            {**common, "identity_kind": "durable_effect_charge"}
        ),
    }


@dataclasses.dataclass(frozen=True)
class DurableEffectExecutionResult:
    """Sealed content-free receipt plus an ephemeral callback value."""

    receipt: Mapping[str, Any]
    value: Any = None


class DurableEffectExecutionError(RuntimeError):
    """Safe failure after a permit may have become durably charged."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        super().__init__("durable provider effect did not reach settlement")
        self.receipt = _clone(dict(receipt))


class DurableEffectReplayRejected(RuntimeError):
    """A deterministic invocation identity already has a durable permit."""


class DurableEffectCASExhausted(RuntimeError):
    """Cooperating writers prevented a bounded metadata-only transition."""


def _permit(state: Mapping[str, Any], permit_ref_sha256: str) -> dict[str, Any]:
    matches = [
        dict(event)
        for event in state["events"]
        if event["role"] == PERMIT_ROLE
        and event["permit_ref_sha256"] == permit_ref_sha256
    ]
    if len(matches) != 1:
        raise ValueError("V2.42.42 durable permit is not unique")
    return matches[0]


def _commit(value: Mapping[str, Any]) -> dict[str, Any]:
    commit = dict(_exact(value, keys=COMMIT_KEYS, label="journal commit"))
    if (
        commit.get("artifact_version") != 1
        or commit.get("role") != "v24241_durable_preauthorization_commit"
        or commit.get("policy_id") != V24241_POLICY_ID
        or not _is_sha256(commit.get("journal_namespace_sha256"))
        or not _is_sha256(commit.get("previous_state_sha256"))
        or not _is_sha256(commit.get("resulting_state_sha256"))
        or not _is_sha256(commit.get("entry_sha256"))
        or not isinstance(commit.get("generation"), int)
        or commit["generation"] < 1
        or not isinstance(
            commit.get("recovered_pending_file_count_before_commit"), int
        )
        or commit["recovered_pending_file_count_before_commit"] < 0
        or commit.get("cross_process_cas_for_cooperating_writers") is not True
        or commit.get("immutable_generation_file_created_no_clobber") is not True
        or commit.get("file_and_directory_fsync_attempted") is not True
        or commit.get("active_harness_durability_integrated") is not False
        or commit.get("external_side_effect_authorized") is not False
        or commit.get("active_forward_integration_authorized") is not False
        or commit.get("benchmark_forward_or_evaluator_authorized") is not False
    ):
        raise ValueError("V2.42.42 journal commit drifted")
    return commit


def _build_attempt_invocation(
    *,
    meter_contract: Mapping[str, Any],
    permit: Mapping[str, Any],
    invocation_ref_sha256: str,
    execution_challenge_sha256: str,
    attempt_index: int,
) -> dict[str, Any]:
    attempt_ref = object_sha256(
        {
            "policy_id": POLICY_ID,
            "invocation_ref_sha256": invocation_ref_sha256,
            "permit_sha256": permit["permit_sha256"],
            "attempt_index": attempt_index,
            "identity_kind": "provider_attempt",
        }
    )
    counter_ref = object_sha256(
        {
            "policy_id": POLICY_ID,
            "attempt_ref_sha256": attempt_ref,
            "identity_kind": "local_counter",
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ATTEMPT_INVOCATION_ROLE,
        "policy_id": V24235_POLICY_ID,
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
        "callback_start_sequence": attempt_index,
        "raw_request_or_response_content_present": False,
        "credential_or_url_present": False,
        "benchmark_or_evaluator_metadata_present": False,
    }
    value["attempt_invocation_sha256"] = object_sha256(value)
    _exact(value, keys=ATTEMPT_INVOCATION_KEYS, label="attempt invocation")
    return value


def validate_durable_effect_execution_receipt(value: Mapping[str, Any]) -> None:
    receipt = _exact(
        value,
        keys=EXECUTION_RECEIPT_KEYS,
        label="execution receipt",
    )
    try:
        meter = dict(receipt["meter_contract"])
        permit = dict(receipt["permit"])
        admission = _commit(receipt["admission_commit"])
        settlement = _commit(receipt["settlement_commit"])
        invocations = [dict(item) for item in receipt["attempt_invocations"]]
        measurement = dict(receipt["measurement"])
        settlement_event = dict(receipt["settlement_event"])
        validate_provider_meter_contract(meter)
        _exact(permit, keys=PERMIT_KEYS, label="embedded permit")
        validate_provider_cost_measurement(
            measurement,
            contract=meter,
            permit=permit,
        )
        _exact(
            settlement_event,
            keys=SETTLEMENT_KEYS,
            label="embedded settlement event",
        )
    except (KeyError, TypeError, ValueError):
        raise ValueError("V2.42.42 embedded execution graph drifted") from None
    derived = derive_effect_references(
        journal_namespace_sha256=str(receipt["journal_namespace_sha256"]),
        invocation_ref_sha256=str(receipt["invocation_ref_sha256"]),
    )
    expected_challenge = object_sha256(
        {
            "policy_id": POLICY_ID,
            "journal_namespace_sha256": receipt["journal_namespace_sha256"],
            "invocation_ref_sha256": receipt["invocation_ref_sha256"],
            "permit_sha256": permit["permit_sha256"],
            "identity_kind": "execution_challenge",
        }
    )
    if (
        receipt.get("role") != EXECUTION_RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("candidate_runtime") is not True
        or receipt.get("execution_challenge_sha256") != expected_challenge
        or receipt.get("permit_ref_sha256") != derived["permit_ref_sha256"]
        or receipt.get("charge_ref_sha256") != derived["charge_ref_sha256"]
        or receipt.get("meter_contract_sha256") != meter["contract_sha256"]
        or permit.get("permit_ref_sha256") != receipt.get("permit_ref_sha256")
        or admission["journal_namespace_sha256"]
        != receipt.get("journal_namespace_sha256")
        or settlement["journal_namespace_sha256"]
        != receipt.get("journal_namespace_sha256")
        or admission["previous_state_sha256"]
        != receipt.get("state_before_admission_sha256")
        or admission["resulting_state_sha256"]
        != receipt.get("state_after_permit_sha256")
        or admission["generation"] != permit.get("sequence_index")
        or settlement["generation"] <= admission["generation"]
        or settlement["previous_state_sha256"]
        != receipt.get("state_before_settlement_sha256")
        or settlement["resulting_state_sha256"]
        != receipt.get("state_after_settlement_sha256")
        or settlement["generation"] != settlement_event.get("sequence_index")
        or settlement_event.get("role") != SETTLEMENT_ROLE
        or settlement_event.get("permit_ref_sha256")
        != receipt.get("permit_ref_sha256")
        or settlement_event.get("permit_sha256") != permit.get("permit_sha256")
        or settlement_event.get("effect_receipt_sha256")
        != measurement.get("effect_receipt_sha256")
        or settlement_event.get("actual_cost_source_sha256")
        != measurement.get("measurement_sha256")
        or settlement_event.get("actual_cost") != measurement.get("settlement_cost")
        or not _sealed(settlement_event, key="settlement_sha256")
        or receipt.get("attempt_count") != len(invocations)
        or receipt.get("attempt_count") != measurement["attempt_count"]
        or receipt.get("attempt_invocation_sha256s")
        != [item.get("attempt_invocation_sha256") for item in invocations]
        or receipt.get("attempt_sha256s")
        != [item["attempt_sha256"] for item in measurement["attempts"]]
        or receipt.get("logical_status") != measurement["logical_status"]
        or receipt.get("measurement_sha256") != measurement["measurement_sha256"]
        or receipt.get("effect_receipt_sha256")
        != measurement["effect_receipt_sha256"]
        or receipt.get("settlement_cost") != measurement["settlement_cost"]
        or receipt.get("durable_permit_before_every_callback") is not True
        or receipt.get("durable_settlement_after_all_callbacks") is not True
        or receipt.get("deterministic_invocation_idempotency_binding") is not True
        or receipt.get("automatic_whole_effect_replay_authorized") is not False
        or receipt.get("callback_concurrency_between_effects") is not True
        or receipt.get("cross_process_cas_used") is not True
        or receipt.get("attempt_measurement_durably_persisted") is not False
        or receipt.get("callback_timeout_implemented") is not False
        or receipt.get("retry_backoff_implemented") is not False
        or receipt.get("total_wall_deadline_implemented") is not False
        or receipt.get("provider_challenge_consumption_independently_verified")
        is not False
        or receipt.get("provider_response_authenticity_independently_verified")
        is not False
        or receipt.get("network_or_distributed_filesystem_semantics_proven")
        is not False
        or receipt.get(
            "schema_resealing_without_secret_cryptographically_excluded"
        )
        is not False
        or receipt.get("raw_provider_value_persisted_hashed_or_emitted") is not False
        or receipt.get("raw_request_or_response_content_present") is not False
        or receipt.get("credential_or_url_present") is not False
        or receipt.get("benchmark_or_evaluator_metadata_present") is not False
        or receipt.get("active_forward_integration_authorized") is not False
        or receipt.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(receipt, key="execution_receipt_sha256")
    ):
        raise ValueError("V2.42.42 execution receipt drifted")
    for index, invocation in enumerate(invocations, start=1):
        expected_invocation = _build_attempt_invocation(
            meter_contract=meter,
            permit=permit,
            invocation_ref_sha256=str(receipt["invocation_ref_sha256"]),
            execution_challenge_sha256=expected_challenge,
            attempt_index=index,
        )
        attempt = measurement["attempts"][index - 1]
        if (
            invocation != expected_invocation
            or attempt["attempt_ref_sha256"] != invocation["attempt_ref_sha256"]
            or attempt["local_counter_ref_sha256"]
            != invocation["local_counter_ref_sha256"]
        ):
            raise ValueError("V2.42.42 attempt invocation drifted")


def validate_durable_effect_failure_receipt(value: Mapping[str, Any]) -> None:
    receipt = _exact(value, keys=FAILURE_RECEIPT_KEYS, label="failure receipt")
    try:
        meter = dict(receipt["meter_contract"])
        permit = dict(receipt["permit"])
        admission = _commit(receipt["admission_commit"])
        validate_provider_meter_contract(meter)
        _exact(permit, keys=PERMIT_KEYS, label="embedded permit")
    except (KeyError, TypeError, ValueError):
        raise ValueError("V2.42.42 embedded failure graph drifted") from None
    derived = derive_effect_references(
        journal_namespace_sha256=str(receipt.get("journal_namespace_sha256")),
        invocation_ref_sha256=str(receipt.get("invocation_ref_sha256")),
    )
    if (
        receipt.get("role") != FAILURE_RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("candidate_runtime") is not True
        or receipt.get("permit_ref_sha256") != derived["permit_ref_sha256"]
        or receipt.get("charge_ref_sha256") != derived["charge_ref_sha256"]
        or receipt.get("meter_contract_sha256") != meter.get("contract_sha256")
        or receipt.get("permit_sha256") != permit.get("permit_sha256")
        or receipt.get("permit_ref_sha256") != permit.get("permit_ref_sha256")
        or permit.get("charge_kind") != meter.get("charge_kind")
        or permit.get("estimate_source_sha256") != meter.get("contract_sha256")
        or permit.get("reserved_cost") != meter.get("reserved_cost")
        or permit.get("external_side_effect_authorized") is not False
        or admission.get("journal_namespace_sha256")
        != receipt.get("journal_namespace_sha256")
        or admission.get("entry_sha256") != receipt.get("admission_entry_sha256")
        or admission.get("generation") != permit.get("sequence_index")
        or admission.get("previous_state_sha256")
        != receipt.get("state_before_admission_sha256")
        or admission.get("resulting_state_sha256")
        != receipt.get("state_after_permit_sha256")
        or any(
            not _is_sha256(item)
            for item in receipt.get("attempt_invocation_sha256s", [])
        )
        or any(not _is_sha256(item) for item in receipt.get("attempt_sha256s", []))
        or receipt.get("failure_phase") not in FAILURE_PHASES
        or not isinstance(receipt.get("completed_callback_count"), int)
        or receipt["completed_callback_count"] < 0
        or receipt["completed_callback_count"]
        > len(receipt.get("attempt_invocation_sha256s", []))
        or len(receipt.get("attempt_sha256s", []))
        > receipt["completed_callback_count"]
        or receipt.get("callback_started")
        is not bool(receipt.get("attempt_invocation_sha256s", []))
        or receipt.get("provider_effect_may_have_occurred")
        is not bool(receipt.get("callback_started"))
        or receipt.get("permit_durably_committed") is not True
        or not isinstance(receipt.get("settlement_durably_committed"), bool)
        or receipt.get("reservation_remains_charged") is not True
        or not isinstance(receipt.get("permit_may_remain_pending"), bool)
        or receipt["settlement_durably_committed"]
        is receipt["permit_may_remain_pending"]
        or receipt.get("automatic_whole_effect_replay_authorized") is not False
        or receipt.get("deterministic_invocation_idempotency_binding") is not True
        or receipt.get(
            "schema_resealing_without_secret_cryptographically_excluded"
        )
        is not False
        or receipt.get("raw_exception_message_persisted") is not False
        or receipt.get("raw_provider_value_persisted_hashed_or_emitted") is not False
        or receipt.get("raw_request_or_response_content_present") is not False
        or receipt.get("credential_or_url_present") is not False
        or receipt.get("benchmark_or_evaluator_metadata_present") is not False
        or receipt.get("active_forward_integration_authorized") is not False
        or receipt.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(receipt, key="failure_receipt_sha256")
    ):
        raise ValueError("V2.42.42 failure receipt drifted")


def validate_durable_effect_recovery_status(value: Mapping[str, Any]) -> None:
    status = _exact(value, keys=RECOVERY_STATUS_KEYS, label="recovery status")
    if (
        status.get("artifact_version") != 1
        or status.get("role") != RECOVERY_STATUS_ROLE
        or status.get("policy_id") != POLICY_ID
        or not _is_sha256(status.get("journal_namespace_sha256"))
        or not _is_sha256(status.get("current_state_sha256"))
        or not isinstance(status.get("generation"), int)
        or status["generation"] < 0
        or not isinstance(status.get("pending_permit_count"), int)
        or not isinstance(status.get("owned_live_pending_permit_count"), int)
        or not isinstance(
            status.get("quarantined_or_preexisting_pending_permit_count"), int
        )
        or min(
            status["pending_permit_count"],
            status["owned_live_pending_permit_count"],
            status["quarantined_or_preexisting_pending_permit_count"],
        )
        < 0
        or status["pending_permit_count"]
        != status["owned_live_pending_permit_count"]
        + status["quarantined_or_preexisting_pending_permit_count"]
        or status.get("automatic_pending_effect_replay_authorized") is not False
        or not isinstance(status.get("unrelated_new_effect_admission_authorized"), bool)
        or status.get("raw_provider_content_present") is not False
        or status.get("active_forward_integration_authorized") is not False
        or status.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(status, key="status_sha256")
    ):
        raise ValueError("V2.42.42 recovery status drifted")


class DurablePreauthorizedEffectCoordinator:
    """Run effects against one V2.42.41 journal without replaying uncertainty."""

    def __init__(
        self,
        *,
        root: Path,
        journal_namespace_sha256: str,
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
        self.journal = DurablePreauthorizationJournal(
            root=root,
            journal_namespace_sha256=journal_namespace_sha256,
            contract=self._guidance_contract,
            guidance_policy=self._guidance_policy,
            guidance_arm=self._guidance_arm,
            scouts=self._scouts,
            probe=self._probe,
            experience=self._experience,
        )
        state = self.journal.load()
        validate_effect_preauthorization_state(state, **self._shared())
        self._lock = threading.Lock()
        self._owned_pending: set[str] = set()
        self._quarantined_pending: set[str] = set(state["pending_permit_refs"])

    @classmethod
    def initialize(
        cls,
        *,
        root: Path,
        journal_namespace_sha256: str,
        initial_state: Mapping[str, Any],
        guidance_contract: Mapping[str, Any],
        guidance_policy: Mapping[str, Any],
        guidance_arm: Mapping[str, Any],
        scouts: Sequence[Mapping[str, Any]],
        probe: Mapping[str, Any] | None,
        experience: Mapping[str, Any] | None,
    ) -> "DurablePreauthorizedEffectCoordinator":
        shared = {
            "contract": guidance_contract,
            "guidance_policy": guidance_policy,
            "guidance_arm": guidance_arm,
            "scouts": scouts,
            "probe": probe,
            "experience": experience,
        }
        journal = DurablePreauthorizationJournal(
            root=root,
            journal_namespace_sha256=journal_namespace_sha256,
            **shared,
        )
        journal.initialize(initial_state)
        return cls(
            root=root,
            journal_namespace_sha256=journal_namespace_sha256,
            guidance_contract=guidance_contract,
            guidance_policy=guidance_policy,
            guidance_arm=guidance_arm,
            scouts=scouts,
            probe=probe,
            experience=experience,
        )

    def _shared(self) -> dict[str, Any]:
        return {
            "contract": self._guidance_contract,
            "guidance_policy": self._guidance_policy,
            "guidance_arm": self._guidance_arm,
            "scouts": self._scouts,
            "probe": self._probe,
            "experience": self._experience,
        }

    def recovery_status(self) -> dict[str, Any]:
        state = self.journal.load()
        pending = set(state["pending_permit_refs"])
        with self._lock:
            owned = pending & self._owned_pending
            quarantined = pending & self._quarantined_pending
        value = {
            "artifact_version": 1,
            "role": RECOVERY_STATUS_ROLE,
            "policy_id": POLICY_ID,
            "journal_namespace_sha256": self.journal.namespace,
            "generation": state["event_count"],
            "current_state_sha256": state["state_sha256"],
            "pending_permit_count": len(pending),
            "owned_live_pending_permit_count": len(owned),
            "quarantined_or_preexisting_pending_permit_count": len(
                pending - owned | quarantined
            ),
            "automatic_pending_effect_replay_authorized": False,
            "unrelated_new_effect_admission_authorized": not bool(
                state["hard_stop_required"]
            ),
            "raw_provider_content_present": False,
            "active_forward_integration_authorized": False,
            "benchmark_forward_or_evaluator_authorized": False,
        }
        value["status_sha256"] = object_sha256(value)
        validate_durable_effect_recovery_status(value)
        return value

    def _mark_quarantined(self, permit_ref_sha256: str) -> None:
        with self._lock:
            self._owned_pending.discard(permit_ref_sha256)
            self._quarantined_pending.add(permit_ref_sha256)

    def _mark_settled(self, permit_ref_sha256: str) -> None:
        with self._lock:
            self._owned_pending.discard(permit_ref_sha256)
            self._quarantined_pending.discard(permit_ref_sha256)

    def _admit(
        self,
        *,
        meter_contract: Mapping[str, Any],
        invocation_ref_sha256: str,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str]]:
        refs = derive_effect_references(
            journal_namespace_sha256=self.journal.namespace,
            invocation_ref_sha256=invocation_ref_sha256,
        )
        for _ in range(MAX_CAS_RETRIES):
            previous = self.journal.load()
            if any(
                event["role"] == PERMIT_ROLE
                and event["permit_ref_sha256"] == refs["permit_ref_sha256"]
                for event in previous["events"]
            ):
                raise DurableEffectReplayRejected(
                    "V2.42.42 invocation already has a durable permit"
                )
            admitted = issue_metered_effect_permit(
                previous,
                contract=meter_contract,
                guidance_contract=self._guidance_contract,
                guidance_policy=self._guidance_policy,
                guidance_arm=self._guidance_arm,
                scouts=self._scouts,
                probe=self._probe,
                experience=self._experience,
                permit_ref_sha256=refs["permit_ref_sha256"],
                charge_ref_sha256=refs["charge_ref_sha256"],
            )
            try:
                commit = self.journal.compare_and_append(
                    expected_state_sha256=str(previous["state_sha256"]),
                    current_state=admitted,
                )
            except DurableJournalCASConflict:
                continue
            normalized_commit = _commit(commit)
            permit = _permit(admitted, refs["permit_ref_sha256"])
            with self._lock:
                self._owned_pending.add(refs["permit_ref_sha256"])
            return previous, admitted, permit, refs | {
                "admission_commit": normalized_commit
            }
        raise DurableEffectCASExhausted("V2.42.42 admission CAS retry cap reached")

    def _failure(
        self,
        *,
        meter_contract: Mapping[str, Any],
        invocation_ref_sha256: str,
        refs: Mapping[str, Any],
        permit: Mapping[str, Any],
        attempt_invocations: Sequence[Mapping[str, Any]],
        attempts: Sequence[Mapping[str, Any]],
        completed_callback_count: int,
        failure_phase: str,
        settlement_durably_committed: bool = False,
    ) -> dict[str, Any]:
        if settlement_durably_committed:
            self._mark_settled(str(permit["permit_ref_sha256"]))
        else:
            self._mark_quarantined(str(permit["permit_ref_sha256"]))
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": FAILURE_RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            "candidate_runtime": True,
            "journal_namespace_sha256": self.journal.namespace,
            "invocation_ref_sha256": invocation_ref_sha256,
            "permit_ref_sha256": refs["permit_ref_sha256"],
            "charge_ref_sha256": refs["charge_ref_sha256"],
            "meter_contract_sha256": meter_contract["contract_sha256"],
            "meter_contract": _clone(dict(meter_contract)),
            "permit_sha256": permit["permit_sha256"],
            "permit": _clone(dict(permit)),
            "admission_entry_sha256": refs["admission_commit"]["entry_sha256"],
            "admission_commit": _clone(dict(refs["admission_commit"])),
            "state_before_admission_sha256": refs["admission_commit"][
                "previous_state_sha256"
            ],
            "state_after_permit_sha256": refs["admission_commit"][
                "resulting_state_sha256"
            ],
            "attempt_invocation_sha256s": [
                item["attempt_invocation_sha256"] for item in attempt_invocations
            ],
            "attempt_sha256s": [item["attempt_sha256"] for item in attempts],
            "failure_phase": failure_phase,
            "callback_started": bool(attempt_invocations),
            "completed_callback_count": completed_callback_count,
            "provider_effect_may_have_occurred": bool(attempt_invocations),
            "permit_durably_committed": True,
            "settlement_durably_committed": settlement_durably_committed,
            "reservation_remains_charged": True,
            "permit_may_remain_pending": not settlement_durably_committed,
            "automatic_whole_effect_replay_authorized": False,
            "deterministic_invocation_idempotency_binding": True,
            "schema_resealing_without_secret_cryptographically_excluded": False,
            "raw_exception_message_persisted": False,
            "raw_provider_value_persisted_hashed_or_emitted": False,
            "raw_request_or_response_content_present": False,
            "credential_or_url_present": False,
            "benchmark_or_evaluator_metadata_present": False,
            "active_forward_integration_authorized": False,
            "benchmark_forward_or_evaluator_authorized": False,
        }
        value["failure_receipt_sha256"] = object_sha256(value)
        validate_durable_effect_failure_receipt(value)
        return value

    def _settle(
        self,
        *,
        meter_contract: Mapping[str, Any],
        measurement: Mapping[str, Any],
        permit_ref_sha256: str,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        for _ in range(MAX_CAS_RETRIES):
            previous = self.journal.load()
            if permit_ref_sha256 not in previous["pending_permit_refs"]:
                raise ValueError("V2.42.42 durable permit is no longer pending")
            settled = settle_metered_effect_permit(
                previous,
                meter_contract=meter_contract,
                measurement=measurement,
                guidance_contract=self._guidance_contract,
                guidance_policy=self._guidance_policy,
                guidance_arm=self._guidance_arm,
                scouts=self._scouts,
                probe=self._probe,
                experience=self._experience,
            )
            try:
                commit = self.journal.compare_and_append(
                    expected_state_sha256=str(previous["state_sha256"]),
                    current_state=settled,
                )
            except DurableJournalCASConflict:
                continue
            self._mark_settled(permit_ref_sha256)
            return previous, settled, _commit(commit)
        raise DurableEffectCASExhausted("V2.42.42 settlement CAS retry cap reached")

    def run_effect(
        self,
        *,
        meter_contract: Mapping[str, Any],
        invocation_ref_sha256: str,
        callback: Callable[[Mapping[str, Any]], ProviderAttemptResult],
        fault_hook: Callable[[str], None] | None = None,
    ) -> DurableEffectExecutionResult:
        """Durably admit, execute bounded callbacks, and durably settle once."""

        meter = _clone(dict(meter_contract))
        validate_provider_meter_contract(meter)
        if not _is_sha256(invocation_ref_sha256):
            raise ValueError("V2.42.42 invocation reference is not SHA-256 bound")
        if not callable(callback):
            raise ValueError("V2.42.42 callback is not callable")
        previous, admitted, permit, refs = self._admit(
            meter_contract=meter,
            invocation_ref_sha256=invocation_ref_sha256,
        )
        if fault_hook is not None:
            try:
                fault_hook("after_durable_permit_before_callback")
            except BaseException:
                self._mark_quarantined(str(permit["permit_ref_sha256"]))
                raise

        challenge = object_sha256(
            {
                "policy_id": POLICY_ID,
                "journal_namespace_sha256": self.journal.namespace,
                "invocation_ref_sha256": invocation_ref_sha256,
                "permit_sha256": permit["permit_sha256"],
                "identity_kind": "execution_challenge",
            }
        )
        attempts: list[dict[str, Any]] = []
        invocations: list[dict[str, Any]] = []
        completed_callbacks = 0
        final_value: Any = None

        for attempt_index in range(1, int(meter["max_attempts"]) + 1):
            invocation = _build_attempt_invocation(
                meter_contract=meter,
                permit=permit,
                invocation_ref_sha256=invocation_ref_sha256,
                execution_challenge_sha256=challenge,
                attempt_index=attempt_index,
            )
            invocations.append(invocation)
            started_ns = time.monotonic_ns()
            try:
                callback_result = callback(_clone(invocation))
            except (KeyboardInterrupt, SystemExit, GeneratorExit):
                self._mark_quarantined(str(permit["permit_ref_sha256"]))
                raise
            except Exception:
                failure = self._failure(
                    meter_contract=meter,
                    invocation_ref_sha256=invocation_ref_sha256,
                    refs=refs,
                    permit=permit,
                    attempt_invocations=invocations,
                    attempts=attempts,
                    completed_callback_count=completed_callbacks,
                    failure_phase="callback_exception",
                )
                raise DurableEffectExecutionError(failure) from None
            completed_callbacks += 1
            elapsed_ms = max(
                1,
                int(math.ceil((time.monotonic_ns() - started_ns) / 1_000_000)),
            )
            if fault_hook is not None:
                try:
                    fault_hook("after_callback_before_observation_commit")
                except BaseException:
                    self._mark_quarantined(str(permit["permit_ref_sha256"]))
                    raise
            try:
                if not isinstance(callback_result, ProviderAttemptResult):
                    raise ValueError("callback result type is invalid")
                observation = _exact(
                    _clone(dict(callback_result.observation)),
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
                    contract=meter,
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
                failure = self._failure(
                    meter_contract=meter,
                    invocation_ref_sha256=invocation_ref_sha256,
                    refs=refs,
                    permit=permit,
                    attempt_invocations=invocations,
                    attempts=attempts,
                    completed_callback_count=completed_callbacks,
                    failure_phase="observation_validation",
                )
                raise DurableEffectExecutionError(failure) from None
            attempts.append(attempt)
            final_value = callback_result.value
            outcome = str(attempt["outcome"])
            if outcome in TERMINAL_OUTCOMES:
                break
            if outcome not in RETRYABLE_OUTCOMES:
                failure = self._failure(
                    meter_contract=meter,
                    invocation_ref_sha256=invocation_ref_sha256,
                    refs=refs,
                    permit=permit,
                    attempt_invocations=invocations,
                    attempts=attempts,
                    completed_callback_count=completed_callbacks,
                    failure_phase="observation_validation",
                )
                raise DurableEffectExecutionError(failure)

        measurement: dict[str, Any] | None = None
        try:
            measurement = build_provider_cost_measurement(
                contract=meter,
                permit=permit,
                measurement_ref_sha256=object_sha256(
                    {
                        "policy_id": POLICY_ID,
                        "journal_namespace_sha256": self.journal.namespace,
                        "invocation_ref_sha256": invocation_ref_sha256,
                        "attempt_sha256s": [
                            item["attempt_sha256"] for item in attempts
                        ],
                    }
                ),
                attempts=attempts,
            )
            validate_provider_cost_measurement(
                measurement,
                contract=meter,
                permit=permit,
            )
            state_before_settlement, settled, settlement_commit = self._settle(
                meter_contract=meter,
                measurement=measurement,
                permit_ref_sha256=str(permit["permit_ref_sha256"]),
            )
        except Exception:
            settlement_committed = False
            if measurement is not None:
                try:
                    current = self.journal.load()
                    settlement_committed = (
                        str(permit["permit_ref_sha256"])
                        not in current["pending_permit_refs"]
                        and any(
                            event["role"] == SETTLEMENT_ROLE
                            and event["permit_ref_sha256"]
                            == permit["permit_ref_sha256"]
                            and event["effect_receipt_sha256"]
                            == measurement["effect_receipt_sha256"]
                            and event["actual_cost_source_sha256"]
                            == measurement["measurement_sha256"]
                            for event in current["events"]
                        )
                    )
                except Exception:
                    settlement_committed = False
            if settlement_committed:
                value = self._failure(
                    meter_contract=meter,
                    invocation_ref_sha256=invocation_ref_sha256,
                    refs=refs,
                    permit=permit,
                    attempt_invocations=invocations,
                    attempts=attempts,
                    completed_callback_count=completed_callbacks,
                    failure_phase="settlement_validation",
                    settlement_durably_committed=True,
                )
                raise DurableEffectExecutionError(value) from None
            failure = self._failure(
                meter_contract=meter,
                invocation_ref_sha256=invocation_ref_sha256,
                refs=refs,
                permit=permit,
                attempt_invocations=invocations,
                attempts=attempts,
                completed_callback_count=completed_callbacks,
                failure_phase="settlement_validation",
            )
            raise DurableEffectExecutionError(failure) from None

        if fault_hook is not None:
            fault_hook("after_durable_settlement_before_return")
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": EXECUTION_RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            "candidate_runtime": True,
            "journal_namespace_sha256": self.journal.namespace,
            "invocation_ref_sha256": invocation_ref_sha256,
            "execution_challenge_sha256": challenge,
            "permit_ref_sha256": refs["permit_ref_sha256"],
            "charge_ref_sha256": refs["charge_ref_sha256"],
            "meter_contract": _clone(meter),
            "meter_contract_sha256": meter["contract_sha256"],
            "permit": _clone(permit),
            "admission_commit": _clone(refs["admission_commit"]),
            "attempt_invocations": _clone(invocations),
            "measurement": _clone(measurement),
            "settlement_event": _clone(settled["events"][-1]),
            "settlement_commit": _clone(settlement_commit),
            "state_before_admission_sha256": previous["state_sha256"],
            "state_after_permit_sha256": admitted["state_sha256"],
            "state_before_settlement_sha256": state_before_settlement[
                "state_sha256"
            ],
            "state_after_settlement_sha256": settled["state_sha256"],
            "attempt_invocation_sha256s": [
                item["attempt_invocation_sha256"] for item in invocations
            ],
            "attempt_sha256s": [item["attempt_sha256"] for item in attempts],
            "attempt_count": len(attempts),
            "logical_status": measurement["logical_status"],
            "measurement_sha256": measurement["measurement_sha256"],
            "effect_receipt_sha256": measurement["effect_receipt_sha256"],
            "settlement_cost": measurement["settlement_cost"],
            "durable_permit_before_every_callback": True,
            "durable_settlement_after_all_callbacks": True,
            "deterministic_invocation_idempotency_binding": True,
            "automatic_whole_effect_replay_authorized": False,
            "callback_concurrency_between_effects": True,
            "cross_process_cas_used": True,
            "attempt_measurement_durably_persisted": False,
            "callback_timeout_implemented": False,
            "retry_backoff_implemented": False,
            "total_wall_deadline_implemented": False,
            "provider_challenge_consumption_independently_verified": False,
            "provider_response_authenticity_independently_verified": False,
            "network_or_distributed_filesystem_semantics_proven": False,
            "schema_resealing_without_secret_cryptographically_excluded": False,
            "raw_provider_value_persisted_hashed_or_emitted": False,
            "raw_request_or_response_content_present": False,
            "credential_or_url_present": False,
            "benchmark_or_evaluator_metadata_present": False,
            "active_forward_integration_authorized": False,
            "benchmark_forward_or_evaluator_authorized": False,
        }
        value["execution_receipt_sha256"] = object_sha256(value)
        validate_durable_effect_execution_receipt(value)
        return DurableEffectExecutionResult(receipt=value, value=final_value)
