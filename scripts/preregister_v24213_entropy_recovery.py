#!/usr/bin/env python3
"""Freeze a new-path recovery after the sealed V2.42.12 activation failure."""

from __future__ import annotations

import argparse
import ast
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
from scripts.preregister_v24212_entropy_component import (  # noqa: E402
    MUST_REMAIN_ABSENT,
    protected_processes,
    publish_new,
    sha256,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.publish_v24213_entropy_recovery import (  # noqa: E402
    CANDIDATE_ROOT,
    FAILED_ACTIVATION_AUDIT,
    FAILED_ACTIVATION_AUDIT_SHA256,
    OUTPUT as PUBLICATION,
)


ROLE = "v24213_selected_entropy_component_recovery_preregistration"
PROTOCOL_ID = "v24213_selected_parent_entropy_component_recovery_v1"
OUTPUT = Path("results/v24213_selected_entropy_component_recovery_preregistration_v1_20260731.json")
STATE = Path("outputs/v24213_selected_entropy_component_recovery_state_v1_20260731.json")
ACTIVATION = Path("results/v24213_selected_entropy_component_recovery_activation_v1_20260731.json")
WAIT_AUDIT = Path("results/v24213_selected_entropy_component_recovery_wait_audit_v1_20260731.json")
WATCHER_MARKER = "scripts/watch_v24213_entropy_recovery.py"
V24212_PROTOCOL = Path(
    "results/v24212_selected_entropy_component_preregistration_v1_20260731.json"
)
V24212_PROTOCOL_SHA256 = "56e22675db41fba96c991f0361b3bd4a0cfdb4917a866dee8b29e6286a695646"
V24212_ACTIVATION = Path(
    "results/v24212_selected_entropy_component_activation_v1_20260731.json"
)
V24212_ACTIVATION_SHA256 = "7ff21665b4d4f9c2f1ad64c09ed48ba81323449704e0e52ea4aa218f84f82e74"
V24212_STATE = Path(
    "outputs/v24212_selected_entropy_component_watcher_state_v1_20260731.json"
)
V24212_CANDIDATE = ROOT / "outputs/v24212_selected_entropy_candidate_v1_20260731"
V24212_PUBLICATION = Path(
    "results/v24212_selected_entropy_component_publication_v1_20260731.json"
)
SEARCH_PROTOCOL = Path(
    "results/v24210_selected_search_component_preregistration_v1_20260731.json"
)
SEARCH_PROTOCOL_SHA256 = "dc5a64d036aac52e9ec76fdc952645678aff9408e18887f425686ba2660c6f23"
SEARCH_STATE = Path(
    "outputs/v24210_selected_search_component_watcher_state_v1_20260731.json"
)
GATE2A_PROTOCOL = Path(
    "results/v24193_replicate_aware_gate2a_consumer_preregistration_v1_20260731.json"
)
GATE2A_PROTOCOL_SHA256 = "9b2fcf677bbb4f7cdb361d689f2634b23326d1cb640416eee920fb2b131b6031"
GATE2A_STATE = Path(
    "outputs/v24193_replicate_aware_gate2a_consumer_state_v1_20260731.json"
)
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
    "scripts/publish_v24213_entropy_recovery.py",
    "scripts/preregister_v24213_entropy_recovery.py",
    "scripts/watch_v24213_entropy_recovery.py",
    "scripts/activate_v24213_entropy_recovery.py",
    "scripts/audit_v24213_entropy_recovery_wait.py",
    "tests/test_v24121_continuation.py",
    "tests/test_v24122_execution.py",
    "tests/test_v24211_entropy_controller.py",
    "tests/test_v24211_entropy_runtime.py",
    "tests/test_v24212_entropy_binding.py",
    "tests/test_publish_v24212_entropy_component.py",
    "tests/test_publish_v24213_entropy_recovery.py",
    "tests/test_preregister_v24213_entropy_recovery.py",
    "tests/test_watch_v24213_entropy_recovery.py",
    "tests/test_activate_v24213_entropy_recovery.py",
    "tests/test_audit_v24213_entropy_recovery_wait.py",
)
DECISION_FIELDS = (
    "protocol_id",
    "recovery_parent",
    "parent_contract",
    "publication_contract",
    "execution",
    "source_policy",
    "authorization",
    "safe_wait_boundary",
    "control_surface",
)


def _failed_watcher_pids(proc_root: Path = Path("/proc")) -> list[int]:
    marker = "scripts/watch_v24212_entropy_component.py"
    result: list[int] = []
    for row in process_snapshot(proc_root):
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (
            script == marker or script.endswith("/" + marker)
        ):
            result.append(int(row["pid"]))
    return sorted(result)


def _read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.13 expected an ordinary JSON file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.13 expected one JSON object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _ordinary(root: Path, relative: str | Path, digest: str | None = None) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.13 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
        or digest is not None
        and sha256(path) != digest
    ):
        raise RuntimeError(f"V2.42.13 frozen input drifted: {relative}")
    return path


def _recovery_parent(root: Path) -> dict[str, Any]:
    audit = _read_object(
        _ordinary(root, FAILED_ACTIVATION_AUDIT, FAILED_ACTIVATION_AUDIT_SHA256)
    )
    activation = _read_object(
        _ordinary(root, V24212_ACTIVATION, V24212_ACTIVATION_SHA256)
    )
    _ordinary(root, V24212_PROTOCOL, V24212_PROTOCOL_SHA256)
    if (
        audit.get("role")
        != "v24212_selected_entropy_component_failed_activation_audit"
        or audit.get("failure", {}).get("classification")
        != "successor_envelope_field_name_mismatch_fail_closed"
        or audit.get("disposition", {}).get("same_protocol_restart_or_retry_allowed")
        is not False
        or audit.get("disposition", {}).get("new_versioned_recovery_protocol_required")
        is not True
        or audit.get("disposition", {}).get("shared_api_lease_acquired") is not False
        or audit.get("disposition", {}).get(
            "benchmark_forward_or_full220_launch_allowed"
        )
        is not False
        or not _sealed(audit, "audit_payload_sha256")
        or activation.get("role")
        != "v24212_selected_entropy_component_activation"
        or not _sealed(activation, "activation_payload_sha256")
        or (root / V24212_PUBLICATION).exists()
        or (root / V24212_PUBLICATION).is_symlink()
        or V24212_CANDIDATE.exists()
        or V24212_CANDIDATE.is_symlink()
    ):
        raise RuntimeError("V2.42.13 recovery parent drifted")
    return {
        "failed_activation_audit": {
            "path": str(FAILED_ACTIVATION_AUDIT),
            "sha256": FAILED_ACTIVATION_AUDIT_SHA256,
            "audit_payload_sha256": audit["audit_payload_sha256"],
        },
        "failed_activation": {
            "path": str(V24212_ACTIVATION),
            "sha256": V24212_ACTIVATION_SHA256,
        },
        "failed_protocol": {
            "path": str(V24212_PROTOCOL),
            "sha256": V24212_PROTOCOL_SHA256,
        },
    }


def _static_capability_audit(root: Path) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for relative in CONTROL_FILES:
        source = _ordinary(root, relative).read_text(encoding="utf-8")
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
            if relative == "scripts/publish_v24212_entropy_component.py"
            else []
        )
        if (
            {"httpx", "requests", "socket"}.intersection(imports)
            or environment_read
            or dynamic_calls
            or process_calls != allowed_process
        ):
            raise RuntimeError("V2.42.13 forbidden capability appeared")
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
    summary = build_entropy_feasibility_manifest()["summary"]
    return {
        "parent_contract": {
            "search_protocol": {
                "path": str(SEARCH_PROTOCOL),
                "sha256": SEARCH_PROTOCOL_SHA256,
            },
            "search_state_path": str(SEARCH_STATE),
            "gate2a_protocol": {
                "path": str(GATE2A_PROTOCOL),
                "sha256": GATE2A_PROTOCOL_SHA256,
            },
            "gate2a_state_path": str(GATE2A_STATE),
            "before_both_terminal_safe_state_envelopes_only": True,
            "selected_parent_model_and_report_read_only_after_both_terminal": True,
        },
        "publication_contract": {
            "summary": summary,
            "eighteen_entropy_decisions_and_fourteen_parent_graphs_preserved": True,
            "only_recovery_delta": (
                "validate_v24210_frozen_false_field_under_its_exact_registered_name"
            ),
            "upstream_state_seal_role_protocol_terminal_and_all_false_authorizations_still_required": True,
            "v24212_activation_state_candidate_or_publication_reuse_forbidden": True,
            "real_state_transition_model_and_parent_hash_contract_unchanged": True,
            "projection_only_action_arm_selected_instantiated_or_called": False,
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
            "after_activation_only_safe_state_envelopes_opened": True,
            "after_both_terminal_only_selected_parent_model_and_report_opened": True,
            "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted": False,
            "mapping_gold_category_question_type_evaluator_score_or_reward_read_for_forward_routing": False,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
        },
        "authorization": {
            "versioned_recovery_watcher_active_after_activation": True,
            "selected_entropy_component_publication_after_both_terminal": True,
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
        raise RuntimeError("V2.42.13 may only freeze the canonical workspace")
    if any(
        (root / name).exists() or (root / name).is_symlink()
        for name in MUST_REMAIN_ABSENT
    ):
        raise RuntimeError("V2.42.13 unattested Python bootstrap path appeared")
    future = (OUTPUT, STATE, ACTIVATION, WAIT_AUDIT, PUBLICATION)
    future_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in future
    ) and not CANDIDATE_ROOT.exists() and not CANDIDATE_ROOT.is_symlink()
    if require_pristine and not future_absent:
        raise RuntimeError("V2.42.13 create-exclusive boundary is not pristine")
    if _failed_watcher_pids(proc_root):
        raise RuntimeError("V2.42.13 failed V2.42.12 watcher is still present")
    control = {
        relative: sha256(_ordinary(root, relative)) for relative in CONTROL_FILES
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
        "recovery_parent": _recovery_parent(root),
        **fixed,
        "safe_wait_boundary": {
            "future_recovery_outputs_and_candidate_absent": future_absent,
            "failed_v24212_watcher_absent": not _failed_watcher_pids(proc_root),
            "failed_v24212_activation_and_state_preserved": True,
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
        or value.get("recovery_parent") != _recovery_parent(root)
        or any(value.get(key) != expected for key, expected in _fixed().items())
        or value.get("safe_wait_boundary", {}).get(
            "future_recovery_outputs_and_candidate_absent"
        )
        is not True
        or value.get("safe_wait_boundary", {}).get("failed_v24212_watcher_absent")
        is not True
        or value.get("safe_wait_boundary", {}).get(
            "failed_v24212_activation_and_state_preserved"
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
        raise RuntimeError("V2.42.13 protocol contract is invalid")
    for relative, digest in manifest.items():
        if sha256(_ordinary(root, relative)) != digest:
            raise RuntimeError("V2.42.13 control surface drifted")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.13 protocol output path drifted")
    publish_new(target, build_protocol())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
