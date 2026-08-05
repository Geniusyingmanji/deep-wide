"""Proof-carrying integration for V2.45.89 title-query alignment.

The V2.45.79 task and auxiliary surfaces remain byte-for-byte unchanged.  A
V2.45.89 execution context surrounds that worker call, after which only a
counts-only query receipt and certificate are written to a new sibling
directory.  Parent validation first mints the V2.45.79 opaque capability and
then validates this exact receipt/certificate surface without replaying task,
row, query, lead, URL, title, page, prediction, value, or search semantics.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24579_proof_carrying_prededup_preservation as parent_proof
from . import v24589_validator_aligned_title_query as query_policy
from .v24309_runner_exit_integration import _new_json
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24470_bounded_adaptive_integration import _validate_layout


POLICY_ID = "v24590_proof_carrying_validator_aligned_title_query_v1"
CERTIFICATE_ROLE = "v24590_validator_aligned_title_query_certificate"
DIRECTORY_PREFIX = "validator_aligned_title_query_"
RECEIPT_NAME = "validator_aligned_title_query_receipt.json"
CERTIFICATE_NAME = "validator_aligned_title_query_certificate.json"
AUXILIARY_NAMES = frozenset({RECEIPT_NAME, CERTIFICATE_NAME})
BOUND_PARENT_NAMES = (parent_proof.RECEIPT_NAME, parent_proof.CERTIFICATE_NAME)
BYTE_RECEIPT_KEYS = frozenset({"name", "byte_length", "sha256"})
CERTIFICATE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "producer_policy_id",
        "parent_proof_policy_id",
        "ordinal",
        "validator_manifest_sha256",
        "artifact_byte_receipts",
        "validator_aligned_title_query_receipt",
        "v24579_worker_returned_before_title_query_receipt",
        "title_query_context_restored_before_receipt",
        "frozen_v24579_task_and_auxiliary_surfaces_preserved_exactly",
        "parent_must_validate_v24579_capability_before_successor_capability",
        "parent_must_not_replay_private_task_row_query_lead_url_title_page_prediction_value_or_search_semantics",
        "query_hint_receives_evidence_source_entropy_epistemic_or_decision_credit",
        "certificate_created_after_bound_artifacts",
        "certificate_is_independently_signed",
        "certificate_is_remote_attestation",
        "malicious_child_resistance_claimed",
        "task_question_opaque_id_entity_query_url_title_page_source_value_prediction_private_content_hash_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder",
        "certificate_payload_sha256",
    }
)


class ValidatedProofCarryingValidatorAlignedTitleQuery:
    """Opaque V2.45.79 capability plus a counts-only V2.45.89 receipt."""

    __slots__ = ("__parent", "__receipt")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use validate_proof_carrying_title_query_bundle")

    @classmethod
    def _create(
        cls,
        *,
        parent: parent_proof.ValidatedProofCarryingPrededupPreservation,
        receipt: Mapping[str, Any],
    ) -> "ValidatedProofCarryingValidatorAlignedTitleQuery":
        if not isinstance(
            parent, parent_proof.ValidatedProofCarryingPrededupPreservation
        ):
            raise TypeError("V2.45.90 requires V2.45.79 capability")
        validated = query_policy.validate_receipt(receipt)
        instance = object.__new__(cls)
        instance.__parent = parent
        instance.__receipt = copy.deepcopy(validated)
        return instance

    def parent_capability(
        self,
    ) -> parent_proof.ValidatedProofCarryingPrededupPreservation:
        return self.__parent

    def validator_aligned_title_query_receipt(self) -> dict[str, Any]:
        return copy.deepcopy(self.__receipt)

    def prededup_preservation_receipt(self) -> dict[str, Any]:
        return self.__parent.prededup_preservation_receipt()

    def validator_aligned_selection_receipt(self) -> dict[str, Any]:
        return self.__parent.validator_aligned_selection_receipt()

    def decision_reachability_receipt(self) -> dict[str, Any]:
        return self.__parent.decision_reachability_receipt()

    def joint_observability_receipt(self) -> dict[str, Any]:
        return self.__parent.joint_observability_receipt()

    def content_free_observation_receipts(self) -> dict[str, Any]:
        return self.__parent.content_free_observation_receipts()


def auxiliary_directory(output_root: Path, ordinal: int) -> Path:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.90 ordinal is invalid")
    root = output_root.resolve()
    if output_root.is_symlink() or not output_root.is_dir():
        raise RuntimeError("V2.45.90 output root is nonordinary")
    path = output_root / f"{DIRECTORY_PREFIX}{ordinal:06d}"
    if path.resolve(strict=False).parent != root:
        raise RuntimeError("V2.45.90 auxiliary directory escaped output root")
    return path


def _ordinary_directory(path: Path, *, output_root: Path) -> Path:
    root = output_root.resolve()
    if path.is_symlink() or not path.is_dir() or path.resolve().parent != root:
        raise RuntimeError("V2.45.90 auxiliary directory is nonordinary")
    return path.resolve()


def _exact_auxiliary_surface(path: Path, *, output_root: Path) -> None:
    directory = _ordinary_directory(path, output_root=output_root)
    observed: set[str] = set()
    for item in directory.iterdir():
        if item.is_symlink() or not item.is_file():
            raise RuntimeError("V2.45.90 auxiliary surface is nonordinary")
        observed.add(item.name)
    if observed != AUXILIARY_NAMES:
        raise RuntimeError("V2.45.90 auxiliary surface drifted")


def _ordinary_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.45.90 bound artifact is nonordinary")
    return path.read_bytes()


def _object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"V2.45.90 {label} is not UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"V2.45.90 {label} is not an object")
    return value


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
        raise ValueError("V2.45.90 byte receipt is not an object")
    copied = dict(value)
    expected = _byte_receipt(name, raw)
    if set(copied) != BYTE_RECEIPT_KEYS or copied != expected:
        raise ValueError("V2.45.90 byte receipt drifted")
    return copied


def _parent_auxiliary_bytes(output_root: Path, ordinal: int) -> dict[str, bytes]:
    parent = parent_proof.auxiliary_directory(output_root, ordinal)
    parent_proof._exact_auxiliary_surface(parent, output_root=output_root)
    return {name: _ordinary_bytes(parent / name) for name in BOUND_PARENT_NAMES}


def _digest(value: object, label: str) -> str:
    return parent_proof._digest(value, label)


def build_certificate(
    *,
    ordinal: int,
    auxiliary: Path,
    output_root: Path,
    title_query_receipt: Mapping[str, Any],
    validator_manifest_sha256: str,
) -> dict[str, Any]:
    manifest = _digest(
        validator_manifest_sha256, "validator-aligned title-query validator manifest"
    )
    receipt = query_policy.validate_receipt(title_query_receipt)
    receipt_raw = _ordinary_bytes(auxiliary / RECEIPT_NAME)
    if _object(receipt_raw, RECEIPT_NAME) != receipt:
        raise ValueError("V2.45.90 durable title-query receipt drifted")
    parent_raw = _parent_auxiliary_bytes(output_root, ordinal)
    raw = {RECEIPT_NAME: receipt_raw, **parent_raw}
    value = {
        "artifact_version": 1,
        "role": CERTIFICATE_ROLE,
        "policy_id": POLICY_ID,
        "producer_policy_id": query_policy.POLICY_ID,
        "parent_proof_policy_id": parent_proof.POLICY_ID,
        "ordinal": ordinal,
        "validator_manifest_sha256": manifest,
        "artifact_byte_receipts": {
            name: _byte_receipt(name, data) for name, data in raw.items()
        },
        "validator_aligned_title_query_receipt": receipt,
        "v24579_worker_returned_before_title_query_receipt": True,
        "title_query_context_restored_before_receipt": True,
        "frozen_v24579_task_and_auxiliary_surfaces_preserved_exactly": True,
        "parent_must_validate_v24579_capability_before_successor_capability": True,
        "parent_must_not_replay_private_task_row_query_lead_url_title_page_prediction_value_or_search_semantics": True,
        "query_hint_receives_evidence_source_entropy_epistemic_or_decision_credit": False,
        "certificate_created_after_bound_artifacts": True,
        "certificate_is_independently_signed": False,
        "certificate_is_remote_attestation": False,
        "malicious_child_resistance_claimed": False,
        "task_question_opaque_id_entity_query_url_title_page_source_value_prediction_private_content_hash_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder": False,
    }
    value["certificate_payload_sha256"] = payload_sha256(value)
    return validate_certificate(
        value,
        ordinal=ordinal,
        auxiliary=auxiliary,
        output_root=output_root,
        expected_validator_manifest_sha256=manifest,
        require_exact_surface=False,
    )


def validate_certificate(
    value: Mapping[str, Any],
    *,
    ordinal: int,
    auxiliary: Path,
    output_root: Path,
    expected_validator_manifest_sha256: str,
    require_exact_surface: bool = True,
) -> dict[str, Any]:
    manifest = _digest(
        expected_validator_manifest_sha256,
        "expected validator-aligned title-query validator manifest",
    )
    if require_exact_surface:
        _exact_auxiliary_surface(auxiliary, output_root=output_root)
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("certificate_payload_sha256", None)
    receipts = copied.get("artifact_byte_receipts")
    receipt_raw = _ordinary_bytes(auxiliary / RECEIPT_NAME)
    receipt = query_policy.validate_receipt(_object(receipt_raw, RECEIPT_NAME))
    raw = {RECEIPT_NAME: receipt_raw, **_parent_auxiliary_bytes(output_root, ordinal)}
    true_fields = (
        "v24579_worker_returned_before_title_query_receipt",
        "title_query_context_restored_before_receipt",
        "frozen_v24579_task_and_auxiliary_surfaces_preserved_exactly",
        "parent_must_validate_v24579_capability_before_successor_capability",
        "parent_must_not_replay_private_task_row_query_lead_url_title_page_prediction_value_or_search_semantics",
        "certificate_created_after_bound_artifacts",
    )
    false_fields = (
        "query_hint_receives_evidence_source_entropy_epistemic_or_decision_credit",
        "certificate_is_independently_signed",
        "certificate_is_remote_attestation",
        "malicious_child_resistance_claimed",
        "task_question_opaque_id_entity_query_url_title_page_source_value_prediction_private_content_hash_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder",
    )
    if (
        set(copied) != CERTIFICATE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != CERTIFICATE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("producer_policy_id") != query_policy.POLICY_ID
        or copied.get("parent_proof_policy_id") != parent_proof.POLICY_ID
        or copied.get("ordinal") != ordinal
        or copied.get("validator_manifest_sha256") != manifest
        or not isinstance(receipts, Mapping)
        or set(receipts) != set(raw)
        or any(
            _validate_byte_receipt(receipts.get(name), name=name, raw=data)
            != receipts[name]
            for name, data in raw.items()
        )
        or copied.get("validator_aligned_title_query_receipt") != receipt
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.90 title-query certificate drifted")
    return copied


def validate_proof_carrying_title_query_bundle(
    value: Mapping[str, Any],
    *,
    ordinal: int,
    directory: Path,
    output_root: Path,
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
) -> ValidatedProofCarryingValidatorAlignedTitleQuery:
    parent = parent_proof.validate_proof_carrying_prededup_bundle(
        value,
        ordinal=ordinal,
        directory=directory,
        output_root=output_root,
        expected_model_cap=expected_model_cap,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )
    auxiliary = auxiliary_directory(output_root, ordinal)
    certificate_raw = _ordinary_bytes(auxiliary / CERTIFICATE_NAME)
    certificate = validate_certificate(
        _object(certificate_raw, CERTIFICATE_NAME),
        ordinal=ordinal,
        auxiliary=auxiliary,
        output_root=output_root,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )
    return ValidatedProofCarryingValidatorAlignedTitleQuery._create(
        parent=parent,
        receipt=certificate["validator_aligned_title_query_receipt"],
    )


def run_worker(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if (
        len(args) > 1
        or bool(args) and "task" in kwargs
        or not args and "task" not in kwargs
    ):
        raise TypeError("V2.45.90 requires exactly one visible task")
    task = args[0] if args else kwargs["task"]
    from .v24257_score_first_runtime import validate_visible_task

    validate_visible_task(task)
    ordinal = kwargs.get("ordinal")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.90 ordinal is invalid")
    output_root = kwargs.get("output_root")
    directory = kwargs.get("directory")
    checkpoint = kwargs.get("checkpoint_directory")
    if not all(
        isinstance(path, Path) for path in (output_root, directory, checkpoint)
    ):
        raise TypeError("V2.45.90 output layout requires Path values")
    _validate_layout(output_root, directory, checkpoint)
    manifest = _digest(
        kwargs.get("validator_manifest_sha256"),
        "worker validator-aligned title-query manifest",
    )
    auxiliary = auxiliary_directory(output_root, ordinal)
    os.mkdir(auxiliary, 0o700)
    title_query = query_policy.ValidatorAlignedTitleQuery()
    with title_query:
        result = parent_proof.run_worker(*args, **kwargs)
    receipt = query_policy.validate_receipt(title_query.content_free_receipt())
    _new_json(auxiliary / RECEIPT_NAME, receipt)
    certificate = build_certificate(
        ordinal=ordinal,
        auxiliary=auxiliary,
        output_root=output_root,
        title_query_receipt=receipt,
        validator_manifest_sha256=manifest,
    )
    _new_json(auxiliary / CERTIFICATE_NAME, certificate)
    _exact_auxiliary_surface(auxiliary, output_root=output_root)
    return result


supervise_worker_with_separated_budget = (
    parent_proof.supervise_worker_with_separated_budget
)
budget_vector_seconds = parent_proof.budget_vector_seconds

# V2.45.81's copied bounded-parent function resolves this compatibility
# surface.  It now validates the stronger V2.45.90 capability.
ValidatedProofCarryingDecisionReachability = (
    ValidatedProofCarryingValidatorAlignedTitleQuery
)
validate_proof_carrying_decision_reachability_bundle = (
    validate_proof_carrying_title_query_bundle
)


__all__ = [
    "AUXILIARY_NAMES",
    "CERTIFICATE_NAME",
    "POLICY_ID",
    "RECEIPT_NAME",
    "ValidatedProofCarryingDecisionReachability",
    "ValidatedProofCarryingValidatorAlignedTitleQuery",
    "auxiliary_directory",
    "budget_vector_seconds",
    "build_certificate",
    "run_worker",
    "supervise_worker_with_separated_budget",
    "validate_certificate",
    "validate_proof_carrying_decision_reachability_bundle",
    "validate_proof_carrying_title_query_bundle",
]
