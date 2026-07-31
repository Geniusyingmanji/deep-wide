#!/usr/bin/env python3
"""Freeze V2.42.12 before its selected parent and Gate-2A terminate."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
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
from deepwide_agent.v24211_entropy_feasibility import (  # noqa: E402
    build_entropy_feasibility_manifest,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    MUST_REMAIN_ABSENT,
    PROTECTED_PROCESS_MARKERS,
    _start_ticks,
    ordinary,
    publish_new,
    sha256,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.publish_v24212_entropy_component import (  # noqa: E402
    ACTION_MODEL,
    CANDIDATE_ROOT,
    GATE2A_REPORT,
    GATE2A_STATE,
    OUTPUT as PUBLICATION,
)


ROLE = "v24212_selected_entropy_component_preregistration"
PROTOCOL_ID = "v24212_selected_parent_entropy_component_publisher_v1"
OUTPUT = Path("results/v24212_selected_entropy_component_preregistration_v1_20260731.json")
STATE = Path("outputs/v24212_selected_entropy_component_watcher_state_v1_20260731.json")
ACTIVATION = Path("results/v24212_selected_entropy_component_activation_v1_20260731.json")
WAIT_AUDIT = Path("results/v24212_selected_entropy_component_wait_activation_audit_v1_20260731.json")
SEARCH_PROTOCOL = Path("results/v24210_selected_search_component_preregistration_v1_20260731.json")
SEARCH_PROTOCOL_SHA256 = "dc5a64d036aac52e9ec76fdc952645678aff9408e18887f425686ba2660c6f23"
SEARCH_ACTIVATION = Path("results/v24210_selected_search_component_activation_v1_20260731.json")
SEARCH_ACTIVATION_SHA256 = "bc927d51b5fc143e5512b87449304832736baae2628cccf51f620cf2a188d9a8"
SEARCH_WAIT_AUDIT = Path("results/v24210_selected_search_component_wait_activation_audit_v1_20260731.json")
SEARCH_WAIT_AUDIT_SHA256 = "6203ae306289451728658c19f5778d191a3ebc4da21454260015ccc7c678a3a7"
SEARCH_STATE = Path("outputs/v24210_selected_search_component_watcher_state_v1_20260731.json")
GATE2A_PROTOCOL = Path("results/v24193_replicate_aware_gate2a_consumer_preregistration_v1_20260731.json")
GATE2A_PROTOCOL_SHA256 = "9b2fcf677bbb4f7cdb361d689f2634b23326d1cb640416eee920fb2b131b6031"
GATE2A_ACTIVATION = Path("results/v24193_replicate_aware_gate2a_consumer_activation_audit_v1_20260731.json")
GATE2A_ACTIVATION_SHA256 = "5a34c68ccdb84e039f2e766739f43d0853258ed5acb0c8a7c888ea3fb245aceb"
WATCHER_MARKER = "scripts/watch_v24212_entropy_component.py"
PROTECTED_MARKERS = {
    **PROTECTED_PROCESS_MARKERS,
    "v24210_search_component_watcher": (
        "scripts/watch_v24210_search_component.py"
    ),
}
CONTROL_FILES = (
    "src/deepwide_agent/owic.py",
    "src/deepwide_agent/v2409_pilot.py",
    "src/deepwide_agent/v2409_interventions.py",
    "src/deepwide_agent/v24121_continuation.py",
    "src/deepwide_agent/v24122_execution.py",
    "src/deepwide_agent/v24211_entropy_controller.py",
    "src/deepwide_agent/v24211_entropy_runtime.py",
    "src/deepwide_agent/v24211_entropy_feasibility.py",
    "src/deepwide_agent/v24212_entropy_binding.py",
    "scripts/publish_v24212_entropy_component.py",
    "scripts/preregister_v24212_entropy_component.py",
    "scripts/watch_v24212_entropy_component.py",
    "scripts/activate_v24212_entropy_component.py",
    "scripts/audit_v24212_entropy_component_wait_activation.py",
    "tests/test_v24211_entropy_controller.py",
    "tests/test_v24211_entropy_runtime.py",
    "tests/test_v24211_entropy_feasibility.py",
    "tests/test_v24121_continuation.py",
    "tests/test_v24122_execution.py",
    "tests/test_v24212_entropy_binding.py",
    "tests/test_publish_v24212_entropy_component.py",
    "tests/test_preregister_v24212_entropy_component.py",
    "tests/test_watch_v24212_entropy_component.py",
    "tests/test_activate_v24212_entropy_component.py",
    "tests/test_audit_v24212_entropy_component_wait_activation.py",
)
DECISION_FIELDS = (
    "protocol_id",
    "parent_contract",
    "publication_contract",
    "quality_contract",
    "execution",
    "source_policy",
    "authorization",
    "safe_wait_boundary",
    "control_surface",
)


def protected_processes(proc_root: Path = Path("/proc")) -> dict[str, Any]:
    """Bind every upstream protected process without emitting command lines."""

    rows = process_snapshot(proc_root)
    result: dict[str, Any] = {}
    for name, marker in PROTECTED_MARKERS.items():
        matches = []
        for row in rows:
            argv = [str(value) for value in row.get("argv") or []]
            script = actual_python_script(argv)
            if script is not None and (
                script == marker or script.endswith("/" + marker)
            ):
                matches.append({"pid": int(row["pid"]), "argv": argv})
        isolated = name not in {"r1_launcher", "r1_forward"}
        if len(matches) != 1 or (
            isolated
            and not all(flag in matches[0]["argv"] for flag in ("-I", "-B"))
        ):
            raise RuntimeError(
                f"V2.42.12 protected process identity is invalid: {marker}"
            )
        pid = matches[0]["pid"]
        result[name] = {
            "marker": marker,
            "pid": pid,
            "start_ticks": _start_ticks(proc_root, pid),
            "python_isolated_no_bytecode_required": isolated,
            "command_line_emitted": False,
        }
    return result


def _read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.12 expected an ordinary JSON file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.12 expected one JSON object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parents(root: Path) -> dict[str, Any]:
    specs = (
        ("v24210_protocol", SEARCH_PROTOCOL, SEARCH_PROTOCOL_SHA256),
        ("v24210_activation", SEARCH_ACTIVATION, SEARCH_ACTIVATION_SHA256),
        ("v24210_wait_audit", SEARCH_WAIT_AUDIT, SEARCH_WAIT_AUDIT_SHA256),
        ("v24193_protocol", GATE2A_PROTOCOL, GATE2A_PROTOCOL_SHA256),
        ("v24193_activation", GATE2A_ACTIVATION, GATE2A_ACTIVATION_SHA256),
    )
    values = {
        name: _read_object(ordinary(root, path, digest))
        for name, path, digest in specs
    }
    if (
        values["v24210_protocol"].get("role")
        != "v24210_selected_search_component_preregistration"
        or values["v24210_protocol"].get("authorization", {}).get(
            "entropy_controller_implementation_or_publication"
        )
        is not False
        or values["v24210_protocol"].get("authorization", {}).get(
            "benchmark_forward_or_full220_launch"
        )
        is not False
        or values["v24210_activation"].get("benchmark_forward_or_full220_launch_allowed")
        is not False
        or not _sealed(values["v24210_activation"], "activation_payload_sha256")
        or not _sealed(values["v24210_wait_audit"], "audit_payload_sha256")
        or values["v24193_protocol"].get("role")
        != "v24193_replicate_aware_gate2a_consumer_preregistration"
        or values["v24193_protocol"].get("authorization", {}).get(
            "controller_implementation_or_pilot_launch"
        )
        is not False
        or values["v24193_protocol"].get("authorization", {}).get(
            "full220_controller_launch"
        )
        is not False
        or values["v24193_activation"].get("activation_valid") is not True
        or not _sealed(values["v24193_activation"], "audit_payload_sha256")
        or values["v24193_activation"].get("boundary", {}).get(
            "manifest_model_prediction_aggregate_or_outcome_opened"
        )
        is not False
        or values["v24193_activation"].get("boundary", {}).get(
            "mapping_gold_category_question_type_evaluator_score_or_outcome_read"
        )
        is not False
        or values["v24193_activation"].get("claims", {}).get(
            "controller_or_training_enabled"
        )
        is not False
        or values["v24193_activation"].get("claims", {}).get(
            "benchmark_score_available"
        )
        is not False
    ):
        raise RuntimeError("V2.42.12 frozen parent contract drifted")
    return {
        name: {"path": str(path), "sha256": digest}
        for name, path, digest in specs
    }


def _static_capability_audit(root: Path) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for relative in CONTROL_FILES:
        source = ordinary(root, relative).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative)
        imported: set[str] = set()
        environment_read = False
        dynamic_calls: list[str] = []
        process_calls: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
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
            if relative == "scripts/publish_v24212_entropy_component.py"
            else []
        )
        if (
            {"httpx", "requests", "socket"}.intersection(imported)
            or environment_read
            or dynamic_calls
            or process_calls != allowed_process
        ):
            raise RuntimeError("V2.42.12 forbidden capability appeared")
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
    manifest = build_entropy_feasibility_manifest()
    return {
        "parent_contract": {
            "search_component_state_path": str(SEARCH_STATE),
            "gate2a_state_path": str(GATE2A_STATE),
            "selected_work_order_path": (
                "results/v24204_selected_postdecision_work_order_v1_20260731.json"
            ),
            "search_publication_path": (
                "results/v24210_selected_search_component_publication_v1_20260731.json"
            ),
            "before_both_terminal_safe_state_envelopes_only": True,
            "selected_parent_model_and_report_read_only_after_both_terminal": True,
            "numeric_metrics_predictions_or_aggregates_read_before_terminal": False,
        },
        "publication_contract": {
            "manifest_payload_sha256": manifest["manifest_payload_sha256"],
            "summary": manifest["summary"],
            "selection_frozen_before_parent_or_gate_outcome": True,
            "owned_component": "entropy_credit_controller",
            "eighteen_entropy_decisions_covered": True,
            "fourteen_unique_parent_byte_graphs_covered": True,
            "nine_search_parents_and_nine_nonsearch_parents_covered": True,
            "real_state_transition_adapters_required": True,
            "runtime_runner_preflight_launcher_rebase_required": True,
            "model_file_sha_model_sha_job_sha_and_parent_sha_bound": True,
            "projection_only_action_arm_forbidden": True,
            "historical_projection_module_allowed_only_as_frozen_adapter_dependency": True,
            "joint_package_or_package_gate_built": False,
        },
        "quality_contract": {
            "terminal_go_status": "replicate_aware_gate2a_pass",
            "terminal_no_go_statuses": [
                "replicate_aware_gate2a_fail",
                "replicate_aware_gate2a_not_evaluable",
            ],
            "go_materializes_exactly_one_selected_parent_rebase": True,
            "no_go_retires_entropy_without_rerun": True,
            "entropy_absent_publishes_content_free_no_op": True,
            "production_model_must_be_ready_and_fit_calibration_only": True,
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
            "before_activation_parent_or_gate_state_opened": False,
            "after_activation_only_safe_state_envelopes_opened": True,
            "after_both_terminal_only_selected_parent_model_and_report_opened": True,
            "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted": False,
            "post_terminal_evaluator_derived_gate_report_read_allowed": True,
            "mapping_gold_category_question_type_evaluator_score_or_reward_read_for_forward_routing": False,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
        },
        "authorization": {
            "selected_entropy_publisher_active_after_activation": True,
            "component_publication_after_validated_parent_and_gate_terminal": True,
            "selected_parent_entropy_candidate_materialization_on_go": True,
            "content_free_noop_or_retirement_publication": True,
            "joint_package_build_merge_or_freeze_generation": False,
            "package_gate_evaluation_or_launch": False,
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
        raise RuntimeError("V2.42.12 may only freeze the canonical workspace")
    if any(
        (root / name).exists() or (root / name).is_symlink()
        for name in MUST_REMAIN_ABSENT
    ):
        raise RuntimeError("V2.42.12 unattested Python bootstrap path appeared")
    future = (OUTPUT, STATE, ACTIVATION, WAIT_AUDIT, PUBLICATION)
    future_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in future
    ) and not CANDIDATE_ROOT.exists() and not CANDIDATE_ROOT.is_symlink()
    if require_pristine and not future_absent:
        raise RuntimeError("V2.42.12 create-exclusive boundary is not pristine")
    terminal_inputs_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in (
            PUBLICATION,
            GATE2A_REPORT,
            ACTION_MODEL,
            Path("results/v24210_selected_search_component_publication_v1_20260731.json"),
            Path("results/v24204_selected_postdecision_work_order_v1_20260731.json"),
        )
    )
    if require_pristine and not terminal_inputs_absent:
        raise RuntimeError("V2.42.12 terminal input appeared before freeze")
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
        "frozen_parents": _parents(root),
        **fixed,
        "safe_wait_boundary": {
            "future_outputs_and_candidate_absent": future_absent,
            "selected_parent_report_and_model_outputs_absent": terminal_inputs_absent,
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
    value = _read_object(target)
    manifest = value.get("control_surface", {}).get("manifest")
    if (
        target.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or target.is_symlink()
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or value.get("frozen_parents") != _parents(root)
        or any(value.get(key) != expected for key, expected in _fixed().items())
        or value.get("safe_wait_boundary", {}).get(
            "future_outputs_and_candidate_absent"
        )
        is not True
        or value.get("safe_wait_boundary", {}).get(
            "selected_parent_report_and_model_outputs_absent"
        )
        is not True
        or not isinstance(
            value.get("safe_wait_boundary", {}).get("protected_processes"), dict
        )
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or value.get("control_surface", {}).get("file_count") != len(CONTROL_FILES)
        or value.get("control_surface", {}).get("manifest_sha256")
        != payload_sha256(manifest)
        or value.get("control_surface", {}).get("must_remain_absent")
        != list(MUST_REMAIN_ABSENT)
        or value.get("control_surface", {}).get("static_capability_audit")
        != _static_capability_audit(root)
        or value.get("decision_contract_sha256")
        != payload_sha256({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.42.12 protocol contract is invalid")
    for relative, digest in manifest.items():
        if sha256(ordinary(root, relative)) != digest:
            raise RuntimeError("V2.42.12 control surface drifted")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.12 protocol output path drifted")
    publish_new(target, build_protocol())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
