#!/usr/bin/env python3
"""Freeze V2.42.10 before its selected parents or quality gate terminate."""

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
from deepwide_agent.v24210_search_publisher import (  # noqa: E402
    build_search_publication_manifest,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.preregister_v24207_scope_alias_component import (  # noqa: E402
    PROTECTED_PROCESS_MARKERS as V24207_PROTECTED_PROCESS_MARKERS,
)
from scripts.publish_v24210_search_component import (  # noqa: E402
    CANDIDATE_ROOT,
    OUTPUT as PUBLICATION,
    SEARCH_GATE,
    SEARCH_STATE,
    V24208,
    V24208_SHA256,
)


ROLE = "v24210_selected_search_component_preregistration"
PROTOCOL_ID = "v24210_selected_parent_search_component_publisher_v1"
OUTPUT = Path("results/v24210_selected_search_component_preregistration_v1_20260731.json")
STATE = Path("outputs/v24210_selected_search_component_watcher_state_v1_20260731.json")
ACTIVATION = Path("results/v24210_selected_search_component_activation_v1_20260731.json")
WAIT_AUDIT = Path("results/v24210_selected_search_component_wait_activation_audit_v1_20260731.json")
PARENT_PROTOCOL = Path(
    "results/v24207_selected_scope_alias_component_preregistration_v1_20260731.json"
)
PARENT_PROTOCOL_SHA256 = "2a2800caf6056526bc432baffcadea913de593ba8bed085b5174bffc7ec1ebe0"
PARENT_ACTIVATION = Path(
    "results/v24207_selected_scope_alias_component_activation_v1_20260731.json"
)
PARENT_ACTIVATION_SHA256 = "bca63bc2371f498834dc443f75694b9efe6c57f9ad6808943560dc9761a61796"
PARENT_WAIT_AUDIT = Path(
    "results/v24207_selected_scope_alias_component_wait_activation_audit_v1_20260731.json"
)
PARENT_WAIT_AUDIT_SHA256 = "25c9d7e443efe05a992df5d0acbf69fac5a2ff6c7e90422eac64ebb7d5169776"
PARENT_STATE = Path(
    "outputs/v24207_selected_scope_alias_component_watcher_state_v1_20260731.json"
)
MARKDOWN_PUBLICATION = Path(
    "results/v24206_selected_markdown_component_publication_v1_20260731.json"
)
SCOPE_PUBLICATION = Path(
    "results/v24207_selected_scope_alias_component_publication_v1_20260731.json"
)
SELECTED_WORK_ORDER = Path(
    "results/v24204_selected_postdecision_work_order_v1_20260731.json"
)
WATCHER_MARKER = "scripts/watch_v24210_search_component.py"
MUST_REMAIN_ABSENT = ("scripts/__init__.py", "sitecustomize.py", "usercustomize.py")
CONTROL_FILES = (
    "src/deepwide_agent/v24210_search_publisher.py",
    "scripts/publish_v24210_search_component.py",
    "scripts/preregister_v24210_search_component.py",
    "scripts/watch_v24210_search_component.py",
    "scripts/activate_v24210_search_component.py",
    "scripts/audit_v24210_search_component_wait_activation.py",
    "tests/test_v24210_search_publisher.py",
    "tests/test_publish_v24210_search_component.py",
    "tests/test_preregister_v24210_search_component.py",
    "tests/test_watch_v24210_search_component.py",
    "tests/test_activate_v24210_search_component.py",
    "tests/test_audit_v24210_search_component_wait_activation.py",
)
PROTECTED_PROCESS_MARKERS = {
    **V24207_PROTECTED_PROCESS_MARKERS,
    "v24207_scope_alias_watcher": "scripts/watch_v24207_scope_alias_component.py",
}
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
FORBIDDEN_CAPABILITY_IMPORTS = frozenset(
    {"httpx", "multiprocessing", "requests", "socket"}
)
FORBIDDEN_URLLIB_IMPORTS = frozenset(
    {"urllib", "urllib.error", "urllib.request", "urllib.response", "urllib.robotparser"}
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ordinary(root: Path, relative: str | Path, digest: str | None = None) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.10 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
        or digest is not None
        and sha256(path) != digest
    ):
        raise RuntimeError(f"V2.42.10 expected a frozen ordinary file: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.10 expected an ordinary JSON file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.10 expected one JSON object")
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
        raise RuntimeError("V2.42.10 process stat is truncated")
    return int(suffix[19])


def protected_processes(proc_root: Path = Path("/proc")) -> dict[str, Any]:
    rows = process_snapshot(proc_root)
    result: dict[str, Any] = {}
    for name, marker in PROTECTED_PROCESS_MARKERS.items():
        matches = []
        for row in rows:
            argv = [str(value) for value in row.get("argv") or []]
            script = actual_python_script(argv)
            if script is not None and (script == marker or script.endswith("/" + marker)):
                matches.append({"pid": int(row["pid"]), "argv": argv})
        isolated = name not in {"r1_launcher", "r1_forward"}
        if len(matches) != 1 or (
            isolated and not all(flag in matches[0]["argv"] for flag in ("-I", "-B"))
        ):
            raise RuntimeError(f"V2.42.10 process identity is invalid: {marker}")
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
    feasibility = read_object(ordinary(root, V24208, V24208_SHA256))
    if (
        protocol.get("role") != "v24207_selected_scope_alias_component_preregistration"
        or protocol.get("protocol_id")
        != "v24207_selected_branch_scope_namespace_alias_publisher_v1"
        or protocol.get("authorization", {}).get("search_yield_implementation_or_publication")
        is not False
        or protocol.get("authorization", {}).get("benchmark_forward_or_full220_launch")
        is not False
        or activation.get("role") != "v24207_selected_scope_alias_component_activation"
        or activation.get("benchmark_forward_or_full220_launch_allowed") is not False
        or not _sealed(activation, "activation_payload_sha256")
        or wait.get("role")
        != "v24207_selected_scope_alias_component_wait_activation_audit"
        or not _sealed(wait, "audit_payload_sha256")
        or feasibility.get("role") != "v24208_search_rebase_feasibility_audit"
        or feasibility.get("label_blind") is not True
        or feasibility.get("candidate_tree_or_package_materialized") is not False
        or feasibility.get("component_publication_or_implementation_authority_granted")
        is not False
        or feasibility.get("benchmark_forward_or_full220_launch_allowed") is not False
        or not _sealed(feasibility, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.10 frozen parent contract drifted")
    return {
        "v24207_protocol": {"path": str(PARENT_PROTOCOL), "sha256": PARENT_PROTOCOL_SHA256},
        "v24207_activation": {"path": str(PARENT_ACTIVATION), "sha256": PARENT_ACTIVATION_SHA256},
        "v24207_wait_audit": {"path": str(PARENT_WAIT_AUDIT), "sha256": PARENT_WAIT_AUDIT_SHA256},
        "v24208_feasibility": {"path": str(V24208), "sha256": V24208_SHA256},
    }


def _static_capability_audit(root: Path) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for relative in CONTROL_FILES:
        if not relative.endswith(".py"):
            continue
        source = ordinary(root, relative).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative)
        imported: set[str] = set()
        environment_read = False
        dynamic_calls: set[str] = set()
        process_calls: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {
                    "compile",
                    "eval",
                    "exec",
                }:
                    dynamic_calls.add(node.func.id)
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in {"os", "subprocess"}
                    and node.func.attr
                    in {
                        "Popen",
                        "call",
                        "execv",
                        "execve",
                        "popen",
                        "run",
                        "spawnl",
                        "spawnlp",
                        "spawnv",
                        "spawnvp",
                        "system",
                    }
                ):
                    process_calls.append(f"{node.func.value.id}.{node.func.attr}")
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "os"
                and node.attr == "environ"
            ):
                environment_read = True
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and node.func.attr == "getenv"
            ):
                environment_read = True
        allowed_process_calls = (
            ["subprocess.run"]
            if relative == "scripts/publish_v24210_search_component.py"
            else []
        )
        if (
            {name.split(".")[0] for name in imported} & FORBIDDEN_CAPABILITY_IMPORTS
            or imported & FORBIDDEN_URLLIB_IMPORTS
            or environment_read
            or dynamic_calls
            or process_calls != allowed_process_calls
        ):
            raise RuntimeError("V2.42.10 forbidden capability appeared")
        if relative == "scripts/publish_v24210_search_component.py" and not all(
            token in source
            for token in (
                'str(candidate / ".venv-eval/bin/python")',
                '"-I", "-B", "-c", runner',
                "env=environment",
                "timeout=600",
                "check=False",
            )
        ):
            raise RuntimeError("V2.42.10 isolated regression subprocess drifted")
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
    manifest = build_search_publication_manifest()
    return {
        "parent_contract": {
            "scope_state_path": str(PARENT_STATE),
            "selected_work_order_path": str(SELECTED_WORK_ORDER),
            "markdown_publication_path": str(MARKDOWN_PUBLICATION),
            "scope_publication_path": str(SCOPE_PUBLICATION),
            "before_parent_terminal_safe_state_envelope_only": True,
            "selected_parent_content_read_only_after_scope_terminal": True,
            "numeric_metrics_reports_predictions_or_aggregates_read": False,
        },
        "publication_contract": {
            "manifest_payload_sha256": manifest["manifest_payload_sha256"],
            "summary": manifest["summary"],
            "selection_frozen_before_parent_or_quality_outcome": True,
            "owned_component": "search_yield_shared_query",
            "nine_semantic_parent_branches_covered": True,
            "seven_unique_parent_byte_graphs_covered": True,
            "p12_scope_parent_is_historical_schema70": True,
            "p12_schema70_search_target_is_schema86": True,
            "mainline_scope_is_zero_byte_markdown_alias": True,
            "same_query_budget_required": True,
            "unowned_entropy_remains_blocker": True,
            "joint_package_or_package_gate_built": False,
        },
        "quality_contract": {
            "state_path": str(SEARCH_STATE),
            "gate_path": str(SEARCH_GATE),
            "terminal_statuses": [
                "complete_search_yield_go",
                "complete_search_yield_no_go",
                "terminal_incomplete_attempt_no_rerun",
            ],
            "go_materializes_exactly_one_selected_parent_rebase": True,
            "no_go_retires_component_without_threshold_change_or_rerun": True,
            "incomplete_attempt_retires_component_without_rerun": True,
            "search_absent_publishes_content_free_no_op": True,
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
            "before_activation_parent_or_quality_state_opened": False,
            "after_activation_only_safe_state_envelopes_opened": True,
            "after_all_terminal_only_selected_parent_and_gate_opened": True,
            "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted": False,
            "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
        },
        "authorization": {
            "selected_search_publisher_active_after_activation": True,
            "component_publication_after_validated_parent_and_quality_terminal": True,
            "selected_parent_search_candidate_materialization_on_go": True,
            "content_free_noop_or_retirement_publication": True,
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
        raise RuntimeError("V2.42.10 may only freeze the canonical workspace")
    if any((root / name).exists() or (root / name).is_symlink() for name in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.42.10 unattested Python bootstrap path appeared")
    future = (OUTPUT, STATE, ACTIVATION, WAIT_AUDIT, PUBLICATION)
    future_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in future
    ) and not CANDIDATE_ROOT.exists() and not CANDIDATE_ROOT.is_symlink()
    if require_pristine and not future_absent:
        raise RuntimeError("V2.42.10 create-exclusive boundary is not pristine")
    parent_outputs_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in (SELECTED_WORK_ORDER, MARKDOWN_PUBLICATION, SCOPE_PUBLICATION)
    )
    quality_terminal_absent = not (root / SEARCH_GATE).exists() and not (
        root / SEARCH_GATE
    ).is_symlink()
    if require_pristine and (not parent_outputs_absent or not quality_terminal_absent):
        raise RuntimeError("V2.42.10 terminal parent appeared before freeze")
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
            "selected_parent_outputs_absent": parent_outputs_absent,
            "search_quality_gate_absent": quality_terminal_absent,
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
    if (
        target.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or target.is_symlink()
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or value.get("frozen_parents") != _parents(root)
        or any(value.get(key) != expected for key, expected in _fixed().items())
        or value.get("safe_wait_boundary", {}).get("future_outputs_and_candidate_absent")
        is not True
        or value.get("safe_wait_boundary", {}).get("selected_parent_outputs_absent")
        is not True
        or value.get("safe_wait_boundary", {}).get("search_quality_gate_absent")
        is not True
        or not isinstance(value.get("safe_wait_boundary", {}).get("protected_processes"), dict)
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or value.get("control_surface", {}).get("file_count") != len(CONTROL_FILES)
        or value.get("control_surface", {}).get("manifest_sha256") != payload_sha256(manifest)
        or value.get("control_surface", {}).get("must_remain_absent")
        != list(MUST_REMAIN_ABSENT)
        or value.get("control_surface", {}).get("static_capability_audit")
        != _static_capability_audit(root)
        or value.get("decision_contract_sha256")
        != payload_sha256({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.42.10 protocol contract is invalid")
    for relative, digest in manifest.items():
        if sha256(ordinary(root, relative)) != digest:
            raise RuntimeError("V2.42.10 control surface drifted")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.10 protocol output path drifted")
    publish_new(target, build_protocol())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
