#!/usr/bin/env python3
"""Freeze the label-blind V2.41.97 capacity-bound all-220 planner."""

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

from deepwide_agent.v24197_parallel_all220 import payload_sha256  # noqa: E402
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)


ROLE = "v24197_parallel_all220_preregistration"
PROTOCOL_ID = "v24197_capacity_bound_parallel_all220_planner_v1"
OUTPUT = Path("results/v24197_parallel_all220_preregistration_v1_20260731.json")
STATE = Path("outputs/v24197_parallel_all220_watcher_state_v1_20260731.json")
PLAN = Path("results/v24197_parallel_all220_plan_v1_20260731.json")
BUNDLE = Path("results/v24197_fresh_all220_execution_bundle_v1_20260731.json")
ACTIVATION = Path("results/v24197_parallel_all220_activation_v1_20260731.json")
WAIT_AUDIT = Path("results/v24197_parallel_all220_wait_activation_audit_v1_20260731.json")
WATCHER_MARKER = "scripts/watch_v24197_parallel_all220.py"
PROTECTED_PROCESS_MARKERS = {
    "r1_launcher": "scripts/launch_frozen_deepwide.py",
    "r1_forward": "scripts/run_deepwide_agent.py",
    "v24187_phase_watcher": "scripts/watch_v24187_phase_liveness.py",
    "v24193_gate2a_watcher": "scripts/watch_v24193_replicate_aware_gate2a.py",
    "v24194_capacity_watcher": "scripts/watch_v24194_capacity_ladder.py",
    "v24195_compatibility_watcher": "scripts/watch_v24195_lease_owner_compatibility.py",
    "v24196_capacity_executor": "scripts/watch_v24196_capacity_executor.py",
}
PARENT_PROTOCOL = Path(
    "results/v24196_capacity_executor_preregistration_v1_20260731.json"
)
PARENT_PROTOCOL_SHA256 = (
    "e413f85dab40c65fee6202f84df2cf45c333cef4a10e81d22950c1c3b528e4d0"
)
PARENT_ACTIVATION = Path(
    "results/v24196_capacity_executor_activation_v1_20260731.json"
)
PARENT_ACTIVATION_SHA256 = (
    "5c08d330003d9c4c59168269a900c63612fe651aff16b2f47f73c6fcb95015c7"
)
PARENT_WAIT_AUDIT = Path(
    "results/v24196_capacity_executor_wait_activation_audit_v1_20260731.json"
)
PARENT_WAIT_AUDIT_SHA256 = (
    "f310049a159c4a5b40240a0b375ebe9cefc48e7fc07afc9f0fdb8a47ab335866"
)
CAPACITY_REPORT = Path("results/v24196_capacity_ladder_report_v1_20260731.json")
CAPACITY_FREEZE = Path(
    "results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json"
)
CONTROL_FILES = (
    "src/deepwide_agent/v24197_parallel_all220.py",
    "scripts/preregister_v24197_parallel_all220.py",
    "scripts/watch_v24197_parallel_all220.py",
    "scripts/activate_v24197_parallel_all220.py",
    "scripts/audit_v24197_parallel_all220_wait_activation.py",
    "tests/test_v24197_parallel_all220.py",
    "tests/test_preregister_v24197_parallel_all220.py",
    "tests/test_watch_v24197_parallel_all220.py",
    "tests/test_activate_v24197_parallel_all220.py",
    "tests/test_audit_v24197_parallel_all220_wait_activation.py",
)
CANONICAL_ID_FILES = {
    "configs/full220_v2403_r1_test_s01.ids": (
        "9f4c7bb4e9f63b01b574a52ec840266358dae6d9982dc7caebfeb813eca02dfb"
    ),
    "configs/full220_v2403_r1_test_s02.ids": (
        "2b48a04896437fdea127e02ad7980f2cb9310db9a16841696affd04796502bbd"
    ),
    "configs/full220_v2403_r1_test_s03.ids": (
        "abaadc27927a9dbd5ad8cc856513baa85e8c900ed041cf6e5c0978534d103566"
    ),
    "configs/full220_v2403_r1_devval_s04.ids": (
        "79ba11a41c186daa80e8779e8fa2c1b47e7907f8e398d817dedb43099333d69c"
    ),
}
CANONICAL_ALL220_SHA256 = (
    "cace8746d5a817a467e7cb70e715ee599a242cc88ce4474802b9d93a9221082b"
)
MUST_REMAIN_ABSENT = ("scripts/__init__.py", "sitecustomize.py", "usercustomize.py")
DECISION_FIELDS = (
    "protocol_id",
    "parent",
    "capacity_input",
    "candidate_input",
    "planning_contract",
    "safe_wait_boundary",
    "execution",
    "source_policy",
    "authorization",
    "control_surface",
)
PROTOCOL_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "label_blind",
        *DECISION_FIELDS,
        "decision_contract_sha256",
    }
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ordinary(root: Path, relative: str | Path, digest: str | None = None) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.41.97 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.41.97 expected an ordinary file: {relative}")
    if digest is not None and sha256(path) != digest:
        raise RuntimeError(f"V2.41.97 frozen parent drifted: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.41.97 expected an ordinary JSON file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.41.97 expected a JSON object")
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
        raise RuntimeError("V2.41.97 process stat is truncated")
    return int(suffix[19])


def protected_processes(proc_root: Path = Path("/proc")) -> dict[str, Any]:
    rows = process_snapshot(proc_root)
    result: dict[str, Any] = {}
    for name, marker in PROTECTED_PROCESS_MARKERS.items():
        matches: list[dict[str, Any]] = []
        for row in rows:
            argv = [str(value) for value in row.get("argv") or []]
            script = actual_python_script(argv)
            if script is not None and (
                script == marker or script.endswith("/" + marker)
            ):
                matches.append({"pid": int(row["pid"]), "argv": argv})
        require_isolated = name not in {"r1_launcher", "r1_forward"}
        if (
            len(matches) != 1
            or (
                require_isolated
                and not ("-I" in matches[0]["argv"] and "-B" in matches[0]["argv"])
            )
        ):
            raise RuntimeError(f"V2.41.97 protected process identity is invalid: {name}")
        pid = matches[0]["pid"]
        result[name] = {
            "marker": marker,
            "pid": pid,
            "start_ticks": _start_ticks(proc_root, pid),
            "python_isolated_no_bytecode_required": require_isolated,
            "command_line_emitted": False,
        }
    return result


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    require_pristine: bool = True,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.41.97 may only freeze the canonical workspace")
    if any((root / name).exists() or (root / name).is_symlink() for name in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.41.97 unattested Python bootstrap path appeared")
    parent = read_object(ordinary(root, PARENT_PROTOCOL, PARENT_PROTOCOL_SHA256))
    ordinary(root, PARENT_ACTIVATION, PARENT_ACTIVATION_SHA256)
    ordinary(root, PARENT_WAIT_AUDIT, PARENT_WAIT_AUDIT_SHA256)
    for relative, digest in CANONICAL_ID_FILES.items():
        ordinary(root, relative, digest)
    if (
        parent.get("role") != "v24196_capacity_executor_preregistration"
        or parent.get("protocol_id") != "v24196_v24194_capacity_executor_successor_v1"
        or parent.get("authorization", {}).get("future_all220_launch") is not False
        or parent.get("authorization", {}).get("benchmark_forward_or_evaluator_call")
        is not False
    ):
        raise RuntimeError("V2.41.97 parent authorization drifted")
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (
            OUTPUT,
            STATE,
            PLAN,
            BUNDLE,
            ACTIVATION,
            WAIT_AUDIT,
            CAPACITY_REPORT,
            CAPACITY_FREEZE,
        )
    ):
        raise RuntimeError("V2.41.97 create-exclusive boundary is not pristine")
    manifest = {relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        "parent": {
            "protocol": {"path": str(PARENT_PROTOCOL), "sha256": PARENT_PROTOCOL_SHA256},
            "activation": {"path": str(PARENT_ACTIVATION), "sha256": PARENT_ACTIVATION_SHA256},
            "wait_audit": {"path": str(PARENT_WAIT_AUDIT), "sha256": PARENT_WAIT_AUDIT_SHA256},
        },
        "capacity_input": {
            "report_path": str(CAPACITY_REPORT),
            "freeze_path": str(CAPACITY_FREEZE),
            "parent_protocol_sha256": PARENT_PROTOCOL_SHA256,
            "must_be_live_recomputed_not_trusted_by_summary": True,
            "capacity_no_go_is_terminal_no_plan": True,
        },
        "candidate_input": {
            "bundle_path": str(BUNDLE),
            "quality_go_receipt_required": True,
            "quality_go_receipt_is_structural_input_not_execution_authority": True,
            "bundle_and_go_receipt_must_both_keep_forward_launch_false": True,
            "four_shards": ["test_s01", "test_s02", "test_s03", "devval"],
            "shard_counts": [52, 52, 52, 64],
            "exact_disjoint_all220_required": True,
            "canonical_all220_source_files": {
                relative: {"sha256": digest}
                for relative, digest in CANONICAL_ID_FILES.items()
            },
            "canonical_all220_opaque_partition_sha256": CANONICAL_ALL220_SHA256,
            "one_pipeline_code_prompt_search_budget_threshold_required": True,
            "fresh_output_roots_required": True,
            "search_capacity_preflight_required": True,
        },
        "planning_contract": {
            "capacity_workers_copied_exactly": True,
            "parallel_shard_width_capped_by_capacity": True,
            "worst_case_model_request_concurrency_must_not_exceed_capacity": True,
            "fixed_wave_schedule_for_entire_all220": True,
            "single_parent_shared_lease_owner_required_for_future_executor": True,
            "forward_failures_scored_as_zero": True,
            "resume_or_selective_rerun_allowed": False,
            "plan_itself_never_authorizes_launch": True,
        },
        "safe_wait_boundary": {
            "v24196_capacity_report_absent": not (root / CAPACITY_REPORT).exists()
            and not (root / CAPACITY_REPORT).is_symlink(),
            "v24196_capacity_freeze_absent": not (root / CAPACITY_FREEZE).exists()
            and not (root / CAPACITY_FREEZE).is_symlink(),
            "candidate_bundle_absent": not (root / BUNDLE).exists(),
            "parallel_plan_absent": not (root / PLAN).exists(),
            "protected_processes": protected_processes(proc_root),
        },
        "execution": {
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "watcher_marker": WATCHER_MARKER,
            "state_path": str(STATE),
            "activation_path": str(ACTIVATION),
            "wait_audit_path": str(WAIT_AUDIT),
            "plan_path": str(PLAN),
        },
        "source_policy": {
            "safe_capacity_state_and_immutable_file_metadata_only_before_inputs_exist": True,
            "opaque_id_and_manifest_files_only_after_candidate_bundle_and_capacity_pair_exist": True,
            "candidate_manifest_bytes_hash_only_never_parsed_or_emitted": True,
            "benchmark_question_answer_evidence_prediction_url_values_parsed_or_emitted": False,
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "process_command_lines_or_environment_emitted": False,
        },
        "authorization": {
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "current_r1_or_quality_chain_forward_config_change": False,
            "shared_api_lease_acquire": False,
            "network_model_search_fetch_evaluator_or_api_call": False,
            "benchmark_forward_or_full220_launch": False,
            "candidate_bundle_or_go_receipt_creation": False,
            "parallel_plan_creation_after_all_inputs_validate": True,
            "future_executor_requires_separate_preregistration_and_activation": True,
            "leaderboard_submission_or_sota_claim": False,
        },
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha256(manifest),
            "must_remain_absent": list(MUST_REMAIN_ABSENT),
        },
    }
    value["decision_contract_sha256"] = payload_sha256(
        {key: value[key] for key in DECISION_FIELDS}
    )
    return value


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    raw = path if path.is_absolute() else root / path
    value = read_object(raw)
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    expected_parent = {
        "protocol": {"path": str(PARENT_PROTOCOL), "sha256": PARENT_PROTOCOL_SHA256},
        "activation": {"path": str(PARENT_ACTIVATION), "sha256": PARENT_ACTIVATION_SHA256},
        "wait_audit": {"path": str(PARENT_WAIT_AUDIT), "sha256": PARENT_WAIT_AUDIT_SHA256},
    }
    expected_capacity = {
        "report_path": str(CAPACITY_REPORT),
        "freeze_path": str(CAPACITY_FREEZE),
        "parent_protocol_sha256": PARENT_PROTOCOL_SHA256,
        "must_be_live_recomputed_not_trusted_by_summary": True,
        "capacity_no_go_is_terminal_no_plan": True,
    }
    expected_candidate = {
        "bundle_path": str(BUNDLE),
        "quality_go_receipt_required": True,
        "quality_go_receipt_is_structural_input_not_execution_authority": True,
        "bundle_and_go_receipt_must_both_keep_forward_launch_false": True,
        "four_shards": ["test_s01", "test_s02", "test_s03", "devval"],
        "shard_counts": [52, 52, 52, 64],
        "exact_disjoint_all220_required": True,
        "canonical_all220_source_files": {
            relative: {"sha256": digest}
            for relative, digest in CANONICAL_ID_FILES.items()
        },
        "canonical_all220_opaque_partition_sha256": CANONICAL_ALL220_SHA256,
        "one_pipeline_code_prompt_search_budget_threshold_required": True,
        "fresh_output_roots_required": True,
        "search_capacity_preflight_required": True,
    }
    expected_planning = {
        "capacity_workers_copied_exactly": True,
        "parallel_shard_width_capped_by_capacity": True,
        "worst_case_model_request_concurrency_must_not_exceed_capacity": True,
        "fixed_wave_schedule_for_entire_all220": True,
        "single_parent_shared_lease_owner_required_for_future_executor": True,
        "forward_failures_scored_as_zero": True,
        "resume_or_selective_rerun_allowed": False,
        "plan_itself_never_authorizes_launch": True,
    }
    expected_execution = {
        "python_flags": ["-I", "-B"],
        "poll_seconds": 60,
        "watcher_marker": WATCHER_MARKER,
        "state_path": str(STATE),
        "activation_path": str(ACTIVATION),
        "wait_audit_path": str(WAIT_AUDIT),
        "plan_path": str(PLAN),
    }
    expected_source = {
        "safe_capacity_state_and_immutable_file_metadata_only_before_inputs_exist": True,
        "opaque_id_and_manifest_files_only_after_candidate_bundle_and_capacity_pair_exist": True,
        "candidate_manifest_bytes_hash_only_never_parsed_or_emitted": True,
        "benchmark_question_answer_evidence_prediction_url_values_parsed_or_emitted": False,
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "credential_value_or_keyring_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "process_command_lines_or_environment_emitted": False,
    }
    expected_authorization = {
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "current_r1_or_quality_chain_forward_config_change": False,
        "shared_api_lease_acquire": False,
        "network_model_search_fetch_evaluator_or_api_call": False,
        "benchmark_forward_or_full220_launch": False,
        "candidate_bundle_or_go_receipt_creation": False,
        "parallel_plan_creation_after_all_inputs_validate": True,
        "future_executor_requires_separate_preregistration_and_activation": True,
        "leaderboard_submission_or_sota_claim": False,
    }
    boundary = value.get("safe_wait_boundary")
    boundary_valid = bool(
        isinstance(boundary, dict)
        and set(boundary)
        == {
            "v24196_capacity_report_absent",
            "v24196_capacity_freeze_absent",
            "candidate_bundle_absent",
            "parallel_plan_absent",
            "protected_processes",
        }
        and all(
            boundary.get(key) is True
            for key in (
                "v24196_capacity_report_absent",
                "v24196_capacity_freeze_absent",
                "candidate_bundle_absent",
                "parallel_plan_absent",
            )
        )
        and isinstance(boundary.get("protected_processes"), dict)
        and set(boundary["protected_processes"]) == set(PROTECTED_PROCESS_MARKERS)
    )
    if boundary_valid:
        seen_pids: set[int] = set()
        for name, marker in PROTECTED_PROCESS_MARKERS.items():
            row = boundary["protected_processes"][name]
            isolated = name not in {"r1_launcher", "r1_forward"}
            if (
                not isinstance(row, dict)
                or set(row)
                != {
                    "marker",
                    "pid",
                    "start_ticks",
                    "python_isolated_no_bytecode_required",
                    "command_line_emitted",
                }
                or row.get("marker") != marker
                or isinstance(row.get("pid"), bool)
                or not isinstance(row.get("pid"), int)
                or row.get("pid", 0) <= 0
                or row["pid"] in seen_pids
                or isinstance(row.get("start_ticks"), bool)
                or not isinstance(row.get("start_ticks"), int)
                or row.get("start_ticks", 0) <= 0
                or row.get("python_isolated_no_bytecode_required") is not isolated
                or row.get("command_line_emitted") is not False
            ):
                boundary_valid = False
                break
            seen_pids.add(row["pid"])
    if (
        set(value) != PROTOCOL_FIELDS
        or raw.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or raw.is_symlink()
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value.get("label_blind") is not True
        or value.get("parent") != expected_parent
        or value.get("capacity_input") != expected_capacity
        or value.get("candidate_input") != expected_candidate
        or value.get("planning_contract") != expected_planning
        or not boundary_valid
        or value.get("execution") != expected_execution
        or value.get("source_policy") != expected_source
        or value.get("authorization") != expected_authorization
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or control.get("file_count") != len(CONTROL_FILES)
        or control.get("manifest_sha256") != payload_sha256(manifest)
        or set(control.get("must_remain_absent") or []) != set(MUST_REMAIN_ABSENT)
        or value.get("decision_contract_sha256")
        != payload_sha256({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.41.97 protocol contract is invalid")
    ordinary(root, PARENT_PROTOCOL, PARENT_PROTOCOL_SHA256)
    ordinary(root, PARENT_ACTIVATION, PARENT_ACTIVATION_SHA256)
    ordinary(root, PARENT_WAIT_AUDIT, PARENT_WAIT_AUDIT_SHA256)
    for relative, digest in CANONICAL_ID_FILES.items():
        ordinary(root, relative, digest)
    for relative, digest in manifest.items():
        if sha256(ordinary(root, relative)) != digest:
            raise RuntimeError("V2.41.97 control surface drifted")
    return {"path": raw, "sha256": sha256(raw), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.41.97 output path drifted")
    publish_new(target, build_protocol())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
