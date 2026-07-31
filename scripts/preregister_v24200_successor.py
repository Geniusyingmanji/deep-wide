#!/usr/bin/env python3
"""Freeze the V2.42.00 hierarchical successor before quality outcomes."""

from __future__ import annotations

import argparse
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

from deepwide_agent.v24200_successor import (  # noqa: E402
    BASELINES,
    PACKAGE_GATE_CONTRACT,
    SOURCE_SPECS,
    build_decision_manifest,
    payload_sha256,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)


ROLE = "v24200_hierarchical_successor_preregistration"
PROTOCOL_ID = "v24200_hierarchical_baseline_integrated_package_gate_v1"
OUTPUT = Path("results/v24200_hierarchical_successor_preregistration_v1_20260731.json")
STATE = Path("outputs/v24200_hierarchical_successor_watcher_state_v1_20260731.json")
ACTIVATION = Path("results/v24200_hierarchical_successor_activation_v1_20260731.json")
WAIT_AUDIT = Path(
    "results/v24200_hierarchical_successor_wait_activation_audit_v1_20260731.json"
)
DECISION_RECEIPT = Path(
    "results/v24200_hierarchical_successor_decision_v1_20260731.json"
)
PARENT_PROTOCOL = Path(
    "results/v24199_candidate_selector_controller_preregistration_v1_20260731.json"
)
PARENT_PROTOCOL_SHA256 = (
    "80034909ca93b6f064ac281dd53b5f69a4425b5a9d4cb6fde32479ac89af500c"
)
PARENT_ACTIVATION = Path("results/v24199_candidate_selector_activation_v1_20260731.json")
PARENT_ACTIVATION_SHA256 = (
    "d345ae00d8de438bef226c7833424167120d7297ff54c0b47bf7d7284b6f0557"
)
PARENT_WAIT_AUDIT = Path(
    "results/v24199_candidate_selector_wait_activation_audit_v1_20260731.json"
)
PARENT_WAIT_AUDIT_SHA256 = (
    "8fa893134f0db4906de3f79ce55ca96a8d78b09dad7477a636bef41854451db5"
)
WATCHER_MARKER = "scripts/watch_v24200_successor.py"
MUST_REMAIN_ABSENT = ("scripts/__init__.py", "sitecustomize.py", "usercustomize.py")
CONTROL_FILES = (
    "src/deepwide_agent/v24200_successor.py",
    "scripts/preregister_v24200_successor.py",
    "scripts/watch_v24200_successor.py",
    "scripts/activate_v24200_successor.py",
    "scripts/audit_v24200_successor_wait_activation.py",
    "tests/test_v24200_successor.py",
    "tests/test_preregister_v24200_successor.py",
    "tests/test_watch_v24200_successor.py",
    "tests/test_activate_v24200_successor.py",
    "tests/test_audit_v24200_successor_wait_activation.py",
)
SOURCE_PATHS = {
    "schema76": Path(
        "outputs/v24154_scope_combined_fasttrack_watcher_state_v1_20260729.json"
    ),
    "schema77": Path(
        "outputs/v24176_predicate_completion_paired_dev_watcher_state_v1_20260730.json"
    ),
    "search_yield": Path(
        "outputs/v24180_predicate_search_yield_watcher_state_v1_20260730.json"
    ),
    "markdown": Path("outputs/v24103_markdown_paired_dev_watcher_state_v1_20260728.json"),
    "markdown_branch_scope": Path(
        "outputs/v24105_scope_open_paired_dev_watcher_state_v1_20260729.json"
    ),
    "entropy_credit": Path(
        "outputs/v24193_replicate_aware_gate2a_consumer_state_v1_20260731.json"
    ),
}
ENTROPY_ROOT = Path("outputs/v24190_tie_aware_gate2a_consumer_state_v1_20260730.json")
PROTECTED_PROCESS_MARKERS = {
    "r1_launcher": "scripts/launch_frozen_deepwide.py",
    "r1_forward": "scripts/run_deepwide_agent.py",
    "v24187_phase_watcher": "scripts/watch_v24187_phase_liveness.py",
    "v24193_gate2a_watcher": "scripts/watch_v24193_replicate_aware_gate2a.py",
    "v24194_capacity_watcher": "scripts/watch_v24194_capacity_ladder.py",
    "v24195_compatibility_watcher": "scripts/watch_v24195_lease_owner_compatibility.py",
    "v24196_capacity_executor": "scripts/watch_v24196_capacity_executor.py",
    "v24197_parallel_planner": "scripts/watch_v24197_parallel_all220.py",
    "v24198_candidate_bundle": "scripts/watch_v24198_candidate_bundle.py",
    "v24199_candidate_selector": "scripts/watch_v24199_candidate_selector.py",
    "v24176_schema77_watcher": "scripts/watch_v24176_predicate_completion_paired_dev.py",
    "v24180_search_yield_launcher": "scripts/launch_v24183_search_yield_after_schema77.py",
    "v24103_markdown_launcher": "scripts/launch_v24185_markdown_after_search_yield.py",
    "v24105_scope_open_watcher": "scripts/watch_v24105_scope_open_paired_dev.py",
    "v24190_tie_aware_watcher": "scripts/watch_v24190_tie_aware_gate2a.py",
    "v24191_policy_value_watcher": "scripts/watch_v24191_policy_value_gate2a.py",
    "v24192_abstain_aware_watcher": "scripts/watch_v24192_abstain_aware_gate2a.py",
}
DECISION_FIELDS = (
    "protocol_id",
    "parent_disposition",
    "source_contract",
    "baseline_contract",
    "component_contract",
    "package_gate_contract",
    "execution",
    "source_policy",
    "authorization",
    "safe_wait_boundary",
    "control_surface",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ordinary(root: Path, relative: str | Path, digest: str | None = None) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.00 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.00 expected an ordinary file: {relative}")
    if digest is not None and sha256(path) != digest:
        raise RuntimeError(f"V2.42.00 frozen input drifted: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.00 expected an ordinary JSON file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.00 expected one JSON object")
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _start_ticks(proc_root: Path, pid: int) -> int:
    raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    suffix = raw[raw.rfind(")") + 2 :].split()
    if len(suffix) <= 19:
        raise RuntimeError("V2.42.00 process stat is truncated")
    return int(suffix[19])


def protected_processes(proc_root: Path = Path("/proc")) -> dict[str, Any]:
    rows = process_snapshot(proc_root)
    result: dict[str, Any] = {}
    for name, marker in PROTECTED_PROCESS_MARKERS.items():
        matches: list[dict[str, Any]] = []
        for row in rows:
            argv = [str(value) for value in row.get("argv") or []]
            script = actual_python_script(argv)
            if script is not None and (script == marker or script.endswith("/" + marker)):
                matches.append({"pid": int(row["pid"]), "argv": argv})
        isolated = name not in {"r1_launcher", "r1_forward"}
        if len(matches) != 1 or (
            isolated and not all(flag in matches[0]["argv"] for flag in ("-I", "-B"))
        ):
            raise RuntimeError(f"V2.42.00 process identity is invalid: {marker}")
        pid = matches[0]["pid"]
        result[name] = {
            "marker": marker,
            "pid": pid,
            "start_ticks": _start_ticks(proc_root, pid),
            "python_isolated_no_bytecode_required": isolated,
            "command_line_emitted": False,
        }
    return result


def _parent(root: Path) -> dict[str, Any]:
    parent = read_object(ordinary(root, PARENT_PROTOCOL, PARENT_PROTOCOL_SHA256))
    ordinary(root, PARENT_ACTIVATION, PARENT_ACTIVATION_SHA256)
    ordinary(root, PARENT_WAIT_AUDIT, PARENT_WAIT_AUDIT_SHA256)
    if (
        parent.get("role") != "v24199_candidate_selector_controller_preregistration"
        or parent.get("authorization", {}).get("benchmark_forward_or_full220_launch")
        is not False
    ):
        raise RuntimeError("V2.42.00 V2.41.99 parent drifted")
    return {
        "protocol": {"path": str(PARENT_PROTOCOL), "sha256": PARENT_PROTOCOL_SHA256},
        "activation": {"path": str(PARENT_ACTIVATION), "sha256": PARENT_ACTIVATION_SHA256},
        "wait_audit": {"path": str(PARENT_WAIT_AUDIT), "sha256": PARENT_WAIT_AUDIT_SHA256},
        "disposition": "diagnostic_only_never_execution_authority",
        "parent_process_remains_healthy_and_unmodified": True,
    }


def _fixed() -> dict[str, Any]:
    manifest = build_decision_manifest()
    return {
        "source_contract": {
            "source_paths": {name: str(path) for name, path in SOURCE_PATHS.items()},
            "source_specs_sha256": payload_sha256(SOURCE_SPECS),
            "entropy_root_path": str(ENTROPY_ROOT),
            "read_only_after_activation": True,
            "status_and_false_authorization_fields_only": True,
            "numeric_metrics_reports_predictions_or_aggregates_read": False,
        },
        "baseline_contract": {
            "publications": BASELINES,
            "rule": [
                "schema76_no_go_selects_p12",
                "schema76_go_and_schema77_no_go_selects_schema76",
                "schema76_go_and_schema77_go_selects_schema77",
                "schema77_never_overrules_schema76_no_go",
            ],
            "p12_to_schema76_paired_gate_consumed": True,
        },
        "component_contract": {
            "mainline_scope_and_markdown_branch_scope_namespaced_separately": True,
            "component_go_means_build_and_package_gate_eligibility_only": True,
            "independent_go_does_not_prove_union_package": True,
            "nonempty_component_set_requires_new_package_gate": True,
            "empty_component_set_uses_selected_baseline_identity_handoff": True,
            "identity_handoff_still_requires_separate_all220_freeze_and_executor": True,
            "terminal_package_count": len(manifest),
            "decision_manifest_sha256": payload_sha256(manifest),
        },
        "package_gate_contract": PACKAGE_GATE_CONTRACT,
        "execution": {
            "watcher_marker": WATCHER_MARKER,
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "state_path": str(STATE),
            "activation_path": str(ACTIVATION),
            "decision_receipt_path": str(DECISION_RECEIPT),
            "wait_audit_path": str(WAIT_AUDIT),
        },
        "source_policy": {
            "before_activation_source_envelopes_opened": False,
            "after_activation_only_registered_status_envelopes_opened": True,
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "benchmark_question_answer_evidence_prediction_or_url_values_parsed_or_emitted": False,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
        },
        "authorization": {
            "status_only_successor_active_after_activation": True,
            "decision_receipt_creation_after_entire_chain_terminal": True,
            "candidate_code_build_merge_or_freeze_generation": False,
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
        raise RuntimeError("V2.42.00 may only freeze the canonical workspace")
    if any((root / name).exists() or (root / name).is_symlink() for name in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.42.00 unattested Python bootstrap path appeared")
    future = (OUTPUT, STATE, ACTIVATION, WAIT_AUDIT, DECISION_RECEIPT)
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise RuntimeError("V2.42.00 create-exclusive boundary is not pristine")
    control = {relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES}
    fixed = _fixed()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        "parent_disposition": _parent(root),
        **fixed,
        "safe_wait_boundary": {
            "future_outputs_absent": all(
                not (root / path).exists() and not (root / path).is_symlink()
                for path in future
            ),
            "protected_processes": protected_processes(proc_root),
        },
        "control_surface": {
            "file_count": len(control),
            "manifest": control,
            "manifest_sha256": payload_sha256(control),
            "must_remain_absent": list(MUST_REMAIN_ABSENT),
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
    if (
        target.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or target.is_symlink()
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or value.get("parent_disposition") != _parent(root)
        or any(value.get(key) != expected for key, expected in _fixed().items())
        or value.get("safe_wait_boundary", {}).get("future_outputs_absent") is not True
        or not isinstance(value.get("safe_wait_boundary", {}).get("protected_processes"), dict)
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or value.get("control_surface", {}).get("file_count") != len(CONTROL_FILES)
        or value.get("control_surface", {}).get("manifest_sha256") != payload_sha256(manifest)
        or value.get("control_surface", {}).get("must_remain_absent") != list(MUST_REMAIN_ABSENT)
        or value.get("decision_contract_sha256")
        != payload_sha256({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.42.00 protocol contract is invalid")
    for relative, digest in manifest.items():
        if sha256(ordinary(root, relative)) != digest:
            raise RuntimeError("V2.42.00 control surface drifted")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.00 protocol output path drifted")
    publish_new(target, build_protocol())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
