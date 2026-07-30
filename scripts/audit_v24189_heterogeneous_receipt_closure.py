#!/usr/bin/env python3
"""Audit heterogeneous handoff receipts and V2.41.87 parent controls."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v24188_parent_closure import replay_manifest  # noqa: E402
from scripts.preregister_v24189_heterogeneous_receipt_closure import (  # noqa: E402
    DEFAULT_PROTOCOL,
    DEFAULT_RESULT,
    ordinary,
    payload_sha,
    publish_new,
    read_object,
    sha256,
    validate_protocol,
)


ROLE = "v24189_heterogeneous_receipt_closure_audit"
V24187_PROTOCOL = Path(
    "results/v24187_phase_liveness_preregistration_v1_20260730.json"
)
V24187_PROTOCOL_SHA256 = (
    "873f42369f6f5ac7d1b619510257f8cc7c932140b734dd14d23c4a5c6e45d34c"
)
V24187_ACTIVATION = Path(
    "results/v24187_phase_liveness_activation_audit_v1_20260730.json"
)
V24187_ACTIVATION_SHA256 = (
    "b57bdc1fbcce3911111f9c571c77dd37f1d1ecbf1030b1658638c0062cbaa4b2"
)
ACTIVATIONS = {
    "v24183": (
        Path("results/v24183_search_yield_launcher_activation_audit_v1_20260730.json"),
        "5e27fc01b5dc8cdc5a8312973f570ac4f5add6deab15f79b17252d704dd99295",
        "v24183_search_yield_launcher_activation_audit",
        "activation_content_addressed",
    ),
    "v24185": (
        Path("results/v24185_markdown_priority_activation_audit_v1_20260730.json"),
        "0ae94c7fac5f2fb4ba0ae3dea5a5385b560155f58da8b830f202f1e3d082c6af",
        "v24185_markdown_priority_activation_audit",
        "standalone_payload_seal",
    ),
    "v24186": (
        Path("results/v24186_owic_after_quality_chain_activation_audit_v1_20260730.json"),
        "3726a4209761d24ad81eb2967c9ded80613257000bfd01c713a5b347eac8029b",
        "v24186_owic_after_quality_chain_activation_audit",
        "standalone_payload_seal",
    ),
}
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
CREDENTIAL_LIKE = re.compile(
    r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def payload_seal(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha(unsigned)


def _activation(
    root: Path,
    name: str,
    path: Path,
    digest: str,
    role: str,
    receipt_contract: str,
) -> dict[str, Any]:
    value = read_object(ordinary(root, path, digest))
    receipt = value.get("handoff_receipt") or {}
    receipt_path = Path(str(receipt.get("path", "")))
    receipt_digest = receipt.get("sha256")
    if (
        value.get("role") != role
        or value.get("activation_valid") is not True
        or not payload_seal(value, "audit_payload_sha256")
        or not isinstance(receipt_digest, str)
    ):
        raise RuntimeError(f"V2.41.89 activation drifted: {name}")
    receipt_value = read_object(ordinary(root, receipt_path, receipt_digest))
    if receipt_contract == "standalone_payload_seal":
        if not payload_seal(receipt_value, "receipt_payload_sha256"):
            raise RuntimeError(f"V2.41.89 receipt payload seal drifted: {name}")
        receipt_validation = "standalone_payload_and_activation_content_address"
    elif receipt_contract == "activation_content_addressed":
        if "receipt_payload_sha256" in receipt_value:
            raise RuntimeError("V2.41.89 v24183 receipt format unexpectedly changed")
        if (
            receipt.get("old_pid") != receipt_value.get("old_launcher", {}).get("pid")
            or receipt.get("old_start_ticks")
            != receipt_value.get("old_launcher", {}).get("start_ticks")
            or receipt.get("signal_authorized_only_for_old_pid") is not True
            or receipt_value.get("signal_authorized_only_for_old_pid") is not True
            or receipt_value.get("network_api_or_lease_authorized_by_handoff")
            is not False
            or receipt_value.get(
                "mapping_gold_category_question_type_evaluator_score_prediction_or_outcome_read"
            )
            is not False
        ):
            raise RuntimeError("V2.41.89 v24183 receipt activation binding drifted")
        receipt_validation = "sealed_activation_exact_sha_and_identity_binding"
    else:
        raise RuntimeError("V2.41.89 unknown receipt contract")

    records = 0
    control = value.get("control_surface") or {}
    for record in control.values():
        if not isinstance(record, dict):
            continue
        relative = record.get("path")
        expected = record.get("sha256")
        if isinstance(relative, str) and isinstance(expected, str):
            ordinary(root, relative, expected)
            records += 1
    protocol = value.get("protocol") or {}
    if isinstance(protocol.get("path"), str) and isinstance(
        protocol.get("sha256"), str
    ):
        ordinary(root, protocol["path"], protocol["sha256"])
        records += 1
    return {
        "path": str(path),
        "sha256": digest,
        "role": role,
        "activation_payload_seal_valid": True,
        "receipt_contract": receipt_contract,
        "receipt_validation": receipt_validation,
        "receipt_content_address_valid": True,
        "frozen_control_records_live_validated": records,
        "contents_emitted": False,
    }


def build_audit(
    root: Path = ROOT,
    *,
    protocol_path: Path = DEFAULT_PROTOCOL,
    created_at_unix: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    verified = validate_protocol(root, protocol_path)
    v87 = read_object(ordinary(root, V24187_PROTOCOL, V24187_PROTOCOL_SHA256))
    v87_activation = read_object(
        ordinary(root, V24187_ACTIVATION, V24187_ACTIVATION_SHA256)
    )
    if (
        not payload_seal(v87_activation, "audit_payload_sha256")
        or v87_activation.get("activation_valid") is not True
    ):
        raise RuntimeError("V2.41.89 V2.41.87 activation drifted")
    own_manifest = replay_manifest(root, V24187_PROTOCOL, v87)
    parents: dict[str, Any] = {}
    entries = 0
    artifact_only = 0
    for relative, record in v87.get("parents", {}).items():
        if not isinstance(record, dict):
            raise RuntimeError("V2.41.89 parent record drifted")
        parent = read_object(ordinary(root, relative, str(record.get("sha256", ""))))
        if parent.get("role") != record.get("role"):
            raise RuntimeError("V2.41.89 parent role drifted")
        report = replay_manifest(root, Path(relative), parent)
        parents[relative] = report
        entries += int(report["manifest_entry_count"])
        artifact_only += report["manifest_kind"] == "artifact_sha_only"
    activations = {
        name: _activation(root, name, *record)
        for name, record in ACTIVATIONS.items()
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "label_blind": True,
        "protocol": {
            "path": str(verified["path"].relative_to(root)),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"][
                "decision_contract_sha256"
            ],
            "control_manifest_sha256": verified["value"]["control_surface"][
                "manifest_sha256"
            ],
        },
        "corrections": {
            "v24187_superseded_field": "boundary.immutable_parent_and_control_bytes_live_revalidated",
            "v24187_replacement": "parent artifact SHA/role and V2.41.87 own control manifest were validated there; all supported parent manifests are first live-replayed here",
            "v24188_invalid_assumption": "V2.41.83 handoff receipt has a standalone receipt_payload_sha256",
            "v24188_failed_before_result_publication": True,
            "v24188_result_path_absent": True,
            "v24187_v24188_sources_or_protocols_modified": False,
        },
        "v24187_control_manifest": own_manifest,
        "parent_manifest_replay": parents,
        "heterogeneous_activation_and_receipt_validation": activations,
        "summary": {
            "v24187_parent_artifact_count": len(parents),
            "parent_manifest_entries_live_replayed": entries,
            "artifact_sha_only_parent_count": artifact_only,
            "activation_payload_seals_validated": len(activations) + 1,
            "standalone_receipt_payload_seals_validated": 2,
            "activation_bound_content_addressed_receipts_validated": 1,
            "control_byte_drift_count": 0,
            "absence_guard_violation_count": 0,
            "closure_valid": True,
        },
        "source_policy": {
            "immutable_protocol_control_activation_and_receipt_bytes_only": True,
            "mutable_runtime_state_task_question_answer_evidence_or_prediction_opened_or_hashed": False,
            "mapping_gold_category_question_type_evaluator_or_score_read": False,
            "credential_value_or_keyring_read": False,
            "network_or_api_called": False,
            "process_command_lines_or_environment_read": False,
        },
        "authorization": {
            "process_signal_restart_resume_rerun_skip_or_launch": False,
            "forward_code_prompt_model_search_budget_gate_threshold_or_controller_change": False,
            "benchmark_model_search_fetch_evaluator_or_api_call": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "avg_at_4_available": False,
            "entropy_or_credit_effect_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if OPAQUE_ID.search(encoded) or CREDENTIAL_LIKE.search(encoded):
        raise RuntimeError("V2.41.89 emitted forbidden content")
    value["audit_payload_sha256"] = payload_sha(value)
    return value


def validate_audit(root: Path, path: Path = DEFAULT_RESULT) -> dict[str, Any]:
    root = root.resolve()
    raw = path if path.is_absolute() else root / path
    if (
        raw.resolve(strict=False) != (root / DEFAULT_RESULT).resolve(strict=False)
        or raw.is_symlink()
        or not raw.is_file()
    ):
        raise RuntimeError("V2.41.89 audit path is noncanonical")
    value = read_object(raw)
    if (
        value.get("role") != ROLE
        or value.get("audit_valid") is not True
        or not payload_seal(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.41.89 audit seal is invalid")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--output", default=str(DEFAULT_RESULT))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output)
    output = output if output.is_absolute() else root / output
    if output.resolve(strict=False) != (root / DEFAULT_RESULT).resolve(strict=False):
        raise RuntimeError("V2.41.89 output path is noncanonical")
    value = build_audit(root, protocol_path=Path(args.protocol))
    publish_new(output, value)
    print(json.dumps({"output": str(output), "sha256": sha256(output), "summary": value["summary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
