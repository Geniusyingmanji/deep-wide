"""Proof-carrying boundary for V2.45.03 record-bound reserve recovery.

One pinned local child fully validates the V2.44.96 reserve parent and the
V2.45.03 zero-effect recovery, persists exact terminal artifacts, and binds
them to a compact certificate.  The parent validates exact bytes and compact
receipts before minting an opaque capability; it never replays private pages
or exposes task content to the public projection.

This is a local-child trust boundary, not a signature or remote attestation.
Runtime input remains exactly ``opaque_id`` and ``question``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import v24497_proof_carrying_targeted_reserve as parent_proof
from . import v24503_record_bound_reserve_integration as recovery
from .v24280_task_union_single_shot import validate_receipt as validate_search_receipt
from .v24308_child_exit_observability import validate_child_receipt
from .v24309_runner_exit_integration import run_child_with_terminal_receipt
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24399_failure_observable_runner import (
    CHILD_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    persist_failure_artifacts,
)
from .v24413_effect_equivalence import (
    compare_effect_snapshots,
    validate_effect_equivalence_receipt,
)
from .v24485_execution_scoped_validation_memo import ExecutionValidationMemo
from .v24486_memoized_worker_integration import validate_memo_receipt


POLICY_ID = "v24504_proof_carrying_record_bound_reserve_v1"
ENVELOPE_ROLE = "v24504_record_bound_reserve_envelope"
CERTIFICATE_ROLE = "v24504_record_bound_reserve_validation_certificate"
CERTIFICATE_NAME = "record_bound_reserve_validation_certificate.json"
COMPLETE_VALIDATOR_POLICY_ID = recovery.POLICY_ID
HEX64 = re.compile(r"[0-9a-f]{64}")
ARTIFACT_NAMES = (RESULT_NAME, MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME)
BYTE_RECEIPT_KEYS = frozenset({"name", "byte_length", "sha256"})
ENVELOPE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_reserve_envelope",
        "record_bound_result",
        "model_slot_receipt_before_record_projection",
        "transport_health_before_record_projection",
        "search_single_shot_receipt_before_record_projection",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "effect_equivalence_receipt",
        "private_task_content_present",
        "private_task_content_emitted_to_public_aggregate",
        "credential_or_privileged_evaluator_content_present",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "envelope_payload_sha256",
    }
)
CERTIFICATE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "producer_policy_id",
        "complete_validator_policy_id",
        "validator_manifest_sha256",
        "artifact_byte_receipts",
        "parent_reserve_support_receipt",
        "parent_reserve_effect_delta_receipt",
        "record_bound_receipt",
        "zero_effect_equivalence_receipt",
        "validation_memo_receipt",
        "complete_parent_and_record_bound_semantic_validation_ran_in_child",
        "same_frozen_page_vector_replayed_without_external_effect",
        "certificate_created_after_exact_terminal_artifacts",
        "independent_terminal_receipts_equal_envelope",
        "validation_memo_fail_closed_before_terminal_success",
        "parent_must_not_recursively_recompute_historical_pipeline",
        "certificate_is_independently_signed",
        "certificate_is_remote_attestation",
        "malicious_child_resistance_claimed",
        "task_question_opaque_id_query_url_page_source_value_prediction_candidate_response_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder",
        "certificate_payload_sha256",
    }
)


@dataclass(frozen=True)
class MemoizedRecordBoundExecution:
    outcome: recovery.IntegratedRecordBoundReserveOutcome
    memo_receipt: dict[str, Any]


class ValidatedRecordBoundExecution:
    """Opaque proof that complete V2.45.03 validation returned in the child."""

    __slots__ = ("__parent", "__outcome", "__envelope")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use run_single_validation_v24503_task")

    @classmethod
    def _create(
        cls,
        parent: parent_proof.ValidatedReserveExecution,
        outcome: recovery.IntegratedRecordBoundReserveOutcome,
        *,
        envelope: Mapping[str, Any],
    ) -> "ValidatedRecordBoundExecution":
        if (
            not isinstance(parent, parent_proof.ValidatedReserveExecution)
            or not isinstance(outcome, recovery.IntegratedRecordBoundReserveOutcome)
        ):
            raise TypeError("V2.45.04 requires validated typed outcomes")
        instance = object.__new__(cls)
        instance.__parent = parent
        instance.__outcome = outcome
        instance.__envelope = copy.deepcopy(dict(envelope))
        return instance

    def _trusted_parent(self) -> parent_proof.ValidatedReserveExecution:
        return self.__parent

    def _trusted_outcome(self) -> recovery.IntegratedRecordBoundReserveOutcome:
        return self.__outcome

    def _trusted_envelope(self) -> dict[str, Any]:
        return copy.deepcopy(self.__envelope)


class ValidatedProofCarryingRecordBoundEnvelope:
    """Opaque capability minted only after exact-byte parent validation."""

    __slots__ = ("__counts", "__memo", "__observations")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use validate_proof_carrying_record_bound_bundle")

    @classmethod
    def _create(
        cls,
        *,
        parent_support: Mapping[str, Any],
        parent_effect: Mapping[str, Any],
        record: Mapping[str, Any],
        zero_effect: Mapping[str, Any],
        memo: Mapping[str, Any],
        child: Mapping[str, Any],
        model: Mapping[str, Any],
        transport: Mapping[str, Any],
        search: Mapping[str, Any],
    ) -> "ValidatedProofCarryingRecordBoundEnvelope":
        instance = object.__new__(cls)
        instance.__counts = {
            "parent_reserve_support_receipt": copy.deepcopy(dict(parent_support)),
            "parent_reserve_effect_delta_receipt": copy.deepcopy(dict(parent_effect)),
            "record_bound_receipt": copy.deepcopy(dict(record)),
            "zero_effect_equivalence_receipt": copy.deepcopy(dict(zero_effect)),
        }
        instance.__memo = copy.deepcopy(dict(memo))
        instance.__observations = {
            "child": copy.deepcopy(dict(child)),
            "model": copy.deepcopy(dict(model)),
            "transport": copy.deepcopy(dict(transport)),
            "search": copy.deepcopy(dict(search)),
        }
        return instance

    def counts_only_receipts(self) -> dict[str, Any]:
        return copy.deepcopy(self.__counts)

    def content_free_memo_receipt(self) -> dict[str, Any]:
        return copy.deepcopy(self.__memo)

    def content_free_observation_receipts(self) -> dict[str, Any]:
        return copy.deepcopy(self.__observations)


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise ValueError(f"V2.45.04 {label} is not a SHA-256 digest")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _ordinary_bytes(directory: Path, name: str) -> bytes:
    if name not in {*ARTIFACT_NAMES, CERTIFICATE_NAME, CHILD_NAME}:
        raise ValueError("V2.45.04 artifact name is not allowed")
    base = directory.resolve()
    path = directory / name
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(base)
    ):
        raise RuntimeError("V2.45.04 terminal artifact is not ordinary")
    return path.read_bytes()


def _validate_exact_surface(directory: Path, expected_names: set[str]) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("V2.45.04 task directory is not ordinary")
    observed: set[str] = set()
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.45.04 task surface contains nonordinary entry")
        observed.add(path.name)
    if observed != expected_names:
        raise RuntimeError("V2.45.04 task artifact surface drifted")


def _object_from_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"V2.45.04 {label} is not UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"V2.45.04 {label} is not an object")
    return value


def _read_object(directory: Path, name: str) -> tuple[bytes, dict[str, Any]]:
    raw = _ordinary_bytes(directory, name)
    return raw, _object_from_bytes(raw, name)


def _byte_receipt(name: str, raw: bytes) -> dict[str, Any]:
    return {
        "name": name,
        "byte_length": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _validate_byte_receipt(
    value: object, *, name: str, raw: bytes
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V2.45.04 byte receipt is not an object")
    copied = dict(value)
    expected = _byte_receipt(name, raw)
    if (
        set(copied) != BYTE_RECEIPT_KEYS
        or copied != expected
        or isinstance(copied.get("byte_length"), bool)
        or not isinstance(copied.get("byte_length"), int)
        or copied["byte_length"] < 0
        or _digest(copied.get("sha256"), f"{name} byte receipt")
        != expected["sha256"]
    ):
        raise ValueError("V2.45.04 byte receipt drifted")
    return copied


def _validate_record_bound_shell(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate compact identities and receipts without semantic replay."""

    copied = copy.deepcopy(dict(value))
    mappings = (
        "parent_reserve_envelope",
        "record_bound_result",
        "model_slot_receipt_before_record_projection",
        "transport_health_before_record_projection",
        "search_single_shot_receipt_before_record_projection",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "effect_equivalence_receipt",
    )
    result = copied.get("record_bound_result")
    if (
        set(copied) != ENVELOPE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ENVELOPE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(not isinstance(copied.get(name), Mapping) for name in mappings)
        or copied.get("private_task_content_present") is not True
        or copied.get("private_task_content_emitted_to_public_aggregate") is not False
        or copied.get("credential_or_privileged_evaluator_content_present") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or not _sealed(copied, "envelope_payload_sha256")
        or not isinstance(result, Mapping)
        or set(result) != recovery.RESULT_KEYS
        or result.get("artifact_version") != 1
        or result.get("role") != recovery.RESULT_ROLE
        or result.get("policy_id") != recovery.POLICY_ID
        or not isinstance(result.get("parent_result"), Mapping)
        or not isinstance(result.get("candidate_prediction"), str)
        or not isinstance(result.get("record_bound_projection"), Mapping)
        or not isinstance(result.get("record_bound_active_evidence_result"), Mapping)
        or not isinstance(result.get("record_bound_receipt"), Mapping)
        or not _sealed(result, "result_sha256")
    ):
        raise ValueError("V2.45.04 record-bound envelope shell drifted")
    parent_shell, parent_support, parent_effect = parent_proof._validate_reserve_shell(
        copied["parent_reserve_envelope"]
    )
    record = recovery.validate_record_bound_receipt(result["record_bound_receipt"])
    zero_effect = validate_effect_equivalence_receipt(
        copied["effect_equivalence_receipt"]
    )
    cap = int(copied["model_slot_receipt"].get("slot_cap", -1))
    before_model = validate_model_receipt(
        copied["model_slot_receipt_before_record_projection"], expected_cap=cap
    )
    after_model = validate_model_receipt(copied["model_slot_receipt"], expected_cap=cap)
    before_transport = validate_transport_health(
        copied["transport_health_before_record_projection"]
    )
    after_transport = validate_transport_health(copied["transport_health"])
    before_search = dict(copied["search_single_shot_receipt_before_record_projection"])
    after_search = dict(copied["search_single_shot_receipt"])
    validate_search_receipt(before_search)
    validate_search_receipt(after_search)
    expected_effect = compare_effect_snapshots(
        model_before=before_model,
        model_after=after_model,
        transport_before=before_transport,
        transport_after=after_transport,
        search_before=before_search,
        search_after=after_search,
        expected_model_cap=cap,
    )
    if (
        result["parent_result"] != parent_shell["reserve_result"]
        or result["record_bound_receipt"] != record
        or copied["effect_equivalence_receipt"] != zero_effect
        or zero_effect != expected_effect
        or before_model != parent_shell["model_slot_receipt"]
        or before_transport != parent_shell["transport_health"]
        or before_search != parent_shell["search_single_shot_receipt"]
        or after_model != copied["model_slot_receipt"]
        or after_transport != copied["transport_health"]
        or after_search != copied["search_single_shot_receipt"]
    ):
        raise ValueError("V2.45.04 compact record-bound binding drifted")
    return copied, parent_support, parent_effect, record, zero_effect


def _validate_cross_artifacts_in_scope(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    copied, shell_support, shell_parent_effect, shell_record, shell_zero = (
        _validate_record_bound_shell(value)
    )
    parent = parent_proof.validate_cross_artifacts(copied["parent_reserve_envelope"])
    result = recovery._validate_result_in_scope(copied["record_bound_result"])
    cap = int(copied["model_slot_receipt"].get("slot_cap", -1))
    recovery._validate_cross_artifacts_in_scope(
        parent["reserve_result"],
        result,
        model_before=copied["model_slot_receipt_before_record_projection"],
        transport_before=copied["transport_health_before_record_projection"],
        search_before=copied["search_single_shot_receipt_before_record_projection"],
        model_after=copied["model_slot_receipt"],
        transport_after=copied["transport_health"],
        search_after=copied["search_single_shot_receipt"],
        effect_equivalence_receipt=copied["effect_equivalence_receipt"],
        expected_model_cap=cap,
    )
    _, parent_support, parent_effect = parent_proof._validate_reserve_shell(parent)
    if (
        result["parent_result"] != parent["reserve_result"]
        or result["record_bound_receipt"] != shell_record
        or parent_support != shell_support
        or parent_effect != shell_parent_effect
        or copied["effect_equivalence_receipt"] != shell_zero
    ):
        raise ValueError("V2.45.04 complete cross-artifact validation drifted")
    return copied


def validate_cross_artifacts(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one external envelope in one fail-closed memo scope."""

    with ExecutionValidationMemo():
        return _validate_cross_artifacts_in_scope(value)


def _unvalidated_envelope(
    parent: parent_proof.ValidatedReserveExecution,
    outcome: recovery.IntegratedRecordBoundReserveOutcome,
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "parent_reserve_envelope": parent_proof.build_envelope_from_validated_execution(
            parent
        ),
        "record_bound_result": copy.deepcopy(outcome.record_bound_result),
        "model_slot_receipt_before_record_projection": copy.deepcopy(
            outcome.model_slot_receipt_before_record_projection
        ),
        "transport_health_before_record_projection": copy.deepcopy(
            outcome.transport_health_before_record_projection
        ),
        "search_single_shot_receipt_before_record_projection": copy.deepcopy(
            outcome.search_single_shot_receipt_before_record_projection
        ),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "search_single_shot_receipt": copy.deepcopy(
            outcome.search_single_shot_receipt
        ),
        "effect_equivalence_receipt": copy.deepcopy(
            outcome.effect_equivalence_receipt
        ),
        "private_task_content_present": True,
        "private_task_content_emitted_to_public_aggregate": False,
        "credential_or_privileged_evaluator_content_present": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    return value


def run_single_validation_v24503_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
) -> ValidatedRecordBoundExecution:
    parent = parent_proof.run_single_validation_v24496_task(
        task,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    first = parent._trusted_outcome()
    before_model = copy.deepcopy(first.model_slot_receipt)
    before_transport = copy.deepcopy(first.transport_health)
    before_search = copy.deepcopy(first.search_single_shot_receipt)
    result = recovery._compute_result_from_validated(first.reserve_result)
    after_model = model.receipt()
    after_transport = search.transport_health()
    after_search = search.single_shot_receipt()
    effect = compare_effect_snapshots(
        model_before=before_model,
        model_after=after_model,
        transport_before=before_transport,
        transport_after=after_transport,
        search_before=before_search,
        search_after=after_search,
        expected_model_cap=int(after_model["slot_cap"]),
    )
    outcome = recovery.IntegratedRecordBoundReserveOutcome(
        parent=first,
        record_bound_result=result,
        model_slot_receipt_before_record_projection=before_model,
        transport_health_before_record_projection=before_transport,
        search_single_shot_receipt_before_record_projection=before_search,
        model_slot_receipt=after_model,
        transport_health=after_transport,
        search_single_shot_receipt=after_search,
        effect_equivalence_receipt=effect,
    )
    envelope = _unvalidated_envelope(parent, outcome)
    validated = _validate_cross_artifacts_in_scope(envelope)
    return ValidatedRecordBoundExecution._create(
        parent, outcome, envelope=validated
    )


def build_envelope_from_validated_execution(
    validated: ValidatedRecordBoundExecution,
) -> dict[str, Any]:
    if not isinstance(validated, ValidatedRecordBoundExecution):
        raise TypeError("V2.45.04 requires validated record-bound execution")
    shell, _, _, _, _ = _validate_record_bound_shell(
        validated._trusted_envelope()
    )
    return shell


def build_terminal_certificate(
    directory: Path,
    completed: ValidatedRecordBoundExecution,
    *,
    memo_receipt: Mapping[str, Any],
    validator_manifest_sha256: str,
    expected_artifacts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(completed, ValidatedRecordBoundExecution):
        raise TypeError("V2.45.04 certificate requires validated execution")
    manifest = _digest(validator_manifest_sha256, "validator manifest")
    memo = validate_memo_receipt(memo_receipt)
    _validate_exact_surface(directory, set(ARTIFACT_NAMES))
    if set(expected_artifacts) != set(ARTIFACT_NAMES):
        raise ValueError("V2.45.04 expected artifact vector drifted")
    artifacts = {name: _read_object(directory, name) for name in ARTIFACT_NAMES}
    if any(
        artifacts[name][1] != dict(expected_artifacts[name])
        for name in ARTIFACT_NAMES
    ):
        raise ValueError("V2.45.04 durable bytes drifted from writer input")
    envelope, parent_support, parent_effect, record, zero_effect = (
        _validate_record_bound_shell(artifacts[RESULT_NAME][1])
    )
    outcome = completed._trusted_outcome()
    model = validate_model_receipt(
        artifacts[MODEL_NAME][1],
        expected_cap=int(outcome.model_slot_receipt.get("slot_cap", -1)),
    )
    transport = validate_transport_health(artifacts[TRANSPORT_NAME][1])
    search = dict(artifacts[SEARCH_NAME][1])
    validate_search_receipt(search)
    if (
        envelope != completed._trusted_envelope()
        or model != outcome.model_slot_receipt
        or transport != outcome.transport_health
        or search != outcome.search_single_shot_receipt
        or envelope["model_slot_receipt"] != model
        or envelope["transport_health"] != transport
        or envelope["search_single_shot_receipt"] != search
        or record
        != recovery.validate_record_bound_receipt(
            outcome.record_bound_result["record_bound_receipt"]
        )
        or zero_effect
        != validate_effect_equivalence_receipt(outcome.effect_equivalence_receipt)
    ):
        raise ValueError("V2.45.04 durable artifacts drifted from validated outcome")
    value = {
        "artifact_version": 1,
        "role": CERTIFICATE_ROLE,
        "policy_id": POLICY_ID,
        "producer_policy_id": recovery.POLICY_ID,
        "complete_validator_policy_id": COMPLETE_VALIDATOR_POLICY_ID,
        "validator_manifest_sha256": manifest,
        "artifact_byte_receipts": {
            name: _byte_receipt(name, artifacts[name][0]) for name in ARTIFACT_NAMES
        },
        "parent_reserve_support_receipt": parent_support,
        "parent_reserve_effect_delta_receipt": parent_effect,
        "record_bound_receipt": record,
        "zero_effect_equivalence_receipt": zero_effect,
        "validation_memo_receipt": copy.deepcopy(memo),
        "complete_parent_and_record_bound_semantic_validation_ran_in_child": True,
        "same_frozen_page_vector_replayed_without_external_effect": True,
        "certificate_created_after_exact_terminal_artifacts": True,
        "independent_terminal_receipts_equal_envelope": True,
        "validation_memo_fail_closed_before_terminal_success": True,
        "parent_must_not_recursively_recompute_historical_pipeline": True,
        "certificate_is_independently_signed": False,
        "certificate_is_remote_attestation": False,
        "malicious_child_resistance_claimed": False,
        "task_question_opaque_id_query_url_page_source_value_prediction_candidate_response_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder": False,
    }
    value["certificate_payload_sha256"] = payload_sha256(value)
    validate_terminal_certificate(
        value,
        directory=directory,
        expected_validator_manifest_sha256=manifest,
    )
    return value


def validate_terminal_certificate(
    value: Mapping[str, Any],
    *,
    directory: Path,
    expected_validator_manifest_sha256: str,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    manifest = _digest(
        expected_validator_manifest_sha256, "expected validator manifest"
    )
    byte_receipts = copied.get("artifact_byte_receipts")
    artifacts = {name: _read_object(directory, name) for name in ARTIFACT_NAMES}
    envelope, parent_support, parent_effect, record, zero_effect = (
        _validate_record_bound_shell(artifacts[RESULT_NAME][1])
    )
    cap = int(envelope["model_slot_receipt"].get("slot_cap", -1))
    model = validate_model_receipt(artifacts[MODEL_NAME][1], expected_cap=cap)
    transport = validate_transport_health(artifacts[TRANSPORT_NAME][1])
    search = dict(artifacts[SEARCH_NAME][1])
    validate_search_receipt(search)
    memo = copied.get("validation_memo_receipt")
    true_fields = (
        "complete_parent_and_record_bound_semantic_validation_ran_in_child",
        "same_frozen_page_vector_replayed_without_external_effect",
        "certificate_created_after_exact_terminal_artifacts",
        "independent_terminal_receipts_equal_envelope",
        "validation_memo_fail_closed_before_terminal_success",
        "parent_must_not_recursively_recompute_historical_pipeline",
    )
    false_fields = (
        "certificate_is_independently_signed",
        "certificate_is_remote_attestation",
        "malicious_child_resistance_claimed",
        "task_question_opaque_id_query_url_page_source_value_prediction_candidate_response_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder",
    )
    if (
        set(copied) != CERTIFICATE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != CERTIFICATE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("producer_policy_id") != recovery.POLICY_ID
        or copied.get("complete_validator_policy_id") != COMPLETE_VALIDATOR_POLICY_ID
        or copied.get("validator_manifest_sha256") != manifest
        or not isinstance(byte_receipts, Mapping)
        or set(byte_receipts) != set(ARTIFACT_NAMES)
        or any(
            _validate_byte_receipt(
                byte_receipts.get(name), name=name, raw=artifacts[name][0]
            )
            != byte_receipts[name]
            for name in ARTIFACT_NAMES
        )
        or parent_proof._normalized_reserve_support_receipt(
            copied.get("parent_reserve_support_receipt", {})
        )
        != parent_support
        or parent_proof.reserve.validate_effect_delta_receipt(
            copied.get("parent_reserve_effect_delta_receipt", {})
        )
        != parent_effect
        or recovery.validate_record_bound_receipt(
            copied.get("record_bound_receipt", {})
        )
        != record
        or validate_effect_equivalence_receipt(
            copied.get("zero_effect_equivalence_receipt", {})
        )
        != zero_effect
        or not isinstance(memo, Mapping)
        or validate_memo_receipt(memo) != memo
        or envelope["model_slot_receipt"] != model
        or envelope["transport_health"] != transport
        or envelope["search_single_shot_receipt"] != search
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or not _sealed(copied, "certificate_payload_sha256")
    ):
        raise ValueError("V2.45.04 record-bound terminal certificate drifted")
    return copied


def validate_proof_carrying_record_bound_bundle(
    value: Mapping[str, Any],
    *,
    directory: Path,
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
) -> ValidatedProofCarryingRecordBoundEnvelope:
    _validate_exact_surface(
        directory, {*ARTIFACT_NAMES, CERTIFICATE_NAME, CHILD_NAME}
    )
    _, child_value = _read_object(directory, CHILD_NAME)
    child = validate_child_receipt(child_value)
    if (
        child.get("stage") != "result_envelope_written"
        or child.get("exception_type") is not None
        or child.get("model_receipt_written") is not True
        or child.get("transport_receipt_written") is not True
        or child.get("result_envelope_written") is not True
    ):
        raise ValueError("V2.45.04 child terminal receipt is not successful")
    _, certificate_value = _read_object(directory, CERTIFICATE_NAME)
    certificate = validate_terminal_certificate(
        certificate_value,
        directory=directory,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )
    _, persisted = _read_object(directory, RESULT_NAME)
    envelope, parent_support, parent_effect, record, zero_effect = (
        _validate_record_bound_shell(value)
    )
    if dict(value) != persisted:
        raise ValueError("V2.45.04 supplied result differs from durable result")
    _, model_value = _read_object(directory, MODEL_NAME)
    _, transport_value = _read_object(directory, TRANSPORT_NAME)
    _, search_value = _read_object(directory, SEARCH_NAME)
    model = validate_model_receipt(model_value, expected_cap=expected_model_cap)
    transport = validate_transport_health(transport_value)
    search = dict(search_value)
    validate_search_receipt(search)
    memo = validate_memo_receipt(certificate["validation_memo_receipt"])
    if (
        int(envelope["model_slot_receipt"].get("slot_cap", -1))
        != expected_model_cap
        or parent_support != certificate["parent_reserve_support_receipt"]
        or parent_effect != certificate["parent_reserve_effect_delta_receipt"]
        or record != certificate["record_bound_receipt"]
        or zero_effect != certificate["zero_effect_equivalence_receipt"]
        or envelope["model_slot_receipt"] != model
        or envelope["transport_health"] != transport
        or envelope["search_single_shot_receipt"] != search
    ):
        raise ValueError("V2.45.04 result/certificate binding drifted")
    return ValidatedProofCarryingRecordBoundEnvelope._create(
        parent_support=parent_support,
        parent_effect=parent_effect,
        record=record,
        zero_effect=zero_effect,
        memo=memo,
        child=child,
        model=model,
        transport=transport,
        search=search,
    )


def run_and_persist_memoized_record_bound_task(
    task: Mapping[str, Any],
    *,
    model_factory: Callable[[], Any],
    search_factory: Callable[[], Any],
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    directory: Path,
    writer: Callable[[str, Mapping[str, Any]], None],
    validator_manifest_sha256: str,
) -> MemoizedRecordBoundExecution:
    model: Any = None
    search: Any = None
    stage = "model_construction"
    try:
        model = model_factory()
        stage = "search_construction"
        search = search_factory()
        stage = "runtime"
        memo = ExecutionValidationMemo()
        with memo:
            validated = run_single_validation_v24503_task(
                task,
                model=model,
                search=search,
                partition_seed_sha256=partition_seed_sha256,
                limits=limits,
                monotonic=monotonic,
            )
        memo_receipt = validate_memo_receipt(memo.content_free_receipt())
    except BaseException as error:
        persist_failure_artifacts(
            error,
            failure_stage=stage,
            model=model,
            search=search,
            expected_model_cap=expected_model_cap,
            writer=writer,
        )
        raise
    outcome = validated._trusted_outcome()
    envelope = build_envelope_from_validated_execution(validated)
    artifacts = {
        MODEL_NAME: copy.deepcopy(outcome.model_slot_receipt),
        TRANSPORT_NAME: copy.deepcopy(outcome.transport_health),
        SEARCH_NAME: copy.deepcopy(outcome.search_single_shot_receipt),
        RESULT_NAME: envelope,
    }
    for name in ARTIFACT_NAMES:
        writer(name, artifacts[name])
    certificate = build_terminal_certificate(
        directory,
        validated,
        memo_receipt=memo_receipt,
        validator_manifest_sha256=validator_manifest_sha256,
        expected_artifacts=artifacts,
    )
    writer(CERTIFICATE_NAME, certificate)
    return MemoizedRecordBoundExecution(
        outcome=outcome, memo_receipt=memo_receipt
    )


def run_memoized_record_bound_worker(
    task: Mapping[str, Any],
    *,
    output_root: Path,
    directory: Path,
    model_factory: Callable[[], Any],
    search_factory: Callable[[], Any],
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
    validator_manifest_sha256: str,
) -> MemoizedRecordBoundExecution:
    completed: MemoizedRecordBoundExecution | None = None

    def action() -> None:
        nonlocal completed
        completed = run_and_persist_memoized_record_bound_task(
            task,
            model_factory=model_factory,
            search_factory=search_factory,
            partition_seed_sha256=partition_seed_sha256,
            limits=limits,
            monotonic=monotonic,
            expected_model_cap=expected_model_cap,
            directory=directory,
            writer=writer,
            validator_manifest_sha256=validator_manifest_sha256,
        )

    run_child_with_terminal_receipt(
        output_root=output_root,
        directory=directory,
        action=action,
        result_name=RESULT_NAME,
        model_receipt_name=MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name=CHILD_NAME,
    )
    if completed is None:
        raise RuntimeError("V2.45.04 memoized record-bound outcome is absent")
    return completed


PROJECTION_CHECKS = (
    "observation_conservation",
    "safe_change_conservation",
    "decision_credit_conservation",
    "zero_additional_effect",
    "memo_fail_closed",
    "single_validation",
)
PARENT_COUNT_FIELDS = (
    "targeted_plan_present",
    "reserve_selected_source_count",
    "reserve_usable_page_count",
    "reserve_new_observation_count",
)
RECORD_COUNT_FIELDS = (
    "parent_active_observation_count",
    "record_bound_active_observation_count",
    "added_observation_count",
    "removed_observation_count",
    "ambiguous_source_observation_removal_count",
    "parent_safe_change_count",
    "record_bound_safe_change_count",
    "safe_change_improvement_count",
    "safe_change_regression_count",
    "parent_candidate_changed_cell_count",
    "record_bound_candidate_changed_cell_count",
    "candidate_change_improvement_count",
    "candidate_change_regression_count",
    "parent_narrative_projection_count",
    "admitted_parent_narrative_projection_count",
    "rejected_parent_narrative_projection_count",
    "record_bound_projection_count",
)
EFFECT_COUNT_FIELDS = (
    "additional_model_requests",
    "additional_logical_queries",
    "additional_search_batches",
    "additional_provider_search_calls",
    "additional_fetch_calls",
)
MEMO_COUNT_FIELDS = (
    "validation_memo_misses",
    "validation_memo_hits",
    "validation_memo_mismatches",
)
PROJECTION_COUNT_FIELDS = (
    *PARENT_COUNT_FIELDS,
    *RECORD_COUNT_FIELDS,
    *EFFECT_COUNT_FIELDS,
    *MEMO_COUNT_FIELDS,
)
PROJECTION_NUMBER_FIELDS = (
    "parent_positive_information_gain_total_nats",
    "record_bound_positive_information_gain_total_nats",
    "positive_information_gain_gain_nats",
    "positive_information_gain_regression_nats",
    "parent_epistemic_credit_total_nats",
    "record_bound_epistemic_credit_total_nats",
    "epistemic_credit_gain_nats",
    "epistemic_credit_regression_nats",
    "parent_decision_credit_total_nats",
    "record_bound_decision_credit_total_nats",
    "decision_credit_gain_nats",
    "decision_credit_regression_nats",
)
PROJECTION_KEYS = frozenset(
    {
        "ordinal",
        *PROJECTION_COUNT_FIELDS,
        *PROJECTION_NUMBER_FIELDS,
        "checks",
        "passed",
        "projection_consumed_only_validated_capability",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
)


def _projection_count(value: Mapping[str, Any], name: str) -> int:
    item = value.get(name)
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        raise ValueError(f"V2.45.04 invalid projection count: {name}")
    return item


def _projection_number(value: Mapping[str, Any], name: str) -> float:
    item = value.get(name)
    if (
        isinstance(item, bool)
        or not isinstance(item, (int, float))
        or not math.isfinite(float(item))
        or float(item) < 0
    ):
        raise ValueError(f"V2.45.04 invalid projection number: {name}")
    return float(item)


def _delta_consistent(value: Mapping[str, Any], prefix: str) -> bool:
    before = float(value.get(f"parent_{prefix}_total_nats", -1))
    after = float(value.get(f"record_bound_{prefix}_total_nats", -1))
    gain = float(value.get(f"{prefix}_gain_nats", -1))
    regression = float(value.get(f"{prefix}_regression_nats", -1))
    return math.isclose(gain, max(0.0, after - before), abs_tol=1e-12) and math.isclose(
        regression, max(0.0, before - after), abs_tol=1e-12
    )


def _projection_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "observation_conservation": (
            int(value.get("record_bound_active_observation_count", -1))
            == int(value.get("parent_active_observation_count", -1))
            + int(value.get("added_observation_count", -1))
            - int(value.get("removed_observation_count", -1))
            and int(value.get("ambiguous_source_observation_removal_count", -1))
            <= int(value.get("removed_observation_count", -1))
        ),
        "safe_change_conservation": (
            int(value.get("safe_change_improvement_count", -1))
            == max(
                0,
                int(value.get("record_bound_safe_change_count", -1))
                - int(value.get("parent_safe_change_count", -1)),
            )
            and int(value.get("safe_change_regression_count", -1))
            == max(
                0,
                int(value.get("parent_safe_change_count", -1))
                - int(value.get("record_bound_safe_change_count", -1)),
            )
        ),
        "decision_credit_conservation": (
            _delta_consistent(value, "positive_information_gain")
            and _delta_consistent(value, "epistemic_credit")
            and _delta_consistent(value, "decision_credit")
            and (
                float(value.get("decision_credit_gain_nats", -1)) == 0
                or int(value.get("safe_change_improvement_count", 0)) > 0
            )
        ),
        "zero_additional_effect": all(
            int(value.get(name, -1)) == 0 for name in EFFECT_COUNT_FIELDS
        ),
        "memo_fail_closed": (
            int(value.get("validation_memo_misses", -1)) == 8
            and int(value.get("validation_memo_hits", -1)) >= 8
            and int(value.get("validation_memo_mismatches", -1)) == 0
        ),
        "single_validation": (
            value.get("projection_consumed_only_validated_capability") is True
            and value.get("private_task_content_emitted") is False
            and value.get("privileged_evaluator_content_read") is False
        ),
    }


def task_projection(
    ordinal: int, capability: ValidatedProofCarryingRecordBoundEnvelope
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(capability, ValidatedProofCarryingRecordBoundEnvelope)
    ):
        raise TypeError("V2.45.04 projection requires ordinal and capability")
    receipts = capability.counts_only_receipts()
    parent_support = parent_proof._normalized_reserve_support_receipt(
        receipts["parent_reserve_support_receipt"]
    )
    record = recovery.validate_record_bound_receipt(
        receipts["record_bound_receipt"]
    )
    zero_effect = validate_effect_equivalence_receipt(
        receipts["zero_effect_equivalence_receipt"]
    )
    memo = validate_memo_receipt(capability.content_free_memo_receipt())
    if zero_effect["external_effect_detected"] is not False:
        raise ValueError("V2.45.04 zero-effect receipt drifted")
    value = {
        "ordinal": ordinal,
        **{name: int(parent_support[name]) for name in PARENT_COUNT_FIELDS},
        **{name: int(record[name]) for name in RECORD_COUNT_FIELDS},
        **{name: int(record[name]) for name in EFFECT_COUNT_FIELDS},
        "validation_memo_misses": int(memo["total_misses"]),
        "validation_memo_hits": int(memo["total_hits"]),
        "validation_memo_mismatches": int(memo["total_mismatches"]),
        **{name: float(record[name]) for name in PROJECTION_NUMBER_FIELDS},
        "projection_consumed_only_validated_capability": True,
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }
    value["checks"] = _projection_checks(value)
    value["passed"] = all(value["checks"].values())
    return validate_task_projection(value)


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    checks = copied.get("checks")
    if (
        set(copied) != PROJECTION_KEYS
        or isinstance(copied.get("ordinal"), bool)
        or not isinstance(copied.get("ordinal"), int)
        or copied["ordinal"] < 1
        or any(_projection_count(copied, name) < 0 for name in PROJECTION_COUNT_FIELDS)
        or any(
            _projection_number(copied, name) < 0
            for name in PROJECTION_NUMBER_FIELDS
        )
        or not isinstance(checks, Mapping)
        or list(checks) != list(PROJECTION_CHECKS)
        or any(not isinstance(checks[name], bool) for name in PROJECTION_CHECKS)
        or dict(checks) != _projection_checks(copied)
        or copied.get("passed") is not all(checks.values())
        or copied.get("projection_consumed_only_validated_capability") is not True
        or copied.get("private_task_content_emitted") is not False
        or copied.get("privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.45.04 capability projection drifted")
    return copied


AGGREGATE_KEYS = frozenset(
    {
        "selected",
        "exact_ordinal_vector",
        "passed_tasks",
        "failed_tasks",
        "target_plan_tasks",
        "reserve_engaged_tasks",
        "reserve_usable_page_tasks",
        "parent_observation_tasks",
        "record_bound_added_observation_tasks",
        "record_bound_removed_observation_tasks",
        "record_bound_projection_tasks",
        "safe_change_improvement_tasks",
        "safe_change_regression_tasks",
        "positive_decision_credit_gain_tasks",
        "decision_credit_regression_tasks",
        "total_added_observation_count",
        "total_removed_observation_count",
        "total_record_bound_projection_count",
        "total_safe_change_improvement_count",
        "total_safe_change_regression_count",
        "total_decision_credit_gain_nats",
        "total_decision_credit_regression_nats",
        "total_additional_external_effects",
        "total_validation_memo_misses",
        "total_validation_memo_hits",
        "all_observation_conservation",
        "all_zero_additional_effect",
        "all_memos_fail_closed",
        "all_single_validations_attested",
        "all_projections_consumed_validated_capabilities",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
)


def aggregate_projections(
    projections: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    rows = sorted(
        (validate_task_projection(value) for value in projections),
        key=lambda value: value["ordinal"],
    )
    if (
        isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or len(rows) != selected
        or [row["ordinal"] for row in rows] != list(range(1, selected + 1))
    ):
        raise ValueError("V2.45.04 aggregate selection drifted")
    value = {
        "selected": selected,
        "exact_ordinal_vector": True,
        "passed_tasks": sum(row["passed"] is True for row in rows),
        "failed_tasks": sum(row["passed"] is False for row in rows),
        "target_plan_tasks": sum(row["targeted_plan_present"] > 0 for row in rows),
        "reserve_engaged_tasks": sum(
            row["reserve_selected_source_count"] > 0 for row in rows
        ),
        "reserve_usable_page_tasks": sum(
            row["reserve_usable_page_count"] > 0 for row in rows
        ),
        "parent_observation_tasks": sum(
            row["reserve_new_observation_count"] > 0 for row in rows
        ),
        "record_bound_added_observation_tasks": sum(
            row["added_observation_count"] > 0 for row in rows
        ),
        "record_bound_removed_observation_tasks": sum(
            row["removed_observation_count"] > 0 for row in rows
        ),
        "record_bound_projection_tasks": sum(
            row["record_bound_projection_count"] > 0 for row in rows
        ),
        "safe_change_improvement_tasks": sum(
            row["safe_change_improvement_count"] > 0 for row in rows
        ),
        "safe_change_regression_tasks": sum(
            row["safe_change_regression_count"] > 0 for row in rows
        ),
        "positive_decision_credit_gain_tasks": sum(
            row["decision_credit_gain_nats"] > 0 for row in rows
        ),
        "decision_credit_regression_tasks": sum(
            row["decision_credit_regression_nats"] > 0 for row in rows
        ),
        "total_added_observation_count": sum(
            row["added_observation_count"] for row in rows
        ),
        "total_removed_observation_count": sum(
            row["removed_observation_count"] for row in rows
        ),
        "total_record_bound_projection_count": sum(
            row["record_bound_projection_count"] for row in rows
        ),
        "total_safe_change_improvement_count": sum(
            row["safe_change_improvement_count"] for row in rows
        ),
        "total_safe_change_regression_count": sum(
            row["safe_change_regression_count"] for row in rows
        ),
        "total_decision_credit_gain_nats": sum(
            row["decision_credit_gain_nats"] for row in rows
        ),
        "total_decision_credit_regression_nats": sum(
            row["decision_credit_regression_nats"] for row in rows
        ),
        "total_additional_external_effects": sum(
            sum(row[name] for name in EFFECT_COUNT_FIELDS) for row in rows
        ),
        "total_validation_memo_misses": sum(
            row["validation_memo_misses"] for row in rows
        ),
        "total_validation_memo_hits": sum(
            row["validation_memo_hits"] for row in rows
        ),
        "all_observation_conservation": all(
            row["checks"]["observation_conservation"] for row in rows
        ),
        "all_zero_additional_effect": all(
            row["checks"]["zero_additional_effect"] for row in rows
        ),
        "all_memos_fail_closed": all(
            row["checks"]["memo_fail_closed"] for row in rows
        ),
        "all_single_validations_attested": all(
            row["checks"]["single_validation"] for row in rows
        ),
        "all_projections_consumed_validated_capabilities": all(
            row["projection_consumed_only_validated_capability"] for row in rows
        ),
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    bool_fields = (
        "exact_ordinal_vector",
        "all_observation_conservation",
        "all_zero_additional_effect",
        "all_memos_fail_closed",
        "all_single_validations_attested",
        "all_projections_consumed_validated_capabilities",
    )
    false_fields = (
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    )
    numeric_fields = (
        "total_decision_credit_gain_nats",
        "total_decision_credit_regression_nats",
    )
    count_fields = tuple(
        name
        for name in AGGREGATE_KEYS
        if name not in {*bool_fields, *false_fields, *numeric_fields}
    )
    task_fields = (
        "passed_tasks",
        "failed_tasks",
        "target_plan_tasks",
        "reserve_engaged_tasks",
        "reserve_usable_page_tasks",
        "parent_observation_tasks",
        "record_bound_added_observation_tasks",
        "record_bound_removed_observation_tasks",
        "record_bound_projection_tasks",
        "safe_change_improvement_tasks",
        "safe_change_regression_tasks",
        "positive_decision_credit_gain_tasks",
        "decision_credit_regression_tasks",
    )
    if (
        set(copied) != AGGREGATE_KEYS
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_fields
        )
        or copied["selected"] < 1
        or copied["passed_tasks"] + copied["failed_tasks"] != copied["selected"]
        or any(copied[name] > copied["selected"] for name in task_fields)
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), (int, float))
            or not math.isfinite(float(copied[name]))
            or float(copied[name]) < 0
            for name in numeric_fields
        )
        or any(copied.get(name) is not True for name in bool_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or copied["total_additional_external_effects"] != 0
        or (copied["positive_decision_credit_gain_tasks"] > 0)
        is not (copied["safe_change_improvement_tasks"] > 0)
    ):
        raise ValueError("V2.45.04 capability aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "ARTIFACT_NAMES",
    "CERTIFICATE_NAME",
    "CERTIFICATE_ROLE",
    "ENVELOPE_ROLE",
    "MemoizedRecordBoundExecution",
    "POLICY_ID",
    "ValidatedProofCarryingRecordBoundEnvelope",
    "ValidatedRecordBoundExecution",
    "aggregate_projections",
    "build_envelope_from_validated_execution",
    "build_terminal_certificate",
    "run_and_persist_memoized_record_bound_task",
    "run_memoized_record_bound_worker",
    "run_single_validation_v24503_task",
    "task_projection",
    "validate_aggregate",
    "validate_cross_artifacts",
    "validate_proof_carrying_record_bound_bundle",
    "validate_task_projection",
    "validate_terminal_certificate",
]
