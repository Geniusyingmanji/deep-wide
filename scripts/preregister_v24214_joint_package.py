#!/usr/bin/env python3
"""Freeze V2.42.14 before the selected entropy chain terminates."""

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
from deepwide_agent.v24214_joint_package import (  # noqa: E402
    build_joint_package_manifest,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.activate_v24213_entropy_recovery import (  # noqa: E402
    validate_activation as validate_parent_activation,
)
from scripts.preregister_v24212_entropy_component import (  # noqa: E402
    MUST_REMAIN_ABSENT,
    protected_processes as base_protected_processes,
)
from scripts.preregister_v24213_entropy_recovery import (  # noqa: E402
    validate_protocol as validate_parent_protocol,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    _start_ticks,
    ordinary,
    publish_new,
    read_object,
    sha256,
)
from scripts.publish_v24214_joint_package import (  # noqa: E402
    CANDIDATE_ROOT,
    COMPONENT_PUBLICATIONS,
    OUTPUT as PUBLICATION,
    SELECTED_WORK_ORDER,
)


ROLE = "v24214_selected_joint_package_preregistration"
PROTOCOL_ID = "v24214_deepest_owner_joint_package_revalidation_v1"
OUTPUT = Path("results/v24214_selected_joint_package_preregistration_v1_20260731.json")
STATE = Path("outputs/v24214_selected_joint_package_watcher_state_v1_20260731.json")
ACTIVATION = Path("results/v24214_selected_joint_package_activation_v1_20260731.json")
WAIT_AUDIT = Path("results/v24214_selected_joint_package_wait_activation_audit_v1_20260731.json")
WATCHER_MARKER = "scripts/watch_v24214_joint_package.py"
PARENT_WATCHER_MARKER = "scripts/watch_v24213_entropy_recovery.py"
PARENT_PROTOCOL = Path(
    "results/v24213_selected_entropy_component_recovery_preregistration_v1_20260731.json"
)
PARENT_PROTOCOL_SHA256 = (
    "aa974037b6c6f20e5c5f78c1ca90efe44b750c4687eda8459f1dd3ada5706b8b"
)
PARENT_ACTIVATION = Path(
    "results/v24213_selected_entropy_component_recovery_activation_v1_20260731.json"
)
PARENT_ACTIVATION_SHA256 = (
    "57597276aa0e0d290dcb2e01de9a07a548687b064377f2c91cad852911e9c687"
)
PARENT_WAIT_AUDIT = Path(
    "results/v24213_selected_entropy_component_recovery_wait_audit_v1_20260731.json"
)
PARENT_WAIT_AUDIT_SHA256 = (
    "905360287ecc6980a0d7b1ab098d169c81b05e79a49302ce384525546db1b2c4"
)
PARENT_STATE = Path(
    "outputs/v24213_selected_entropy_component_recovery_state_v1_20260731.json"
)
CONTROL_FILES = (
    "src/deepwide_agent/v24214_joint_package.py",
    "scripts/publish_v24214_joint_package.py",
    "scripts/preregister_v24214_joint_package.py",
    "scripts/watch_v24214_joint_package.py",
    "scripts/activate_v24214_joint_package.py",
    "scripts/audit_v24214_joint_package_wait.py",
    "tests/test_v24214_joint_package.py",
    "tests/test_publish_v24214_joint_package.py",
    "tests/test_preregister_v24214_joint_package.py",
    "tests/test_watch_v24214_joint_package.py",
    "tests/test_activate_v24214_joint_package.py",
    "tests/test_audit_v24214_joint_package_wait.py",
)
DECISION_FIELDS = (
    "protocol_id",
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


def _frozen_parent_contract() -> dict[str, Any]:
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
        "safe_state_envelope_only_before_parent_terminal": True,
    }


def _validate_parent_receipts_at_freeze(root: Path) -> None:
    protocol = validate_parent_protocol(root, PARENT_PROTOCOL)
    activation = validate_parent_activation(
        root, PARENT_ACTIVATION, protocol_path=PARENT_PROTOCOL
    )
    audit = read_object(
        ordinary(root, PARENT_WAIT_AUDIT, PARENT_WAIT_AUDIT_SHA256)
    )
    if (
        protocol["sha256"] != PARENT_PROTOCOL_SHA256
        or activation["sha256"] != PARENT_ACTIVATION_SHA256
        or audit.get("role")
        != "v24213_selected_entropy_component_recovery_wait_audit"
        or audit.get("protocol", {}).get("sha256") != PARENT_PROTOCOL_SHA256
        or audit.get("execution_activation", {}).get("sha256")
        != PARENT_ACTIVATION_SHA256
        or audit.get("boundary", {}).get(
            "mapping_gold_category_question_type_evaluator_score_or_reward_read_for_forward_routing"
        )
        is not False
        or audit.get("boundary", {}).get("shared_api_lease_acquired") is not False
        or audit.get("boundary", {}).get(
            "benchmark_forward_or_full220_launch_allowed"
        )
        is not False
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.14 parent receipts drifted")


def _validate_frozen_parent_files(root: Path) -> None:
    ordinary(root, PARENT_PROTOCOL, PARENT_PROTOCOL_SHA256)
    ordinary(root, PARENT_ACTIVATION, PARENT_ACTIVATION_SHA256)
    ordinary(root, PARENT_WAIT_AUDIT, PARENT_WAIT_AUDIT_SHA256)


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
        raise RuntimeError("V2.42.14 parent preterminal state drifted")
    return {
        "path": str(PARENT_STATE),
        "status": state["status"],
        "terminal": False,
        "selected_content_opened": False,
        "contents_emitted": False,
    }


def _valid_frozen_parent_snapshot(value: object) -> bool:
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


def protected_processes(proc_root: Path = Path("/proc")) -> dict[str, Any]:
    result = base_protected_processes(proc_root)
    matches: list[dict[str, Any]] = []
    for row in process_snapshot(proc_root):
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (
            script == PARENT_WATCHER_MARKER
            or script.endswith("/" + PARENT_WATCHER_MARKER)
        ):
            matches.append({"pid": int(row["pid"]), "argv": argv})
    if len(matches) != 1 or not all(
        flag in matches[0]["argv"] for flag in ("-I", "-B")
    ):
        raise RuntimeError("V2.42.14 parent watcher identity is invalid")
    pid = matches[0]["pid"]
    result["v24213_entropy_recovery_watcher"] = {
        "marker": PARENT_WATCHER_MARKER,
        "pid": pid,
        "start_ticks": _start_ticks(proc_root, pid),
        "python_isolated_no_bytecode_required": True,
        "command_line_emitted": False,
    }
    return result


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
        allowed_process = (
            ["subprocess.run"]
            if relative == "scripts/publish_v24214_joint_package.py"
            else []
        )
        if (
            {"httpx", "requests", "socket"}.intersection(imports)
            or environment_read
            or dynamic_calls
            or process_calls != allowed_process
        ):
            raise RuntimeError("V2.42.14 forbidden capability appeared")
        rows[relative] = {
            "sha256": sha256(root / relative),
            "network_import": False,
            "credential_environment_read": False,
            "dynamic_execution": False,
            "process_calls": process_calls,
            "isolated_scrubbed_local_regression_only": bool(process_calls),
        }
    return rows


def _fixed() -> dict[str, Any]:
    manifest = build_joint_package_manifest()
    return {
        "parent_contract": {
            **_frozen_parent_contract(),
            "selected_work_order_path": str(SELECTED_WORK_ORDER),
            "component_publication_paths": {
                name: str(path) for name, path in COMPONENT_PUBLICATIONS.items()
            },
            "selected_content_read_only_after_parent_terminal": True,
        },
        "joint_package_contract": {
            "manifest_payload_sha256": manifest["manifest_payload_sha256"],
            "summary": manifest["summary"],
            "thirty_six_decisions_predeclared": True,
            "three_identity_handoffs_and_thirty_three_revalidations": True,
            "single_deepest_cumulative_graph_required": True,
            "component_directory_overlay_forbidden": True,
            "all_selected_components_must_be_covered_exactly_once": True,
            "silent_component_drop_or_baseline_fallback_forbidden": True,
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
            "joint_package_watcher_active_after_activation": True,
            "joint_package_publication_after_parent_terminal": True,
            "local_regression_subprocess_after_parent_terminal": True,
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
        raise RuntimeError("V2.42.14 may only freeze the canonical workspace")
    if any(
        (root / name).exists() or (root / name).is_symlink()
        for name in MUST_REMAIN_ABSENT
    ):
        raise RuntimeError("V2.42.14 unattested Python bootstrap path appeared")
    future = (OUTPUT, STATE, ACTIVATION, WAIT_AUDIT, PUBLICATION)
    future_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in future
    ) and not CANDIDATE_ROOT.exists() and not CANDIDATE_ROOT.is_symlink()
    if require_pristine and not future_absent:
        raise RuntimeError("V2.42.14 create-exclusive boundary is not pristine")
    selected_inputs_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in (SELECTED_WORK_ORDER, *COMPONENT_PUBLICATIONS.values())
    )
    if require_pristine and not selected_inputs_absent:
        raise RuntimeError("V2.42.14 selected input appeared before freeze")
    control = {
        relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES
    }
    _validate_parent_receipts_at_freeze(root)
    fixed = _fixed()
    # _fixed validates the parent against canonical ROOT; bind the same bytes
    # for the canonical root accepted above.
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
            "future_outputs_and_candidate_absent": future_absent,
            "selected_work_order_and_component_publications_absent": selected_inputs_absent,
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
    _validate_frozen_parent_files(root)
    if (
        target.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or target.is_symlink()
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or any(value.get(key) != expected for key, expected in fixed.items())
        or value.get("safe_wait_boundary", {}).get(
            "future_outputs_and_candidate_absent"
        )
        is not True
        or value.get("safe_wait_boundary", {}).get(
            "selected_work_order_and_component_publications_absent"
        )
        is not True
        or value.get("safe_wait_boundary", {}).get("parent_preterminal_at_freeze")
        is None
        or not _valid_frozen_parent_snapshot(
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
        raise RuntimeError("V2.42.14 protocol contract drifted")
    for relative, digest in manifest.items():
        ordinary(root, relative, str(digest))
    if value["control_surface"]["static_capability_audit"] != _static_capability_audit(
        root
    ):
        raise RuntimeError("V2.42.14 static capability receipt drifted")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.14 protocol output path drifted")
    value = build_protocol()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
