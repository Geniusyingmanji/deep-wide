"""Create-exclusive, label-blind preparation for a paired dev64 runtime gate.

V2.42.53 proves that one source-bound V2.42.52 package can be consumed by a
production-shaped ``DeepWideRuntime`` without widening the visible task schema
or page-evidence authority.  It deliberately does not reserve two cold arms,
bind the exact development manifest, or define shared-lease and evaluator
barriers.  This module supplies that preparation boundary.

The launcher package snapshots exactly 64 ``{opaque_id, question}`` rows and a
matching ordered opaque-ID file, but persists only their byte hashes, count,
and schema.  It then create-exclusively prepares disjoint, empty package and
output roots for an unmodified-runtime control and the V2.42.53 candidate.  A
content-free lease intent requires one contiguous repository shared lease to
span both forwards and both evaluators.  Mapping/evaluator access remains
forbidden until a durable two-arm exact-terminal barrier exists; failures stay
in the denominator and neither forward nor evaluator may resume.

This version is preparation-only.  It has no launch, subprocess, network,
credential, lease-acquire, evaluator, mapping, or aggregate-score method and is
not imported by the active runner.  Existing V2.42.16--20 control flow retains
priority and must explicitly authorize any later activation.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Mapping

from deepwide_agent.runtime import MANIFEST_KEYS
from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24253_candidate_runtime_integration import (
    build_candidate_runtime_integration_source_manifest,
    validate_candidate_runtime_integration_contract,
    validate_visible_runtime_task,
)


POLICY_ID = "v24254_candidate_dev64_launcher_v1"
SOURCE_MANIFEST_ROLE = "v24254_candidate_dev64_launcher_source_manifest"
CONTRACT_ROLE = "v24254_candidate_dev64_launcher_contract"
INPUT_SNAPSHOT_ROLE = "v24254_candidate_dev64_visible_input_snapshot"
INITIAL_ROLE = "v24254_candidate_dev64_launcher_initial"
LEASE_INTENT_ROLE = "v24254_candidate_dev64_shared_lease_intent"
READY_ROLE = "v24254_candidate_dev64_launcher_ready"
STATUS_ROLE = "v24254_candidate_dev64_launcher_status"

PARENT_AUDIT_PATH = (
    "results/v24253_candidate_runtime_integration_candidate_audit_v1_20260801.json"
)
PARENT_AUDIT_FILE_SHA256 = (
    "9f627eb24acb2c8f71f3f6def8f151193eedb349d01989e68350e9d89bc662cb"
)
PARENT_AUDIT_PAYLOAD_SHA256 = (
    "24893a166feabaea8a7f3e1efddccceb7244bb6688f89751e5ac1506e6ab1b16"
)
PARENT_AUDIT_CONTROL_MANIFEST_SHA256 = (
    "cfd9d0ce656cc501a74a97203038d1e3591a954d660c889eb5f4169452f31d35"
)
PARENT_CONTROL_RELATIVE_PATHS = (
    "src/deepwide_agent/v24253_candidate_runtime_integration.py",
    "tests/test_v24253_candidate_runtime_integration.py",
    "scripts/audit_v24253_candidate_runtime_integration.py",
    "tests/test_audit_v24253_candidate_runtime_integration.py",
)
UPSTREAM_V24216_RECEIPTS = (
    (
        "results/v24216_package_gate_preregistration_v1_20260731.json",
        "5ad2ba72fda4dc516f922ddc33066a72054c7b082abee50dc7ac0b201a42b714",
        "v24216_package_gate_preregistration",
    ),
    (
        "results/v24216_package_gate_activation_v1_20260731.json",
        "fe3f285142086be6e7e64db5872bbe21b35b103d95747a76f0844bf74c2e30e5",
        "v24216_package_gate_activation",
    ),
    (
        "results/v24216_package_gate_wait_audit_v1_20260731.json",
        "75f70b056e0e780901205e461267e5bd08089c1820d4546e2a8ac181cd491dcb",
        "v24216_package_gate_wait_audit",
    ),
)

PRODUCTION_LAUNCHER_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
DEV64_LAUNCH_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
MAPPING_OR_EVALUATOR_OPEN_AUTHORIZED = False
EXACT220_LAUNCH_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

CREATE_EXCLUSIVE_PAIR_PREPARATION_IMPLEMENTED = True
EXACT_VISIBLE_DEV64_INPUT_SNAPSHOT_IMPLEMENTED = True
TWO_DISJOINT_PRISTINE_ARM_ROOTS_IMPLEMENTED = True
SINGLE_CONTIGUOUS_SHARED_LEASE_CONTRACT_FROZEN = True
TWO_ARM_TERMINAL_BEFORE_EVALUATOR_CONTRACT_FROZEN = True
FAILURE_AS_ZERO_CONTRACT_FROZEN = True
NO_RESUME_OR_SELECTIVE_RERUN_CONTRACT_FROZEN = True
EXISTING_V24216_TO_V24220_PRIORITY_ENFORCED = True
LAUNCH_ACTIVATION_IMPLEMENTED = False
LEASE_ACQUISITION_IMPLEMENTED = False
ARM_EXECUTION_IMPLEMENTED = False
EVALUATOR_EXECUTION_IMPLEMENTED = False
FAILURE_AS_ZERO_AGGREGATE_IMPLEMENTED = False

ARM_ORDER = ("legacy_control", "candidate_runtime")
INITIAL_FILE = "launcher_initial.json"
LEASE_INTENT_FILE = "shared_lease_intent.json"
READY_FILE = "launcher_ready.json"
ARMS_DIRECTORY = "arms"
RECORDS_DIRECTORY = "records"
PACKAGE_DIRECTORY = "package"
OUTPUT_DIRECTORY = "output"
SHARED_LEASE_RELATIVE_PATH = "outputs/deepwide_benchmark_api.lease.lock"
SHARED_LEASE_OWNER = "v24254_candidate_runtime_same_dev64_gate_v1"
SHARED_LEASE_PURPOSE = "paired_runtime_integration_engineering_gate"

OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
MAX_INPUT_FILE_BYTES = 16_000_000
MAX_SOURCE_FILE_BYTES = 8_000_000
MAX_SOURCE_TOTAL_BYTES = 40_000_000
LAUNCHER_SOURCE_RELATIVE_PATHS = (
    "src/deepwide_agent/v24216_package_gate.py",
    "src/deepwide_agent/v24253_candidate_runtime_integration.py",
    "src/deepwide_agent/v24254_candidate_dev64_launcher.py",
    "scripts/deepwide_api_lease.py",
)
LOADED_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

SOURCE_FILE_KEYS = frozenset({"path", "size_bytes", "sha256"})
SOURCE_MANIFEST_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "files",
        "file_count",
        "total_bytes",
        "ordinary_regular_single_link_files",
        "source_manifest_sha256",
    }
)
INPUT_SNAPSHOT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "selected_count",
        "runtime_manifest_sha256",
        "opaque_id_file_sha256",
        "runtime_manifest_schema",
        "manifest_and_id_order_identical",
        "raw_opaque_ids_persisted_or_emitted",
        "questions_persisted_or_emitted",
        "benchmark_labels_mapping_gold_evaluator_or_score_read",
        "input_snapshot_sha256",
    }
)
CONTRACT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_runtime_audit",
        "launcher_source_manifest",
        "launcher_source_manifest_sha256",
        "runtime_integration_contract",
        "runtime_integration_contract_sha256",
        "runtime_source_manifest_sha256",
        "package_contract_sha256",
        "runtime_config_sha256",
        "dev64_identity",
        "visible_task_exact_keys",
        "arm_order",
        "arm_execution_contracts",
        "relative_root_layout",
        "shared_lease_contract",
        "terminal_and_evaluator_barrier_contract",
        "engineering_gate_decision_contract",
        "upstream_priority_contract",
        "create_exclusive_pair_preparation_implemented",
        "launch_activation_implemented",
        "shared_api_lease_acquire_authorized",
        "active_provider_traffic_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "dev64_launch_authorized",
        "exact220_launch_authorized",
        "leaderboard_submission_or_sota_claim_authorized",
        "launcher_contract_sha256",
    }
)
INITIAL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "launcher_contract",
        "launcher_contract_sha256",
        "input_snapshot",
        "input_snapshot_sha256",
        "preparation_only",
        "launcher_initial_sha256",
    }
)
LEASE_INTENT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "launcher_contract_sha256",
        "lease_relative_path",
        "owner",
        "purpose",
        "one_contiguous_lease_spans_both_forwards_and_evaluators",
        "flock_is_authoritative_and_json_record_is_observability_only",
        "lease_acquired",
        "launch_or_evaluator_effect_occurred",
        "lease_intent_sha256",
    }
)
READY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "launcher_contract_sha256",
        "launcher_source_manifest_sha256",
        "runtime_integration_contract_sha256",
        "input_snapshot_sha256",
        "launcher_initial_sha256",
        "lease_intent_sha256",
        "arm_order",
        "relative_root_layout",
        "both_package_and_output_roots_pristine",
        "records_directory_empty",
        "mapping_or_evaluator_opened",
        "lease_acquired",
        "launch_or_provider_effect_occurred",
        "launcher_ready_sha256",
    }
)


class CandidateDev64LauncherError(RuntimeError):
    """Sanitized launcher preparation failure."""


class CandidateDev64LauncherPoisoned(CandidateDev64LauncherError):
    """A source, input, contract, receipt, or root binding drifted."""


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _exact(value: Mapping[str, Any], *, keys: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.54 {label} schema is not exact")
    return dict(value)


def _reject_duplicate_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("V2.42.54 runtime manifest contains duplicate JSON keys")
        value[key] = item
    return value


def _sealed(value: Mapping[str, Any], *, key: str) -> bool:
    seal = value.get(key)
    if not _is_sha256(seal):
        return False
    unsigned = dict(value)
    unsigned.pop(key)
    return seal == object_sha256(unsigned)


def _stable_stat(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _ordinary_directory(path: Path, *, label: str) -> Path:
    candidate = path.absolute()
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ValueError(f"V2.42.54 {label} is absent") from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.is_symlink()
        or path.resolve(strict=True) != candidate
    ):
        raise ValueError(f"V2.42.54 {label} is not an ordinary directory")
    return candidate


def _read_regular_bytes(path: Path, *, label: str, maximum: int) -> bytes:
    candidate = path.absolute()
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ValueError(f"V2.42.54 {label} is absent") from error
    if (
        path.resolve(strict=True) != candidate
        or path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size > maximum
    ):
        raise ValueError(f"V2.42.54 {label} is nonordinary or oversized")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1_048_576, maximum + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > maximum:
                raise ValueError(f"V2.42.54 {label} exceeds the frozen cap")
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    payload = b"".join(chunks)
    if (
        _stable_stat(metadata) != _stable_stat(before)
        or _stable_stat(before) != _stable_stat(after)
        or len(payload) != metadata.st_size
    ):
        raise ValueError(f"V2.42.54 {label} changed during snapshot")
    return payload


def _source_row(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if path.resolve(strict=False) != path.absolute() or not path.is_relative_to(root):
        raise ValueError("V2.42.54 source path is noncanonical")
    payload = _read_regular_bytes(
        path,
        label="launcher source file",
        maximum=MAX_SOURCE_FILE_BYTES,
    )
    return {
        "path": relative,
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def build_candidate_dev64_launcher_source_manifest(
    *, repository_root: Path
) -> dict[str, Any]:
    root = _ordinary_directory(repository_root, label="repository root")
    if root != LOADED_REPOSITORY_ROOT:
        raise ValueError("V2.42.54 repository root does not contain executing modules")
    files = [_source_row(root, relative) for relative in LAUNCHER_SOURCE_RELATIVE_PATHS]
    total = sum(int(row["size_bytes"]) for row in files)
    if total > MAX_SOURCE_TOTAL_BYTES:
        raise ValueError("V2.42.54 launcher source closure exceeds the frozen cap")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": SOURCE_MANIFEST_ROLE,
        "policy_id": POLICY_ID,
        "files": files,
        "file_count": len(files),
        "total_bytes": total,
        "ordinary_regular_single_link_files": True,
    }
    value["source_manifest_sha256"] = object_sha256(value)
    validate_candidate_dev64_launcher_source_manifest(value)
    return value


def validate_candidate_dev64_launcher_source_manifest(
    value: Mapping[str, Any]
) -> None:
    manifest = _exact(value, keys=SOURCE_MANIFEST_KEYS, label="source manifest")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != len(LAUNCHER_SOURCE_RELATIVE_PATHS):
        raise ValueError("V2.42.54 source manifest file set drifted")
    total = 0
    for expected, supplied in zip(LAUNCHER_SOURCE_RELATIVE_PATHS, files, strict=True):
        row = _exact(supplied, keys=SOURCE_FILE_KEYS, label="source file row")
        size = row.get("size_bytes")
        if (
            row.get("path") != expected
            or isinstance(size, bool)
            or not isinstance(size, int)
            or not 0 <= size <= MAX_SOURCE_FILE_BYTES
            or not _is_sha256(row.get("sha256"))
        ):
            raise ValueError("V2.42.54 source manifest row drifted")
        total += size
    if (
        total > MAX_SOURCE_TOTAL_BYTES
        or manifest.get("artifact_version") != 1
        or manifest.get("role") != SOURCE_MANIFEST_ROLE
        or manifest.get("policy_id") != POLICY_ID
        or manifest.get("file_count") != len(LAUNCHER_SOURCE_RELATIVE_PATHS)
        or manifest.get("total_bytes") != total
        or manifest.get("ordinary_regular_single_link_files") is not True
        or not _sealed(manifest, key="source_manifest_sha256")
    ):
        raise ValueError("V2.42.54 source manifest drifted")


def snapshot_visible_dev64_inputs(
    *,
    runtime_manifest_path: Path,
    opaque_id_file_path: Path,
    expected_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate 64 visible tasks while returning no task content."""

    manifest_bytes = _read_regular_bytes(
        runtime_manifest_path,
        label="runtime manifest",
        maximum=MAX_INPUT_FILE_BYTES,
    )
    id_bytes = _read_regular_bytes(
        opaque_id_file_path,
        label="opaque ID file",
        maximum=MAX_INPUT_FILE_BYTES,
    )
    try:
        manifest_text = manifest_bytes.decode("utf-8")
        id_text = id_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("V2.42.54 visible inputs are not UTF-8") from error
    if not manifest_text.endswith("\n") or not id_text.endswith("\n"):
        raise ValueError("V2.42.54 visible inputs require canonical final newlines")
    manifest_lines = manifest_text.splitlines()
    ids = id_text.splitlines()
    if (
        len(manifest_lines) != 64
        or len(ids) != 64
        or len(set(ids)) != 64
        or any(OPAQUE_ID.fullmatch(value) is None for value in ids)
    ):
        raise ValueError("V2.42.54 visible inputs are not exact dev64")
    observed_ids: list[str] = []
    for line in manifest_lines:
        try:
            raw = json.loads(line, object_pairs_hook=_reject_duplicate_object_pairs)
        except json.JSONDecodeError as error:
            raise ValueError("V2.42.54 runtime manifest JSONL is invalid") from error
        task = validate_visible_runtime_task(raw)
        observed_ids.append(task["opaque_id"])
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    ids_sha = hashlib.sha256(id_bytes).hexdigest()
    if (
        observed_ids != ids
        or expected_identity.get("selected_count") != 64
        or expected_identity.get("opaque_id_file_sha256") != ids_sha
        or expected_identity.get("runtime_manifest_sha256") != manifest_sha
        or expected_identity.get("runtime_manifest_schema") != sorted(MANIFEST_KEYS)
        or expected_identity.get("raw_opaque_ids_embedded") is not False
        or expected_identity.get("questions_embedded") is not False
        or expected_identity.get("mapping_gold_evaluator_or_score_read") is not False
        or expected_identity.get("consumed_development_partition") is not True
    ):
        raise ValueError("V2.42.54 visible input identity drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": INPUT_SNAPSHOT_ROLE,
        "policy_id": POLICY_ID,
        "selected_count": 64,
        "runtime_manifest_sha256": manifest_sha,
        "opaque_id_file_sha256": ids_sha,
        "runtime_manifest_schema": sorted(MANIFEST_KEYS),
        "manifest_and_id_order_identical": True,
        "raw_opaque_ids_persisted_or_emitted": False,
        "questions_persisted_or_emitted": False,
        "benchmark_labels_mapping_gold_evaluator_or_score_read": False,
    }
    value["input_snapshot_sha256"] = object_sha256(value)
    validate_visible_dev64_input_snapshot(value)
    return value


def validate_visible_dev64_input_snapshot(value: Mapping[str, Any]) -> None:
    snapshot = _exact(value, keys=INPUT_SNAPSHOT_KEYS, label="input snapshot")
    if (
        snapshot.get("artifact_version") != 1
        or snapshot.get("role") != INPUT_SNAPSHOT_ROLE
        or snapshot.get("policy_id") != POLICY_ID
        or snapshot.get("selected_count") != 64
        or not _is_sha256(snapshot.get("runtime_manifest_sha256"))
        or not _is_sha256(snapshot.get("opaque_id_file_sha256"))
        or snapshot.get("runtime_manifest_schema") != sorted(MANIFEST_KEYS)
        or snapshot.get("manifest_and_id_order_identical") is not True
        or snapshot.get("raw_opaque_ids_persisted_or_emitted") is not False
        or snapshot.get("questions_persisted_or_emitted") is not False
        or snapshot.get(
            "benchmark_labels_mapping_gold_evaluator_or_score_read"
        )
        is not False
        or not _sealed(snapshot, key="input_snapshot_sha256")
    ):
        raise ValueError("V2.42.54 input snapshot drifted")


def _parent_runtime_audit() -> dict[str, Any]:
    return {
        "path": PARENT_AUDIT_PATH,
        "file_sha256": PARENT_AUDIT_FILE_SHA256,
        "payload_sha256": PARENT_AUDIT_PAYLOAD_SHA256,
        "control_manifest_sha256": PARENT_AUDIT_CONTROL_MANIFEST_SHA256,
        "audit_valid": True,
        "candidate_runtime_integration": True,
        "active_runtime_wrapper_available": False,
        "benchmark_score_available": False,
    }


def _validate_parent_runtime_audit(repository_root: Path) -> None:
    root = _ordinary_directory(repository_root, label="repository root")
    receipt_path = root / PARENT_AUDIT_PATH
    receipt_bytes = _read_regular_bytes(
        receipt_path,
        label="parent runtime audit",
        maximum=MAX_INPUT_FILE_BYTES,
    )
    if hashlib.sha256(receipt_bytes).hexdigest() != PARENT_AUDIT_FILE_SHA256:
        raise ValueError("V2.42.54 parent runtime audit bytes drifted")
    try:
        receipt = json.loads(receipt_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("V2.42.54 parent runtime audit is invalid") from error
    if not isinstance(receipt, dict):
        raise ValueError("V2.42.54 parent runtime audit is not an object")
    unsigned = dict(receipt)
    payload = unsigned.pop("audit_payload_sha256", None)
    control = receipt.get("control_surface")
    manifest = control.get("manifest") if isinstance(control, Mapping) else None
    claims = receipt.get("claims")
    if (
        receipt.get("role")
        != "v24253_candidate_runtime_integration_candidate_audit"
        or receipt.get("audit_valid") is not True
        or receipt.get("label_blind_runtime") is not True
        or receipt.get("candidate_deepwide_runtime_integration") is not True
        or payload != PARENT_AUDIT_PAYLOAD_SHA256
        or object_sha256(unsigned) != PARENT_AUDIT_PAYLOAD_SHA256
        or not isinstance(control, Mapping)
        or control.get("manifest_sha256")
        != PARENT_AUDIT_CONTROL_MANIFEST_SHA256
        or not isinstance(manifest, Mapping)
        or set(manifest) != set(PARENT_CONTROL_RELATIVE_PATHS)
        or object_sha256(dict(manifest))
        != PARENT_AUDIT_CONTROL_MANIFEST_SHA256
        or not isinstance(claims, Mapping)
        or claims.get("candidate_deepwide_runtime_integration_available") is not True
        or claims.get("active_runtime_wrapper_available") is not False
        or claims.get("benchmark_score_available") is not False
        or claims.get("sota") is not False
    ):
        raise ValueError("V2.42.54 parent runtime audit semantics drifted")
    for relative in PARENT_CONTROL_RELATIVE_PATHS:
        path = root / relative
        if path.resolve(strict=False) != path.absolute() or not path.is_relative_to(root):
            raise ValueError("V2.42.54 parent control path is noncanonical")
        content = _read_regular_bytes(
            path,
            label="parent runtime control file",
            maximum=MAX_INPUT_FILE_BYTES,
        )
        if hashlib.sha256(content).hexdigest() != manifest[relative]:
            raise ValueError("V2.42.54 parent runtime control file drifted")


def _validate_upstream_v24216_receipts(repository_root: Path) -> None:
    root = _ordinary_directory(repository_root, label="repository root")
    for relative, expected_sha256, expected_role in UPSTREAM_V24216_RECEIPTS:
        path = root / relative
        payload = _read_regular_bytes(
            path,
            label="upstream V2.42.16 receipt",
            maximum=MAX_INPUT_FILE_BYTES,
        )
        if hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise ValueError("V2.42.54 upstream V2.42.16 receipt bytes drifted")
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("V2.42.54 upstream V2.42.16 receipt is invalid") from error
        if not isinstance(value, dict) or value.get("role") != expected_role:
            raise ValueError("V2.42.54 upstream V2.42.16 receipt role drifted")
        if expected_role == "v24216_package_gate_preregistration" and (
            value.get("protocol_id")
            != "v24216_joint_package_paired_cold_same_dev64_gate_v1"
            or value.get("label_blind") is not True
        ):
            raise ValueError("V2.42.54 upstream V2.42.16 protocol drifted")
        if expected_role == "v24216_package_gate_activation" and (
            value.get("activation_valid") is not True
            or value.get("mapping_and_evaluator_only_after_both_forward_arms_terminal")
            is not True
            or value.get("forward_or_evaluator_resume_or_selective_rerun_allowed")
            is not False
            or value.get("benchmark_forward_or_full220_launch_allowed") is not False
        ):
            raise ValueError("V2.42.54 upstream V2.42.16 activation drifted")
        if expected_role == "v24216_package_gate_wait_audit" and (
            value.get("authorization", {}).get(
                "future_dev64_requires_single_shared_lease_and_live_compatibility"
            )
            is not True
            or value.get("authorization", {}).get(
                "future_mapping_requires_both_forward_arms_exact_terminal"
            )
            is not True
            or value.get("authorization", {}).get(
                "future_all220_requires_capacity_freeze_and_separate_single_owner"
            )
            is not True
            or value.get("boundary", {}).get("shared_api_lease_acquired") is not False
            or value.get("boundary", {}).get(
                "network_model_search_fetch_evaluator_or_api_called"
            )
            is not False
            or value.get("boundary", {}).get(
                "benchmark_forward_or_full220_launch_allowed"
            )
            is not False
        ):
            raise ValueError("V2.42.54 upstream V2.42.16 wait audit drifted")


def _arm_execution_contracts(integration: Mapping[str, Any]) -> dict[str, Any]:
    shared = {
        "package_contract_sha256": integration["package_contract_sha256"],
        "runtime_config_sha256": integration["runtime_config_sha256"],
        "launch_limits": _clone(integration["launch_limits"]),
        "exact_visible_task_schema": sorted(MANIFEST_KEYS),
        "same_model_search_fetch_prompt_output_and_total_budget": True,
        "fresh_package_root_required": True,
        "fresh_output_root_required": True,
        "failure_as_zero": True,
        "resume_or_selective_rerun_allowed": False,
    }
    return {
        "legacy_control": {
            **_clone(shared),
            "runtime_kind": "unmodified_deepwide_runtime_with_v24252_package_clients",
            "v24253_checkpoint_and_page_postcondition_wrapper_enabled": False,
        },
        "candidate_runtime": {
            **_clone(shared),
            "runtime_kind": "v24253_candidate_package_deepwide_runtime",
            "v24253_checkpoint_and_page_postcondition_wrapper_enabled": True,
        },
    }


def _relative_root_layout() -> dict[str, Any]:
    return {
        "arms_directory": ARMS_DIRECTORY,
        "records_directory": RECORDS_DIRECTORY,
        "arms": {
            arm: {
                "root": f"{ARMS_DIRECTORY}/{arm}",
                "package_root": f"{ARMS_DIRECTORY}/{arm}/{PACKAGE_DIRECTORY}",
                "output_root": f"{ARMS_DIRECTORY}/{arm}/{OUTPUT_DIRECTORY}",
            }
            for arm in ARM_ORDER
        },
        "all_directories_ordinary_and_disjoint": True,
        "package_and_output_roots_pristine_until_activation": True,
    }


def _shared_lease_contract() -> dict[str, Any]:
    return {
        "lease_relative_path": SHARED_LEASE_RELATIVE_PATH,
        "owner": SHARED_LEASE_OWNER,
        "purpose": SHARED_LEASE_PURPOSE,
        "one_nonblocking_flock_acquisition_required": True,
        "one_contiguous_lease_spans_both_forwards_and_evaluators": True,
        "lease_json_record_is_observability_only": True,
        "lock_descriptor_is_authoritative": True,
        "lease_acquisition_implemented_by_this_module": False,
        "lease_acquire_authorized": False,
    }


def _terminal_barrier_contract() -> dict[str, Any]:
    return {
        "both_arms_exact_terminal_count_required": 64,
        "same_ordered_opaque_ids_required": True,
        "same_runtime_manifest_required": True,
        "forward_failures_remain_in_denominator": True,
        "failure_as_zero": True,
        "forward_resume_or_selective_rerun_allowed": False,
        "mapping_path_open_hash_or_read_before_barrier_allowed": False,
        "evaluator_input_result_or_score_before_barrier_allowed": False,
        "both_evaluators_terminal_before_aggregate_required": True,
        "evaluator_resume_or_selective_rerun_allowed": False,
        "completed_only_primary_metric_allowed": False,
        "dev64_is_consumed_engineering_gate_not_primary_result": True,
    }


def _engineering_gate_decision_contract() -> dict[str, Any]:
    return {
        "gate_kind": "paired_runtime_integration_same_dev64_engineering_gate",
        "thresholds_frozen_before_pair_materialization": True,
        "conservative_denominator": 64,
        "failure_as_zero": True,
        "runtime_completed_non_decrease_required": True,
        "whole_table_success_non_decrease_required": True,
        "each_quality_component_min_delta": -0.005,
        "quality_components": [
            "entity_acc",
            "f1_by_row",
            "f1_by_item",
            "column_f1",
        ],
        "system_total_token_ratio_max": 1.05,
        "minimum_material_improvement_any": {
            "runtime_completed_count_delta": 1,
            "whole_table_success_count_delta": 1,
            "quality_composite_delta": 0.001,
        },
        "candidate_runtime_wrapper_activation_observed_required": True,
        "legacy_control_runtime_wrapper_activation_observed_required": False,
        "mapping_or_score_used_for_forward_routing": False,
        "go_authorizes_only_future_activation_design": True,
        "go_authorizes_exact220_launch": False,
        "threshold_change_after_any_forward_or_evaluator_output_allowed": False,
        "leaderboard_submission_or_sota_claim_authorized": False,
    }


def _upstream_priority_contract() -> dict[str, Any]:
    return {
        "existing_v24216_to_v24220_chain_has_priority": True,
        "v24216_frozen_receipts": [
            {"path": relative, "sha256": digest}
            for relative, digest, _role in UPSTREAM_V24216_RECEIPTS
        ],
        "v24216_terminal_go_and_released_shared_lease_required": True,
        "healthy_r1_or_existing_watcher_may_not_be_signaled_restarted_or_resumed": True,
        "second_full220_or_capacity_probe_allowed": False,
        "this_launcher_may_replace_patch_or_import_active_runner": False,
        "activation_receipt_materialized": False,
    }


def build_candidate_dev64_launcher_contract(
    *,
    repository_root: Path,
    runtime_integration_contract: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_parent_runtime_audit(repository_root)
    _validate_upstream_v24216_receipts(repository_root)
    integration = _clone(dict(runtime_integration_contract))
    validate_candidate_runtime_integration_contract(integration)
    current_runtime_source = build_candidate_runtime_integration_source_manifest(
        repository_root=repository_root
    )
    if current_runtime_source != integration["source_manifest"]:
        raise ValueError("V2.42.54 runtime integration source drifted")
    source = build_candidate_dev64_launcher_source_manifest(
        repository_root=repository_root
    )
    gate = integration["paired_dev64_gate_contract"]
    if (
        gate.get("candidate_and_legacy_control_both_fresh_cold_roots_required")
        is not True
        or gate.get("same_opaque_dev64_ids_required") is not True
        or gate.get("same_runtime_manifest_required") is not True
        or gate.get("both_forwards_exact_terminal_before_mapping_or_evaluator")
        is not True
        or gate.get("failure_as_zero") is not True
        or gate.get("forward_or_evaluator_resume_allowed") is not False
        or gate.get("single_shared_api_lease_required") is not True
        or gate.get("existing_v24216_to_v24220_chain_has_priority") is not True
        or gate.get("dev64_launch_authorized") is not False
        or gate.get("exact220_launch_authorized") is not False
    ):
        raise ValueError("V2.42.54 prospective parent gate contract drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CONTRACT_ROLE,
        "policy_id": POLICY_ID,
        "parent_runtime_audit": _parent_runtime_audit(),
        "launcher_source_manifest": source,
        "launcher_source_manifest_sha256": source["source_manifest_sha256"],
        "runtime_integration_contract": integration,
        "runtime_integration_contract_sha256": integration[
            "integration_contract_sha256"
        ],
        "runtime_source_manifest_sha256": integration["source_manifest_sha256"],
        "package_contract_sha256": integration["package_contract_sha256"],
        "runtime_config_sha256": integration["runtime_config_sha256"],
        "dev64_identity": _clone(integration["dev64_identity"]),
        "visible_task_exact_keys": sorted(MANIFEST_KEYS),
        "arm_order": list(ARM_ORDER),
        "arm_execution_contracts": _arm_execution_contracts(integration),
        "relative_root_layout": _relative_root_layout(),
        "shared_lease_contract": _shared_lease_contract(),
        "terminal_and_evaluator_barrier_contract": _terminal_barrier_contract(),
        "engineering_gate_decision_contract": _engineering_gate_decision_contract(),
        "upstream_priority_contract": _upstream_priority_contract(),
        "create_exclusive_pair_preparation_implemented": True,
        "launch_activation_implemented": False,
        "shared_api_lease_acquire_authorized": False,
        "active_provider_traffic_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
        "dev64_launch_authorized": False,
        "exact220_launch_authorized": False,
        "leaderboard_submission_or_sota_claim_authorized": False,
    }
    value["launcher_contract_sha256"] = object_sha256(value)
    validate_candidate_dev64_launcher_contract(value)
    return value


def validate_candidate_dev64_launcher_contract(value: Mapping[str, Any]) -> None:
    contract = _exact(value, keys=CONTRACT_KEYS, label="launcher contract")
    source = contract.get("launcher_source_manifest")
    integration = contract.get("runtime_integration_contract")
    identity = contract.get("dev64_identity")
    if not all(isinstance(item, Mapping) for item in (source, integration, identity)):
        raise ValueError("V2.42.54 launcher contract parent is invalid")
    validate_candidate_dev64_launcher_source_manifest(source)
    validate_candidate_runtime_integration_contract(integration)
    if (
        contract.get("artifact_version") != 1
        or contract.get("role") != CONTRACT_ROLE
        or contract.get("policy_id") != POLICY_ID
        or contract.get("parent_runtime_audit") != _parent_runtime_audit()
        or contract.get("launcher_source_manifest_sha256")
        != source.get("source_manifest_sha256")
        or contract.get("runtime_integration_contract_sha256")
        != integration.get("integration_contract_sha256")
        or contract.get("runtime_source_manifest_sha256")
        != integration.get("source_manifest_sha256")
        or contract.get("package_contract_sha256")
        != integration.get("package_contract_sha256")
        or contract.get("runtime_config_sha256")
        != integration.get("runtime_config_sha256")
        or identity != integration.get("dev64_identity")
        or identity.get("selected_count") != 64
        or contract.get("visible_task_exact_keys") != sorted(MANIFEST_KEYS)
        or contract.get("arm_order") != list(ARM_ORDER)
        or contract.get("arm_execution_contracts")
        != _arm_execution_contracts(integration)
        or contract.get("relative_root_layout") != _relative_root_layout()
        or contract.get("shared_lease_contract") != _shared_lease_contract()
        or contract.get("terminal_and_evaluator_barrier_contract")
        != _terminal_barrier_contract()
        or contract.get("engineering_gate_decision_contract")
        != _engineering_gate_decision_contract()
        or contract.get("upstream_priority_contract")
        != _upstream_priority_contract()
        or contract.get("create_exclusive_pair_preparation_implemented") is not True
        or any(
            contract.get(field) is not False
            for field in (
                "launch_activation_implemented",
                "shared_api_lease_acquire_authorized",
                "active_provider_traffic_authorized",
                "benchmark_forward_or_evaluator_authorized",
                "dev64_launch_authorized",
                "exact220_launch_authorized",
                "leaderboard_submission_or_sota_claim_authorized",
            )
        )
        or not _sealed(contract, key="launcher_contract_sha256")
    ):
        raise ValueError("V2.42.54 launcher contract drifted")


def _initial_receipt(
    contract: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": INITIAL_ROLE,
        "policy_id": POLICY_ID,
        "launcher_contract": _clone(dict(contract)),
        "launcher_contract_sha256": contract["launcher_contract_sha256"],
        "input_snapshot": _clone(dict(snapshot)),
        "input_snapshot_sha256": snapshot["input_snapshot_sha256"],
        "preparation_only": True,
    }
    value["launcher_initial_sha256"] = object_sha256(value)
    validate_candidate_dev64_launcher_initial(value)
    return value


def validate_candidate_dev64_launcher_initial(value: Mapping[str, Any]) -> None:
    initial = _exact(value, keys=INITIAL_KEYS, label="launcher initial")
    contract = initial.get("launcher_contract")
    snapshot = initial.get("input_snapshot")
    if not isinstance(contract, Mapping) or not isinstance(snapshot, Mapping):
        raise ValueError("V2.42.54 launcher initial parent is invalid")
    validate_candidate_dev64_launcher_contract(contract)
    validate_visible_dev64_input_snapshot(snapshot)
    if (
        initial.get("artifact_version") != 1
        or initial.get("role") != INITIAL_ROLE
        or initial.get("policy_id") != POLICY_ID
        or initial.get("launcher_contract_sha256")
        != contract.get("launcher_contract_sha256")
        or initial.get("input_snapshot_sha256")
        != snapshot.get("input_snapshot_sha256")
        or initial.get("preparation_only") is not True
        or not _sealed(initial, key="launcher_initial_sha256")
    ):
        raise ValueError("V2.42.54 launcher initial drifted")


def _lease_intent_receipt(contract: Mapping[str, Any]) -> dict[str, Any]:
    lease = contract["shared_lease_contract"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": LEASE_INTENT_ROLE,
        "policy_id": POLICY_ID,
        "launcher_contract_sha256": contract["launcher_contract_sha256"],
        "lease_relative_path": lease["lease_relative_path"],
        "owner": lease["owner"],
        "purpose": lease["purpose"],
        "one_contiguous_lease_spans_both_forwards_and_evaluators": True,
        "flock_is_authoritative_and_json_record_is_observability_only": True,
        "lease_acquired": False,
        "launch_or_evaluator_effect_occurred": False,
    }
    value["lease_intent_sha256"] = object_sha256(value)
    validate_candidate_dev64_lease_intent(value, contract=contract)
    return value


def validate_candidate_dev64_lease_intent(
    value: Mapping[str, Any], *, contract: Mapping[str, Any]
) -> None:
    intent = _exact(value, keys=LEASE_INTENT_KEYS, label="lease intent")
    validate_candidate_dev64_launcher_contract(contract)
    lease = contract["shared_lease_contract"]
    if (
        intent.get("artifact_version") != 1
        or intent.get("role") != LEASE_INTENT_ROLE
        or intent.get("policy_id") != POLICY_ID
        or intent.get("launcher_contract_sha256")
        != contract.get("launcher_contract_sha256")
        or intent.get("lease_relative_path") != lease["lease_relative_path"]
        or intent.get("owner") != lease["owner"]
        or intent.get("purpose") != lease["purpose"]
        or intent.get("one_contiguous_lease_spans_both_forwards_and_evaluators")
        is not True
        or intent.get(
            "flock_is_authoritative_and_json_record_is_observability_only"
        )
        is not True
        or intent.get("lease_acquired") is not False
        or intent.get("launch_or_evaluator_effect_occurred") is not False
        or not _sealed(intent, key="lease_intent_sha256")
    ):
        raise ValueError("V2.42.54 lease intent drifted")


def _ready_receipt(
    *,
    contract: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    initial: Mapping[str, Any],
    lease_intent: Mapping[str, Any],
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": READY_ROLE,
        "policy_id": POLICY_ID,
        "launcher_contract_sha256": contract["launcher_contract_sha256"],
        "launcher_source_manifest_sha256": contract[
            "launcher_source_manifest_sha256"
        ],
        "runtime_integration_contract_sha256": contract[
            "runtime_integration_contract_sha256"
        ],
        "input_snapshot_sha256": snapshot["input_snapshot_sha256"],
        "launcher_initial_sha256": initial["launcher_initial_sha256"],
        "lease_intent_sha256": lease_intent["lease_intent_sha256"],
        "arm_order": list(ARM_ORDER),
        "relative_root_layout": _relative_root_layout(),
        "both_package_and_output_roots_pristine": True,
        "records_directory_empty": True,
        "mapping_or_evaluator_opened": False,
        "lease_acquired": False,
        "launch_or_provider_effect_occurred": False,
    }
    value["launcher_ready_sha256"] = object_sha256(value)
    validate_candidate_dev64_launcher_ready(
        value,
        contract=contract,
        snapshot=snapshot,
        initial=initial,
        lease_intent=lease_intent,
    )
    return value


def validate_candidate_dev64_launcher_ready(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    initial: Mapping[str, Any],
    lease_intent: Mapping[str, Any],
) -> None:
    ready = _exact(value, keys=READY_KEYS, label="launcher ready")
    validate_candidate_dev64_launcher_contract(contract)
    validate_visible_dev64_input_snapshot(snapshot)
    validate_candidate_dev64_launcher_initial(initial)
    validate_candidate_dev64_lease_intent(lease_intent, contract=contract)
    if (
        ready.get("artifact_version") != 1
        or ready.get("role") != READY_ROLE
        or ready.get("policy_id") != POLICY_ID
        or ready.get("launcher_contract_sha256")
        != contract.get("launcher_contract_sha256")
        or ready.get("launcher_source_manifest_sha256")
        != contract.get("launcher_source_manifest_sha256")
        or ready.get("runtime_integration_contract_sha256")
        != contract.get("runtime_integration_contract_sha256")
        or ready.get("input_snapshot_sha256")
        != snapshot.get("input_snapshot_sha256")
        or ready.get("launcher_initial_sha256")
        != initial.get("launcher_initial_sha256")
        or ready.get("lease_intent_sha256")
        != lease_intent.get("lease_intent_sha256")
        or ready.get("arm_order") != list(ARM_ORDER)
        or ready.get("relative_root_layout") != _relative_root_layout()
        or ready.get("both_package_and_output_roots_pristine") is not True
        or ready.get("records_directory_empty") is not True
        or ready.get("mapping_or_evaluator_opened") is not False
        or ready.get("lease_acquired") is not False
        or ready.get("launch_or_provider_effect_occurred") is not False
        or not _sealed(ready, key="launcher_ready_sha256")
    ):
        raise ValueError("V2.42.54 launcher ready drifted")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_new(path: Path, value: Mapping[str, Any]) -> None:
    parent = _ordinary_directory(path.parent, label="receipt parent")
    target = path.absolute()
    if target.parent != parent or target.exists() or target.is_symlink():
        raise FileExistsError("V2.42.54 receipt target is not create-exclusive")
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(parent)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _read_object(path: Path) -> dict[str, Any]:
    payload = _read_regular_bytes(path, label="launcher receipt", maximum=MAX_INPUT_FILE_BYTES)
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("V2.42.54 launcher receipt is invalid JSON") from error
    if not isinstance(value, dict):
        raise ValueError("V2.42.54 launcher receipt is not an object")
    return value


def _mkdir(parent: Path, name: str) -> Path:
    path = parent / name
    os.mkdir(path, 0o700)
    _fsync_directory(parent)
    return path


class CandidateDev64LauncherPackage:
    """Prepared two-arm root set with no activation or execution method."""

    def __init__(
        self,
        *,
        root: Path,
        repository_root: Path,
        contract: Mapping[str, Any],
        runtime_manifest_path: Path,
        opaque_id_file_path: Path,
        initial: Mapping[str, Any],
        lease_intent: Mapping[str, Any],
        ready: Mapping[str, Any],
    ) -> None:
        self.root = _ordinary_directory(root, label="launcher root")
        self.repository_root = _ordinary_directory(
            repository_root, label="repository root"
        )
        self.runtime_manifest_path = runtime_manifest_path.absolute()
        self.opaque_id_file_path = opaque_id_file_path.absolute()
        self._contract = _clone(dict(contract))
        self._initial = _clone(dict(initial))
        self._lease_intent = _clone(dict(lease_intent))
        self._ready = _clone(dict(ready))
        self.initial_path = self.root / INITIAL_FILE
        self.lease_intent_path = self.root / LEASE_INTENT_FILE
        self.ready_path = self.root / READY_FILE
        self.arms_root = self.root / ARMS_DIRECTORY
        self.records_root = self.root / RECORDS_DIRECTORY

    @classmethod
    def initialize(
        cls,
        *,
        root: Path,
        repository_root: Path,
        contract: Mapping[str, Any],
        runtime_manifest_path: Path,
        opaque_id_file_path: Path,
    ) -> "CandidateDev64LauncherPackage":
        launcher_root = _ordinary_directory(root, label="launcher root")
        repository = _ordinary_directory(repository_root, label="repository root")
        for protected in (repository / "src", runtime_manifest_path, opaque_id_file_path):
            candidate = protected.absolute()
            if (
                launcher_root == candidate
                or launcher_root.is_relative_to(candidate)
                or candidate.is_relative_to(launcher_root)
            ):
                raise ValueError("V2.42.54 launcher root overlaps protected input")
        if any(launcher_root.iterdir()):
            raise FileExistsError("V2.42.54 launcher root is not pristine")
        frozen = _clone(dict(contract))
        validate_candidate_dev64_launcher_contract(frozen)
        current_source = build_candidate_dev64_launcher_source_manifest(
            repository_root=repository
        )
        current_runtime_source = build_candidate_runtime_integration_source_manifest(
            repository_root=repository
        )
        if (
            current_source != frozen["launcher_source_manifest"]
            or current_runtime_source
            != frozen["runtime_integration_contract"]["source_manifest"]
        ):
            raise CandidateDev64LauncherPoisoned(
                "V2.42.54 source changed before preparation"
            )
        snapshot = snapshot_visible_dev64_inputs(
            runtime_manifest_path=runtime_manifest_path,
            opaque_id_file_path=opaque_id_file_path,
            expected_identity=frozen["dev64_identity"],
        )
        initial = _initial_receipt(frozen, snapshot)
        lease_intent = _lease_intent_receipt(frozen)
        _publish_new(launcher_root / INITIAL_FILE, initial)
        arms = _mkdir(launcher_root, ARMS_DIRECTORY)
        for arm in ARM_ORDER:
            arm_root = _mkdir(arms, arm)
            _mkdir(arm_root, PACKAGE_DIRECTORY)
            _mkdir(arm_root, OUTPUT_DIRECTORY)
        _mkdir(launcher_root, RECORDS_DIRECTORY)
        _publish_new(launcher_root / LEASE_INTENT_FILE, lease_intent)
        ready = _ready_receipt(
            contract=frozen,
            snapshot=snapshot,
            initial=initial,
            lease_intent=lease_intent,
        )
        _publish_new(launcher_root / READY_FILE, ready)
        package = cls(
            root=launcher_root,
            repository_root=repository,
            contract=frozen,
            runtime_manifest_path=runtime_manifest_path,
            opaque_id_file_path=opaque_id_file_path,
            initial=initial,
            lease_intent=lease_intent,
            ready=ready,
        )
        package._require_ready()
        return package

    @classmethod
    def open(
        cls,
        *,
        root: Path,
        repository_root: Path,
        contract: Mapping[str, Any],
        runtime_manifest_path: Path,
        opaque_id_file_path: Path,
    ) -> "CandidateDev64LauncherPackage":
        launcher_root = _ordinary_directory(root, label="launcher root")
        frozen = _clone(dict(contract))
        initial = _read_object(launcher_root / INITIAL_FILE)
        lease_intent = _read_object(launcher_root / LEASE_INTENT_FILE)
        ready = _read_object(launcher_root / READY_FILE)
        package = cls(
            root=launcher_root,
            repository_root=repository_root,
            contract=frozen,
            runtime_manifest_path=runtime_manifest_path,
            opaque_id_file_path=opaque_id_file_path,
            initial=initial,
            lease_intent=lease_intent,
            ready=ready,
        )
        package._require_ready()
        return package

    def arm_roots(self, arm: str) -> dict[str, Path]:
        if arm not in ARM_ORDER:
            raise ValueError("V2.42.54 arm is invalid")
        root = self.arms_root / arm
        return {
            "root": root,
            "package": root / PACKAGE_DIRECTORY,
            "output": root / OUTPUT_DIRECTORY,
        }

    def _require_layout(self) -> None:
        expected_root = {
            self.initial_path,
            self.lease_intent_path,
            self.ready_path,
            self.arms_root,
            self.records_root,
        }
        if set(self.root.iterdir()) != expected_root:
            raise CandidateDev64LauncherPoisoned(
                "V2.42.54 launcher root contains residue or is partial"
            )
        _ordinary_directory(self.arms_root, label="arms directory")
        _ordinary_directory(self.records_root, label="records directory")
        if any(self.records_root.iterdir()):
            raise CandidateDev64LauncherPoisoned(
                "V2.42.54 prelaunch records directory is not empty"
            )
        expected_arms = {self.arms_root / arm for arm in ARM_ORDER}
        if set(self.arms_root.iterdir()) != expected_arms:
            raise CandidateDev64LauncherPoisoned(
                "V2.42.54 launcher arm set drifted"
            )
        observed: list[Path] = []
        for arm in ARM_ORDER:
            roots = self.arm_roots(arm)
            arm_root = _ordinary_directory(roots["root"], label="arm root")
            package_root = _ordinary_directory(
                roots["package"], label="arm package root"
            )
            output_root = _ordinary_directory(
                roots["output"], label="arm output root"
            )
            if set(arm_root.iterdir()) != {package_root, output_root}:
                raise CandidateDev64LauncherPoisoned(
                    "V2.42.54 arm root contains residue"
                )
            if any(package_root.iterdir()) or any(output_root.iterdir()):
                raise CandidateDev64LauncherPoisoned(
                    "V2.42.54 prepared arm roots are not pristine"
                )
            observed.extend((package_root, output_root))
        if len({path.resolve() for path in observed}) != 4:
            raise CandidateDev64LauncherPoisoned(
                "V2.42.54 prepared roots are not disjoint"
            )

    def _require_ready(self) -> dict[str, Any]:
        try:
            _validate_parent_runtime_audit(self.repository_root)
            _validate_upstream_v24216_receipts(self.repository_root)
            validate_candidate_dev64_launcher_contract(self._contract)
            current_source = build_candidate_dev64_launcher_source_manifest(
                repository_root=self.repository_root
            )
            current_runtime_source = build_candidate_runtime_integration_source_manifest(
                repository_root=self.repository_root
            )
            snapshot = snapshot_visible_dev64_inputs(
                runtime_manifest_path=self.runtime_manifest_path,
                opaque_id_file_path=self.opaque_id_file_path,
                expected_identity=self._contract["dev64_identity"],
            )
            initial = _read_object(self.initial_path)
            lease_intent = _read_object(self.lease_intent_path)
            ready = _read_object(self.ready_path)
            validate_candidate_dev64_launcher_initial(initial)
            validate_candidate_dev64_lease_intent(
                lease_intent, contract=self._contract
            )
            validate_candidate_dev64_launcher_ready(
                ready,
                contract=self._contract,
                snapshot=snapshot,
                initial=initial,
                lease_intent=lease_intent,
            )
            self._require_layout()
        except (KeyError, TypeError, ValueError, RuntimeError):
            raise CandidateDev64LauncherPoisoned(
                "V2.42.54 launcher preparation preflight failed"
            ) from None
        if (
            current_source != self._contract["launcher_source_manifest"]
            or current_runtime_source
            != self._contract["runtime_integration_contract"]["source_manifest"]
            or initial != self._initial
            or lease_intent != self._lease_intent
            or ready != self._ready
            or initial["launcher_contract"] != self._contract
            or snapshot != initial["input_snapshot"]
        ):
            raise CandidateDev64LauncherPoisoned(
                "V2.42.54 live launcher binding drifted"
            )
        return snapshot

    def preflight(self) -> dict[str, Any]:
        snapshot = self._require_ready()
        value = {
            "artifact_version": 1,
            "role": STATUS_ROLE,
            "policy_id": POLICY_ID,
            "launcher_contract_sha256": self._contract[
                "launcher_contract_sha256"
            ],
            "launcher_ready_sha256": self._ready["launcher_ready_sha256"],
            "launcher_source_manifest_sha256": self._contract[
                "launcher_source_manifest_sha256"
            ],
            "runtime_integration_contract_sha256": self._contract[
                "runtime_integration_contract_sha256"
            ],
            "input_snapshot_sha256": snapshot["input_snapshot_sha256"],
            "selected_count": 64,
            "arm_order": list(ARM_ORDER),
            "prepared_pristine_package_root_count": 2,
            "prepared_pristine_output_root_count": 2,
            "single_contiguous_shared_lease_required": True,
            "existing_v24216_to_v24220_chain_has_priority": True,
            "label_blind": True,
            "raw_opaque_ids_questions_or_credentials_emitted": False,
            "mapping_gold_category_question_type_evaluator_or_score_read": False,
            "launch_activation_implemented": False,
            "shared_api_lease_acquired": False,
            "provider_model_search_fetch_or_evaluator_called": False,
            "dev64_launch_authorized": False,
            "exact220_launch_authorized": False,
            "leaderboard_submission_or_sota_claim_authorized": False,
        }
        value["status_sha256"] = object_sha256(value)
        return value


__all__ = [
    "ACTIVE_FORWARD_INTEGRATION_AUTHORIZED",
    "ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED",
    "ARM_EXECUTION_IMPLEMENTED",
    "ARM_ORDER",
    "BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED",
    "CandidateDev64LauncherError",
    "CandidateDev64LauncherPackage",
    "CandidateDev64LauncherPoisoned",
    "CREATE_EXCLUSIVE_PAIR_PREPARATION_IMPLEMENTED",
    "DEV64_LAUNCH_AUTHORIZED",
    "EVALUATOR_EXECUTION_IMPLEMENTED",
    "EXACT220_LAUNCH_AUTHORIZED",
    "EXACT_VISIBLE_DEV64_INPUT_SNAPSHOT_IMPLEMENTED",
    "FAILURE_AS_ZERO_AGGREGATE_IMPLEMENTED",
    "FAILURE_AS_ZERO_CONTRACT_FROZEN",
    "LAUNCH_ACTIVATION_IMPLEMENTED",
    "LEASE_ACQUISITION_IMPLEMENTED",
    "LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED",
    "MAPPING_OR_EVALUATOR_OPEN_AUTHORIZED",
    "NO_RESUME_OR_SELECTIVE_RERUN_CONTRACT_FROZEN",
    "PRODUCTION_LAUNCHER_AUTHORIZED",
    "SHARED_API_LEASE_ACQUIRE_AUTHORIZED",
    "SINGLE_CONTIGUOUS_SHARED_LEASE_CONTRACT_FROZEN",
    "TWO_ARM_TERMINAL_BEFORE_EVALUATOR_CONTRACT_FROZEN",
    "TWO_DISJOINT_PRISTINE_ARM_ROOTS_IMPLEMENTED",
    "build_candidate_dev64_launcher_contract",
    "build_candidate_dev64_launcher_source_manifest",
    "snapshot_visible_dev64_inputs",
    "validate_candidate_dev64_launcher_contract",
    "validate_candidate_dev64_launcher_initial",
    "validate_candidate_dev64_launcher_ready",
    "validate_candidate_dev64_launcher_source_manifest",
    "validate_candidate_dev64_lease_intent",
    "validate_visible_dev64_input_snapshot",
]
