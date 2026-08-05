"""Proof-carrying integration for contradiction-aware targeted reserve.

The trusted child completely validates V2.44.90 once, continues the typed
outcome through V2.44.96, and performs one complete reserve semantic and
cross-artifact validation.  Exact durable result/model/transport/search bytes,
the reserve support/effect receipts, validator manifest, and fail-closed
execution memo are then bound by a compact certificate.  A parent validates
only ordinary-file shape, outer seals, compact receipts, exact bytes, the
certificate, and the child terminal receipt before minting an opaque
capability.  It does not recursively replay the historical semantic graph.

This is a pinned local-child trust boundary, not a signature or remote
attestation.  Runtime input remains exactly ``opaque_id`` and ``question``.
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

from . import v24490_entropy_targeted_support_search as targeted
from . import v24491_proof_carrying_targeted_support as parent_proof
from . import v24496_targeted_reserve_contradiction as reserve
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
from .v24447_third_source_entropy_to_decision import THRESHOLD_PARTITION_FIELDS
from .v24485_execution_scoped_validation_memo import ExecutionValidationMemo
from .v24486_memoized_worker_integration import validate_memo_receipt


POLICY_ID = "v24497_proof_carrying_targeted_reserve_v1"
ENVELOPE_ROLE = "v24497_targeted_reserve_envelope"
CERTIFICATE_ROLE = "v24497_targeted_reserve_validation_certificate"
CERTIFICATE_NAME = "targeted_reserve_validation_certificate.json"
COMPLETE_VALIDATOR_POLICY_ID = reserve.POLICY_ID
HEX64 = re.compile(r"[0-9a-f]{64}")
ARTIFACT_NAMES = (RESULT_NAME, MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME)
BYTE_RECEIPT_KEYS = frozenset({"name", "byte_length", "sha256"})
ENVELOPE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_envelope",
        "reserve_result",
        "model_slot_receipt_before_reserve",
        "transport_health_before_reserve",
        "search_single_shot_receipt_before_reserve",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "effect_delta_receipt",
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
        "reserve_support_receipt",
        "reserve_effect_delta_receipt",
        "validation_memo_receipt",
        "complete_reserve_semantic_and_cross_artifact_validation_ran_in_child",
        "parent_v24490_outcome_reused_without_runtime_rerun",
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
class MemoizedReserveExecution:
    outcome: reserve.IntegratedTargetedReserveOutcome
    memo_receipt: dict[str, Any]


class ValidatedReserveExecution:
    """Opaque proof that complete reserve validation returned in the child."""

    __slots__ = ("__outcome", "__envelope")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use run_single_validation_v24496_task")

    @classmethod
    def _create(
        cls,
        outcome: reserve.IntegratedTargetedReserveOutcome,
        *,
        envelope: Mapping[str, Any],
    ) -> "ValidatedReserveExecution":
        if not isinstance(outcome, reserve.IntegratedTargetedReserveOutcome):
            raise TypeError("V2.44.97 requires a reserve outcome")
        instance = object.__new__(cls)
        instance.__outcome = outcome
        instance.__envelope = copy.deepcopy(dict(envelope))
        return instance

    def _trusted_outcome(self) -> reserve.IntegratedTargetedReserveOutcome:
        return self.__outcome

    def _trusted_envelope(self) -> dict[str, Any]:
        return copy.deepcopy(self.__envelope)


class ValidatedProofCarryingReserveEnvelope:
    """Opaque capability minted only after exact-byte parent validation."""

    __slots__ = ("__counts", "__observations", "__memo")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use validate_proof_carrying_reserve_bundle")

    @classmethod
    def _create(
        cls,
        *,
        support: Mapping[str, Any],
        effect: Mapping[str, Any],
        memo: Mapping[str, Any],
        child: Mapping[str, Any],
        model: Mapping[str, Any],
        transport: Mapping[str, Any],
        search: Mapping[str, Any],
    ) -> "ValidatedProofCarryingReserveEnvelope":
        instance = object.__new__(cls)
        instance.__counts = {
            "reserve_support_receipt": copy.deepcopy(dict(support)),
            "reserve_effect_delta_receipt": copy.deepcopy(dict(effect)),
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
        raise ValueError(f"V2.44.97 {label} is not a SHA-256 digest")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _ordinary_bytes(directory: Path, name: str) -> bytes:
    if name not in {*ARTIFACT_NAMES, CERTIFICATE_NAME, CHILD_NAME}:
        raise ValueError("V2.44.97 artifact name is not allowed")
    base = directory.resolve()
    path = directory / name
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(base)
    ):
        raise RuntimeError("V2.44.97 terminal artifact is not ordinary")
    return path.read_bytes()


def _validate_exact_surface(directory: Path, expected_names: set[str]) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("V2.44.97 task directory is not ordinary")
    observed: set[str] = set()
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.44.97 task surface contains nonordinary entry")
        observed.add(path.name)
    if observed != expected_names:
        raise RuntimeError("V2.44.97 task artifact surface drifted")


def _object_from_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"V2.44.97 {label} is not UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"V2.44.97 {label} is not an object")
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
        raise ValueError("V2.44.97 byte receipt is not an object")
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
        raise ValueError("V2.44.97 byte receipt drifted")
    return copied


def _normalized_reserve_support_receipt(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V2.44.97 reserve support receipt is not an object")
    copied = copy.deepcopy(dict(value))
    partition = copied.get("threshold_failure_partition_after_reserve")
    if not isinstance(partition, Mapping) or set(partition) != set(
        THRESHOLD_PARTITION_FIELDS
    ):
        raise ValueError("V2.44.97 reserve threshold partition drifted")
    copied["threshold_failure_partition_after_reserve"] = {
        name: copy.deepcopy(partition[name]) for name in THRESHOLD_PARTITION_FIELDS
    }
    return reserve.validate_reserve_receipt(copied)


def _validate_reserve_shell(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate compact reserve identities and receipts without replay."""

    copied = copy.deepcopy(dict(value))
    mappings = (
        "parent_envelope",
        "reserve_result",
        "model_slot_receipt_before_reserve",
        "transport_health_before_reserve",
        "search_single_shot_receipt_before_reserve",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "effect_delta_receipt",
    )
    result = copied.get("reserve_result")
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
        or set(result) != reserve.RESULT_KEYS
        or result.get("artifact_version") != 1
        or result.get("role") != reserve.RESULT_ROLE
        or result.get("policy_id") != reserve.POLICY_ID
        or not isinstance(result.get("parent_result"), Mapping)
        or not isinstance(result.get("candidate_prediction"), str)
        or not isinstance(result.get("reserve_projection"), Mapping)
        or not isinstance(result.get("reserve_active_evidence_result"), Mapping)
        or not isinstance(result.get("reserve_private_state"), Mapping)
        or not isinstance(result.get("reserve_support_receipt"), Mapping)
        or not _sealed(result, "result_sha256")
    ):
        raise ValueError("V2.44.97 reserve envelope shell drifted")
    parent_shell, _, _ = parent_proof._validate_targeted_shell(
        copied["parent_envelope"]
    )
    support = _normalized_reserve_support_receipt(
        result["reserve_support_receipt"]
    )
    effect = reserve.validate_effect_delta_receipt(copied["effect_delta_receipt"])
    cap = int(copied["model_slot_receipt"].get("slot_cap", -1))
    before_model = validate_model_receipt(
        copied["model_slot_receipt_before_reserve"], expected_cap=cap
    )
    after_model = validate_model_receipt(copied["model_slot_receipt"], expected_cap=cap)
    before_transport = validate_transport_health(
        copied["transport_health_before_reserve"]
    )
    after_transport = validate_transport_health(copied["transport_health"])
    before_search = dict(copied["search_single_shot_receipt_before_reserve"])
    after_search = dict(copied["search_single_shot_receipt"])
    validate_search_receipt(before_search)
    validate_search_receipt(after_search)
    if (
        result["parent_result"] != parent_shell["targeted_result"]
        or result["reserve_support_receipt"] != support
        or copied["effect_delta_receipt"] != effect
        or before_model != parent_shell["model_slot_receipt"]
        or before_transport != parent_shell["transport_health"]
        or before_search != parent_shell["search_single_shot_receipt"]
        or after_model != copied["model_slot_receipt"]
        or after_transport != copied["transport_health"]
        or after_search != copied["search_single_shot_receipt"]
    ):
        raise ValueError("V2.44.97 compact reserve binding drifted")
    return copied, support, effect


def validate_cross_artifacts(value: Mapping[str, Any]) -> dict[str, Any]:
    copied, shell_support, shell_effect = _validate_reserve_shell(value)
    parent = parent_proof.validate_cross_artifacts(copied["parent_envelope"])
    result = reserve.validate_result(copied["reserve_result"])
    cap = int(copied["model_slot_receipt"].get("slot_cap", -1))
    before_model = validate_model_receipt(
        copied["model_slot_receipt_before_reserve"], expected_cap=cap
    )
    after_model = validate_model_receipt(copied["model_slot_receipt"], expected_cap=cap)
    before_transport = validate_transport_health(
        copied["transport_health_before_reserve"]
    )
    after_transport = validate_transport_health(copied["transport_health"])
    before_search = dict(copied["search_single_shot_receipt_before_reserve"])
    after_search = dict(copied["search_single_shot_receipt"])
    validate_search_receipt(before_search)
    validate_search_receipt(after_search)
    expected_effect = reserve.build_effect_delta_receipt(
        model_before=before_model,
        model_after=after_model,
        transport_before=before_transport,
        transport_after=after_transport,
        search_before=before_search,
        search_after=after_search,
        reserve_receipt=result["reserve_support_receipt"],
        expected_model_cap=cap,
    )
    if (
        result["parent_result"] != parent["targeted_result"]
        or result["reserve_support_receipt"] != shell_support
        or expected_effect != shell_effect
        or before_model != parent["model_slot_receipt"]
        or before_transport != parent["transport_health"]
        or before_search != parent["search_single_shot_receipt"]
    ):
        raise ValueError("V2.44.97 complete cross-artifact validation drifted")
    return copied


def _unvalidated_envelope(
    parent: parent_proof.ValidatedTargetedExecution,
    outcome: reserve.IntegratedTargetedReserveOutcome,
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "parent_envelope": parent_proof.build_envelope_from_validated_execution(parent),
        "reserve_result": copy.deepcopy(outcome.reserve_result),
        "model_slot_receipt_before_reserve": copy.deepcopy(
            outcome.model_slot_receipt_before_reserve
        ),
        "transport_health_before_reserve": copy.deepcopy(
            outcome.transport_health_before_reserve
        ),
        "search_single_shot_receipt_before_reserve": copy.deepcopy(
            outcome.search_single_shot_receipt_before_reserve
        ),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "search_single_shot_receipt": copy.deepcopy(
            outcome.search_single_shot_receipt
        ),
        "effect_delta_receipt": copy.deepcopy(outcome.effect_delta_receipt),
        "private_task_content_present": True,
        "private_task_content_emitted_to_public_aggregate": False,
        "credential_or_privileged_evaluator_content_present": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    return value


def run_single_validation_v24496_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
) -> ValidatedReserveExecution:
    parent = parent_proof.run_single_validation_v24490_task(
        task,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    outcome = reserve._run_reserve_stage_from_v24490_outcome(
        parent._trusted_outcome(), model=model, search=search
    )
    envelope = _unvalidated_envelope(parent, outcome)
    validated = validate_cross_artifacts(envelope)
    return ValidatedReserveExecution._create(outcome, envelope=validated)


def build_envelope_from_validated_execution(
    validated: ValidatedReserveExecution,
) -> dict[str, Any]:
    if not isinstance(validated, ValidatedReserveExecution):
        raise TypeError("V2.44.97 requires validated reserve execution")
    shell, _, _ = _validate_reserve_shell(validated._trusted_envelope())
    return shell


def build_terminal_certificate(
    directory: Path,
    completed: ValidatedReserveExecution,
    *,
    memo_receipt: Mapping[str, Any],
    validator_manifest_sha256: str,
    expected_artifacts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(completed, ValidatedReserveExecution):
        raise TypeError("V2.44.97 certificate requires validated execution")
    manifest = _digest(validator_manifest_sha256, "validator manifest")
    memo = validate_memo_receipt(memo_receipt)
    _validate_exact_surface(directory, set(ARTIFACT_NAMES))
    if set(expected_artifacts) != set(ARTIFACT_NAMES):
        raise ValueError("V2.44.97 expected artifact vector drifted")
    artifacts = {name: _read_object(directory, name) for name in ARTIFACT_NAMES}
    if any(
        artifacts[name][1] != dict(expected_artifacts[name])
        for name in ARTIFACT_NAMES
    ):
        raise ValueError("V2.44.97 durable bytes drifted from writer input")
    envelope, support, effect = _validate_reserve_shell(artifacts[RESULT_NAME][1])
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
        or support
        != _normalized_reserve_support_receipt(
            outcome.reserve_result["reserve_support_receipt"]
        )
        or effect
        != reserve.validate_effect_delta_receipt(outcome.effect_delta_receipt)
    ):
        raise ValueError("V2.44.97 durable artifacts drifted from validated outcome")
    value = {
        "artifact_version": 1,
        "role": CERTIFICATE_ROLE,
        "policy_id": POLICY_ID,
        "producer_policy_id": reserve.POLICY_ID,
        "complete_validator_policy_id": COMPLETE_VALIDATOR_POLICY_ID,
        "validator_manifest_sha256": manifest,
        "artifact_byte_receipts": {
            name: _byte_receipt(name, artifacts[name][0]) for name in ARTIFACT_NAMES
        },
        "reserve_support_receipt": support,
        "reserve_effect_delta_receipt": effect,
        "validation_memo_receipt": copy.deepcopy(memo),
        "complete_reserve_semantic_and_cross_artifact_validation_ran_in_child": True,
        "parent_v24490_outcome_reused_without_runtime_rerun": True,
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
    envelope, support, effect = _validate_reserve_shell(artifacts[RESULT_NAME][1])
    cap = int(envelope["model_slot_receipt"].get("slot_cap", -1))
    model = validate_model_receipt(artifacts[MODEL_NAME][1], expected_cap=cap)
    transport = validate_transport_health(artifacts[TRANSPORT_NAME][1])
    search = dict(artifacts[SEARCH_NAME][1])
    validate_search_receipt(search)
    memo = copied.get("validation_memo_receipt")
    if (
        set(copied) != CERTIFICATE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != CERTIFICATE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("producer_policy_id") != reserve.POLICY_ID
        or copied.get("complete_validator_policy_id")
        != COMPLETE_VALIDATOR_POLICY_ID
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
        or _normalized_reserve_support_receipt(
            copied.get("reserve_support_receipt", {})
        )
        != support
        or reserve.validate_effect_delta_receipt(
            copied.get("reserve_effect_delta_receipt", {})
        )
        != effect
        or not isinstance(memo, Mapping)
        or validate_memo_receipt(memo) != memo
        or envelope["model_slot_receipt"] != model
        or envelope["transport_health"] != transport
        or envelope["search_single_shot_receipt"] != search
        or any(
            copied.get(name) is not True
            for name in (
                "complete_reserve_semantic_and_cross_artifact_validation_ran_in_child",
                "parent_v24490_outcome_reused_without_runtime_rerun",
                "certificate_created_after_exact_terminal_artifacts",
                "independent_terminal_receipts_equal_envelope",
                "validation_memo_fail_closed_before_terminal_success",
                "parent_must_not_recursively_recompute_historical_pipeline",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "certificate_is_independently_signed",
                "certificate_is_remote_attestation",
                "malicious_child_resistance_claimed",
                "task_question_opaque_id_query_url_page_source_value_prediction_candidate_response_or_credential_emitted",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder",
            )
        )
        or not _sealed(copied, "certificate_payload_sha256")
    ):
        raise ValueError("V2.44.97 reserve terminal certificate drifted")
    return copied


def validate_proof_carrying_reserve_bundle(
    value: Mapping[str, Any],
    *,
    directory: Path,
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
) -> ValidatedProofCarryingReserveEnvelope:
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
        raise ValueError("V2.44.97 child terminal receipt is not successful")
    _, certificate_value = _read_object(directory, CERTIFICATE_NAME)
    certificate = validate_terminal_certificate(
        certificate_value,
        directory=directory,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )
    _, persisted = _read_object(directory, RESULT_NAME)
    envelope, support, effect = _validate_reserve_shell(value)
    if dict(value) != persisted:
        raise ValueError("V2.44.97 supplied result differs from durable result")
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
        or support != certificate["reserve_support_receipt"]
        or effect != certificate["reserve_effect_delta_receipt"]
        or envelope["model_slot_receipt"] != model
        or envelope["transport_health"] != transport
        or envelope["search_single_shot_receipt"] != search
    ):
        raise ValueError("V2.44.97 result/certificate binding drifted")
    return ValidatedProofCarryingReserveEnvelope._create(
        support=support,
        effect=effect,
        memo=memo,
        child=child,
        model=model,
        transport=transport,
        search=search,
    )


def run_and_persist_memoized_reserve_task(
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
) -> MemoizedReserveExecution:
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
            validated = run_single_validation_v24496_task(
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
    for name in (MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME, RESULT_NAME):
        writer(name, artifacts[name])
    certificate = build_terminal_certificate(
        directory,
        validated,
        memo_receipt=memo_receipt,
        validator_manifest_sha256=validator_manifest_sha256,
        expected_artifacts=artifacts,
    )
    writer(CERTIFICATE_NAME, certificate)
    return MemoizedReserveExecution(outcome=outcome, memo_receipt=memo_receipt)


def run_memoized_reserve_worker(
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
) -> MemoizedReserveExecution:
    completed: MemoizedReserveExecution | None = None

    def action() -> None:
        nonlocal completed
        completed = run_and_persist_memoized_reserve_task(
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
        raise RuntimeError("V2.44.97 memoized reserve outcome is absent")
    return completed


PROJECTION_CHECKS = (
    "conversion_funnel",
    "incremental_credit",
    "effect_conservation",
    "memo_fail_closed",
    "single_validation",
)
PROJECTION_COUNT_FIELDS = (
    "targeted_plan_present",
    "targeted_discovered_source_count",
    "targeted_selected_source_count_before_reserve",
    "targeted_usable_page_count_before_reserve",
    "targeted_new_observation_count_before_reserve",
    "reserve_candidate_source_count",
    "reserve_selected_source_count",
    "reserve_alternative_visible_source_count",
    "reserve_alternative_blind_source_count",
    "reserve_usable_page_count",
    "reserve_new_observation_count",
    "reserve_supporting_target_observation_count",
    "reserve_conflicting_target_observation_count",
    "reserve_other_observation_count",
    "total_targeted_selected_source_count",
    "total_targeted_usable_page_count",
    "total_targeted_new_observation_count",
    "safe_change_count_before_reserve",
    "safe_change_count_after_reserve",
    "safe_change_improvement_count",
    "safe_change_regression_count",
    "additional_fetch_attempts",
    "additional_fetch_effects",
    "additional_model_acquisitions",
    "validation_memo_misses",
    "validation_memo_hits",
    "validation_memo_mismatches",
)
PROJECTION_NUMERIC_FIELDS = (
    "decision_credit_total_nats_before_reserve",
    "decision_credit_total_nats_after_reserve",
    "decision_credit_gain_nats",
    "decision_credit_regression_nats",
)
PROJECTION_KEYS = frozenset(
    {
        "ordinal",
        *PROJECTION_COUNT_FIELDS,
        *PROJECTION_NUMERIC_FIELDS,
        "threshold_failure_partition_after_reserve",
        "checks",
        "passed",
        "projection_consumed_only_validated_capability",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
)
AGGREGATE_KEYS = frozenset(
    {
        "selected",
        "exact_ordinal_vector",
        "passed_tasks",
        "failed_tasks",
        "target_plan_tasks",
        "reserve_engaged_tasks",
        "reserve_usable_page_tasks",
        "reserve_new_observation_tasks",
        "reserve_supporting_observation_tasks",
        "reserve_conflicting_observation_tasks",
        "safe_change_improvement_tasks",
        "safe_change_regression_tasks",
        "positive_decision_credit_gain_tasks",
        "decision_credit_regression_tasks",
        "total_reserve_selected_source_count",
        "total_reserve_usable_page_count",
        "total_reserve_new_observation_count",
        "total_reserve_supporting_target_observation_count",
        "total_reserve_conflicting_target_observation_count",
        "total_additional_fetch_effects",
        "total_additional_model_acquisitions",
        "total_validation_memo_misses",
        "total_validation_memo_hits",
        "total_decision_credit_gain_nats",
        "total_decision_credit_regression_nats",
        "all_effects_conserved",
        "all_memos_fail_closed",
        "all_single_validations_attested",
        "all_projections_consumed_validated_capabilities",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
)


def _projection_count(value: Mapping[str, Any], name: str) -> int:
    item = value.get(name)
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        raise ValueError(f"V2.44.97 invalid projection count: {name}")
    return item


def _projection_number(value: Mapping[str, Any], name: str) -> float:
    item = value.get(name)
    if (
        isinstance(item, bool)
        or not isinstance(item, (int, float))
        or not math.isfinite(float(item))
        or float(item) < 0
    ):
        raise ValueError(f"V2.44.97 invalid projection number: {name}")
    return float(item)


def _projection_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "conversion_funnel": (
            int(value.get("targeted_selected_source_count_before_reserve", -1))
            + int(value.get("reserve_selected_source_count", -1))
            == int(value.get("total_targeted_selected_source_count", -2))
            and int(value.get("targeted_usable_page_count_before_reserve", -1))
            + int(value.get("reserve_usable_page_count", -1))
            == int(value.get("total_targeted_usable_page_count", -2))
            and int(value.get("targeted_new_observation_count_before_reserve", -1))
            + int(value.get("reserve_new_observation_count", -1))
            == int(value.get("total_targeted_new_observation_count", -2))
        ),
        "incremental_credit": (
            math.isclose(
                float(value.get("decision_credit_gain_nats", -1)),
                max(
                    0.0,
                    float(value.get("decision_credit_total_nats_after_reserve", -1))
                    - float(value.get("decision_credit_total_nats_before_reserve", -1)),
                ),
                abs_tol=1e-12,
            )
            and (
                float(value.get("decision_credit_gain_nats", -1)) == 0
                or int(value.get("safe_change_improvement_count", 0)) > 0
            )
        ),
        "effect_conservation": (
            int(value.get("additional_fetch_attempts", -1))
            == int(value.get("reserve_selected_source_count", -2))
            == int(value.get("additional_fetch_effects", -3))
            and int(value.get("additional_model_acquisitions", -1)) == 0
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
    ordinal: int, capability: ValidatedProofCarryingReserveEnvelope
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(capability, ValidatedProofCarryingReserveEnvelope)
    ):
        raise TypeError("V2.44.97 projection requires ordinal and capability")
    receipts = capability.counts_only_receipts()
    support = _normalized_reserve_support_receipt(
        receipts["reserve_support_receipt"]
    )
    effect = reserve.validate_effect_delta_receipt(
        receipts["reserve_effect_delta_receipt"]
    )
    memo = validate_memo_receipt(capability.content_free_memo_receipt())
    support_fields = tuple(
        name
        for name in PROJECTION_COUNT_FIELDS
        if name
        not in {
            "additional_fetch_attempts",
            "additional_fetch_effects",
            "additional_model_acquisitions",
            "validation_memo_misses",
            "validation_memo_hits",
            "validation_memo_mismatches",
        }
    )
    value = {
        "ordinal": ordinal,
        **{name: int(support[name]) for name in support_fields},
        "additional_fetch_attempts": int(effect["additional_fetch_attempts"]),
        "additional_fetch_effects": int(effect["additional_fetch_effects"]),
        "additional_model_acquisitions": int(effect["additional_model_acquisitions"]),
        "validation_memo_misses": int(memo["total_misses"]),
        "validation_memo_hits": int(memo["total_hits"]),
        "validation_memo_mismatches": int(memo["total_mismatches"]),
        **{name: float(support[name]) for name in PROJECTION_NUMERIC_FIELDS},
        "threshold_failure_partition_after_reserve": {
            name: int(support["threshold_failure_partition_after_reserve"][name])
            for name in THRESHOLD_PARTITION_FIELDS
        },
        "projection_consumed_only_validated_capability": True,
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }
    value["checks"] = _projection_checks(value)
    value["passed"] = all(value["checks"].values())
    return validate_task_projection(value)


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    partition = copied.get("threshold_failure_partition_after_reserve")
    checks = copied.get("checks")
    if (
        set(copied) != PROJECTION_KEYS
        or isinstance(copied.get("ordinal"), bool)
        or not isinstance(copied.get("ordinal"), int)
        or copied["ordinal"] < 1
        or any(_projection_count(copied, name) < 0 for name in PROJECTION_COUNT_FIELDS)
        or any(_projection_number(copied, name) < 0 for name in PROJECTION_NUMERIC_FIELDS)
        or not isinstance(partition, Mapping)
        or tuple(partition) != THRESHOLD_PARTITION_FIELDS
        or any(
            isinstance(partition[name], bool)
            or not isinstance(partition[name], int)
            or partition[name] < 0
            for name in THRESHOLD_PARTITION_FIELDS
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
        raise ValueError("V2.44.97 capability projection drifted")
    return copied


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
        raise ValueError("V2.44.97 aggregate selection drifted")
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
        "reserve_new_observation_tasks": sum(
            row["reserve_new_observation_count"] > 0 for row in rows
        ),
        "reserve_supporting_observation_tasks": sum(
            row["reserve_supporting_target_observation_count"] > 0
            for row in rows
        ),
        "reserve_conflicting_observation_tasks": sum(
            row["reserve_conflicting_target_observation_count"] > 0
            for row in rows
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
        "total_reserve_selected_source_count": sum(
            row["reserve_selected_source_count"] for row in rows
        ),
        "total_reserve_usable_page_count": sum(
            row["reserve_usable_page_count"] for row in rows
        ),
        "total_reserve_new_observation_count": sum(
            row["reserve_new_observation_count"] for row in rows
        ),
        "total_reserve_supporting_target_observation_count": sum(
            row["reserve_supporting_target_observation_count"] for row in rows
        ),
        "total_reserve_conflicting_target_observation_count": sum(
            row["reserve_conflicting_target_observation_count"] for row in rows
        ),
        "total_additional_fetch_effects": sum(
            row["additional_fetch_effects"] for row in rows
        ),
        "total_additional_model_acquisitions": sum(
            row["additional_model_acquisitions"] for row in rows
        ),
        "total_validation_memo_misses": sum(
            row["validation_memo_misses"] for row in rows
        ),
        "total_validation_memo_hits": sum(
            row["validation_memo_hits"] for row in rows
        ),
        "total_decision_credit_gain_nats": sum(
            row["decision_credit_gain_nats"] for row in rows
        ),
        "total_decision_credit_regression_nats": sum(
            row["decision_credit_regression_nats"] for row in rows
        ),
        "all_effects_conserved": all(
            row["checks"]["effect_conservation"] for row in rows
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
    count_names = tuple(
        name
        for name in AGGREGATE_KEYS
        if name
        not in {
            "exact_ordinal_vector",
            "total_decision_credit_gain_nats",
            "total_decision_credit_regression_nats",
            "all_effects_conserved",
            "all_memos_fail_closed",
            "all_single_validations_attested",
            "all_projections_consumed_validated_capabilities",
            "private_task_content_emitted",
            "privileged_evaluator_content_read",
        }
    )
    task_counts = (
        "passed_tasks",
        "failed_tasks",
        "target_plan_tasks",
        "reserve_engaged_tasks",
        "reserve_usable_page_tasks",
        "reserve_new_observation_tasks",
        "reserve_supporting_observation_tasks",
        "reserve_conflicting_observation_tasks",
        "safe_change_improvement_tasks",
        "safe_change_regression_tasks",
        "positive_decision_credit_gain_tasks",
        "decision_credit_regression_tasks",
    )
    booleans = (
        "all_effects_conserved",
        "all_memos_fail_closed",
        "all_single_validations_attested",
        "all_projections_consumed_validated_capabilities",
    )
    if (
        set(copied) != AGGREGATE_KEYS
        or any(_projection_count(copied, name) < 0 for name in count_names)
        or copied["selected"] < 1
        or copied["passed_tasks"] + copied["failed_tasks"] != copied["selected"]
        or any(copied[name] > copied["selected"] for name in task_counts)
        or copied["reserve_usable_page_tasks"] > copied["reserve_engaged_tasks"]
        or copied["reserve_new_observation_tasks"]
        > copied["reserve_usable_page_tasks"]
        or copied["safe_change_improvement_tasks"]
        > copied["reserve_new_observation_tasks"]
        or copied["positive_decision_credit_gain_tasks"]
        > copied["safe_change_improvement_tasks"]
        or copied["total_reserve_usable_page_count"]
        > copied["total_reserve_selected_source_count"]
        or copied["total_reserve_supporting_target_observation_count"]
        + copied["total_reserve_conflicting_target_observation_count"]
        > copied["total_reserve_new_observation_count"]
        or copied["total_additional_fetch_effects"]
        != copied["total_reserve_selected_source_count"]
        or copied["total_additional_model_acquisitions"] != 0
        or _projection_number(copied, "total_decision_credit_gain_nats") < 0
        or _projection_number(copied, "total_decision_credit_regression_nats") < 0
        or (copied["total_decision_credit_gain_nats"] > 0)
        is not (copied["positive_decision_credit_gain_tasks"] > 0)
        or (copied["total_decision_credit_regression_nats"] > 0)
        is not (copied["decision_credit_regression_tasks"] > 0)
        or copied.get("exact_ordinal_vector") is not True
        or any(not isinstance(copied.get(name), bool) for name in booleans)
        or copied.get("private_task_content_emitted") is not False
        or copied.get("privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.44.97 capability aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "ARTIFACT_NAMES",
    "CERTIFICATE_NAME",
    "CERTIFICATE_ROLE",
    "ENVELOPE_ROLE",
    "MemoizedReserveExecution",
    "POLICY_ID",
    "ValidatedProofCarryingReserveEnvelope",
    "ValidatedReserveExecution",
    "aggregate_projections",
    "build_envelope_from_validated_execution",
    "build_terminal_certificate",
    "run_and_persist_memoized_reserve_task",
    "run_memoized_reserve_worker",
    "run_single_validation_v24496_task",
    "task_projection",
    "validate_cross_artifacts",
    "validate_aggregate",
    "validate_proof_carrying_reserve_bundle",
    "validate_task_projection",
    "validate_terminal_certificate",
]
