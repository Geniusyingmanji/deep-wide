"""Proof-carrying integration for entropy-targeted support search.

V2.44.90 proved synthetically that one source-disjoint targeted page can
convert positive epistemic information gain into a safe output change without
relaxing the frozen source-count, posterior, margin, or leave-one-out credit
rules.  This module supplies the missing execution boundary before any new
external population is allowed:

* the unchanged V2.44.57 parent is completely validated once;
* V2.44.90 continues from that typed parent outcome instead of rerunning it;
* one complete targeted semantic and cross-artifact validation runs in the
  trusted child under the execution-scoped sealed-validation memo;
* four exact terminal artifacts and a content-free memo receipt are bound by
  a byte certificate; and
* the parent validates only the exact ordinary-file surface, outer seals,
  compact receipts, byte bindings, validator manifest, and child terminal
  receipt before minting an opaque capability.

The parent does not recursively replay the historical semantic pipeline.
This is a pinned local-child trust boundary, not a signature, remote
attestation, or defence against a malicious child.  Runtime input remains
strictly label blind and no evaluator-side metadata is available here.
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

from . import v24457_adaptive_entropy_support as adaptive
from . import v24490_entropy_targeted_support_search as targeted
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
from .v24459_proof_carrying_adaptive_entropy_support import (
    _validate_shells as validate_adaptive_shell,
)
from .v24464_single_validation_adaptive_persistence import (
    ValidatedAdaptiveExecution,
    build_envelope_from_validated_execution as build_adaptive_envelope,
    run_single_validation_v24457_task,
)
from .v24485_execution_scoped_validation_memo import ExecutionValidationMemo
from .v24486_memoized_worker_integration import validate_memo_receipt


POLICY_ID = "v24491_proof_carrying_entropy_targeted_support_v1"
ENVELOPE_ROLE = "v24491_entropy_targeted_support_envelope"
CERTIFICATE_ROLE = "v24491_entropy_targeted_validation_certificate"
CERTIFICATE_NAME = "entropy_targeted_validation_certificate.json"
COMPLETE_VALIDATOR_POLICY_ID = targeted.POLICY_ID
HEX64 = re.compile(r"[0-9a-f]{64}")
ARTIFACT_NAMES = (RESULT_NAME, MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME)
BYTE_RECEIPT_KEYS = frozenset({"name", "byte_length", "sha256"})
ENVELOPE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_envelope",
        "targeted_result",
        "model_slot_receipt_before_targeted_support",
        "transport_health_before_targeted_support",
        "search_single_shot_receipt_before_targeted_support",
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
        "targeted_support_receipt",
        "targeted_effect_delta_receipt",
        "validation_memo_receipt",
        "complete_targeted_semantic_and_cross_artifact_validation_ran_in_child",
        "parent_v24457_outcome_reused_without_runtime_rerun",
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
class MemoizedTargetedExecution:
    outcome: targeted.IntegratedEntropyTargetedSupportOutcome
    memo_receipt: dict[str, Any]


class ValidatedTargetedExecution:
    """Opaque in-process proof that the complete targeted validator returned."""

    __slots__ = ("__outcome", "__envelope")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use run_single_validation_v24490_task")

    @classmethod
    def _create(
        cls,
        outcome: targeted.IntegratedEntropyTargetedSupportOutcome,
        *,
        envelope: Mapping[str, Any],
    ) -> "ValidatedTargetedExecution":
        if not isinstance(
            outcome, targeted.IntegratedEntropyTargetedSupportOutcome
        ):
            raise TypeError("V2.44.91 requires a targeted outcome")
        instance = object.__new__(cls)
        instance.__outcome = outcome
        instance.__envelope = copy.deepcopy(dict(envelope))
        return instance

    def _trusted_outcome(self) -> targeted.IntegratedEntropyTargetedSupportOutcome:
        return self.__outcome

    def _trusted_envelope(self) -> dict[str, Any]:
        return copy.deepcopy(self.__envelope)


class ValidatedProofCarryingTargetedEnvelope:
    """Opaque capability minted only after exact-byte parent validation."""

    __slots__ = ("__counts", "__observations", "__memo")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use validate_proof_carrying_targeted_bundle")

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
    ) -> "ValidatedProofCarryingTargetedEnvelope":
        instance = object.__new__(cls)
        instance.__counts = {
            "targeted_support_receipt": copy.deepcopy(dict(support)),
            "targeted_effect_delta_receipt": copy.deepcopy(dict(effect)),
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
        raise ValueError(f"V2.44.91 {label} is not a SHA-256 digest")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _ordinary_bytes(directory: Path, name: str) -> bytes:
    if name not in {*ARTIFACT_NAMES, CERTIFICATE_NAME, CHILD_NAME}:
        raise ValueError("V2.44.91 artifact name is not allowed")
    base = directory.resolve()
    path = directory / name
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(base)
    ):
        raise RuntimeError("V2.44.91 terminal artifact is not ordinary")
    return path.read_bytes()


def _validate_exact_surface(directory: Path, expected_names: set[str]) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("V2.44.91 task directory is not ordinary")
    observed: set[str] = set()
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.44.91 task surface contains nonordinary entry")
        observed.add(path.name)
    if observed != expected_names:
        raise RuntimeError("V2.44.91 task artifact surface drifted")


def _object_from_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"V2.44.91 {label} is not UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"V2.44.91 {label} is not an object")
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
        raise ValueError("V2.44.91 byte receipt is not an object")
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
        raise ValueError("V2.44.91 terminal byte receipt drifted")
    return copied


def _normalized_targeted_support_receipt(value: object) -> dict[str, Any]:
    """Restore the frozen semantic field order after sorted JSON persistence."""

    if not isinstance(value, Mapping):
        raise ValueError("V2.44.91 targeted support receipt is not an object")
    copied = copy.deepcopy(dict(value))
    partition = copied.get("threshold_failure_partition_after_targeted_search")
    if not isinstance(partition, Mapping) or set(partition) != set(
        THRESHOLD_PARTITION_FIELDS
    ):
        raise ValueError("V2.44.91 targeted threshold partition drifted")
    copied["threshold_failure_partition_after_targeted_search"] = {
        name: copy.deepcopy(partition[name])
        for name in THRESHOLD_PARTITION_FIELDS
    }
    return targeted.validate_recovery_receipt(copied)


def _validate_targeted_shell(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate compact identities and receipts without semantic replay."""

    copied = copy.deepcopy(dict(value))
    mappings = (
        "parent_envelope",
        "targeted_result",
        "model_slot_receipt_before_targeted_support",
        "transport_health_before_targeted_support",
        "search_single_shot_receipt_before_targeted_support",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "effect_delta_receipt",
    )
    result = copied.get("targeted_result")
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
        or set(result) != targeted.RESULT_KEYS
        or result.get("artifact_version") != 1
        or result.get("role") != targeted.RESULT_ROLE
        or result.get("policy_id") != targeted.POLICY_ID
        or not isinstance(result.get("parent_result"), Mapping)
        or not isinstance(result.get("candidate_prediction"), str)
        or not isinstance(result.get("targeted_projection"), Mapping)
        or not isinstance(result.get("targeted_active_evidence_result"), Mapping)
        or not isinstance(result.get("targeted_private_state"), Mapping)
        or not isinstance(result.get("targeted_support_receipt"), Mapping)
        or not _sealed(result, "result_sha256")
    ):
        raise ValueError("V2.44.91 targeted envelope identity shell drifted")

    parent_shell, _, _ = validate_adaptive_shell(copied["parent_envelope"])
    support = _normalized_targeted_support_receipt(
        result["targeted_support_receipt"]
    )
    effect = targeted.validate_effect_delta_receipt(copied["effect_delta_receipt"])
    cap = int(copied["model_slot_receipt"].get("slot_cap", -1))
    before_model = validate_model_receipt(
        copied["model_slot_receipt_before_targeted_support"], expected_cap=cap
    )
    after_model = validate_model_receipt(copied["model_slot_receipt"], expected_cap=cap)
    before_transport = validate_transport_health(
        copied["transport_health_before_targeted_support"]
    )
    after_transport = validate_transport_health(copied["transport_health"])
    before_search = dict(copied["search_single_shot_receipt_before_targeted_support"])
    after_search = dict(copied["search_single_shot_receipt"])
    validate_search_receipt(before_search)
    validate_search_receipt(after_search)
    if (
        result["parent_result"] != parent_shell["adaptive_result"]
        or result["targeted_support_receipt"] != support
        or copied["effect_delta_receipt"] != effect
        or before_model != parent_shell["model_slot_receipt"]
        or before_transport != parent_shell["transport_health"]
        or before_search != parent_shell["search_single_shot_receipt"]
        or after_model != copied["model_slot_receipt"]
        or after_transport != copied["transport_health"]
        or after_search != copied["search_single_shot_receipt"]
    ):
        raise ValueError("V2.44.91 targeted compact receipt binding drifted")
    return copied, support, effect


def validate_cross_artifacts(value: Mapping[str, Any]) -> dict[str, Any]:
    """Run the complete targeted semantic and cross-artifact validator."""

    copied, shell_support, shell_effect = _validate_targeted_shell(value)
    parent = adaptive.validate_envelope(copied["parent_envelope"])
    result = targeted.validate_result(copied["targeted_result"])
    effect = targeted.validate_effect_delta_receipt(copied["effect_delta_receipt"])
    cap = int(copied["model_slot_receipt"].get("slot_cap", -1))
    before_model = validate_model_receipt(
        copied["model_slot_receipt_before_targeted_support"], expected_cap=cap
    )
    after_model = validate_model_receipt(copied["model_slot_receipt"], expected_cap=cap)
    before_transport = validate_transport_health(
        copied["transport_health_before_targeted_support"]
    )
    after_transport = validate_transport_health(copied["transport_health"])
    before_search = dict(copied["search_single_shot_receipt_before_targeted_support"])
    after_search = dict(copied["search_single_shot_receipt"])
    validate_search_receipt(before_search)
    validate_search_receipt(after_search)
    private = result["targeted_private_state"]
    expected_effect = targeted.build_effect_delta_receipt(
        model_before=before_model,
        model_after=after_model,
        transport_before=before_transport,
        transport_after=after_transport,
        search_before=before_search,
        search_after=after_search,
        union_receipt=private["targeted_union_receipt"],
        plan=private["target_plan"],
        expected_model_cap=cap,
    )
    if (
        result["parent_result"] != parent["adaptive_result"]
        or result["targeted_support_receipt"] != shell_support
        or effect != shell_effect
        or effect != expected_effect
        or before_model != parent["model_slot_receipt"]
        or before_transport != parent["transport_health"]
        or before_search != parent["search_single_shot_receipt"]
    ):
        raise ValueError("V2.44.91 complete cross-artifact validation drifted")
    return copied


def _unvalidated_envelope(
    parent: ValidatedAdaptiveExecution,
    outcome: targeted.IntegratedEntropyTargetedSupportOutcome,
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "parent_envelope": build_adaptive_envelope(parent),
        "targeted_result": copy.deepcopy(outcome.targeted_result),
        "model_slot_receipt_before_targeted_support": copy.deepcopy(
            outcome.model_slot_receipt_before_targeted_support
        ),
        "transport_health_before_targeted_support": copy.deepcopy(
            outcome.transport_health_before_targeted_support
        ),
        "search_single_shot_receipt_before_targeted_support": copy.deepcopy(
            outcome.search_single_shot_receipt_before_targeted_support
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


def run_single_validation_v24490_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
) -> ValidatedTargetedExecution:
    """Validate V2.44.57 once, continue V2.44.90, then validate once."""

    parent = run_single_validation_v24457_task(
        task,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    outcome = targeted._run_targeted_stage_from_v24457_outcome(
        parent._trusted_outcome(), model=model, search=search
    )
    envelope = _unvalidated_envelope(parent, outcome)
    validated = validate_cross_artifacts(envelope)
    return ValidatedTargetedExecution._create(outcome, envelope=validated)


def build_envelope_from_validated_execution(
    validated: ValidatedTargetedExecution,
) -> dict[str, Any]:
    if not isinstance(validated, ValidatedTargetedExecution):
        raise TypeError("V2.44.91 requires validated targeted execution")
    value = validated._trusted_envelope()
    shell, _, _ = _validate_targeted_shell(value)
    return shell


def build_terminal_certificate(
    directory: Path,
    completed: ValidatedTargetedExecution,
    *,
    memo_receipt: Mapping[str, Any],
    validator_manifest_sha256: str,
    expected_artifacts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind exact durable artifacts after full child validation and memo exit."""

    if not isinstance(completed, ValidatedTargetedExecution):
        raise TypeError("V2.44.91 certificate requires validated execution")
    manifest = _digest(validator_manifest_sha256, "validator manifest")
    memo = validate_memo_receipt(memo_receipt)
    _validate_exact_surface(directory, set(ARTIFACT_NAMES))
    if set(expected_artifacts) != set(ARTIFACT_NAMES):
        raise ValueError("V2.44.91 expected artifact vector drifted")
    artifacts = {name: _read_object(directory, name) for name in ARTIFACT_NAMES}
    if any(
        artifacts[name][1] != dict(expected_artifacts[name])
        for name in ARTIFACT_NAMES
    ):
        raise ValueError("V2.44.91 durable bytes drifted from writer input")
    envelope, support, effect = _validate_targeted_shell(artifacts[RESULT_NAME][1])
    outcome = completed._trusted_outcome()
    trusted_envelope = completed._trusted_envelope()
    model = validate_model_receipt(
        artifacts[MODEL_NAME][1],
        expected_cap=int(outcome.model_slot_receipt.get("slot_cap", -1)),
    )
    transport = validate_transport_health(artifacts[TRANSPORT_NAME][1])
    search = dict(artifacts[SEARCH_NAME][1])
    validate_search_receipt(search)
    if (
        envelope != trusted_envelope
        or model != outcome.model_slot_receipt
        or transport != outcome.transport_health
        or search != outcome.search_single_shot_receipt
        or envelope["model_slot_receipt"] != model
        or envelope["transport_health"] != transport
        or envelope["search_single_shot_receipt"] != search
        or support
        != _normalized_targeted_support_receipt(
            outcome.targeted_result["targeted_support_receipt"]
        )
        or effect
        != targeted.validate_effect_delta_receipt(outcome.effect_delta_receipt)
    ):
        raise ValueError("V2.44.91 durable artifacts drifted from validated outcome")
    value = {
        "artifact_version": 1,
        "role": CERTIFICATE_ROLE,
        "policy_id": POLICY_ID,
        "producer_policy_id": targeted.POLICY_ID,
        "complete_validator_policy_id": COMPLETE_VALIDATOR_POLICY_ID,
        "validator_manifest_sha256": manifest,
        "artifact_byte_receipts": {
            name: _byte_receipt(name, artifacts[name][0]) for name in ARTIFACT_NAMES
        },
        "targeted_support_receipt": support,
        "targeted_effect_delta_receipt": effect,
        "validation_memo_receipt": copy.deepcopy(memo),
        "complete_targeted_semantic_and_cross_artifact_validation_ran_in_child": True,
        "parent_v24457_outcome_reused_without_runtime_rerun": True,
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
    envelope, support, effect = _validate_targeted_shell(artifacts[RESULT_NAME][1])
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
        or copied.get("producer_policy_id") != targeted.POLICY_ID
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
        or _normalized_targeted_support_receipt(
            copied.get("targeted_support_receipt", {})
        )
        != support
        or targeted.validate_effect_delta_receipt(
            copied.get("targeted_effect_delta_receipt", {})
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
                "complete_targeted_semantic_and_cross_artifact_validation_ran_in_child",
                "parent_v24457_outcome_reused_without_runtime_rerun",
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
        raise ValueError("V2.44.91 targeted terminal certificate drifted")
    return copied


def validate_proof_carrying_targeted_bundle(
    value: Mapping[str, Any],
    *,
    directory: Path,
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
) -> ValidatedProofCarryingTargetedEnvelope:
    """Validate exact bytes and compact invariants, then mint a capability."""

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
        raise ValueError("V2.44.91 child terminal receipt is not successful")
    _, certificate_value = _read_object(directory, CERTIFICATE_NAME)
    certificate = validate_terminal_certificate(
        certificate_value,
        directory=directory,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )
    _, persisted = _read_object(directory, RESULT_NAME)
    envelope, support, effect = _validate_targeted_shell(value)
    if dict(value) != persisted:
        raise ValueError("V2.44.91 supplied result differs from durable result")
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
        or support != certificate["targeted_support_receipt"]
        or effect != certificate["targeted_effect_delta_receipt"]
        or envelope["model_slot_receipt"] != model
        or envelope["transport_health"] != transport
        or envelope["search_single_shot_receipt"] != search
    ):
        raise ValueError("V2.44.91 result/certificate binding drifted")
    return ValidatedProofCarryingTargetedEnvelope._create(
        support=support,
        effect=effect,
        memo=memo,
        child=child,
        model=model,
        transport=transport,
        search=search,
    )


def run_and_persist_memoized_targeted_task(
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
) -> MemoizedTargetedExecution:
    """Run one targeted worker body and persist proof only after memo exit."""

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
            validated = run_single_validation_v24490_task(
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
    return MemoizedTargetedExecution(outcome=outcome, memo_receipt=memo_receipt)


def run_memoized_targeted_worker(
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
) -> MemoizedTargetedExecution:
    """Publish the child terminal receipt only after proof and memo succeed."""

    completed: MemoizedTargetedExecution | None = None

    def action() -> None:
        nonlocal completed
        completed = run_and_persist_memoized_targeted_task(
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
        raise RuntimeError("V2.44.91 memoized targeted outcome is absent")
    return completed


PROJECTION_CHECKS = (
    "targeted_mechanism",
    "entropy_decision_credit",
    "effect_conservation",
    "memo_fail_closed",
    "single_validation",
)
PROJECTION_COUNT_FIELDS = (
    "targeted_cell_count",
    "targeted_selected_target_count",
    "targeted_logical_query_count",
    "targeted_search_batch_count",
    "targeted_discovered_source_count",
    "targeted_selected_source_count",
    "targeted_usable_page_count",
    "targeted_new_observation_count",
    "safe_change_count_before_targeted_search",
    "safe_change_count_after_targeted_search",
    "candidate_changed_cell_count_after_targeted_search",
    "additional_provider_search_attempts",
    "additional_provider_deadline_failures",
    "additional_fetch_attempts",
    "additional_hard_fetch_helper_calls",
    "additional_fetch_deadline_rejections",
    "additional_hard_fetch_deadline_failures",
    "additional_fetch_helper_failures",
    "additional_fetch_effects",
    "additional_model_acquisitions",
    "validation_memo_misses",
    "validation_memo_hits",
    "validation_memo_mismatches",
)
PROJECTION_NUMERIC_FIELDS = (
    "positive_information_gain_total_nats_after_targeted_search",
    "epistemic_credit_total_nats_after_targeted_search",
    "decision_credit_total_nats_after_targeted_search",
)
PROJECTION_KEYS = frozenset(
    {
        "ordinal",
        "target_plan_present",
        *PROJECTION_COUNT_FIELDS,
        *PROJECTION_NUMERIC_FIELDS,
        "threshold_failure_partition_after_targeted_search",
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
        "safe_change_improvement_tasks",
        "positive_decision_credit_tasks",
        "total_targeted_selected_source_count",
        "total_additional_fetch_effects",
        "total_additional_model_acquisitions",
        "total_validation_memo_misses",
        "total_validation_memo_hits",
        "total_positive_information_gain_nats",
        "total_epistemic_credit_nats",
        "total_decision_credit_nats",
        "all_effects_conserved",
        "all_memos_fail_closed",
        "all_single_validations_attested",
        "all_projections_consumed_validated_capabilities",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
)


def _count(value: Mapping[str, Any], name: str) -> int:
    item = value.get(name)
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        raise ValueError(f"V2.44.91 invalid projection count: {name}")
    return item


def _number(value: Mapping[str, Any], name: str) -> float:
    item = value.get(name)
    if (
        isinstance(item, bool)
        or not isinstance(item, (int, float))
        or not math.isfinite(float(item))
        or float(item) < 0
    ):
        raise ValueError(f"V2.44.91 invalid projection number: {name}")
    return float(item)


def _projection_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    safe_before = int(value.get("safe_change_count_before_targeted_search", -1))
    safe_after = int(value.get("safe_change_count_after_targeted_search", -1))
    decision = float(
        value.get("decision_credit_total_nats_after_targeted_search", -1.0)
    )
    epistemic = float(
        value.get("epistemic_credit_total_nats_after_targeted_search", -1.0)
    )
    information = float(
        value.get("positive_information_gain_total_nats_after_targeted_search", -1.0)
    )
    present = value.get("target_plan_present") is True
    return {
        "targeted_mechanism": (
            value.get("target_plan_present") in {True, False}
            and int(value.get("targeted_cell_count", -1)) == int(present)
            and int(value.get("targeted_logical_query_count", -1))
            == int(present) * targeted.MAXIMUM_TARGETED_LOGICAL_QUERIES
            and int(value.get("targeted_search_batch_count", -1)) == int(present)
            and int(value.get("targeted_selected_source_count", -1))
            <= targeted.MAXIMUM_TARGETED_SOURCES
            and safe_after >= safe_before >= 0
        ),
        "entropy_decision_credit": (
            0.0 <= decision <= epistemic + 1e-12 <= information + 1e-12
            and (decision == 0.0 or safe_after > safe_before)
        ),
        "effect_conservation": (
            int(value.get("additional_fetch_effects", -1))
            == int(value.get("additional_fetch_attempts", -2))
            == int(value.get("targeted_selected_source_count", -3))
            and int(value.get("additional_fetch_effects", -1))
            == int(value.get("additional_hard_fetch_helper_calls", -2))
            + int(value.get("additional_fetch_deadline_rejections", -2))
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
    ordinal: int, capability: ValidatedProofCarryingTargetedEnvelope
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(capability, ValidatedProofCarryingTargetedEnvelope)
    ):
        raise TypeError("V2.44.91 projection requires ordinal and capability")
    receipts = capability.counts_only_receipts()
    support = _normalized_targeted_support_receipt(
        receipts["targeted_support_receipt"]
    )
    effect = targeted.validate_effect_delta_receipt(
        receipts["targeted_effect_delta_receipt"]
    )
    memo = validate_memo_receipt(capability.content_free_memo_receipt())
    support_count_map = {
        "targeted_cell_count": "targeted_cell_count",
        "targeted_selected_target_count": "selected_target_count",
        "targeted_logical_query_count": "targeted_logical_query_count",
        "targeted_search_batch_count": "targeted_search_batch_count",
        "targeted_discovered_source_count": "targeted_discovered_source_count",
        "targeted_selected_source_count": "targeted_selected_source_count",
        "targeted_usable_page_count": "targeted_usable_page_count",
        "targeted_new_observation_count": "targeted_new_observation_count",
        "safe_change_count_before_targeted_search": "safe_change_count_before_targeted_search",
        "safe_change_count_after_targeted_search": "safe_change_count_after_targeted_search",
        "candidate_changed_cell_count_after_targeted_search": "candidate_changed_cell_count_after_targeted_search",
    }
    value = {
        "ordinal": ordinal,
        "target_plan_present": bool(effect["target_plan_present"]),
        **{
            public: int(support[private])
            for public, private in support_count_map.items()
        },
        **{
            name: int(effect[name])
            for name in (
                "additional_provider_search_attempts",
                "additional_provider_deadline_failures",
                "additional_fetch_attempts",
                "additional_hard_fetch_helper_calls",
                "additional_fetch_deadline_rejections",
                "additional_hard_fetch_deadline_failures",
                "additional_fetch_helper_failures",
                "additional_fetch_effects",
                "additional_model_acquisitions",
            )
        },
        "validation_memo_misses": int(memo["total_misses"]),
        "validation_memo_hits": int(memo["total_hits"]),
        "validation_memo_mismatches": int(memo["total_mismatches"]),
        **{
            name: float(support[name])
            for name in PROJECTION_NUMERIC_FIELDS
        },
        "threshold_failure_partition_after_targeted_search": {
            name: int(
                support["threshold_failure_partition_after_targeted_search"][name]
            )
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
    partition = copied.get("threshold_failure_partition_after_targeted_search")
    checks = copied.get("checks")
    if (
        set(copied) != PROJECTION_KEYS
        or isinstance(copied.get("ordinal"), bool)
        or not isinstance(copied.get("ordinal"), int)
        or copied["ordinal"] < 1
        or copied.get("target_plan_present") not in {True, False}
        or any(_count(copied, name) < 0 for name in PROJECTION_COUNT_FIELDS)
        or any(_number(copied, name) < 0 for name in PROJECTION_NUMERIC_FIELDS)
        or not isinstance(partition, Mapping)
        or set(partition) != set(THRESHOLD_PARTITION_FIELDS)
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
        raise ValueError("V2.44.91 capability projection drifted")
    return copied


def aggregate_projections(
    projections: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    values = sorted(
        (validate_task_projection(value) for value in projections),
        key=lambda value: value["ordinal"],
    )
    if (
        isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or len(values) != selected
        or [value["ordinal"] for value in values]
        != list(range(1, selected + 1))
    ):
        raise ValueError("V2.44.91 aggregate selection drifted")
    value = {
        "selected": selected,
        "exact_ordinal_vector": True,
        "passed_tasks": sum(item["passed"] is True for item in values),
        "failed_tasks": sum(item["passed"] is False for item in values),
        "target_plan_tasks": sum(item["target_plan_present"] is True for item in values),
        "safe_change_improvement_tasks": sum(
            item["safe_change_count_after_targeted_search"]
            > item["safe_change_count_before_targeted_search"]
            for item in values
        ),
        "positive_decision_credit_tasks": sum(
            item["decision_credit_total_nats_after_targeted_search"] > 0
            for item in values
        ),
        "total_targeted_selected_source_count": sum(
            item["targeted_selected_source_count"] for item in values
        ),
        "total_additional_fetch_effects": sum(
            item["additional_fetch_effects"] for item in values
        ),
        "total_additional_model_acquisitions": sum(
            item["additional_model_acquisitions"] for item in values
        ),
        "total_validation_memo_misses": sum(
            item["validation_memo_misses"] for item in values
        ),
        "total_validation_memo_hits": sum(
            item["validation_memo_hits"] for item in values
        ),
        "total_positive_information_gain_nats": sum(
            item["positive_information_gain_total_nats_after_targeted_search"]
            for item in values
        ),
        "total_epistemic_credit_nats": sum(
            item["epistemic_credit_total_nats_after_targeted_search"]
            for item in values
        ),
        "total_decision_credit_nats": sum(
            item["decision_credit_total_nats_after_targeted_search"]
            for item in values
        ),
        "all_effects_conserved": all(
            item["checks"]["effect_conservation"] for item in values
        ),
        "all_memos_fail_closed": all(
            item["checks"]["memo_fail_closed"] for item in values
        ),
        "all_single_validations_attested": all(
            item["checks"]["single_validation"] for item in values
        ),
        "all_projections_consumed_validated_capabilities": all(
            item["projection_consumed_only_validated_capability"] for item in values
        ),
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    count_names = (
        "selected",
        "passed_tasks",
        "failed_tasks",
        "target_plan_tasks",
        "safe_change_improvement_tasks",
        "positive_decision_credit_tasks",
        "total_targeted_selected_source_count",
        "total_additional_fetch_effects",
        "total_additional_model_acquisitions",
        "total_validation_memo_misses",
        "total_validation_memo_hits",
    )
    numeric_names = (
        "total_positive_information_gain_nats",
        "total_epistemic_credit_nats",
        "total_decision_credit_nats",
    )
    if (
        set(copied) != AGGREGATE_KEYS
        or any(_count(copied, name) < 0 for name in count_names)
        or copied["selected"] < 1
        or copied["passed_tasks"] + copied["failed_tasks"] != copied["selected"]
        or any(copied[name] > copied["selected"] for name in (
            "target_plan_tasks",
            "safe_change_improvement_tasks",
            "positive_decision_credit_tasks",
        ))
        or any(_number(copied, name) < 0 for name in numeric_names)
        or copied["total_decision_credit_nats"]
        > copied["total_epistemic_credit_nats"] + 1e-12
        or copied["total_epistemic_credit_nats"]
        > copied["total_positive_information_gain_nats"] + 1e-12
        or copied.get("exact_ordinal_vector") is not True
        or any(
            not isinstance(copied.get(name), bool)
            for name in (
                "all_effects_conserved",
                "all_memos_fail_closed",
                "all_single_validations_attested",
                "all_projections_consumed_validated_capabilities",
            )
        )
        or copied.get("private_task_content_emitted") is not False
        or copied.get("privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.44.91 capability aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "ARTIFACT_NAMES",
    "CERTIFICATE_NAME",
    "CERTIFICATE_ROLE",
    "ENVELOPE_ROLE",
    "MemoizedTargetedExecution",
    "POLICY_ID",
    "ValidatedProofCarryingTargetedEnvelope",
    "ValidatedTargetedExecution",
    "aggregate_projections",
    "build_envelope_from_validated_execution",
    "build_terminal_certificate",
    "run_and_persist_memoized_targeted_task",
    "run_memoized_targeted_worker",
    "run_single_validation_v24490_task",
    "task_projection",
    "validate_aggregate",
    "validate_cross_artifacts",
    "validate_proof_carrying_targeted_bundle",
    "validate_task_projection",
    "validate_terminal_certificate",
]
