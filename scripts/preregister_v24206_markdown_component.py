#!/usr/bin/env python3
"""Freeze the selected-baseline Markdown publisher before V2.42.04 terminates."""

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

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from deepwide_agent.v24206_markdown_publisher import (  # noqa: E402
    build_markdown_publication_manifest,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.preregister_v24204_postdecision_work_order import (  # noqa: E402
    PROTECTED_PROCESS_MARKERS as V24204_PROTECTED_PROCESS_MARKERS,
)
from scripts.publish_v24206_markdown_component import (  # noqa: E402
    CANDIDATE_ROOT,
    EXPECTED_TESTS,
    OUTPUT as PUBLICATION,
)


ROLE = "v24206_selected_markdown_component_preregistration"
PROTOCOL_ID = "v24206_selected_baseline_markdown_component_publisher_v1"
OUTPUT = Path(
    "results/v24206_selected_markdown_component_preregistration_v1_20260731.json"
)
STATE = Path(
    "outputs/v24206_selected_markdown_component_watcher_state_v1_20260731.json"
)
ACTIVATION = Path(
    "results/v24206_selected_markdown_component_activation_v1_20260731.json"
)
WAIT_AUDIT = Path(
    "results/v24206_selected_markdown_component_wait_activation_audit_v1_20260731.json"
)
PARENT_PROTOCOL = Path(
    "results/v24204_postdecision_work_order_preregistration_v1_20260731.json"
)
PARENT_PROTOCOL_SHA256 = (
    "aedd97c0ccbfaa3e18f157aa56e0d0969c39fc28b0903cbe2260a3db1172d5e4"
)
PARENT_ACTIVATION = Path(
    "results/v24204_postdecision_work_order_activation_v1_20260731.json"
)
PARENT_ACTIVATION_SHA256 = (
    "92c726d4b32caaf09cd80f7ed91e0c2e9dca13b3b8ef0d172300210a363222ca"
)
PARENT_WAIT_AUDIT = Path(
    "results/v24204_postdecision_work_order_wait_activation_audit_v1_20260731.json"
)
PARENT_WAIT_AUDIT_SHA256 = (
    "1bb747cb31b25b49a98cd654546bbac797061a62a7203577f819da84213d3c6c"
)
PARENT_STATE = Path(
    "outputs/v24204_postdecision_work_order_watcher_state_v1_20260731.json"
)
PARENT_SELECTED_WORK_ORDER = Path(
    "results/v24204_selected_postdecision_work_order_v1_20260731.json"
)
FEASIBILITY_AUDIT = Path(
    "results/v24205_markdown_rebase_feasibility_audit_v1_20260731.json"
)
FEASIBILITY_AUDIT_SHA256 = (
    "271151d8b41612deb2eb1667a1d038e1b44fbd409eae5c9cfd3a370277315c1c"
)
WATCHER_MARKER = "scripts/watch_v24206_markdown_component.py"
MUST_REMAIN_ABSENT = ("scripts/__init__.py", "sitecustomize.py", "usercustomize.py")
CONTROL_FILES = (
    "src/deepwide_agent/v24206_markdown_publisher.py",
    "scripts/publish_v24206_markdown_component.py",
    "scripts/preregister_v24206_markdown_component.py",
    "scripts/watch_v24206_markdown_component.py",
    "scripts/activate_v24206_markdown_component.py",
    "scripts/audit_v24206_markdown_component_wait_activation.py",
    "tests/test_v24206_markdown_publisher.py",
    "tests/test_publish_v24206_markdown_component.py",
    "tests/test_preregister_v24206_markdown_component.py",
    "tests/test_watch_v24206_markdown_component.py",
    "tests/test_activate_v24206_markdown_component.py",
    "tests/test_audit_v24206_markdown_component_wait_activation.py",
)
PROTECTED_PROCESS_MARKERS = {
    **V24204_PROTECTED_PROCESS_MARKERS,
    "v24204_postdecision_work_order_watcher": (
        "scripts/watch_v24204_postdecision_work_order.py"
    ),
}
DECISION_FIELDS = (
    "protocol_id",
    "parent_contract",
    "publication_contract",
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
        raise RuntimeError("V2.42.06 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.06 expected an ordinary file: {relative}")
    if digest is not None and sha256(path) != digest:
        raise RuntimeError(f"V2.42.06 frozen input drifted: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.06 expected an ordinary JSON file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.06 expected one JSON object")
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
        raise RuntimeError("V2.42.06 process stat is truncated")
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
            raise RuntimeError(f"V2.42.06 process identity is invalid: {marker}")
        pid = matches[0]["pid"]
        result[name] = {
            "marker": marker,
            "pid": pid,
            "start_ticks": _start_ticks(proc_root, pid),
            "python_isolated_no_bytecode_required": isolated,
            "command_line_emitted": False,
        }
    return result


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parents(root: Path) -> dict[str, Any]:
    protocol = read_object(ordinary(root, PARENT_PROTOCOL, PARENT_PROTOCOL_SHA256))
    activation = read_object(
        ordinary(root, PARENT_ACTIVATION, PARENT_ACTIVATION_SHA256)
    )
    wait = read_object(ordinary(root, PARENT_WAIT_AUDIT, PARENT_WAIT_AUDIT_SHA256))
    feasibility = read_object(
        ordinary(root, FEASIBILITY_AUDIT, FEASIBILITY_AUDIT_SHA256)
    )
    conclusion = feasibility.get("conclusion") or {}
    if (
        protocol.get("role") != "v24204_postdecision_work_order_preregistration"
        or protocol.get("protocol_id")
        != "v24204_content_free_postdecision_work_order_v1"
        or protocol.get("authorization", {}).get("benchmark_forward_or_full220_launch")
        is not False
        or activation.get("role") != "v24204_postdecision_work_order_activation"
        or activation.get("benchmark_forward_or_full220_launch_allowed") is not False
        or not _sealed(activation, "activation_payload_sha256")
        or wait.get("role")
        != "v24204_postdecision_work_order_wait_activation_audit"
        or not _sealed(wait, "audit_payload_sha256")
        or feasibility.get("role") != "v24205_markdown_rebase_feasibility_audit"
        or feasibility.get("label_blind") is not True
        or conclusion.get("p12_schema69_schema70_bytes_repo_local_and_exact") is not True
        or conclusion.get("schema76_schema77_markdown_production_hooks_compatible")
        is not True
        or conclusion.get("schema76_schema77_mainline_scope_hook_already_active_once")
        is not True
        or conclusion.get("branch_scope_must_not_reapply_historical_v24104_patch")
        is not True
        or feasibility.get("candidate_tree_or_package_materialized") is not False
        or feasibility.get("benchmark_forward_or_full220_launch_allowed") is not False
        or not _sealed(feasibility, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.06 frozen parent contract drifted")
    return {
        "v24204_protocol": {
            "path": str(PARENT_PROTOCOL),
            "sha256": PARENT_PROTOCOL_SHA256,
        },
        "v24204_activation": {
            "path": str(PARENT_ACTIVATION),
            "sha256": PARENT_ACTIVATION_SHA256,
        },
        "v24204_wait_audit": {
            "path": str(PARENT_WAIT_AUDIT),
            "sha256": PARENT_WAIT_AUDIT_SHA256,
        },
        "v24205_feasibility_audit": {
            "path": str(FEASIBILITY_AUDIT),
            "sha256": FEASIBILITY_AUDIT_SHA256,
            "audit_payload_sha256": feasibility["audit_payload_sha256"],
        },
    }


def _fixed() -> dict[str, Any]:
    manifest = build_markdown_publication_manifest()
    return {
        "parent_contract": {
            "state_path": str(PARENT_STATE),
            "selected_work_order_path": str(PARENT_SELECTED_WORK_ORDER),
            "before_parent_terminal_state_envelope_only": True,
            "selected_work_order_read_only_after_parent_terminal": True,
            "numeric_metrics_reports_predictions_or_aggregates_read": False,
        },
        "publication_contract": {
            "manifest_payload_sha256": manifest["manifest_payload_sha256"],
            "summary": manifest["summary"],
            "selection_frozen_before_parent_outcome": True,
            "terminal_work_order_must_be_content_addressed_to_frozen_manifest": True,
            "owned_component": "markdown_rank_slot",
            "unowned_scope_search_and_entropy_remain_blockers": True,
            "p12_reuses_byte_exact_historical_schema69_publication": True,
            "schema76_schema77_rebase_selected_baseline_only": True,
            "schema76_schema77_expected_joint_tests": EXPECTED_TESTS,
            "branch_scope_patch_or_namespace_alias_applied": False,
            "joint_package_or_package_gate_built": False,
        },
        "execution": {
            "watcher_marker": WATCHER_MARKER,
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "state_path": str(STATE),
            "activation_path": str(ACTIVATION),
            "publication_path": str(PUBLICATION),
            "candidate_root": str(CANDIDATE_ROOT.relative_to(ROOT)),
            "wait_audit_path": str(WAIT_AUDIT),
        },
        "source_policy": {
            "before_activation_parent_state_opened": False,
            "after_activation_only_parent_safe_state_envelope_opened": True,
            "after_parent_terminal_selected_work_order_opened": True,
            "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted": False,
            "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
        },
        "authorization": {
            "selected_markdown_publisher_active_after_activation": True,
            "component_publication_after_validated_parent_terminal": True,
            "selected_baseline_markdown_candidate_materialization": True,
            "historical_p12_markdown_binding": True,
            "branch_scope_patch_or_namespace_alias": False,
            "search_yield_implementation_or_publication": False,
            "entropy_controller_implementation_or_publication": False,
            "joint_package_build_merge_materialization_or_freeze_generation": False,
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
        raise RuntimeError("V2.42.06 may only freeze the canonical workspace")
    if not CANDIDATE_ROOT.resolve(strict=False).is_relative_to(root):
        raise RuntimeError("V2.42.06 candidate root escaped the repository")
    if any((root / name).exists() or (root / name).is_symlink() for name in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.42.06 unattested Python bootstrap path appeared")
    future = (OUTPUT, STATE, ACTIVATION, WAIT_AUDIT, PUBLICATION)
    future_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in future
    ) and not CANDIDATE_ROOT.exists() and not CANDIDATE_ROOT.is_symlink()
    if require_pristine and not future_absent:
        raise RuntimeError("V2.42.06 create-exclusive boundary is not pristine")
    selected_absent = not (root / PARENT_SELECTED_WORK_ORDER).exists() and not (
        root / PARENT_SELECTED_WORK_ORDER
    ).is_symlink()
    if require_pristine and not selected_absent:
        raise RuntimeError("V2.42.06 parent selected work order appeared before freeze")
    control = {relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES}
    fixed = _fixed()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        "frozen_parents": _parents(root),
        **fixed,
        "safe_wait_boundary": {
            "future_outputs_and_candidate_absent": future_absent,
            "v24204_selected_work_order_absent_before_freeze": selected_absent,
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
        or value.get("frozen_parents") != _parents(root)
        or any(value.get(key) != expected for key, expected in _fixed().items())
        or value.get("safe_wait_boundary", {}).get(
            "future_outputs_and_candidate_absent"
        )
        is not True
        or value.get("safe_wait_boundary", {}).get(
            "v24204_selected_work_order_absent_before_freeze"
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
        or value.get("decision_contract_sha256")
        != payload_sha256({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.42.06 protocol contract is invalid")
    for relative, digest in manifest.items():
        if sha256(ordinary(root, relative)) != digest:
            raise RuntimeError("V2.42.06 control surface drifted")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.06 protocol output path drifted")
    publish_new(target, build_protocol())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
