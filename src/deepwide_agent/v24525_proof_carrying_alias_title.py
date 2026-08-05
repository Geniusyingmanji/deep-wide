"""Proof boundary for zero-effect conservative alias-title integration.

The child completes one typed V2.45.03 validation and then computes and fully
validates the pure V2.45.24 alias integration while the private page vector is
still in memory.  It persists the unchanged V2.45.04 parent proof surface,
one separate alias result, and an outer exact-byte certificate.

The parent validates ordinary files, exact bytes, the V2.45.04 compact proof,
the alias result shell and counts-only receipt, and execution-scoped memo and
planner receipts.  It does not recursively replay the private alias semantic
pipeline.  This is a pinned local-child trust boundary, not a signature,
remote attestation, or malicious-child defence.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from . import v24504_proof_carrying_record_bound_reserve as parent
from . import v24524_alias_title_integration as integration
from . import v24523_conservative_alias_title_projection as alias_projection
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
from .v24413_effect_equivalence import compare_effect_snapshots
from .v24485_execution_scoped_validation_memo import ExecutionValidationMemo
from .v24486_memoized_worker_integration import validate_memo_receipt
from .v24508_execution_scoped_high_level_validation_memo import (
    HighLevelValidationMemo,
    validate_receipt as validate_high_level_receipt,
)
from .v24515_neutral_cell_discovery_planner import (
    NeutralCellDiscoveryPlanner,
    validate_receipt as validate_planner_receipt,
)


POLICY_ID = "v24525_proof_carrying_alias_title_integration_v1"
CERTIFICATE_ROLE = "v24525_alias_title_validation_certificate"
ALIAS_RESULT_NAME = "alias_title_result.json"
CERTIFICATE_NAME = "alias_title_validation_certificate.json"
PARENT_ARTIFACT_NAMES = (
    RESULT_NAME,
    MODEL_NAME,
    TRANSPORT_NAME,
    SEARCH_NAME,
    parent.CERTIFICATE_NAME,
)
BYTE_BOUND_NAMES = (*PARENT_ARTIFACT_NAMES, ALIAS_RESULT_NAME)
SUCCESS_NAMES = {*BYTE_BOUND_NAMES, CERTIFICATE_NAME, CHILD_NAME}
HEX64 = re.compile(r"[0-9a-f]{64}")
BYTE_RECEIPT_KEYS = frozenset({"name", "byte_length", "sha256"})
CERTIFICATE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "producer_policy_id",
        "parent_certificate_policy_id",
        "validator_manifest_sha256",
        "artifact_byte_receipts",
        "alias_title_receipt",
        "low_level_validation_memo_receipt",
        "high_level_validation_memo_receipt",
        "neutral_discovery_planner_receipt",
        "complete_parent_and_alias_semantic_validation_ran_in_child",
        "parent_artifacts_and_certificate_preserved_exactly",
        "alias_result_created_from_typed_validated_execution",
        "alias_recovery_has_no_external_effect_by_construction",
        "certificate_created_after_exact_bound_artifacts",
        "parent_must_not_replay_private_alias_semantic_pipeline",
        "certificate_is_independently_signed",
        "certificate_is_remote_attestation",
        "malicious_child_resistance_claimed",
        "task_question_opaque_id_entity_column_value_query_url_page_source_prediction_private_content_hash_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_outer_certificate_builder",
        "certificate_payload_sha256",
    }
)


class ValidatedAliasTitleExecution:
    """Opaque proof of one complete child-side alias validation."""

    __slots__ = ("__parent", "__outcome")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use run_single_validation_v24524_task")

    @classmethod
    def _create(
        cls,
        *,
        parent_execution: parent.ValidatedRecordBoundExecution,
        outcome: integration.IntegratedAliasTitleOutcome,
    ) -> "ValidatedAliasTitleExecution":
        if not isinstance(parent_execution, parent.ValidatedRecordBoundExecution):
            raise TypeError("V2.45.25 requires typed parent execution")
        instance = object.__new__(cls)
        instance.__parent = parent_execution
        instance.__outcome = outcome
        return instance

    def _trusted_parent(self) -> parent.ValidatedRecordBoundExecution:
        return self.__parent

    def _trusted_outcome(self) -> integration.IntegratedAliasTitleOutcome:
        return self.__outcome


class ValidatedProofCarryingAliasTitle:
    """Opaque parent capability exposing only fixed-vocabulary receipts."""

    __slots__ = ("__receipt", "__parent")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use validate_proof_carrying_alias_bundle")

    @classmethod
    def _create(
        cls,
        *,
        receipt: Mapping[str, Any],
        parent_capability: parent.ValidatedProofCarryingRecordBoundEnvelope,
    ) -> "ValidatedProofCarryingAliasTitle":
        if not isinstance(
            parent_capability, parent.ValidatedProofCarryingRecordBoundEnvelope
        ):
            raise TypeError("V2.45.25 requires parent capability")
        instance = object.__new__(cls)
        instance.__receipt = copy.deepcopy(dict(receipt))
        instance.__parent = parent_capability
        return instance

    def counts_only_receipt(self) -> dict[str, Any]:
        return copy.deepcopy(self.__receipt)

    def parent_capability(
        self,
    ) -> parent.ValidatedProofCarryingRecordBoundEnvelope:
        return self.__parent

    def content_free_observation_receipts(self) -> dict[str, Any]:
        return self.__parent.content_free_observation_receipts()


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise ValueError(f"V2.45.25 {label} is not a SHA-256 digest")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _ordinary_bytes(directory: Path, name: str) -> bytes:
    if name not in SUCCESS_NAMES:
        raise ValueError("V2.45.25 artifact name is not allowed")
    base = directory.resolve()
    path = directory / name
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(base)
    ):
        raise RuntimeError("V2.45.25 terminal artifact is not ordinary")
    return path.read_bytes()


def _validate_exact_surface(directory: Path, expected_names: set[str]) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("V2.45.25 task directory is not ordinary")
    observed: set[str] = set()
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.45.25 task surface contains nonordinary entry")
        observed.add(path.name)
    if observed != expected_names:
        raise RuntimeError("V2.45.25 task artifact surface drifted")


def _object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"V2.45.25 {label} is not UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"V2.45.25 {label} is not an object")
    return value


def _read(directory: Path, name: str) -> tuple[bytes, dict[str, Any]]:
    raw = _ordinary_bytes(directory, name)
    return raw, _object(raw, name)


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
        raise ValueError("V2.45.25 byte receipt is not an object")
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
        raise ValueError("V2.45.25 byte receipt drifted")
    return copied


def run_single_validation_v24524_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
) -> ValidatedAliasTitleExecution:
    validated_parent = parent.run_single_validation_v24503_task(
        task,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    parent_outcome = validated_parent._trusted_outcome()
    model_receipt = copy.deepcopy(parent_outcome.model_slot_receipt)
    transport = copy.deepcopy(parent_outcome.transport_health)
    search_receipt = copy.deepcopy(parent_outcome.search_single_shot_receipt)
    alias_result = integration._compute_result_from_validated(
        parent_outcome.record_bound_result
    )
    effect = compare_effect_snapshots(
        model_before=model_receipt,
        model_after=model_receipt,
        transport_before=transport,
        transport_after=transport,
        search_before=search_receipt,
        search_after=search_receipt,
        expected_model_cap=int(model_receipt["slot_cap"]),
    )
    outcome = integration.IntegratedAliasTitleOutcome(
        parent=parent_outcome,
        alias_title_result=alias_result,
        model_slot_receipt_before_alias_projection=model_receipt,
        transport_health_before_alias_projection=transport,
        search_single_shot_receipt_before_alias_projection=search_receipt,
        model_slot_receipt=model_receipt,
        transport_health=transport,
        search_single_shot_receipt=search_receipt,
        effect_equivalence_receipt=effect,
    )
    integration._validate_cross_artifacts_in_scope(
        parent_outcome.record_bound_result,
        alias_result,
        model_before=model_receipt,
        transport_before=transport,
        search_before=search_receipt,
        model_after=model_receipt,
        transport_after=transport,
        search_after=search_receipt,
        effect_equivalence_receipt=effect,
        expected_model_cap=int(model_receipt["slot_cap"]),
    )
    return ValidatedAliasTitleExecution._create(
        parent_execution=validated_parent, outcome=outcome
    )


def build_outer_certificate(
    directory: Path,
    *,
    alias_result: Mapping[str, Any],
    low_memo_receipt: Mapping[str, Any],
    high_memo_receipt: Mapping[str, Any],
    planner_receipt: Mapping[str, Any],
    validator_manifest_sha256: str,
) -> dict[str, Any]:
    manifest = _digest(validator_manifest_sha256, "validator manifest")
    low = validate_memo_receipt(low_memo_receipt)
    high = validate_high_level_receipt(high_memo_receipt)
    planner = validate_planner_receipt(planner_receipt)
    _validate_exact_surface(directory, set(BYTE_BOUND_NAMES))
    artifacts = {name: _read(directory, name) for name in BYTE_BOUND_NAMES}
    if artifacts[ALIAS_RESULT_NAME][1] != dict(alias_result):
        raise ValueError("V2.45.25 durable alias result drifted")
    receipt = integration.validate_alias_title_receipt(
        alias_result["alias_title_receipt"]
    )
    value = {
        "artifact_version": 1,
        "role": CERTIFICATE_ROLE,
        "policy_id": POLICY_ID,
        "producer_policy_id": integration.POLICY_ID,
        "parent_certificate_policy_id": parent.POLICY_ID,
        "validator_manifest_sha256": manifest,
        "artifact_byte_receipts": {
            name: _byte_receipt(name, artifacts[name][0])
            for name in BYTE_BOUND_NAMES
        },
        "alias_title_receipt": receipt,
        "low_level_validation_memo_receipt": low,
        "high_level_validation_memo_receipt": high,
        "neutral_discovery_planner_receipt": planner,
        "complete_parent_and_alias_semantic_validation_ran_in_child": True,
        "parent_artifacts_and_certificate_preserved_exactly": True,
        "alias_result_created_from_typed_validated_execution": True,
        "alias_recovery_has_no_external_effect_by_construction": True,
        "certificate_created_after_exact_bound_artifacts": True,
        "parent_must_not_replay_private_alias_semantic_pipeline": True,
        "certificate_is_independently_signed": False,
        "certificate_is_remote_attestation": False,
        "malicious_child_resistance_claimed": False,
        "task_question_opaque_id_entity_column_value_query_url_page_source_prediction_private_content_hash_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_process_or_evaluator_called_by_outer_certificate_builder": False,
    }
    value["certificate_payload_sha256"] = payload_sha256(value)
    return validate_outer_certificate(
        value,
        directory=directory,
        expected_validator_manifest_sha256=manifest,
    )


def validate_outer_certificate(
    value: Mapping[str, Any],
    *,
    directory: Path,
    expected_validator_manifest_sha256: str,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    manifest = _digest(
        expected_validator_manifest_sha256, "expected validator manifest"
    )
    receipts = copied.get("artifact_byte_receipts")
    artifacts = {name: _read(directory, name) for name in BYTE_BOUND_NAMES}
    alias_result = artifacts[ALIAS_RESULT_NAME][1]
    alias_receipt = integration.validate_alias_title_receipt(
        alias_result.get("alias_title_receipt", {})
    )
    low = copied.get("low_level_validation_memo_receipt")
    high = copied.get("high_level_validation_memo_receipt")
    planner = copied.get("neutral_discovery_planner_receipt")
    true_fields = (
        "complete_parent_and_alias_semantic_validation_ran_in_child",
        "parent_artifacts_and_certificate_preserved_exactly",
        "alias_result_created_from_typed_validated_execution",
        "alias_recovery_has_no_external_effect_by_construction",
        "certificate_created_after_exact_bound_artifacts",
        "parent_must_not_replay_private_alias_semantic_pipeline",
    )
    false_fields = (
        "certificate_is_independently_signed",
        "certificate_is_remote_attestation",
        "malicious_child_resistance_claimed",
        "task_question_opaque_id_entity_column_value_query_url_page_source_prediction_private_content_hash_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_outer_certificate_builder",
    )
    if (
        set(copied) != CERTIFICATE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != CERTIFICATE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("producer_policy_id") != integration.POLICY_ID
        or copied.get("parent_certificate_policy_id") != parent.POLICY_ID
        or copied.get("validator_manifest_sha256") != manifest
        or not isinstance(receipts, Mapping)
        or set(receipts) != set(BYTE_BOUND_NAMES)
        or any(
            _validate_byte_receipt(
                receipts.get(name), name=name, raw=artifacts[name][0]
            )
            != receipts[name]
            for name in BYTE_BOUND_NAMES
        )
        or copied.get("alias_title_receipt") != alias_receipt
        or not isinstance(low, Mapping)
        or validate_memo_receipt(low) != low
        or not isinstance(high, Mapping)
        or validate_high_level_receipt(high) != high
        or not isinstance(planner, Mapping)
        or validate_planner_receipt(planner) != planner
        or planner.get("build_calls") != 1
        or planner.get("replay_calls", 0) < 1
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or not _sealed(copied, "certificate_payload_sha256")
    ):
        raise ValueError("V2.45.25 outer certificate drifted")
    return copied


def _validate_alias_shell(
    value: Mapping[str, Any], *, parent_envelope: Mapping[str, Any]
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    projection = copied.get("alias_title_projection")
    if (
        set(copied) != integration.RESULT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != integration.RESULT_ROLE
        or copied.get("policy_id") != integration.POLICY_ID
        or not _sealed(copied, "result_sha256")
        or copied.get("parent_result") != parent_envelope.get("record_bound_result")
        or not isinstance(copied.get("candidate_prediction"), str)
        or not isinstance(projection, Mapping)
        or projection.get("artifact_version") != 1
        or projection.get("role") != alias_projection.ROLE
        or projection.get("policy_id") != alias_projection.POLICY_ID
        or not _sealed(projection, "catalog_payload_sha256")
        or projection.get("parent_projection")
        != copied["parent_result"].get("record_bound_projection")
        or not isinstance(copied.get("alias_active_evidence_result"), Mapping)
        or integration.validate_alias_title_receipt(
            copied.get("alias_title_receipt", {})
        )
        != copied["alias_title_receipt"]
    ):
        raise ValueError("V2.45.25 compact alias result shell drifted")
    return copied


def _parent_capability(
    directory: Path,
    *,
    envelope: Mapping[str, Any],
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
) -> parent.ValidatedProofCarryingRecordBoundEnvelope:
    _, certificate_value = _read(directory, parent.CERTIFICATE_NAME)
    certificate = parent.validate_terminal_certificate(
        certificate_value,
        directory=directory,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )
    shell, parent_support, parent_effect, record_receipt, zero_effect = (
        parent._validate_record_bound_shell(envelope)
    )
    _, model_value = _read(directory, MODEL_NAME)
    _, transport_value = _read(directory, TRANSPORT_NAME)
    _, search_value = _read(directory, SEARCH_NAME)
    model = validate_model_receipt(model_value, expected_cap=expected_model_cap)
    transport = validate_transport_health(transport_value)
    search = dict(search_value)
    validate_search_receipt(search)
    memo = validate_memo_receipt(certificate["validation_memo_receipt"])
    _, child_value = _read(directory, CHILD_NAME)
    child = validate_child_receipt(child_value)
    if (
        shell["model_slot_receipt"] != model
        or shell["transport_health"] != transport
        or shell["search_single_shot_receipt"] != search
        or parent_support != certificate["parent_reserve_support_receipt"]
        or parent_effect != certificate["parent_reserve_effect_delta_receipt"]
        or record_receipt != certificate["record_bound_receipt"]
        or zero_effect != certificate["zero_effect_equivalence_receipt"]
    ):
        raise ValueError("V2.45.25 parent compact proof binding drifted")
    return parent.ValidatedProofCarryingRecordBoundEnvelope._create(
        parent_support=parent_support,
        parent_effect=parent_effect,
        record=record_receipt,
        zero_effect=zero_effect,
        memo=memo,
        child=child,
        model=model,
        transport=transport,
        search=search,
    )


def validate_proof_carrying_alias_bundle(
    value: Mapping[str, Any],
    *,
    directory: Path,
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
) -> ValidatedProofCarryingAliasTitle:
    _validate_exact_surface(directory, set(SUCCESS_NAMES))
    _, child_value = _read(directory, CHILD_NAME)
    child = validate_child_receipt(child_value)
    if (
        child.get("stage") != "result_envelope_written"
        or child.get("exception_type") is not None
        or child.get("model_receipt_written") is not True
        or child.get("transport_receipt_written") is not True
        or child.get("result_envelope_written") is not True
    ):
        raise ValueError("V2.45.25 child terminal receipt is not successful")
    _, outer_value = _read(directory, CERTIFICATE_NAME)
    outer = validate_outer_certificate(
        outer_value,
        directory=directory,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )
    _, persisted = _read(directory, RESULT_NAME)
    if dict(value) != persisted:
        raise ValueError("V2.45.25 supplied parent result differs from durable result")
    parent_capability = _parent_capability(
        directory,
        envelope=persisted,
        expected_model_cap=expected_model_cap,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )
    _, alias_value = _read(directory, ALIAS_RESULT_NAME)
    alias_result = _validate_alias_shell(alias_value, parent_envelope=persisted)
    receipt = integration.validate_alias_title_receipt(
        alias_result["alias_title_receipt"]
    )
    if receipt != outer["alias_title_receipt"]:
        raise ValueError("V2.45.25 alias receipt/certificate drifted")
    return ValidatedProofCarryingAliasTitle._create(
        receipt=receipt, parent_capability=parent_capability
    )


def run_and_persist_alias_title_task(
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
) -> dict[str, Any]:
    model: Any = None
    search: Any = None
    stage = "model_construction"
    try:
        model = model_factory()
        stage = "search_construction"
        search = search_factory()
        stage = "runtime"
        low = ExecutionValidationMemo()
        high = HighLevelValidationMemo()
        planner = NeutralCellDiscoveryPlanner()
        with low, high, planner:
            validated = run_single_validation_v24524_task(
                task,
                model=model,
                search=search,
                partition_seed_sha256=partition_seed_sha256,
                limits=limits,
                monotonic=monotonic,
            )
        low_receipt = validate_memo_receipt(low.content_free_receipt())
        high_receipt = validate_high_level_receipt(high.content_free_receipt())
        planner_receipt = validate_planner_receipt(planner.content_free_receipt())
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
    parent_execution = validated._trusted_parent()
    parent_outcome = parent_execution._trusted_outcome()
    artifacts = {
        MODEL_NAME: parent_outcome.model_slot_receipt,
        TRANSPORT_NAME: parent_outcome.transport_health,
        SEARCH_NAME: parent_outcome.search_single_shot_receipt,
        RESULT_NAME: parent.build_envelope_from_validated_execution(
            parent_execution
        ),
    }
    for name in parent.ARTIFACT_NAMES:
        writer(name, artifacts[name])
    parent_certificate = parent.build_terminal_certificate(
        directory,
        parent_execution,
        memo_receipt=low_receipt,
        validator_manifest_sha256=validator_manifest_sha256,
        expected_artifacts=artifacts,
    )
    writer(parent.CERTIFICATE_NAME, parent_certificate)
    writer(ALIAS_RESULT_NAME, outcome.alias_title_result)
    outer = build_outer_certificate(
        directory,
        alias_result=outcome.alias_title_result,
        low_memo_receipt=low_receipt,
        high_memo_receipt=high_receipt,
        planner_receipt=planner_receipt,
        validator_manifest_sha256=validator_manifest_sha256,
    )
    writer(CERTIFICATE_NAME, outer)
    return copy.deepcopy(outcome.alias_title_result)


def run_alias_title_worker(
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
) -> dict[str, Any]:
    completed: dict[str, Any] | None = None

    def action() -> None:
        nonlocal completed
        completed = run_and_persist_alias_title_task(
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
        raise RuntimeError("V2.45.25 alias title outcome is absent")
    return completed


__all__ = [
    "ALIAS_RESULT_NAME",
    "CERTIFICATE_NAME",
    "POLICY_ID",
    "SUCCESS_NAMES",
    "ValidatedAliasTitleExecution",
    "ValidatedProofCarryingAliasTitle",
    "build_outer_certificate",
    "run_alias_title_worker",
    "run_single_validation_v24524_task",
    "validate_outer_certificate",
    "validate_proof_carrying_alias_bundle",
]
