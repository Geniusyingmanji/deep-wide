"""Proof-carrying terminal validation for V2.44.47 task artifacts.

V2.44.52 measured a material parent-side cost from recursively replaying the
complete historical envelope after a child had already validated the same
semantics before persistence.  This append-only adapter moves the trust
boundary without weakening the frozen semantic validator:

* the child still runs the unchanged V2.44.47 implementation and its complete
  semantic/cross-artifact validation;
* after the exact terminal files are durable, the child writes a sealed
  certificate binding their raw bytes and the two content-free receipts used
  by public projection;
* the parent independently checks ordinary-file containment, exact byte
  hashes, outer result seals, independent terminal receipts, compact
  effect/entropy invariants, and the frozen validator-manifest identity;
* the parent deliberately does not recursively recompute the full historical
  pipeline.

The certificate is a private temporary artifact.  It contains no task text,
opaque identifier, query, URL, page, value, prediction, candidate, benchmark
label, gold answer, evaluator state, reward, score, or credential.  Raw file
hashes remain private and are never authorized for a public aggregate.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .v24280_task_union_single_shot import validate_receipt as validate_search_receipt
from .v24308_child_exit_observability import validate_child_receipt
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24399_failure_observable_runner import (
    CHILD_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
)
from .v24447_third_source_entropy_to_decision import (
    EFFECT_KEYS,
    ENVELOPE_KEYS,
    ENVELOPE_ROLE,
    IntegratedThirdSourceOutcome,
    POLICY_ID as THIRD_SOURCE_POLICY_ID,
    RECEIPT_KEYS,
    RESULT_KEYS,
    RESULT_ROLE,
    THRESHOLD_PARTITION_FIELDS,
    run_and_persist_v24447_task,
    validate_effect_delta_receipt,
    validate_recovery_receipt,
)
from .v24448_serialized_third_source_envelope import (
    POLICY_ID as COMPLETE_VALIDATOR_POLICY_ID,
    ValidatedSerializedThirdSourceEnvelope,
)


POLICY_ID = "v24454_proof_carrying_third_source_envelope_v1"
CERTIFICATE_ROLE = "v24454_third_source_terminal_validation_certificate"
CERTIFICATE_NAME = "third_source_validation_certificate.json"
HEX64 = re.compile(r"[0-9a-f]{64}")
ARTIFACT_NAMES = (RESULT_NAME, MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME)
CERTIFICATE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "producer_policy_id",
        "complete_validator_policy_id",
        "validator_manifest_sha256",
        "artifact_byte_receipts",
        "third_source_recovery_receipt",
        "effect_delta_receipt",
        "complete_semantic_and_cross_artifact_validation_ran_in_child",
        "certificate_created_after_exact_terminal_artifacts",
        "independent_terminal_receipts_equal_envelope",
        "parent_must_not_recursively_recompute_historical_pipeline",
        "task_question_opaque_id_query_url_page_value_prediction_candidate_response_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder",
        "certificate_payload_sha256",
    }
)
BYTE_RECEIPT_KEYS = frozenset({"name", "byte_length", "sha256"})


class ValidatedProofCarryingThirdSourceEnvelope(ValidatedSerializedThirdSourceEnvelope):
    """Opaque capability backed by a child proof and parent byte validation."""

    __slots__ = ("__observation_receipts",)

    @classmethod
    def _create_proof(
        cls,
        value: Mapping[str, Any],
        *,
        child: Mapping[str, Any],
        model: Mapping[str, Any],
        transport: Mapping[str, Any],
        search: Mapping[str, Any],
    ) -> "ValidatedProofCarryingThirdSourceEnvelope":
        instance = cls._create(value, observed_bundle_validated=True)
        instance.__observation_receipts = {
            "child": copy.deepcopy(dict(child)),
            "model": copy.deepcopy(dict(model)),
            "transport": copy.deepcopy(dict(transport)),
            "search": copy.deepcopy(dict(search)),
        }
        return instance

    def content_free_observation_receipts(self) -> dict[str, Any]:
        """Return already validated terminal receipts for parent observation."""

        return copy.deepcopy(self.__observation_receipts)


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise ValueError(f"V2.44.54 {label} is not a SHA-256 digest")
    return value


def _ordinary_bytes(directory: Path, name: str) -> bytes:
    if name not in {*ARTIFACT_NAMES, CERTIFICATE_NAME, CHILD_NAME}:
        raise ValueError("V2.44.54 artifact name is not allowed")
    base = directory.resolve()
    path = directory / name
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(base)
    ):
        raise RuntimeError("V2.44.54 terminal artifact is not ordinary")
    return path.read_bytes()


def _validate_exact_surface(directory: Path, expected_names: set[str]) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("V2.44.54 task directory is not ordinary")
    observed: set[str] = set()
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.44.54 task surface contains a nonordinary entry")
        observed.add(path.name)
    if observed != expected_names:
        raise RuntimeError("V2.44.54 task artifact surface drifted")


def _object_from_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"V2.44.54 {label} is not UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"V2.44.54 {label} is not an object")
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


def _validate_byte_receipt(value: object, *, name: str, raw: bytes) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V2.44.54 byte receipt is not an object")
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
        raise ValueError("V2.44.54 terminal artifact byte receipt drifted")
    return copied


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _normalized_recovery_receipt(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V2.44.54 recovery receipt is not an object")
    copied = copy.deepcopy(dict(value))
    partition = copied.get("threshold_failure_partition")
    if not isinstance(partition, Mapping) or set(partition) != set(
        THRESHOLD_PARTITION_FIELDS
    ):
        raise ValueError("V2.44.54 threshold partition drifted")
    copied["threshold_failure_partition"] = {
        name: copy.deepcopy(partition[name]) for name in THRESHOLD_PARTITION_FIELDS
    }
    return validate_recovery_receipt(copied)


def _validate_effect_receipt(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V2.44.54 effect receipt is not an object")
    return validate_effect_delta_receipt(dict(value))


def _validate_shells(
    envelope: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate identity seals and compact receipts without semantic replay."""

    copied = dict(envelope)
    result = copied.get("third_source_result")
    effect = copied.get("effect_delta_receipt")
    mapping_fields = (
        "parent_envelope",
        "third_source_result",
        "model_slot_receipt_before_third_source",
        "transport_health_before_third_source",
        "search_single_shot_receipt_before_third_source",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "effect_delta_receipt",
    )
    if (
        set(copied) != ENVELOPE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ENVELOPE_ROLE
        or copied.get("policy_id") != THIRD_SOURCE_POLICY_ID
        or any(not isinstance(copied.get(name), Mapping) for name in mapping_fields)
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
        or set(result) != RESULT_KEYS
        or result.get("artifact_version") != 1
        or result.get("role") != RESULT_ROLE
        or result.get("policy_id") != THIRD_SOURCE_POLICY_ID
        or not isinstance(result.get("parent_result"), Mapping)
        or not isinstance(result.get("candidate_prediction"), str)
        or not isinstance(result.get("extended_narrative_title_projection"), Mapping)
        or not isinstance(result.get("extended_active_evidence_result"), Mapping)
        or not isinstance(result.get("third_source_private_state"), Mapping)
        or not isinstance(result.get("third_source_recovery_receipt"), Mapping)
        or not _sealed(result, "result_sha256")
        or not isinstance(effect, Mapping)
        or set(effect) != EFFECT_KEYS
        or set(result["third_source_recovery_receipt"]) != RECEIPT_KEYS
    ):
        raise ValueError("V2.44.54 envelope identity shell drifted")
    recovery = _normalized_recovery_receipt(result["third_source_recovery_receipt"])
    validated_effect = _validate_effect_receipt(effect)
    return copied, recovery, validated_effect


def build_terminal_certificate(
    directory: Path,
    completed: IntegratedThirdSourceOutcome,
    *,
    validator_manifest_sha256: str,
    expected_artifacts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind exact durable files after the trusted child completed validation."""

    if not isinstance(completed, IntegratedThirdSourceOutcome):
        raise TypeError("V2.44.54 requires a completed V2.44.47 outcome")
    manifest = _digest(validator_manifest_sha256, "validator manifest")
    _validate_exact_surface(directory, set(ARTIFACT_NAMES))
    if set(expected_artifacts) != set(ARTIFACT_NAMES):
        raise ValueError("V2.44.54 expected artifact vector drifted")
    artifacts = {name: _read_object(directory, name) for name in ARTIFACT_NAMES}
    if any(
        artifacts[name][1] != dict(expected_artifacts[name])
        for name in ARTIFACT_NAMES
    ):
        raise ValueError("V2.44.54 durable bytes drifted from validated writer input")
    envelope, recovery, effect = _validate_shells(artifacts[RESULT_NAME][1])
    model = validate_model_receipt(
        artifacts[MODEL_NAME][1],
        expected_cap=int(completed.model_slot_receipt.get("slot_cap", -1)),
    )
    transport = validate_transport_health(artifacts[TRANSPORT_NAME][1])
    search = artifacts[SEARCH_NAME][1]
    validate_search_receipt(search)
    completed_recovery = _normalized_recovery_receipt(
        completed.third_source_result["third_source_recovery_receipt"]
    )
    completed_effect = _validate_effect_receipt(completed.effect_delta_receipt)
    if (
        envelope["model_slot_receipt"] != model
        or envelope["transport_health"] != transport
        or envelope["search_single_shot_receipt"] != search
        or completed.model_slot_receipt != model
        or completed.transport_health != transport
        or completed.search_single_shot_receipt != search
        or recovery != completed_recovery
        or effect != completed_effect
    ):
        raise ValueError("V2.44.54 durable artifacts drifted from completed outcome")
    value = {
        "artifact_version": 1,
        "role": CERTIFICATE_ROLE,
        "policy_id": POLICY_ID,
        "producer_policy_id": THIRD_SOURCE_POLICY_ID,
        "complete_validator_policy_id": COMPLETE_VALIDATOR_POLICY_ID,
        "validator_manifest_sha256": manifest,
        "artifact_byte_receipts": {
            name: _byte_receipt(name, artifacts[name][0]) for name in ARTIFACT_NAMES
        },
        "third_source_recovery_receipt": recovery,
        "effect_delta_receipt": effect,
        "complete_semantic_and_cross_artifact_validation_ran_in_child": True,
        "certificate_created_after_exact_terminal_artifacts": True,
        "independent_terminal_receipts_equal_envelope": True,
        "parent_must_not_recursively_recompute_historical_pipeline": True,
        "task_question_opaque_id_query_url_page_value_prediction_candidate_response_or_credential_emitted": False,
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
    recovery = copied.get("third_source_recovery_receipt")
    effect = copied.get("effect_delta_receipt")
    artifacts = {name: _read_object(directory, name) for name in ARTIFACT_NAMES}
    envelope, envelope_recovery, envelope_effect = _validate_shells(
        artifacts[RESULT_NAME][1]
    )
    model = validate_model_receipt(
        artifacts[MODEL_NAME][1],
        expected_cap=int(envelope["model_slot_receipt"].get("slot_cap", -1)),
    )
    transport = validate_transport_health(artifacts[TRANSPORT_NAME][1])
    search = artifacts[SEARCH_NAME][1]
    validate_search_receipt(search)
    if (
        set(copied) != CERTIFICATE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != CERTIFICATE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("producer_policy_id") != THIRD_SOURCE_POLICY_ID
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
        or _normalized_recovery_receipt(recovery) != envelope_recovery
        or _validate_effect_receipt(effect) != envelope_effect
        or envelope["model_slot_receipt"] != model
        or envelope["transport_health"] != transport
        or envelope["search_single_shot_receipt"] != search
        or copied.get(
            "complete_semantic_and_cross_artifact_validation_ran_in_child"
        )
        is not True
        or copied.get("certificate_created_after_exact_terminal_artifacts") is not True
        or copied.get("independent_terminal_receipts_equal_envelope") is not True
        or copied.get(
            "parent_must_not_recursively_recompute_historical_pipeline"
        )
        is not True
        or copied.get(
            "task_question_opaque_id_query_url_page_value_prediction_candidate_response_or_credential_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get(
            "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder"
        )
        is not False
        or not _sealed(copied, "certificate_payload_sha256")
    ):
        raise ValueError("V2.44.54 terminal certificate drifted")
    return copied


def validate_proof_carrying_observed_bundle(
    value: Mapping[str, Any],
    *,
    directory: Path,
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
) -> ValidatedProofCarryingThirdSourceEnvelope:
    """Validate exact bytes and compact invariants, then mint a capability."""

    _validate_exact_surface(
        directory, {*ARTIFACT_NAMES, CERTIFICATE_NAME, CHILD_NAME}
    )
    child_raw, child_value = _read_object(directory, CHILD_NAME)
    del child_raw
    child = validate_child_receipt(child_value)
    if (
        child.get("stage") != "result_envelope_written"
        or child.get("exception_type") is not None
        or child.get("model_receipt_written") is not True
        or child.get("transport_receipt_written") is not True
        or child.get("result_envelope_written") is not True
    ):
        raise ValueError("V2.44.54 child terminal receipt is not successful")
    certificate_raw, certificate = _read_object(directory, CERTIFICATE_NAME)
    del certificate_raw
    validated_certificate = validate_terminal_certificate(
        certificate,
        directory=directory,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )
    result_raw, persisted = _read_object(directory, RESULT_NAME)
    del result_raw
    envelope, recovery, effect = _validate_shells(value)
    if (
        dict(value) != persisted
        or recovery
        != _normalized_recovery_receipt(
            validated_certificate["third_source_recovery_receipt"]
        )
        or effect
        != _validate_effect_receipt(validated_certificate["effect_delta_receipt"])
        or int(envelope["model_slot_receipt"].get("slot_cap", -1))
        != expected_model_cap
    ):
        raise ValueError("V2.44.54 parent result/certificate binding drifted")
    model_raw, model_value = _read_object(directory, MODEL_NAME)
    transport_raw, transport_value = _read_object(directory, TRANSPORT_NAME)
    search_raw, search_value = _read_object(directory, SEARCH_NAME)
    del model_raw, transport_raw, search_raw
    model = validate_model_receipt(
        model_value, expected_cap=expected_model_cap
    )
    transport = validate_transport_health(transport_value)
    validate_search_receipt(search_value)
    capability = ValidatedProofCarryingThirdSourceEnvelope._create_proof(
        envelope,
        child=child,
        model=model,
        transport=transport,
        search=search_value,
    )
    if not isinstance(capability, ValidatedProofCarryingThirdSourceEnvelope):
        raise RuntimeError("V2.44.54 capability type drifted")
    return capability


def run_and_persist_proof_carrying_v24447_task(
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
) -> IntegratedThirdSourceOutcome:
    """Run the unchanged child, then publish its private byte certificate."""

    expected_artifacts: dict[str, dict[str, Any]] = {}

    def binding_writer(name: str, value: Mapping[str, Any]) -> None:
        if name in expected_artifacts:
            raise FileExistsError(name)
        expected_artifacts[name] = copy.deepcopy(dict(value))
        writer(name, value)

    completed = run_and_persist_v24447_task(
        task,
        model_factory=model_factory,
        search_factory=search_factory,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
        expected_model_cap=expected_model_cap,
        writer=binding_writer,
    )
    certificate = build_terminal_certificate(
        directory,
        completed,
        validator_manifest_sha256=validator_manifest_sha256,
        expected_artifacts=expected_artifacts,
    )
    writer(CERTIFICATE_NAME, certificate)
    return completed


__all__ = [
    "CERTIFICATE_NAME",
    "CERTIFICATE_ROLE",
    "POLICY_ID",
    "ValidatedProofCarryingThirdSourceEnvelope",
    "build_terminal_certificate",
    "run_and_persist_proof_carrying_v24447_task",
    "validate_proof_carrying_observed_bundle",
    "validate_terminal_certificate",
]
