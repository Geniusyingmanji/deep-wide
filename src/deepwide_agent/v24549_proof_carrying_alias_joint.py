"""Proof-carrying boundary for V2.45.48 alias/action joint observability.

The frozen V2.45.25 task artifact surface remains byte-for-byte unchanged.  A
new sibling directory contains exactly one content-free V2.45.48 receipt and
one certificate binding that receipt to the frozen alias result and outer
certificate bytes.  Parent validation mints an opaque capability without
replaying task, page, or acquisition semantics.

This is a pinned local-child trust boundary, not a signature, remote
attestation, or malicious-child defence.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24525_proof_carrying_alias_title as alias_proof
from . import v24527_bounded_alias_title_parent as bounded_parent
from . import v24548_alias_action_joint_observability as joint
from .v24309_runner_exit_integration import _new_json
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24470_bounded_adaptive_integration import _validate_layout


POLICY_ID = "v24549_proof_carrying_alias_action_joint_v1"
CERTIFICATE_ROLE = "v24549_alias_action_joint_certificate"
DIRECTORY_PREFIX = "alias_action_joint_"
RECEIPT_NAME = "alias_action_joint_receipt.json"
CERTIFICATE_NAME = "alias_action_joint_certificate.json"
AUXILIARY_NAMES = frozenset({RECEIPT_NAME, CERTIFICATE_NAME})
BOUND_TASK_NAMES = (
    alias_proof.ALIAS_RESULT_NAME,
    alias_proof.CERTIFICATE_NAME,
)
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
        "joint_observability_receipt",
        "complete_alias_surface_joint_and_action_credit_validation_ran_in_child",
        "frozen_v24525_task_surface_preserved_exactly",
        "certificate_created_after_bound_artifacts",
        "parent_must_not_replay_private_alias_surface_or_action_semantics",
        "same_task_joint_counts_do_not_claim_lead_level_causality",
        "certificate_is_independently_signed",
        "certificate_is_remote_attestation",
        "malicious_child_resistance_claimed",
        "task_question_opaque_id_entity_query_url_page_source_value_prediction_private_content_hash_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder",
        "certificate_payload_sha256",
    }
)


class ValidatedProofCarryingAliasJoint:
    """Opaque capability combining V2.45.25 proof and V2.45.48 receipt."""

    __slots__ = ("__parent", "__receipt")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use validate_proof_carrying_alias_joint_bundle")

    @classmethod
    def _create(
        cls,
        *,
        parent: alias_proof.ValidatedProofCarryingAliasTitle,
        receipt: Mapping[str, Any],
    ) -> "ValidatedProofCarryingAliasJoint":
        if not isinstance(parent, alias_proof.ValidatedProofCarryingAliasTitle):
            raise TypeError("V2.45.49 requires V2.45.25 capability")
        validated = joint.validate_joint_receipt(receipt)
        instance = object.__new__(cls)
        instance.__parent = parent
        instance.__receipt = copy.deepcopy(validated)
        return instance

    def parent_capability(self) -> alias_proof.ValidatedProofCarryingAliasTitle:
        return self.__parent

    def joint_observability_receipt(self) -> dict[str, Any]:
        return copy.deepcopy(self.__receipt)

    def content_free_observation_receipts(self) -> dict[str, Any]:
        return self.__parent.content_free_observation_receipts()


def auxiliary_directory(output_root: Path, ordinal: int) -> Path:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.49 ordinal is invalid")
    root = output_root.resolve()
    if output_root.is_symlink() or not output_root.is_dir():
        raise RuntimeError("V2.45.49 output root is nonordinary")
    path = output_root / f"{DIRECTORY_PREFIX}{ordinal:06d}"
    if path.resolve(strict=False).parent != root:
        raise RuntimeError("V2.45.49 auxiliary directory escaped output root")
    return path


def _ordinary_directory(path: Path, *, output_root: Path) -> Path:
    root = output_root.resolve()
    if path.is_symlink() or not path.is_dir() or path.resolve().parent != root:
        raise RuntimeError("V2.45.49 auxiliary directory is nonordinary")
    return path.resolve()


def _exact_auxiliary_surface(path: Path, *, output_root: Path) -> None:
    directory = _ordinary_directory(path, output_root=output_root)
    observed: set[str] = set()
    for item in directory.iterdir():
        if item.is_symlink() or not item.is_file():
            raise RuntimeError("V2.45.49 auxiliary surface is nonordinary")
        observed.add(item.name)
    if observed != AUXILIARY_NAMES:
        raise RuntimeError("V2.45.49 auxiliary surface drifted")


def _ordinary_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.45.49 bound artifact is nonordinary")
    return path.read_bytes()


def _object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"V2.45.49 {label} is not UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"V2.45.49 {label} is not an object")
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
        raise ValueError("V2.45.49 byte receipt is not an object")
    copied = dict(value)
    expected = _byte_receipt(name, raw)
    if set(copied) != BYTE_RECEIPT_KEYS or copied != expected:
        raise ValueError("V2.45.49 byte receipt drifted")
    return copied


def build_certificate(
    *,
    ordinal: int,
    directory: Path,
    auxiliary: Path,
    output_root: Path,
    joint_receipt: Mapping[str, Any],
    validator_manifest_sha256: str,
) -> dict[str, Any]:
    manifest = alias_proof._digest(
        validator_manifest_sha256, "joint validator manifest"
    )
    receipt = joint.validate_joint_receipt(joint_receipt)
    receipt_raw = _ordinary_bytes(auxiliary / RECEIPT_NAME)
    if _object(receipt_raw, RECEIPT_NAME) != receipt:
        raise ValueError("V2.45.49 durable joint receipt drifted")
    task_raw = {
        name: _ordinary_bytes(directory / name) for name in BOUND_TASK_NAMES
    }
    value = {
        "artifact_version": 1,
        "role": CERTIFICATE_ROLE,
        "policy_id": POLICY_ID,
        "producer_policy_id": joint.POLICY_ID,
        "parent_proof_policy_id": alias_proof.POLICY_ID,
        "ordinal": ordinal,
        "validator_manifest_sha256": manifest,
        "artifact_byte_receipts": {
            RECEIPT_NAME: _byte_receipt(RECEIPT_NAME, receipt_raw),
            **{
                name: _byte_receipt(name, raw)
                for name, raw in task_raw.items()
            },
        },
        "joint_observability_receipt": receipt,
        "complete_alias_surface_joint_and_action_credit_validation_ran_in_child": True,
        "frozen_v24525_task_surface_preserved_exactly": True,
        "certificate_created_after_bound_artifacts": True,
        "parent_must_not_replay_private_alias_surface_or_action_semantics": True,
        "same_task_joint_counts_do_not_claim_lead_level_causality": True,
        "certificate_is_independently_signed": False,
        "certificate_is_remote_attestation": False,
        "malicious_child_resistance_claimed": False,
        "task_question_opaque_id_entity_query_url_page_source_value_prediction_private_content_hash_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder": False,
    }
    value["certificate_payload_sha256"] = payload_sha256(value)
    return validate_certificate(
        value,
        ordinal=ordinal,
        directory=directory,
        auxiliary=auxiliary,
        output_root=output_root,
        expected_validator_manifest_sha256=manifest,
        require_exact_surface=False,
    )


def validate_certificate(
    value: Mapping[str, Any],
    *,
    ordinal: int,
    directory: Path,
    auxiliary: Path,
    output_root: Path,
    expected_validator_manifest_sha256: str,
    require_exact_surface: bool = True,
) -> dict[str, Any]:
    manifest = alias_proof._digest(
        expected_validator_manifest_sha256,
        "expected joint validator manifest",
    )
    if require_exact_surface:
        _exact_auxiliary_surface(auxiliary, output_root=output_root)
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("certificate_payload_sha256", None)
    receipts = copied.get("artifact_byte_receipts")
    receipt_raw = _ordinary_bytes(auxiliary / RECEIPT_NAME)
    receipt = joint.validate_joint_receipt(_object(receipt_raw, RECEIPT_NAME))
    raw = {
        RECEIPT_NAME: receipt_raw,
        **{
            name: _ordinary_bytes(directory / name) for name in BOUND_TASK_NAMES
        },
    }
    true_fields = (
        "complete_alias_surface_joint_and_action_credit_validation_ran_in_child",
        "frozen_v24525_task_surface_preserved_exactly",
        "certificate_created_after_bound_artifacts",
        "parent_must_not_replay_private_alias_surface_or_action_semantics",
        "same_task_joint_counts_do_not_claim_lead_level_causality",
    )
    false_fields = (
        "certificate_is_independently_signed",
        "certificate_is_remote_attestation",
        "malicious_child_resistance_claimed",
        "task_question_opaque_id_entity_query_url_page_source_value_prediction_private_content_hash_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder",
    )
    if (
        set(copied) != CERTIFICATE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != CERTIFICATE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("producer_policy_id") != joint.POLICY_ID
        or copied.get("parent_proof_policy_id") != alias_proof.POLICY_ID
        or copied.get("ordinal") != ordinal
        or copied.get("validator_manifest_sha256") != manifest
        or not isinstance(receipts, Mapping)
        or set(receipts) != set(raw)
        or any(
            _validate_byte_receipt(receipts.get(name), name=name, raw=data)
            != receipts[name]
            for name, data in raw.items()
        )
        or copied.get("joint_observability_receipt") != receipt
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.49 certificate drifted")
    return copied


def validate_proof_carrying_alias_joint_bundle(
    value: Mapping[str, Any],
    *,
    ordinal: int,
    directory: Path,
    output_root: Path,
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
) -> ValidatedProofCarryingAliasJoint:
    parent = alias_proof.validate_proof_carrying_alias_bundle(
        value,
        directory=directory,
        expected_model_cap=expected_model_cap,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )
    auxiliary = auxiliary_directory(output_root, ordinal)
    certificate_raw = _ordinary_bytes(auxiliary / CERTIFICATE_NAME)
    certificate = validate_certificate(
        _object(certificate_raw, CERTIFICATE_NAME),
        ordinal=ordinal,
        directory=directory,
        auxiliary=auxiliary,
        output_root=output_root,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )
    return ValidatedProofCarryingAliasJoint._create(
        parent=parent,
        receipt=certificate["joint_observability_receipt"],
    )


def run_worker(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if (
        len(args) > 1
        or bool(args) and "task" in kwargs
        or not args and "task" not in kwargs
    ):
        raise TypeError("V2.45.49 requires exactly one visible task")
    task = args[0] if args else kwargs["task"]
    from .v24257_score_first_runtime import validate_visible_task

    # Reject privileged fields before directory creation or any remote effect.
    validate_visible_task(task)
    ordinal = kwargs.get("ordinal")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.49 ordinal is invalid")
    output_root = kwargs.get("output_root")
    directory = kwargs.get("directory")
    checkpoint = kwargs.get("checkpoint_directory")
    if not all(isinstance(path, Path) for path in (output_root, directory, checkpoint)):
        raise TypeError("V2.45.49 output layout requires Path values")
    _validate_layout(output_root, directory, checkpoint)
    manifest = alias_proof._digest(
        kwargs.get("validator_manifest_sha256"), "worker validator manifest"
    )
    auxiliary = auxiliary_directory(output_root, ordinal)
    os.mkdir(auxiliary, 0o700)
    result, joint_receipt = joint.run_alias_surface_worker_with_receipt(
        *args, **kwargs
    )
    _new_json(auxiliary / RECEIPT_NAME, joint_receipt)
    certificate = build_certificate(
        ordinal=ordinal,
        directory=directory,
        auxiliary=auxiliary,
        output_root=output_root,
        joint_receipt=joint_receipt,
        validator_manifest_sha256=manifest,
    )
    _new_json(auxiliary / CERTIFICATE_NAME, certificate)
    _exact_auxiliary_surface(auxiliary, output_root=output_root)
    return result


supervise_worker_with_separated_budget = (
    bounded_parent.supervise_alias_title_worker_with_separated_budget
)
budget_vector_seconds = bounded_parent.budget_vector_seconds


__all__ = [
    "AUXILIARY_NAMES",
    "CERTIFICATE_NAME",
    "POLICY_ID",
    "RECEIPT_NAME",
    "ValidatedProofCarryingAliasJoint",
    "auxiliary_directory",
    "budget_vector_seconds",
    "build_certificate",
    "run_worker",
    "supervise_worker_with_separated_budget",
    "validate_certificate",
    "validate_proof_carrying_alias_joint_bundle",
]
