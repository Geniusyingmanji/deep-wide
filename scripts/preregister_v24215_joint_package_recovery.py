#!/usr/bin/env python3
"""Freeze the versioned V2.42.15 joint-package path recovery."""

from __future__ import annotations

import argparse
import ast
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from deepwide_agent.v24215_joint_package_recovery import (  # noqa: E402
    ACTUAL_ENTROPY_PATH,
    FAILED_AUDIT_PATH,
    FAILED_AUDIT_SHA256,
    FROZEN_WRONG_ENTROPY_PATH,
    build_recovery_manifest,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    _start_ticks,
    ordinary,
    publish_new,
    read_object,
    sha256,
)
from scripts.preregister_v24212_entropy_component import (  # noqa: E402
    MUST_REMAIN_ABSENT,
)
from scripts.preregister_v24214_joint_package import (  # noqa: E402
    PARENT_ACTIVATION,
    PARENT_ACTIVATION_SHA256,
    PARENT_PROTOCOL,
    PARENT_PROTOCOL_SHA256,
    PARENT_STATE,
    PARENT_WAIT_AUDIT,
    PARENT_WAIT_AUDIT_SHA256,
    protected_processes,
)
from scripts.publish_v24214_joint_package import (  # noqa: E402
    COMPONENT_PUBLICATIONS,
    SELECTED_WORK_ORDER,
)
from scripts.publish_v24215_joint_package_recovery import (  # noqa: E402
    CANDIDATE_ROOT,
    OUTPUT as PUBLICATION,
)


ROLE = "v24215_selected_joint_package_recovery_preregistration"
PROTOCOL_ID = "v24215_joint_package_entropy_path_recovery_v1"
OUTPUT = Path(
    "results/v24215_selected_joint_package_recovery_preregistration_v1_20260731.json"
)
STATE = Path(
    "outputs/v24215_selected_joint_package_recovery_state_v1_20260731.json"
)
ACTIVATION = Path(
    "results/v24215_selected_joint_package_recovery_activation_v1_20260731.json"
)
WAIT_AUDIT = Path(
    "results/v24215_selected_joint_package_recovery_wait_audit_v1_20260731.json"
)
WATCHER_MARKER = "scripts/watch_v24215_joint_package_recovery.py"
V24214_PROTOCOL = Path(
    "results/v24214_selected_joint_package_preregistration_v1_20260731.json"
)
V24214_PROTOCOL_SHA256 = (
    "d565ed96245c3746b71615c2b8e8e5089d7373effbba686b8efb6da7b3242fff"
)
V24214_ACTIVATION = Path(
    "results/v24214_selected_joint_package_activation_v1_20260731.json"
)
V24214_ACTIVATION_SHA256 = (
    "7288f7f01391df2a15c9ed9cc31f0f9b19509ae4d2ed326cc67ccee1ca1541c5"
)
V24214_STATE = Path(
    "outputs/v24214_selected_joint_package_watcher_state_v1_20260731.json"
)
V24214_STATE_SHA256 = (
    "1a4dd7703508d6a0c97cc5406b614903751000bdc41e3e0c666a7377170207a3"
)
V24214_PUBLICATION = Path(
    "results/v24214_selected_joint_package_publication_v1_20260731.json"
)
V24214_CANDIDATE = ROOT / "outputs/v24214_selected_joint_package_candidate_v1_20260731"
CONTROL_FILES = (
    "src/deepwide_agent/v24215_joint_package_recovery.py",
    "scripts/publish_v24215_joint_package_recovery.py",
    "scripts/preregister_v24215_joint_package_recovery.py",
    "scripts/watch_v24215_joint_package_recovery.py",
    "scripts/activate_v24215_joint_package_recovery.py",
    "scripts/audit_v24215_joint_package_recovery_wait.py",
    "tests/test_v24215_joint_package_recovery.py",
    "tests/test_publish_v24215_joint_package_recovery.py",
    "tests/test_preregister_v24215_joint_package_recovery.py",
    "tests/test_watch_v24215_joint_package_recovery.py",
    "tests/test_activate_v24215_joint_package_recovery.py",
    "tests/test_audit_v24215_joint_package_recovery_wait.py",
)
DECISION_FIELDS = (
    "protocol_id",
    "recovery_parent",
    "parent_contract",
    "joint_package_contract",
    "regression_contract",
    "execution",
    "source_policy",
    "authorization",
    "safe_wait_boundary",
    "control_surface",
)


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _failed_parent(root: Path) -> dict[str, Any]:
    audit = read_object(ordinary(root, FAILED_AUDIT_PATH, FAILED_AUDIT_SHA256))
    ordinary(root, V24214_PROTOCOL, V24214_PROTOCOL_SHA256)
    ordinary(root, V24214_ACTIVATION, V24214_ACTIVATION_SHA256)
    ordinary(root, V24214_STATE, V24214_STATE_SHA256)
    if (
        audit.get("role")
        != "v24214_selected_joint_package_failed_activation_audit"
        or audit.get("failure", {}).get("classification")
        != "entropy_publication_path_binding_mismatch_fail_closed"
        or audit.get("disposition", {}).get(
            "same_namespace_restart_retry_resume_or_overwrite_allowed"
        )
        is not False
        or audit.get("disposition", {}).get(
            "new_versioned_recovery_protocol_required"
        )
        is not True
        or audit.get("boundary", {}).get("joint_candidate_or_publication_created")
        is not False
        or audit.get("boundary", {}).get("package_gate_evaluated_or_launched")
        is not False
        or audit.get("boundary", {}).get("dev64_launched") is not False
        or audit.get("boundary", {}).get("shared_api_lease_acquired") is not False
        or audit.get("boundary", {}).get(
            "benchmark_forward_or_full220_launched"
        )
        is not False
        or not _sealed(audit, "audit_payload_sha256")
        or (root / V24214_PUBLICATION).exists()
        or (root / V24214_PUBLICATION).is_symlink()
        or V24214_CANDIDATE.exists()
        or V24214_CANDIDATE.is_symlink()
    ):
        raise RuntimeError("V2.42.15 failed recovery parent drifted")
    return {
        "failed_activation_audit": {
            "path": FAILED_AUDIT_PATH,
            "sha256": FAILED_AUDIT_SHA256,
        },
        "failed_protocol": {
            "path": str(V24214_PROTOCOL),
            "sha256": V24214_PROTOCOL_SHA256,
        },
        "failed_activation": {
            "path": str(V24214_ACTIVATION),
            "sha256": V24214_ACTIVATION_SHA256,
        },
        "failed_last_state": {
            "path": str(V24214_STATE),
            "sha256": V24214_STATE_SHA256,
        },
    }


def _parent_contract() -> dict[str, Any]:
    return {
        "protocol": {
            "path": str(PARENT_PROTOCOL),
            "sha256": PARENT_PROTOCOL_SHA256,
        },
        "activation": {
            "path": str(PARENT_ACTIVATION),
            "sha256": PARENT_ACTIVATION_SHA256,
        },
        "wait_audit": {
            "path": str(PARENT_WAIT_AUDIT),
            "sha256": PARENT_WAIT_AUDIT_SHA256,
        },
        "state_path": str(PARENT_STATE),
        "selected_work_order_path": str(SELECTED_WORK_ORDER),
        "component_publication_paths": {
            name: str(path) for name, path in COMPONENT_PUBLICATIONS.items()
        },
        "actual_entropy_publication_path": ACTUAL_ENTROPY_PATH,
        "selected_content_read_only_after_parent_terminal": True,
    }


def _parent_preterminal_state(root: Path) -> dict[str, Any]:
    state = read_object(root / PARENT_STATE)
    unsigned = dict(state)
    seal = unsigned.pop("state_payload_sha256", None)
    false_fields = (
        "selected_work_order_opened",
        "search_publication_opened",
        "gate2a_report_opened",
        "action_model_opened",
        "numeric_metrics_predictions_or_aggregates_read_before_both_terminal",
        "component_publication_created",
        "joint_package_quality_gate_evaluated_or_launched",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read_for_forward_routing",
        "credential_value_read_persisted_hashed_or_emitted",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
        "terminal",
    )
    if (
        state.get("role")
        != "v24213_selected_entropy_component_recovery_state"
        or state.get("protocol", {}).get("path") != str(PARENT_PROTOCOL)
        or state.get("protocol", {}).get("sha256") != PARENT_PROTOCOL_SHA256
        or state.get("status")
        not in {
            "waiting_for_search_parent_and_gate2a_terminal",
            "waiting_for_search_parent_terminal",
            "waiting_for_gate2a_terminal",
        }
        or any(state.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.15 parent preterminal state drifted")
    return {
        "path": str(PARENT_STATE),
        "status": state["status"],
        "terminal": False,
        "selected_content_opened": False,
        "contents_emitted": False,
    }


def _valid_parent_snapshot(value: object) -> bool:
    return (
        isinstance(value, dict)
        and value.get("path") == str(PARENT_STATE)
        and value.get("status")
        in {
            "waiting_for_search_parent_and_gate2a_terminal",
            "waiting_for_search_parent_terminal",
            "waiting_for_gate2a_terminal",
        }
        and value.get("terminal") is False
        and value.get("selected_content_opened") is False
        and value.get("contents_emitted") is False
        and set(value)
        == {
            "path",
            "status",
            "terminal",
            "selected_content_opened",
            "contents_emitted",
        }
    )


def _v24214_watcher_pids(proc_root: Path = Path("/proc")) -> list[int]:
    marker = "scripts/watch_v24214_joint_package.py"
    result: list[int] = []
    for row in process_snapshot(proc_root):
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (
            script == marker or script.endswith("/" + marker)
        ):
            result.append(int(row["pid"]))
    return sorted(result)


def _static_capability_audit(root: Path) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for relative in CONTROL_FILES:
        source = ordinary(root, relative).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative)
        imports: set[str] = set()
        environment_read = False
        dynamic_calls: list[str] = []
        process_calls: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {
                    "compile",
                    "eval",
                    "exec",
                }:
                    dynamic_calls.append(node.func.id)
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in {"os", "subprocess"}
                    and node.func.attr in {"Popen", "run", "system", "execve"}
                ):
                    process_calls.append(
                        f"{node.func.value.id}.{node.func.attr}"
                    )
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "os"
                and node.attr == "environ"
            ) or (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and node.func.attr == "getenv"
            ):
                environment_read = True
        if (
            {"httpx", "requests", "socket"}.intersection(imports)
            or environment_read
            or dynamic_calls
            or process_calls
        ):
            raise RuntimeError("V2.42.15 forbidden capability appeared")
        rows[relative] = {
            "sha256": sha256(root / relative),
            "network_import": False,
            "credential_environment_read": False,
            "dynamic_execution": False,
            "process_calls": [],
        }
    return rows


def _fixed() -> dict[str, Any]:
    manifest = build_recovery_manifest()
    return {
        "recovery_parent": {
            "failed_activation_audit": {
                "path": FAILED_AUDIT_PATH,
                "sha256": FAILED_AUDIT_SHA256,
            },
            "failed_protocol": {
                "path": str(V24214_PROTOCOL),
                "sha256": V24214_PROTOCOL_SHA256,
            },
            "failed_activation": {
                "path": str(V24214_ACTIVATION),
                "sha256": V24214_ACTIVATION_SHA256,
            },
            "failed_last_state": {
                "path": str(V24214_STATE),
                "sha256": V24214_STATE_SHA256,
            },
        },
        "parent_contract": _parent_contract(),
        "joint_package_contract": {
            "manifest_payload_sha256": manifest["manifest_payload_sha256"],
            "summary": manifest["summary"],
            "only_recovery_delta": manifest["only_recovery_delta"],
            "failed_path": FROZEN_WRONG_ENTROPY_PATH,
            "actual_path": ACTUAL_ENTROPY_PATH,
            "owner_schema_component_regression_and_authority_contract_unchanged": True,
            "component_directory_overlay_forbidden": True,
            "package_gate_evaluated_or_launched": False,
        },
        "regression_contract": {
            "complete_deepest_parent_and_component_suite_required": True,
            "fresh_repo_local_candidate_required_for_nonempty_component_set": True,
            "candidate_source_manifest_immutable_before_and_after_tests": True,
            "scrubbed_isolated_environment_required": True,
            "network_or_api_required": False,
            "runtime_label_blind_ast_audit_required": True,
        },
        "execution": {
            "watcher_marker": WATCHER_MARKER,
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "state_path": str(STATE),
            "activation_path": str(ACTIVATION),
            "publication_path": str(PUBLICATION),
            "candidate_root": str(CANDIDATE_ROOT),
            "wait_audit_path": str(WAIT_AUDIT),
        },
        "source_policy": {
            "before_activation_parent_state_opened": False,
            "after_activation_preterminal_parent_safe_state_envelope_only": True,
            "selected_work_order_or_component_publication_opened_before_parent_terminal": False,
            "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted": False,
            "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
        },
        "authorization": {
            "versioned_recovery_watcher_active_after_activation": True,
            "joint_package_publication_after_parent_terminal": True,
            "local_regression_via_frozen_v24214_publisher_only_after_parent_terminal": True,
            "v24214_namespace_reuse_overwrite_resume_or_retry": False,
            "package_gate_evaluation_or_launch": False,
            "dev64_launch": False,
            "shared_api_lease_acquire": False,
            "network_model_search_fetch_evaluator_or_api_call": False,
            "benchmark_forward_or_full220_launch": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    require_pristine: bool = True,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.15 may only freeze the canonical workspace")
    if any(
        (root / name).exists() or (root / name).is_symlink()
        for name in MUST_REMAIN_ABSENT
    ):
        raise RuntimeError("V2.42.15 unattested Python bootstrap path appeared")
    future = (OUTPUT, STATE, ACTIVATION, WAIT_AUDIT, PUBLICATION)
    future_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in future
    ) and not CANDIDATE_ROOT.exists() and not CANDIDATE_ROOT.is_symlink()
    if require_pristine and not future_absent:
        raise RuntimeError("V2.42.15 create-exclusive boundary is not pristine")
    selected_inputs_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in (SELECTED_WORK_ORDER, *COMPONENT_PUBLICATIONS.values())
    )
    if require_pristine and not selected_inputs_absent:
        raise RuntimeError("V2.42.15 selected input appeared before freeze")
    if _v24214_watcher_pids(proc_root):
        raise RuntimeError("V2.42.15 failed V2.42.14 watcher remains active")
    if _failed_parent(root) != _fixed()["recovery_parent"]:
        raise RuntimeError("V2.42.15 failed parent binding drifted")
    control = {
        relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES
    }
    fixed = _fixed()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "label_blind": True,
        **fixed,
        "safe_wait_boundary": {
            "future_recovery_outputs_and_candidate_absent": future_absent,
            "selected_work_order_and_component_publications_absent": selected_inputs_absent,
            "failed_v24214_watcher_absent": True,
            "failed_v24214_protocol_activation_and_state_preserved": True,
            "parent_preterminal_at_freeze": _parent_preterminal_state(root),
            "protected_processes": protected_processes(proc_root),
        },
        "control_surface": {
            "file_count": len(control),
            "manifest": control,
            "manifest_sha256": payload_sha256(control),
            "must_remain_absent": list(MUST_REMAIN_ABSENT),
            "static_capability_audit": _static_capability_audit(root),
        },
    }
    value["decision_contract_sha256"] = payload_sha256(
        {key: value[key] for key in DECISION_FIELDS}
    )
    return value


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    target = path if path.is_absolute() else root / path
    value = read_object(target)
    manifest = value.get("control_surface", {}).get("manifest")
    fixed = _fixed()
    ordinary(root, FAILED_AUDIT_PATH, FAILED_AUDIT_SHA256)
    ordinary(root, V24214_PROTOCOL, V24214_PROTOCOL_SHA256)
    ordinary(root, V24214_ACTIVATION, V24214_ACTIVATION_SHA256)
    ordinary(root, V24214_STATE, V24214_STATE_SHA256)
    if (
        target.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or target.is_symlink()
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or any(value.get(key) != expected for key, expected in fixed.items())
        or value.get("safe_wait_boundary", {}).get(
            "future_recovery_outputs_and_candidate_absent"
        )
        is not True
        or value.get("safe_wait_boundary", {}).get(
            "selected_work_order_and_component_publications_absent"
        )
        is not True
        or value.get("safe_wait_boundary", {}).get(
            "failed_v24214_watcher_absent"
        )
        is not True
        or value.get("safe_wait_boundary", {}).get(
            "failed_v24214_protocol_activation_and_state_preserved"
        )
        is not True
        or not _valid_parent_snapshot(
            value.get("safe_wait_boundary", {}).get(
                "parent_preterminal_at_freeze"
            )
        )
        or not isinstance(
            value.get("safe_wait_boundary", {}).get("protected_processes"), dict
        )
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or value.get("control_surface", {}).get("file_count")
        != len(CONTROL_FILES)
        or value.get("control_surface", {}).get("manifest_sha256")
        != payload_sha256(manifest)
        or value.get("control_surface", {}).get("must_remain_absent")
        != list(MUST_REMAIN_ABSENT)
        or value.get("decision_contract_sha256")
        != payload_sha256({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.42.15 protocol contract drifted")
    for relative, digest in manifest.items():
        ordinary(root, relative, str(digest))
    if value["control_surface"]["static_capability_audit"] != _static_capability_audit(
        root
    ):
        raise RuntimeError("V2.42.15 static capability receipt drifted")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.15 protocol output path drifted")
    value = build_protocol()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
