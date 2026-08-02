#!/usr/bin/env python3
"""Audit V2.42.57 smoke16 and its append-only lease compatibility overlay."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24257_score_first_smoke import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    EXPECTED_LEGACY_ACTIVE_FINDING,
    LEASE_OWNER,
    LEASE_PURPOSE,
    OUTPUT,
    RESULT,
    ROLE as PROTOCOL_ROLE,
    RUNNER_MARKER,
    STATE,
    WATCHER_MARKER,
    _ordinary,
    _read_object,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    sha256,
)


ROLE = "v24257_score_first_smoke_audit"
OUTPUT_PATH = Path("results/v24257_score_first_smoke_audit_v1_20260802.json")
PRIVILEGED = {
    "category",
    "question_type",
    "task_category",
    "split",
    "ground_truth",
    "gold",
    "answer_key",
    "mapping",
    "evaluator",
    "score",
    "reward",
}
DISALLOWED_IMPORTS = {
    "socket",
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
    "subprocess",
}


def _activation(root: Path, protocol: dict[str, Any]) -> dict[str, Any] | None:
    path = root / ACTIVATION
    if not path.exists() and not path.is_symlink():
        return None
    value = _read_object(_ordinary(root, ACTIVATION))
    unsigned = dict(value)
    seal = unsigned.pop("activation_payload_sha256", None)
    if (
        value.get("role") != "v24257_score_first_smoke_activation"
        or value.get("status") != "active"
        or value.get("protocol_sha256") != sha256(root / OUTPUT)
        or value.get("control_manifest_sha256")
        != protocol["control_surface"]["manifest_sha256"]
        or value.get("benchmark_question_prediction_mapping_gold_score_read")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.57 activation drifted")
    return value


def _execution_start(root: Path, protocol: dict[str, Any]) -> dict[str, Any] | None:
    path = root / EXECUTION_START
    if not path.exists() and not path.is_symlink():
        return None
    value = _read_object(_ordinary(root, EXECUTION_START))
    unsigned = dict(value)
    seal = unsigned.pop("execution_start_payload_sha256", None)
    runner = value.get("runner") or {}
    if (
        value.get("role") != "v24257_score_first_smoke_execution_start"
        or value.get("protocol_sha256") != sha256(root / OUTPUT)
        or value.get("label_blind") is not True
        or value.get("mapping_gold_evaluator_or_score_read") is not False
        or value.get("api_called_before_execution_start") is not False
        or runner.get("marker") != RUNNER_MARKER
        or not isinstance(runner.get("pid"), int)
        or not isinstance(runner.get("start_ticks"), int)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.57 execution start drifted")
    return value


def _matching_processes(rows: list[dict[str, Any]], marker: str) -> list[int]:
    pids: list[int] = []
    for row in rows:
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script and (script == marker or script.endswith("/" + marker)):
            pids.append(int(row["pid"]))
    return sorted(pids)


def _start_ticks(pid: int, proc_root: Path) -> int:
    raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    suffix = raw[raw.rfind(")") + 2 :].split()
    if len(suffix) <= 19:
        raise RuntimeError("V2.42.57 process stat is truncated")
    return int(suffix[19])


def lease_overlay(
    root: Path,
    protocol: dict[str, Any],
    *,
    proc_root: Path,
    processes: list[dict[str, Any]],
    observed_lease: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lease = lease_observation(root, proc_root) if observed_lease is None else dict(observed_lease)
    execution = _execution_start(root, protocol)
    pids = _matching_processes(processes, RUNNER_MARKER)
    findings: list[str] = []
    active = lease.get("active") is True
    expected_active = active and lease.get("owner") == LEASE_OWNER
    if active and not expected_active:
        findings.append("unrelated_active_lease_owner")
    if expected_active:
        runner = (execution or {}).get("runner") or {}
        pid = runner.get("pid")
        ticks = runner.get("start_ticks")
        try:
            live_ticks = _start_ticks(int(pid), proc_root)
        except (OSError, RuntimeError, TypeError, ValueError):
            live_ticks = None
        if execution is None:
            findings.append("execution_start_absent")
        if lease.get("purpose") != LEASE_PURPOSE:
            findings.append("lease_purpose")
        if lease.get("ordinary") is not True or lease.get("record_valid") is not True:
            findings.append("lease_record")
        if lease.get("pid") != pid:
            findings.append("lease_pid")
        if lease.get("lock_holder_pids") != [pid]:
            findings.append("lease_lock_holder")
        if pids != [pid]:
            findings.append("runner_process_identity")
        if live_ticks != ticks:
            findings.append("runner_start_ticks")
    elif active:
        findings.append("owner_not_registered_by_v24257")
    return {
        "active": active,
        "expected_v24257_owner_active": expected_active,
        "identity_valid": expected_active and not findings,
        "findings": sorted(set(findings)),
        "runner_pid": (execution or {}).get("runner", {}).get("pid"),
        "legacy_expected_finding": EXPECTED_LEGACY_ACTIVE_FINDING,
        "legacy_finding_suppression_allowed": expected_active and not findings,
        "all_unrelated_legacy_findings_must_be_preserved": True,
        "owner_purpose_or_command_line_emitted": False,
    }


def _static_source_audit(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    imports: set[str] = set()
    privileged_accesses: list[str] = []
    for relative in protocol["control_surface"]["manifest"]:
        if not str(relative).startswith("src/"):
            continue
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value.casefold() in PRIVILEGED
            ):
                privileged_accesses.append(
                    f"{relative}:{node.lineno}:get:{node.args[0].value}"
                )
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
                and node.slice.value.casefold() in PRIVILEGED
            ):
                privileged_accesses.append(
                    f"{relative}:{node.lineno}:subscript:{node.slice.value}"
                )
    disallowed = sorted(imports.intersection(DISALLOWED_IMPORTS))
    if disallowed or privileged_accesses:
        raise RuntimeError(
            f"V2.42.57 runtime capability audit failed: imports={disallowed}, "
            f"privileged={privileged_accesses}"
        )
    return {
        "runtime_import_roots": sorted(imports),
        "disallowed_imports": disallowed,
        "privileged_runtime_field_accesses": privileged_accesses,
        "runtime_has_direct_network_or_subprocess_capability": False,
    }


def publish_audit(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT_PATH).resolve(strict=False)
    if target != expected or not target.is_relative_to((ROOT / "results").resolve()):
        raise RuntimeError("V2.42.57 audit output is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        parent = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def build_report(
    root: Path = ROOT,
    *,
    now: int | None = None,
    proc_root: Path = Path("/proc"),
    processes: list[dict[str, Any]] | None = None,
    observed_lease: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    activation = _activation(root, protocol)
    rows = process_snapshot(proc_root) if processes is None else processes
    overlay = lease_overlay(
        root,
        protocol,
        proc_root=proc_root,
        processes=rows,
        observed_lease=observed_lease,
    )
    result_path = root / RESULT
    result_present = result_path.is_file() and not result_path.is_symlink()
    result_summary: dict[str, Any] | None = None
    if result_present:
        result = _read_object(result_path)
        unsigned = dict(result)
        seal = unsigned.pop("result_payload_sha256", None)
        if (
            result.get("role") != "v24257_score_first_smoke_result"
            or result.get("protocol_id") != protocol["protocol_id"]
            or result.get("selected") != 16
            or result.get("terminal") != 16
            or result.get("mapping_gold_category_question_type_evaluator_score_read")
            is not False
            or result.get("official_evaluator_called") is not False
            or seal != payload_sha256(unsigned)
        ):
            raise RuntimeError("V2.42.57 smoke result drifted")
        result_summary = {
            key: result.get(key)
            for key in (
                "selected",
                "terminal",
                "model_generated_tables",
                "fallback_tables",
                "p95_wall_seconds",
                "mean_system_tokens",
                "mean_fetch_calls",
                "engineering_gate",
                "findings",
            )
        }
    report: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "protocol": {
            "path": str(OUTPUT),
            "sha256": sha256(root / OUTPUT),
            "role": PROTOCOL_ROLE,
            "decision_contract_sha256": protocol["decision_contract_sha256"],
            "control_manifest_sha256": protocol["control_surface"]["manifest_sha256"],
        },
        "activation": {
            "present": activation is not None,
            "valid": activation is not None,
            "contents_emitted": False,
        },
        "lease_compatibility_overlay": overlay,
        "static_source_audit": _static_source_audit(root, protocol),
        "result": {
            "present": result_present,
            "summary": result_summary,
            "prediction_question_query_url_page_or_answer_emitted": False,
        },
        "source_policy": {
            "runtime_task_or_prediction_opened_by_audit": False,
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_or_evaluator_api_called_by_audit": False,
        },
        "authorization": {
            "activation_publish": activation is None,
            "single_smoke16_launch_after_activation_and_lease_overlay_validation": (
                activation is not None and not result_present
            ),
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "official_evaluator_call": False,
            "paired_dev64_or_full220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "baseline_full220_score_available": True,
            "score_first_smoke_result_available": result_present,
            "benchmark_improvement_observed": False,
            "paired_quality_result_available": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    report["audit_payload_sha256"] = payload_sha256(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args()
    output = Path(args.output)
    output = output if output.is_absolute() else ROOT / output
    value = build_report()
    publish_audit(output, value)
    print(json.dumps({"path": str(output), "sha256": sha256(output)}))


if __name__ == "__main__":
    main()
