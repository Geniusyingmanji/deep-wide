#!/usr/bin/env python3
"""Freeze the V2.41.99 outcome-before candidate inheritance selector."""

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

from deepwide_agent.v24199_candidate_selector import (  # noqa: E402
    BASELINE_PUBLICATIONS,
    ENTROPY_ROOT_SOURCE,
    FEATURE_ORDER,
    QUALITY_SOURCES,
    build_slot_manifest,
    derive_terminal_vector,
    object_snapshot,
    payload_sha256,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.preregister_v24198_candidate_bundle import (  # noqa: E402
    PROTECTED_PROCESS_MARKERS as PARENT_PROTECTED_PROCESS_MARKERS,
    protected_processes as parent_protected_processes,
)


ROLE = "v24199_candidate_selector_controller_preregistration"
PROTOCOL_ID = "v24199_outcome_before_inheritance_selector_controller_v1"
SELECTOR_ROLE = "v24198_selected_candidate_selector_preregistration"
SELECTOR_ID = "v24198_predeclared_quality_chain_candidate_selector_v1"
SELECTOR_PROTOCOL = Path(
    "results/v24198_selected_candidate_selector_preregistration_v1_20260731.json"
)
OUTPUT = Path(
    "results/v24199_candidate_selector_controller_preregistration_v1_20260731.json"
)
STATE = Path("outputs/v24199_candidate_selector_watcher_state_v1_20260731.json")
ACTIVATION = Path("results/v24199_candidate_selector_activation_v1_20260731.json")
WAIT_AUDIT = Path(
    "results/v24199_candidate_selector_wait_activation_audit_v1_20260731.json"
)
TERMINAL_RECEIPT = Path(
    "results/v24198_selected_candidate_terminal_receipt_v1_20260731.json"
)
SELECTED_HANDOFF = Path(
    "results/v24198_selected_candidate_handoff_v1_20260731.json"
)
CAPACITY_REPORT = Path("results/v24196_capacity_ladder_report_v1_20260731.json")
CAPACITY_FREEZE = Path(
    "results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json"
)
CAPACITY_PROTOCOL_SHA256 = (
    "e413f85dab40c65fee6202f84df2cf45c333cef4a10e81d22950c1c3b528e4d0"
)
PARENT_PROTOCOL = Path(
    "results/v24198_candidate_bundle_preregistration_v1_20260731.json"
)
PARENT_PROTOCOL_SHA256 = (
    "cc49075e9a3976ca4e72d642918e00178076daebd5c33d49f3f7d9046dacf431"
)
PARENT_ACTIVATION = Path("results/v24198_candidate_bundle_activation_v1_20260731.json")
PARENT_ACTIVATION_SHA256 = (
    "21bb201d79c9d2dc1924398ce818765cc2b4e6a4e9165181d2a0d3f43a9cb256"
)
PARENT_WAIT_AUDIT = Path(
    "results/v24198_candidate_bundle_wait_activation_audit_v1_20260731.json"
)
PARENT_WAIT_AUDIT_SHA256 = (
    "afc1ea4fae0bc345019ef03531a38d08205361010898383b1085e050c6fd9a2b"
)
WATCHER_MARKER = "scripts/watch_v24199_candidate_selector.py"
PARENT_WATCHER_MARKER = "scripts/watch_v24198_candidate_bundle.py"
QUALITY_PROCESS_MARKERS = {
    "v24176_schema77_watcher": "scripts/watch_v24176_predicate_completion_paired_dev.py",
    "v24180_search_yield_launcher": "scripts/launch_v24183_search_yield_after_schema77.py",
    "v24103_markdown_launcher": "scripts/launch_v24185_markdown_after_search_yield.py",
    "v24105_scope_open_watcher": "scripts/watch_v24105_scope_open_paired_dev.py",
    "v24190_tie_aware_watcher": "scripts/watch_v24190_tie_aware_gate2a.py",
    "v24191_policy_value_watcher": "scripts/watch_v24191_policy_value_gate2a.py",
    "v24192_abstain_aware_watcher": "scripts/watch_v24192_abstain_aware_gate2a.py",
}
MUST_REMAIN_ABSENT = ("scripts/__init__.py", "sitecustomize.py", "usercustomize.py")
CONTROL_FILES = (
    "src/deepwide_agent/v24199_candidate_selector.py",
    "scripts/preregister_v24199_candidate_selector.py",
    "scripts/watch_v24199_candidate_selector.py",
    "scripts/activate_v24199_candidate_selector.py",
    "scripts/audit_v24199_candidate_selector_wait_activation.py",
    "tests/test_v24199_candidate_selector.py",
    "tests/test_preregister_v24199_candidate_selector.py",
    "tests/test_watch_v24199_candidate_selector.py",
    "tests/test_activate_v24199_candidate_selector.py",
    "tests/test_audit_v24199_candidate_selector_wait_activation.py",
)
DECISION_FIELDS = (
    "protocol_id",
    "selector_protocol",
    "parent",
    "inheritance_contract",
    "quality_status_sources",
    "capacity_input",
    "publication_contract",
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
        raise RuntimeError("V2.41.99 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.41.99 expected an ordinary file: {relative}")
    if digest is not None and sha256(path) != digest:
        raise RuntimeError(f"V2.41.99 frozen input drifted: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.41.99 expected an ordinary JSON file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.41.99 expected one JSON object")
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
        raise RuntimeError("V2.41.99 process stat is truncated")
    return int(suffix[19])


def _unique_process(marker: str, proc_root: Path) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for row in process_snapshot(proc_root):
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (script == marker or script.endswith("/" + marker)):
            matches.append({"pid": int(row["pid"]), "argv": argv})
    if len(matches) != 1 or not all(flag in matches[0]["argv"] for flag in ("-I", "-B")):
        raise RuntimeError(f"V2.41.99 process identity is invalid: {marker}")
    pid = matches[0]["pid"]
    return {
        "marker": marker,
        "pid": pid,
        "start_ticks": _start_ticks(proc_root, pid),
        "python_isolated_no_bytecode_required": True,
        "command_line_emitted": False,
    }


def protected_processes(proc_root: Path = Path("/proc")) -> dict[str, Any]:
    result = parent_protected_processes(proc_root)
    result["v24198_candidate_bundle_compiler"] = _unique_process(
        PARENT_WATCHER_MARKER, proc_root
    )
    for name, marker in QUALITY_PROCESS_MARKERS.items():
        result[name] = _unique_process(marker, proc_root)
    return result


def quality_preterminal_snapshot(root: Path) -> dict[str, Any]:
    states = {
        name: object_snapshot(root / spec["path"])[0]
        for name, spec in QUALITY_SOURCES.items()
    }
    entropy_root = object_snapshot(root / ENTROPY_ROOT_SOURCE["path"])[0]
    vector, statuses = derive_terminal_vector(states, entropy_root=entropy_root)
    if vector is not None or any(status != "waiting" for status in statuses.values()):
        raise RuntimeError("V2.41.99 selector was not frozen before quality outcomes")
    snapshot = {
        name: {
            "path": str(QUALITY_SOURCES[name]["path"]),
            "role": states[name].get("role"),
            "status": states[name].get("status"),
            "classification": statuses[name],
            "terminal": states[name].get("terminal") is True,
        }
        for name in QUALITY_SOURCES
    }
    snapshot["entropy_root"] = {
        "path": str(ENTROPY_ROOT_SOURCE["path"]),
        "role": entropy_root.get("role"),
        "status": entropy_root.get("status"),
        "classification": "waiting",
        "terminal": entropy_root.get("terminal") is True,
    }
    if any(row["terminal"] for row in snapshot.values()):
        raise RuntimeError("V2.41.99 quality source was terminal before selector freeze")
    return snapshot


def _selector(created: int, slots: dict[str, Any]) -> dict[str, Any]:
    inheritance = {
        "feature_order": list(FEATURE_ORDER),
        "slot_count": len(slots),
        "legal_scope_relationship": "scope_open_implies_markdown",
        "missing_slot_action": "wait_fail_closed_no_fallback",
        "multiple_match_or_merge_conflict_action": "fail_closed",
        "design_only_go_requires_integrated_implementation": True,
        "selection_ranking_or_score_used": False,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": SELECTOR_ROLE,
        "protocol_id": SELECTOR_ID,
        "created_at_unix": created,
        "label_blind": True,
        "selection_frozen_before_quality_outcomes": True,
        "candidate_set_manifest_sha256": payload_sha256(slots),
        "candidate_inheritance_rule_sha256": payload_sha256(inheritance),
        "selection_uses_only_predeclared_quality_gate_statuses": True,
        "selection_requires_entire_quality_chain_terminal": True,
        "selected_candidate_must_have_integrated_canonical_all220_freezes": True,
        "bundle_compiler_has_no_selection_discretion": True,
        "terminal_receipt_path": str(TERMINAL_RECEIPT),
        "handoff_path": str(SELECTED_HANDOFF),
        "benchmark_forward_launch_allowed": False,
        "mapping_gold_category_question_type_evaluator_score_read_by_selector_runtime": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["selector_payload_sha256"] = payload_sha256(value)
    return value


def _parent(root: Path) -> dict[str, Any]:
    parent = read_object(ordinary(root, PARENT_PROTOCOL, PARENT_PROTOCOL_SHA256))
    ordinary(root, PARENT_ACTIVATION, PARENT_ACTIVATION_SHA256)
    ordinary(root, PARENT_WAIT_AUDIT, PARENT_WAIT_AUDIT_SHA256)
    if (
        parent.get("role") != "v24198_candidate_bundle_preregistration"
        or parent.get("authorization", {}).get("benchmark_forward_or_full220_launch")
        is not False
        or parent.get("authorization", {}).get("candidate_selection_or_gate_evaluation")
        is not False
    ):
        raise RuntimeError("V2.41.99 parent authorization drifted")
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


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    require_pristine: bool = True,
    proc_root: Path = Path("/proc"),
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.41.99 may only freeze the canonical workspace")
    if any((root / name).exists() or (root / name).is_symlink() for name in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.41.99 unattested Python bootstrap path appeared")
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (
            SELECTOR_PROTOCOL,
            OUTPUT,
            STATE,
            ACTIVATION,
            WAIT_AUDIT,
            TERMINAL_RECEIPT,
            SELECTED_HANDOFF,
        )
    ):
        raise RuntimeError("V2.41.99 create-exclusive boundary is not pristine")
    created = int(time.time()) if created_at_unix is None else int(created_at_unix)
    parent = _parent(root)
    for row in BASELINE_PUBLICATIONS.values():
        ordinary(root, row["path"], row["sha256"])
    slots = build_slot_manifest()
    selector = _selector(created, slots)
    preterminal_snapshot = quality_preterminal_snapshot(root)
    manifest = {relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES}
    quality = {
        name: {
            key: str(value) if isinstance(value, Path) else value
            for key, value in spec.items()
        }
        for name, spec in QUALITY_SOURCES.items()
    }
    quality["entropy_root"] = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in ENTROPY_ROOT_SOURCE.items()
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": created,
        "label_blind": True,
        "selector_protocol": {
            "path": str(SELECTOR_PROTOCOL),
            "sha256": hashlib.sha256(
                (json.dumps(selector, ensure_ascii=False, indent=2) + "\n").encode()
            ).hexdigest(),
            "payload_sha256": selector["selector_payload_sha256"],
        },
        "parent": parent,
        "inheritance_contract": {
            "feature_order": list(FEATURE_ORDER),
            "slot_count": len(slots),
            "slot_manifest": slots,
            "slot_manifest_sha256": payload_sha256(slots),
            "inheritance_rule_sha256": selector["candidate_inheritance_rule_sha256"],
            "one_legal_vector_maps_to_exactly_one_slot": True,
            "scope_open_requires_markdown_go": True,
            "missing_integrated_candidate_waits_without_fallback": True,
            "multiple_match_or_merge_conflict_fails_closed": True,
            "passed_feature_may_not_be_dropped": True,
            "score_rank_last_go_or_best_observed_selection_allowed": False,
        },
        "quality_status_sources": quality,
        "capacity_input": {
            "report_path": str(CAPACITY_REPORT),
            "freeze_path": str(CAPACITY_FREEZE),
            "protocol_sha256": CAPACITY_PROTOCOL_SHA256,
            "live_replay_required_before_candidate_handoff": True,
            "capacity_no_go_is_terminal_no_handoff": True,
        },
        "publication_contract": {
            "terminal_receipt_path": str(TERMINAL_RECEIPT),
            "selected_handoff_path": str(SELECTED_HANDOFF),
            "entire_quality_chain_terminal_required": True,
            "candidate_slot_publication_and_handoff_both_required": True,
            "all_required_integrations_present_required": True,
            "four_canonical_all220_freezes_required": True,
            "capacity_model_and_workers_binding_required": True,
            "terminal_then_handoff_create_exclusive": True,
            "benchmark_forward_launch_allowed": False,
        },
        "safe_wait_boundary": {
            "all_selector_outputs_absent": all(
                not (root / path).exists() and not (root / path).is_symlink()
                for path in (TERMINAL_RECEIPT, SELECTED_HANDOFF)
            ),
            "protected_processes": protected_processes(proc_root),
            "quality_sources_preterminal": preterminal_snapshot,
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
            "preterminal_reads_status_envelopes_and_file_existence_only": True,
            "quality_numeric_values_reports_predictions_or_aggregates_read": False,
            "benchmark_question_answer_evidence_prediction_or_url_values_read": False,
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "candidate_bytes_opened_only_after_terminal_vector_and_capacity_pair": True,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "process_command_lines_or_environment_emitted": False,
        },
        "authorization": {
            "status_only_predeclared_slot_selection": True,
            "candidate_code_build_merge_or_freeze_generation": False,
            "silent_feature_drop_or_fallback": False,
            "shared_api_lease_acquire": False,
            "network_model_search_fetch_evaluator_or_api_call": False,
            "benchmark_forward_or_full220_launch": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "terminal_receipt_and_handoff_publish_after_full_validation": True,
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
    return selector, value


def validate_selector(root: Path, path: Path = SELECTOR_PROTOCOL) -> dict[str, Any]:
    raw = path if path.is_absolute() else root / path
    value = read_object(raw)
    slots = build_slot_manifest()
    expected = _selector(int(value.get("created_at_unix", -1)), slots)
    if value != expected:
        raise RuntimeError("V2.41.99 selector protocol is invalid")
    return {"path": raw, "sha256": sha256(raw), "value": value}


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    raw = path if path.is_absolute() else root / path
    value = read_object(raw)
    selector = validate_selector(root)
    manifest = value.get("control_surface", {}).get("manifest")
    frozen_processes = value.get("safe_wait_boundary", {}).get(
        "protected_processes"
    )
    expected_process_names = {
        *PARENT_PROTECTED_PROCESS_MARKERS,
        "v24198_candidate_bundle_compiler",
        *QUALITY_PROCESS_MARKERS,
    }
    preterminal = value.get("safe_wait_boundary", {}).get(
        "quality_sources_preterminal"
    )
    if (
        set(value) != PROTOCOL_FIELDS
        or
        value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or value.get("selector_protocol", {}).get("sha256") != selector["sha256"]
        or value.get("selector_protocol", {}).get("payload_sha256")
        != selector["value"]["selector_payload_sha256"]
        or value.get("parent") != _parent(root)
        or value.get("inheritance_contract", {}).get("slot_manifest")
        != build_slot_manifest()
        or value.get("inheritance_contract", {}).get("slot_count") != 24
        or value.get("safe_wait_boundary", {}).get("all_selector_outputs_absent")
        is not True
        or not isinstance(frozen_processes, dict)
        or set(frozen_processes) != expected_process_names
        or not isinstance(preterminal, dict)
        or set(preterminal) != {*QUALITY_SOURCES, "entropy_root"}
        or any(
            not isinstance(row, dict)
            or set(row)
            != {"path", "role", "status", "classification", "terminal"}
            or row.get("classification") != "waiting"
            or row.get("terminal") is not False
            for row in preterminal.values()
        )
        or value.get("inheritance_contract", {}).get(
            "score_rank_last_go_or_best_observed_selection_allowed"
        )
        is not False
        or value.get("authorization", {}).get("candidate_code_build_merge_or_freeze_generation")
        is not False
        or value.get("authorization", {}).get("shared_api_lease_acquire") is not False
        or value.get("authorization", {}).get("benchmark_forward_or_full220_launch")
        is not False
        or value.get("source_policy", {}).get(
            "quality_numeric_values_reports_predictions_or_aggregates_read"
        )
        is not False
        or value.get("source_policy", {}).get(
            "mapping_gold_category_question_type_evaluator_score_read"
        )
        is not False
        or value.get("source_policy", {}).get(
            "network_model_search_fetch_evaluator_or_api_called"
        )
        is not False
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or value.get("control_surface", {}).get("file_count") != len(CONTROL_FILES)
        or value.get("control_surface", {}).get("manifest_sha256")
        != payload_sha256(manifest)
        or value.get("decision_contract_sha256")
        != payload_sha256({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.41.99 controller protocol contract is invalid")
    for relative, digest in manifest.items():
        if sha256(ordinary(root, relative)) != digest:
            raise RuntimeError("V2.41.99 control surface drifted")
    for row in BASELINE_PUBLICATIONS.values():
        ordinary(root, row["path"], row["sha256"])
    return {"path": raw, "sha256": sha256(raw), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selector-output", default=str(SELECTOR_PROTOCOL))
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    selector_target = Path(args.selector_output)
    target = Path(args.output)
    if (
        selector_target.resolve(strict=False) != (ROOT / SELECTOR_PROTOCOL).resolve(strict=False)
        or target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False)
    ):
        raise RuntimeError("V2.41.99 output path drifted")
    selector, protocol = build_protocol()
    publish_new(selector_target, selector)
    publish_new(target, protocol)
    validate_protocol(ROOT, target)
    print(
        json.dumps(
            {
                "selector": {"path": str(selector_target), "sha256": sha256(selector_target)},
                "controller": {"path": str(target), "sha256": sha256(target)},
            }
        )
    )


if __name__ == "__main__":
    main()
