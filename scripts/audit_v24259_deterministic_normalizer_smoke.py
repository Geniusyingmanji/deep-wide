#!/usr/bin/env python3
"""Read-only audit for the V2.42.59 deterministic-normalizer smoke."""

from __future__ import annotations

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

from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    EXPECTED_LEGACY_ACTIVE_FINDING,
    LEASE_OWNER,
    LEASE_PURPOSE,
    OUTPUT,
    RESULT,
    ROLE as PROTOCOL_ROLE,
    RUNNER_MARKER,
    _matching,
    _ordinary,
    _read_object,
    _sealed,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


ROLE = "v24259_deterministic_normalizer_smoke_audit"
OUTPUT_PATH = Path(
    "results/v24259_deterministic_normalizer_smoke_preactivation_audit_v1_20260802.json"
)
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
DISALLOWED_IMPORTS = {"socket", "requests", "urllib", "httpx", "aiohttp", "subprocess"}


def _activation(root: Path, protocol: dict[str, Any]) -> dict[str, Any] | None:
    if not (root / ACTIVATION).exists() and not (root / ACTIVATION).is_symlink():
        return None
    value = _read_object(_ordinary(root, ACTIVATION))
    if (
        value.get("role") != "v24259_deterministic_normalizer_smoke_activation"
        or value.get("status") != "active"
        or value.get("protocol_sha256") != sha256(root / OUTPUT)
        or value.get("control_manifest_sha256")
        != protocol["control_surface"]["manifest_sha256"]
        or value.get(
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read"
        )
        is not False
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.59 activation drifted")
    return value


def source_audit(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    imports: set[str] = set()
    privileged: list[str] = []
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
                privileged.append(
                    f"{relative}:{node.lineno}:get:{node.args[0].value}"
                )
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
                and node.slice.value.casefold() in PRIVILEGED
            ):
                privileged.append(
                    f"{relative}:{node.lineno}:subscript:{node.slice.value}"
                )
    disallowed = sorted(imports.intersection(DISALLOWED_IMPORTS))
    if disallowed or privileged:
        raise RuntimeError(
            f"V2.42.59 source audit failed: imports={disallowed}, privileged={privileged}"
        )
    return {
        "runtime_import_roots": sorted(imports),
        "disallowed_imports": disallowed,
        "privileged_runtime_field_accesses": privileged,
        "runtime_has_direct_network_or_subprocess_capability": False,
    }


def lease_overlay(
    root: Path,
    protocol: dict[str, Any],
    *,
    proc_root: Path,
    processes: list[dict[str, Any]],
    observed_lease: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lease = (
        lease_observation(root, proc_root)
        if observed_lease is None
        else dict(observed_lease)
    )
    pids = _matching(processes, RUNNER_MARKER)
    active = lease.get("active") is True
    expected = active and lease.get("owner") == LEASE_OWNER
    findings: list[str] = []
    if active and not expected:
        findings.append("unrelated_active_lease_owner")
    if expected:
        start: dict[str, Any] | None = None
        start_path = root / EXECUTION_START
        if start_path.is_file() and not start_path.is_symlink():
            start = _read_object(start_path)
        runner = (start or {}).get("runner") or {}
        pid = runner.get("pid")
        ticks = runner.get("start_ticks")
        try:
            raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
            suffix = raw[raw.rfind(")") + 2 :].split()
            live_ticks = int(suffix[19]) if len(suffix) > 19 else None
        except (OSError, TypeError, ValueError):
            live_ticks = None
        if (
            start is None
            or start.get("role")
            != "v24259_deterministic_normalizer_smoke_execution_start"
            or start.get("protocol_sha256") != sha256(root / OUTPUT)
            or start.get("label_blind") is not True
            or start.get(
                "mapping_gold_category_question_type_evaluator_score_read"
            )
            is not False
            or start.get("api_called_before_execution_start") is not False
            or runner.get("marker") != RUNNER_MARKER
            or not _sealed(start, "execution_start_payload_sha256")
        ):
            findings.append("execution_start_identity")
        if lease.get("purpose") != LEASE_PURPOSE:
            findings.append("lease_purpose")
        if lease.get("ordinary") is not True or lease.get("record_valid") is not True:
            findings.append("lease_record")
        if lease.get("pid") != pid or pids != [pid]:
            findings.append("runner_process_identity")
        if lease.get("lock_holder_pids") != [pid]:
            findings.append("lease_lock_holder")
        if live_ticks != ticks:
            findings.append("runner_start_ticks")
    return {
        "active": active,
        "expected_v24259_owner_active": expected,
        "identity_valid": expected and not findings,
        "findings": sorted(set(findings)),
        "runner_pid": lease.get("pid") if expected else None,
        "legacy_expected_finding": EXPECTED_LEGACY_ACTIVE_FINDING,
        "legacy_finding_suppression_allowed": expected and not findings,
        "all_unrelated_legacy_findings_must_be_preserved": True,
        "owner_purpose_or_command_line_emitted": False,
    }


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
    result_present = (root / RESULT).is_file() and not (root / RESULT).is_symlink()
    summary = None
    if result_present:
        result = _read_object(root / RESULT)
        if (
            result.get("role") != "v24259_deterministic_normalizer_smoke_result"
            or result.get("protocol_id") != protocol["protocol_id"]
            or result.get("selected") != 16
            or result.get("terminal") != 16
            or result.get(
                "mapping_gold_category_question_type_evaluator_score_read"
            )
            is not False
            or result.get("official_evaluator_called") is not False
            or not _sealed(result, "result_payload_sha256")
        ):
            raise RuntimeError("V2.42.59 result drifted")
        summary = {
            key: result.get(key)
            for key in (
                "selected",
                "terminal",
                "model_generated_tables",
                "fallback_tables",
                "completion_kinds",
                "normalization_modes",
                "p95_wall_seconds",
                "mean_system_tokens",
                "mean_fetch_calls",
                "engineering_gate",
                "findings",
            )
        }
    value: dict[str, Any] = {
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
        "static_source_audit": source_audit(root, protocol),
        "result": {
            "present": result_present,
            "summary": summary,
            "prediction_question_query_url_page_or_answer_emitted": False,
        },
        "source_policy": {
            "runtime_task_candidate_or_prediction_opened_by_audit": False,
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_or_evaluator_api_called_by_audit": False,
        },
        "authorization": {
            "activation_publish": activation is None,
            "single_fresh_smoke16_launch_after_activation": activation is not None and not result_present,
            "process_signal_restart_resume_skip_or_selective_retry": False,
            "official_evaluator_call": False,
            "paired_dev64_or_full220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "parent_no_go_result_available": True,
            "normalizer_smoke_result_available": result_present,
            "benchmark_quality_improvement_observed": False,
            "paired_quality_result_available": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError("V2.42.59 audit path exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    publish(ROOT / OUTPUT_PATH, build_report())
    print(json.dumps({"path": str(OUTPUT_PATH), "sha256": sha256(ROOT / OUTPUT_PATH)}))
