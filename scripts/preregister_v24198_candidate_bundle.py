#!/usr/bin/env python3
"""Freeze the wait-only V2.41.98 selected-candidate bundle compiler."""

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
from deepwide_agent.v24198_candidate_bundle import (  # noqa: E402
    BUNDLE,
    COMPILER_PROTOCOL,
    GO_RECEIPT,
    HANDOFF,
    QUALITY_TERMINAL_RECEIPT,
    SELECTION_PROTOCOL,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)


ROLE = "v24198_candidate_bundle_preregistration"
PROTOCOL_ID = "v24198_selected_candidate_bundle_compiler_v1"
OUTPUT = COMPILER_PROTOCOL
STATE = Path("outputs/v24198_candidate_bundle_watcher_state_v1_20260731.json")
ACTIVATION = Path("results/v24198_candidate_bundle_activation_v1_20260731.json")
WAIT_AUDIT = Path(
    "results/v24198_candidate_bundle_wait_activation_audit_v1_20260731.json"
)
WATCHER_MARKER = "scripts/watch_v24198_candidate_bundle.py"
PARENT_PROTOCOL = Path(
    "results/v24197_parallel_all220_preregistration_v1_20260731.json"
)
PARENT_PROTOCOL_SHA256 = (
    "768b787d8b092f9416ab0a9f4a795423d46b060dba558f743454d0d2a0086b4d"
)
PARENT_ACTIVATION = Path(
    "results/v24197_parallel_all220_activation_v1_20260731.json"
)
PARENT_ACTIVATION_SHA256 = (
    "00e0915ed34020a602f2ae609f4ffe18a1a413e708120abb6c74a3a4f053dce3"
)
PARENT_WAIT_AUDIT = Path(
    "results/v24197_parallel_all220_wait_activation_audit_v1_20260731.json"
)
PARENT_WAIT_AUDIT_SHA256 = (
    "6748e559b85e1339bc83e8d83af9052d2a837c498c3afe06f706c95c46b0bba7"
)
CAPACITY_REPORT = Path("results/v24196_capacity_ladder_report_v1_20260731.json")
CAPACITY_FREEZE = Path(
    "results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json"
)
CAPACITY_PARENT_PROTOCOL_SHA256 = (
    "e413f85dab40c65fee6202f84df2cf45c333cef4a10e81d22950c1c3b528e4d0"
)
PLAN = Path("results/v24197_parallel_all220_plan_v1_20260731.json")
PROTECTED_PROCESS_MARKERS = {
    "r1_launcher": "scripts/launch_frozen_deepwide.py",
    "r1_forward": "scripts/run_deepwide_agent.py",
    "v24187_phase_watcher": "scripts/watch_v24187_phase_liveness.py",
    "v24193_gate2a_watcher": "scripts/watch_v24193_replicate_aware_gate2a.py",
    "v24194_capacity_watcher": "scripts/watch_v24194_capacity_ladder.py",
    "v24195_compatibility_watcher": "scripts/watch_v24195_lease_owner_compatibility.py",
    "v24196_capacity_executor": "scripts/watch_v24196_capacity_executor.py",
    "v24197_parallel_planner": "scripts/watch_v24197_parallel_all220.py",
}
CONTROL_FILES = (
    "src/deepwide_agent/v24198_candidate_bundle.py",
    "scripts/preregister_v24198_candidate_bundle.py",
    "scripts/watch_v24198_candidate_bundle.py",
    "scripts/activate_v24198_candidate_bundle.py",
    "scripts/audit_v24198_candidate_bundle_wait_activation.py",
    "tests/test_v24198_candidate_bundle.py",
    "tests/test_preregister_v24198_candidate_bundle.py",
    "tests/test_watch_v24198_candidate_bundle.py",
    "tests/test_activate_v24198_candidate_bundle.py",
    "tests/test_audit_v24198_candidate_bundle_wait_activation.py",
)
MUST_REMAIN_ABSENT = ("scripts/__init__.py", "sitecustomize.py", "usercustomize.py")
DECISION_FIELDS = (
    "protocol_id",
    "parent",
    "selection_contract",
    "capacity_contract",
    "compilation_contract",
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
        raise RuntimeError("V2.41.98 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.41.98 expected an ordinary file: {relative}")
    if digest is not None and sha256(path) != digest:
        raise RuntimeError(f"V2.41.98 frozen parent drifted: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.41.98 expected an ordinary JSON file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.41.98 expected a JSON object")
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
        raise RuntimeError("V2.41.98 process stat is truncated")
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
        isolated = name not in {"r1_launcher", "r1_forward"}
        if (
            len(matches) != 1
            or (
                isolated
                and not ("-I" in matches[0]["argv"] and "-B" in matches[0]["argv"])
            )
        ):
            raise RuntimeError(f"V2.41.98 protected process identity is invalid: {name}")
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
    protocol = read_object(ordinary(root, PARENT_PROTOCOL, PARENT_PROTOCOL_SHA256))
    ordinary(root, PARENT_ACTIVATION, PARENT_ACTIVATION_SHA256)
    ordinary(root, PARENT_WAIT_AUDIT, PARENT_WAIT_AUDIT_SHA256)
    if (
        protocol.get("role") != "v24197_parallel_all220_preregistration"
        or protocol.get("protocol_id")
        != "v24197_capacity_bound_parallel_all220_planner_v1"
        or protocol.get("label_blind") is not True
        or protocol.get("authorization", {}).get(
            "benchmark_forward_or_full220_launch"
        )
        is not False
        or protocol.get("authorization", {}).get(
            "candidate_bundle_or_go_receipt_creation"
        )
        is not False
    ):
        raise RuntimeError("V2.41.98 parent authorization drifted")
    return {
        "protocol": {"path": str(PARENT_PROTOCOL), "sha256": PARENT_PROTOCOL_SHA256},
        "activation": {
            "path": str(PARENT_ACTIVATION),
            "sha256": PARENT_ACTIVATION_SHA256,
        },
        "wait_audit": {
            "path": str(PARENT_WAIT_AUDIT),
            "sha256": PARENT_WAIT_AUDIT_SHA256,
        },
    }


def _fixed_contracts() -> dict[str, Any]:
    return {
        "selection_contract": {
            "selector_protocol_path": str(SELECTION_PROTOCOL),
            "quality_chain_terminal_receipt_path": str(QUALITY_TERMINAL_RECEIPT),
            "selected_candidate_handoff_path": str(HANDOFF),
            "selector_protocol_must_be_frozen_before_quality_outcomes": True,
            "entire_quality_chain_terminal_required": True,
            "selection_rule_live_replay_required": True,
            "candidate_publication_and_method_contract_hash_bound": True,
            "compiler_has_no_candidate_selection_discretion": True,
        },
        "capacity_contract": {
            "report_path": str(CAPACITY_REPORT),
            "freeze_path": str(CAPACITY_FREEZE),
            "parent_protocol_sha256": CAPACITY_PARENT_PROTOCOL_SHA256,
            "live_replay_with_v24197_validator_required": True,
            "capacity_no_go_is_terminal_no_bundle": True,
        },
        "compilation_contract": {
            "go_receipt_path": str(GO_RECEIPT),
            "bundle_path": str(BUNDLE),
            "four_canonical_shards": ["test_s01", "test_s02", "test_s03", "devval"],
            "shard_counts": [52, 52, 52, 64],
            "exact_disjoint_all220_required": True,
            "same_pipeline_code_prompt_search_budget_threshold_required": True,
            "capacity_workers_copied_exactly": True,
            "fresh_output_roots_required": True,
            "forward_failures_scored_as_zero": True,
            "resume_or_selective_rerun_allowed": False,
            "go_receipt_and_bundle_keep_launch_false": True,
            "v24197_live_candidate_replay_required_after_publication": True,
        },
        "execution": {
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "watcher_marker": WATCHER_MARKER,
            "state_path": str(STATE),
            "activation_path": str(ACTIVATION),
            "wait_audit_path": str(WAIT_AUDIT),
        },
        "source_policy": {
            "safe_file_existence_and_parent_metadata_only_before_all_inputs_exist": True,
            "selector_protocol_terminal_receipt_handoff_and_freezes_opened_only_after_capacity_pair": True,
            "candidate_manifest_bytes_hash_only_never_parsed_or_emitted": True,
            "benchmark_question_answer_evidence_prediction_or_url_values_parsed_or_emitted": False,
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "process_command_lines_or_environment_emitted": False,
        },
        "authorization": {
            "wait_only_candidate_bundle_compiler": True,
            "selected_go_receipt_and_bundle_publish_after_all_inputs_validate": True,
            "candidate_selection_or_gate_evaluation": False,
            "shared_api_lease_acquire": False,
            "network_model_search_fetch_evaluator_or_api_call": False,
            "benchmark_forward_or_full220_launch": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "future_executor_requires_separate_preregistration_and_activation": True,
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
        raise RuntimeError("V2.41.98 may only freeze the canonical workspace")
    if any((root / name).exists() or (root / name).is_symlink() for name in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.41.98 unattested Python bootstrap path appeared")
    parent = _parent(root)
    pristine_paths = (
        OUTPUT,
        STATE,
        ACTIVATION,
        WAIT_AUDIT,
        SELECTION_PROTOCOL,
        QUALITY_TERMINAL_RECEIPT,
        HANDOFF,
        GO_RECEIPT,
        BUNDLE,
        PLAN,
        CAPACITY_REPORT,
        CAPACITY_FREEZE,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink()
        for path in pristine_paths
    ):
        raise RuntimeError("V2.41.98 create-exclusive boundary is not pristine")
    manifest = {relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES}
    fixed = _fixed_contracts()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        "parent": parent,
        "selection_contract": fixed["selection_contract"],
        "capacity_contract": fixed["capacity_contract"],
        "compilation_contract": fixed["compilation_contract"],
        "safe_wait_boundary": {
            "all_future_inputs_and_outputs_absent": (
                True
                if not require_pristine
                else all(
                    not (root / path).exists() and not (root / path).is_symlink()
                    for path in pristine_paths
                )
            ),
            "protected_processes": protected_processes(proc_root),
        },
        "execution": fixed["execution"],
        "source_policy": fixed["source_policy"],
        "authorization": fixed["authorization"],
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
        or value.get("parent") != _parent(root)
        or any(value.get(key) != expected for key, expected in _fixed_contracts().items())
        or not isinstance(value.get("safe_wait_boundary"), dict)
        or set(value["safe_wait_boundary"])
        != {"all_future_inputs_and_outputs_absent", "protected_processes"}
        or value["safe_wait_boundary"].get("all_future_inputs_and_outputs_absent") is not True
        or not isinstance(value["safe_wait_boundary"].get("protected_processes"), dict)
        or set(value["safe_wait_boundary"]["protected_processes"])
        != set(PROTECTED_PROCESS_MARKERS)
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or control.get("file_count") != len(CONTROL_FILES)
        or control.get("manifest_sha256") != payload_sha256(manifest)
        or set(control.get("must_remain_absent") or []) != set(MUST_REMAIN_ABSENT)
        or value.get("decision_contract_sha256")
        != payload_sha256({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.41.98 protocol contract is invalid")
    if any((root / name).exists() or (root / name).is_symlink() for name in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.41.98 unattested Python bootstrap path appeared")
    seen_pids: set[int] = set()
    for name, marker in PROTECTED_PROCESS_MARKERS.items():
        row = value["safe_wait_boundary"]["protected_processes"].get(name)
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
            raise RuntimeError("V2.41.98 protected process seal is invalid")
        seen_pids.add(row["pid"])
    for relative, digest in manifest.items():
        if sha256(ordinary(root, relative)) != digest:
            raise RuntimeError("V2.41.98 control surface drifted")
    return {"path": raw, "sha256": sha256(raw), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.41.98 output path drifted")
    publish_new(target, build_protocol())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
