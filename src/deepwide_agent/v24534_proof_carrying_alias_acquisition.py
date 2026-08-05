"""Proof-carrying boundary for alias acquisition entropy credit.

The frozen V2.45.25 task artifact surface is preserved byte-for-byte.  A
sibling execution-scoped directory contains exactly one content-free V2.45.33
receipt and one certificate binding that receipt to the frozen alias result
and outer certificate bytes.  The parent validates the old capability once,
then mints a combined opaque capability without replaying private pages.

This is a pinned local-child trust boundary, not a signature, remote
attestation, or malicious-child defence.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24525_proof_carrying_alias_title as alias_proof
from . import v24527_bounded_alias_title_parent as bounded_parent
from . import v24530_alias_seeded_bounded_worker as seeded_worker
from . import v24533_alias_acquisition_entropy_credit as action_credit
from .v24308_child_exit_observability import validate_parent_receipt
from .v24309_runner_exit_integration import _new_json, run_observed_subprocess
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24397_failure_observability import build_task_observation
from .v24399_failure_observable_runner import (
    MODEL_NAME,
    PARENT_NAME,
    RESULT_NAME,
    TRANSPORT_NAME,
    build_directory_observation,
)
from .v24461_proof_carrying_adaptive_timed_runner import (
    ProofCarryingAdaptiveTimedOutcome,
    build_timing_receipt,
)
from .v24470_bounded_adaptive_integration import (
    BoundedAdaptiveParentOutcome,
    _read_supervision_receipt,
    _validate_layout,
)
from .v24480_separated_effect_validation_budget import (
    BATCH_WALL_CEILING_SECONDS,
    PARENT_TOTAL_SECONDS,
    REMOTE_EFFECT_SECONDS,
    WORKER_TOTAL_SECONDS,
    build_phase_deadlines,
    remaining_parent_seconds,
)
from .v24482_separated_budget_worker_integration import append_deadline_origin


POLICY_ID = "v24534_proof_carrying_alias_acquisition_credit_v1"
CERTIFICATE_ROLE = "v24534_alias_acquisition_credit_certificate"
DIRECTORY_PREFIX = "alias_acquisition_credit_"
RECEIPT_NAME = "alias_acquisition_credit_receipt.json"
CERTIFICATE_NAME = "alias_acquisition_credit_certificate.json"
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
        "action_credit_receipt",
        "complete_alias_acquisition_and_action_credit_validation_ran_in_child",
        "frozen_v24525_task_surface_preserved_exactly",
        "certificate_created_after_bound_artifacts",
        "parent_must_not_replay_private_alias_or_acquisition_semantics",
        "certificate_is_independently_signed",
        "certificate_is_remote_attestation",
        "malicious_child_resistance_claimed",
        "task_question_opaque_id_entity_query_url_page_source_value_prediction_private_content_hash_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_certificate_builder",
        "certificate_payload_sha256",
    }
)


class ValidatedProofCarryingAliasAcquisition:
    """Opaque capability combining V2.45.25 proof and V2.45.33 receipt."""

    __slots__ = ("__parent", "__receipt")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use validate_proof_carrying_alias_acquisition_bundle")

    @classmethod
    def _create(
        cls,
        *,
        parent: alias_proof.ValidatedProofCarryingAliasTitle,
        receipt: Mapping[str, Any],
    ) -> "ValidatedProofCarryingAliasAcquisition":
        if not isinstance(parent, alias_proof.ValidatedProofCarryingAliasTitle):
            raise TypeError("V2.45.34 requires V2.45.25 capability")
        instance = object.__new__(cls)
        instance.__parent = parent
        instance.__receipt = copy.deepcopy(dict(receipt))
        return instance

    def parent_capability(self) -> alias_proof.ValidatedProofCarryingAliasTitle:
        return self.__parent

    def action_credit_receipt(self) -> dict[str, Any]:
        return copy.deepcopy(self.__receipt)

    def content_free_observation_receipts(self) -> dict[str, Any]:
        return self.__parent.content_free_observation_receipts()


def auxiliary_directory(output_root: Path, ordinal: int) -> Path:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.34 ordinal is invalid")
    root = output_root.resolve()
    if output_root.is_symlink() or not output_root.is_dir():
        raise RuntimeError("V2.45.34 output root is nonordinary")
    path = output_root / f"{DIRECTORY_PREFIX}{ordinal:06d}"
    if path.resolve(strict=False).parent != root:
        raise RuntimeError("V2.45.34 auxiliary directory escaped output root")
    return path


def _ordinary_directory(path: Path, *, output_root: Path) -> Path:
    root = output_root.resolve()
    if (
        path.is_symlink()
        or not path.is_dir()
        or path.resolve().parent != root
    ):
        raise RuntimeError("V2.45.34 auxiliary directory is nonordinary")
    return path.resolve()


def _exact_auxiliary_surface(path: Path, *, output_root: Path) -> None:
    directory = _ordinary_directory(path, output_root=output_root)
    observed: set[str] = set()
    for item in directory.iterdir():
        if item.is_symlink() or not item.is_file():
            raise RuntimeError("V2.45.34 auxiliary surface is nonordinary")
        observed.add(item.name)
    if observed != AUXILIARY_NAMES:
        raise RuntimeError("V2.45.34 auxiliary surface drifted")


def _ordinary_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.45.34 bound artifact is nonordinary")
    return path.read_bytes()


def _object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"V2.45.34 {label} is not UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"V2.45.34 {label} is not an object")
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
        raise ValueError("V2.45.34 byte receipt is not an object")
    copied = dict(value)
    expected = _byte_receipt(name, raw)
    if set(copied) != BYTE_RECEIPT_KEYS or copied != expected:
        raise ValueError("V2.45.34 byte receipt drifted")
    return copied


def build_certificate(
    *,
    ordinal: int,
    directory: Path,
    auxiliary: Path,
    output_root: Path,
    action_receipt: Mapping[str, Any],
    validator_manifest_sha256: str,
) -> dict[str, Any]:
    manifest = alias_proof._digest(
        validator_manifest_sha256, "acquisition validator manifest"
    )
    receipt = action_credit.validate_action_credit_receipt(action_receipt)
    receipt_raw = _ordinary_bytes(auxiliary / RECEIPT_NAME)
    if _object(receipt_raw, RECEIPT_NAME) != receipt:
        raise ValueError("V2.45.34 durable action receipt drifted")
    task_raw = {
        name: _ordinary_bytes(directory / name) for name in BOUND_TASK_NAMES
    }
    value = {
        "artifact_version": 1,
        "role": CERTIFICATE_ROLE,
        "policy_id": POLICY_ID,
        "producer_policy_id": action_credit.POLICY_ID,
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
        "action_credit_receipt": receipt,
        "complete_alias_acquisition_and_action_credit_validation_ran_in_child": True,
        "frozen_v24525_task_surface_preserved_exactly": True,
        "certificate_created_after_bound_artifacts": True,
        "parent_must_not_replay_private_alias_or_acquisition_semantics": True,
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
        "expected acquisition validator manifest",
    )
    if require_exact_surface:
        _exact_auxiliary_surface(auxiliary, output_root=output_root)
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("certificate_payload_sha256", None)
    receipts = copied.get("artifact_byte_receipts")
    receipt_raw = _ordinary_bytes(auxiliary / RECEIPT_NAME)
    receipt = action_credit.validate_action_credit_receipt(
        _object(receipt_raw, RECEIPT_NAME)
    )
    raw = {
        RECEIPT_NAME: receipt_raw,
        **{
            name: _ordinary_bytes(directory / name) for name in BOUND_TASK_NAMES
        },
    }
    true_fields = (
        "complete_alias_acquisition_and_action_credit_validation_ran_in_child",
        "frozen_v24525_task_surface_preserved_exactly",
        "certificate_created_after_bound_artifacts",
        "parent_must_not_replay_private_alias_or_acquisition_semantics",
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
        or copied.get("producer_policy_id") != action_credit.POLICY_ID
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
        or copied.get("action_credit_receipt") != receipt
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.34 certificate drifted")
    return copied


def validate_proof_carrying_alias_acquisition_bundle(
    value: Mapping[str, Any],
    *,
    ordinal: int,
    directory: Path,
    output_root: Path,
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
) -> ValidatedProofCarryingAliasAcquisition:
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
    return ValidatedProofCarryingAliasAcquisition._create(
        parent=parent,
        receipt=certificate["action_credit_receipt"],
    )


def run_worker(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if (
        len(args) > 1
        or bool(args) and "task" in kwargs
        or not args and "task" not in kwargs
    ):
        raise TypeError("V2.45.34 requires exactly one visible task")
    task = args[0] if args else kwargs["task"]
    from .v24257_score_first_runtime import validate_visible_task

    validate_visible_task(task)
    ordinal = kwargs.get("ordinal")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.34 ordinal is invalid")
    output_root = kwargs.get("output_root")
    directory = kwargs.get("directory")
    checkpoint = kwargs.get("checkpoint_directory")
    if not all(isinstance(path, Path) for path in (output_root, directory, checkpoint)):
        raise TypeError("V2.45.34 output layout requires Path values")
    _validate_layout(output_root, directory, checkpoint)
    manifest = alias_proof._digest(
        kwargs.get("validator_manifest_sha256"), "worker validator manifest"
    )
    auxiliary = auxiliary_directory(output_root, ordinal)
    os.mkdir(auxiliary, 0o700)
    result, acquisition_receipt = (
        seeded_worker.run_alias_seeded_worker_with_receipt(*args, **kwargs)
    )
    action_receipt = action_credit.build_action_credit_receipt(
        result, acquisition_receipt
    )
    _new_json(auxiliary / RECEIPT_NAME, action_receipt)
    certificate = build_certificate(
        ordinal=ordinal,
        directory=directory,
        auxiliary=auxiliary,
        output_root=output_root,
        action_receipt=action_receipt,
        validator_manifest_sha256=manifest,
    )
    _new_json(auxiliary / CERTIFICATE_NAME, certificate)
    _exact_auxiliary_surface(auxiliary, output_root=output_root)
    return result


def run_timed_subprocess(
    *,
    ordinal: int,
    cwd: Path,
    output_root: Path,
    directory: Path,
    command: Sequence[str],
    environment: Mapping[str, str],
    timeout_seconds: float,
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
    monotonic: Callable[[], float] = time.monotonic,
    popen: Any = None,
) -> ProofCarryingAdaptiveTimedOutcome:
    capabilities: list[ValidatedProofCarryingAliasAcquisition] = []
    child_wall = 0.0
    child_started = 0.0
    certificate_wall = 0.0
    certificate_invocations = 0

    def result_validator(value: Mapping[str, Any]) -> object:
        nonlocal certificate_invocations, certificate_wall
        certificate_invocations += 1
        started = monotonic()
        try:
            capability = validate_proof_carrying_alias_acquisition_bundle(
                value,
                ordinal=ordinal,
                directory=directory,
                output_root=output_root,
                expected_model_cap=expected_model_cap,
                expected_validator_manifest_sha256=(
                    expected_validator_manifest_sha256
                ),
            )
            capabilities.append(capability)
            return capability
        finally:
            certificate_wall += max(0.0, monotonic() - started)

    def model_validator(value: Mapping[str, Any]) -> object:
        nonlocal certificate_wall
        started = monotonic()
        try:
            return validate_model_receipt(dict(value), expected_cap=expected_model_cap)
        finally:
            certificate_wall += max(0.0, monotonic() - started)

    def transport_validator(value: Mapping[str, Any]) -> object:
        nonlocal certificate_wall
        started = monotonic()
        try:
            return validate_transport_health(value)
        finally:
            certificate_wall += max(0.0, monotonic() - started)

    base_popen = subprocess.Popen if popen is None else popen

    class TimedProcess:
        def __init__(self, inner: Any) -> None:
            self.inner = inner

        @property
        def pid(self) -> int:
            return int(self.inner.pid)

        @property
        def returncode(self) -> int | None:
            return self.inner.returncode

        def wait(self, timeout: float | None = None) -> int:
            nonlocal child_wall
            try:
                return int(self.inner.wait(timeout=timeout))
            finally:
                if self.inner.returncode is not None:
                    child_wall = max(0.0, monotonic() - child_started)

    def timed_popen(*args: Any, **kwargs: Any) -> TimedProcess:
        nonlocal child_started, child_wall
        child_started = monotonic()
        try:
            return TimedProcess(base_popen(*args, **kwargs))
        except BaseException:
            child_wall = max(0.0, monotonic() - child_started)
            raise

    outcome = run_observed_subprocess(
        cwd=cwd,
        output_root=output_root,
        directory=directory,
        command=command,
        environment=environment,
        timeout_seconds=timeout_seconds,
        result_validator=result_validator,
        model_receipt_validator=model_validator,
        transport_receipt_validator=transport_validator,
        result_name=RESULT_NAME,
        model_receipt_name=MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name="child_terminal_receipt.json",
        parent_name=PARENT_NAME,
        popen=timed_popen,
    )
    parent_receipt = validate_parent_receipt(outcome.receipt)
    success = parent_receipt["failure_taxonomy"] == "success"
    observation_started = monotonic()
    capability_observation = False
    failure_lower_bound = False
    try:
        if success:
            if certificate_invocations != 1 or len(capabilities) != 1:
                raise RuntimeError("V2.45.34 success lacks one capability")
            bounded_parent._validate_success_surface(directory)
            receipts = capabilities[0].content_free_observation_receipts()
            observation = build_task_observation(
                ordinal,
                parent_receipt,
                child=receipts["child"],
                failure_snapshot=None,
                model_receipt=receipts["model"],
                transport_health=receipts["transport"],
                search_receipt=receipts["search"],
                expected_model_cap=expected_model_cap,
            )
            capability_observation = True
        else:
            observation = build_directory_observation(
                ordinal,
                parent_receipt,
                directory=directory,
                expected_model_cap=expected_model_cap,
            )
            failure_lower_bound = True
    finally:
        observation_wall = max(0.0, monotonic() - observation_started)
    from . import v24535_total_alias_acquisition_projection as total

    projection = total.failure_projection(ordinal)
    projection_wall = 0.0
    projection_invocations = 0
    capability_projection = False
    if success:
        projection_invocations = 1
        started = monotonic()
        try:
            projection = total.task_projection(ordinal, capabilities[0])
            capability_projection = True
        finally:
            projection_wall = max(0.0, monotonic() - started)
    total.validate_total_row(projection)
    timing = build_timing_receipt(
        ordinal=ordinal,
        parent=parent_receipt,
        child_wall_seconds=child_wall,
        certificate_validation_wall_seconds=certificate_wall,
        observation_projection_wall_seconds=observation_wall,
        adaptive_projection_wall_seconds=projection_wall,
        certificate_validation_invocations=certificate_invocations,
        observation_projection_invocations=1,
        adaptive_projection_invocations=projection_invocations,
        child_complete_validation_attested=success,
        certificate_validated_once=success and len(capabilities) == 1,
        capability_observation=capability_observation,
        capability_adaptive_projection=capability_projection,
        failure_lower_bound_observation=failure_lower_bound,
    )
    return ProofCarryingAdaptiveTimedOutcome(
        parent_receipt=parent_receipt,
        adaptive_projection=projection,
        observation=observation,
        timing_receipt=timing,
    )


supervise_worker_with_separated_budget = (
    bounded_parent.supervise_alias_title_worker_with_separated_budget
)


def run_parent_with_separated_budget(
    *,
    ordinal: int,
    cwd: Path,
    output_root: Path,
    directory: Path,
    checkpoint_directory: Path,
    supervisor_command: Sequence[str],
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
    monotonic: Callable[[], float] = time.monotonic,
) -> BoundedAdaptiveParentOutcome:
    deadlines = build_phase_deadlines(monotonic=monotonic)
    proof = run_timed_subprocess(
        ordinal=ordinal,
        cwd=cwd,
        output_root=output_root,
        directory=directory,
        command=append_deadline_origin(supervisor_command, deadlines),
        environment={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        timeout_seconds=remaining_parent_seconds(deadlines, monotonic=monotonic),
        expected_model_cap=expected_model_cap,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
        monotonic=monotonic,
    )
    supervision = _read_supervision_receipt(
        checkpoint_directory, ordinal=ordinal
    )
    success = proof.parent_receipt["failure_taxonomy"] == "success"
    if success is not (
        supervision["worker_hard_timeout"] is False
        and supervision["return_code"] == 0
        and supervision["last_stage"] == "worker_complete"
    ):
        raise RuntimeError("V2.45.34 proof/supervision outcome drifted")
    return BoundedAdaptiveParentOutcome(
        proof=proof, supervision_receipt=supervision
    )


def budget_vector_seconds() -> tuple[float, float, float, float]:
    value = (
        REMOTE_EFFECT_SECONDS,
        WORKER_TOTAL_SECONDS,
        PARENT_TOTAL_SECONDS,
        BATCH_WALL_CEILING_SECONDS,
    )
    if value != (150.0, 220.0, 245.0, 255.0):
        raise RuntimeError("V2.45.34 inherited budget vector drifted")
    return value


__all__ = [
    "AUXILIARY_NAMES",
    "CERTIFICATE_NAME",
    "POLICY_ID",
    "RECEIPT_NAME",
    "ValidatedProofCarryingAliasAcquisition",
    "auxiliary_directory",
    "budget_vector_seconds",
    "build_certificate",
    "run_parent_with_separated_budget",
    "run_timed_subprocess",
    "run_worker",
    "supervise_worker_with_separated_budget",
    "validate_certificate",
    "validate_proof_carrying_alias_acquisition_bundle",
]
