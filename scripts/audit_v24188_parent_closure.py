#!/usr/bin/env python3
"""Create the one-shot V2.41.88 parent-control closure correction audit."""

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

from scripts.preregister_v24188_parent_closure import (  # noqa: E402
    DEFAULT_PROTOCOL,
    DEFAULT_RESULT,
    V24187_ACTIVATION,
    V24187_ACTIVATION_SHA256,
    V24187_PROTOCOL,
    V24187_PROTOCOL_SHA256,
    ordinary,
    payload_sha,
    publish_new,
    read_object,
    sha256,
    validate_protocol,
)


ROLE = "v24188_parent_control_closure_audit"
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
CREDENTIAL_LIKE = re.compile(
    r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
ACTIVATIONS = {
    "v24183": (
        Path("results/v24183_search_yield_launcher_activation_audit_v1_20260730.json"),
        "5e27fc01b5dc8cdc5a8312973f570ac4f5add6deab15f79b17252d704dd99295",
        "v24183_search_yield_launcher_activation_audit",
    ),
    "v24185": (
        Path("results/v24185_markdown_priority_activation_audit_v1_20260730.json"),
        "0ae94c7fac5f2fb4ba0ae3dea5a5385b560155f58da8b830f202f1e3d082c6af",
        "v24185_markdown_priority_activation_audit",
    ),
    "v24186": (
        Path("results/v24186_owic_after_quality_chain_activation_audit_v1_20260730.json"),
        "3726a4209761d24ad81eb2967c9ded80613257000bfd01c713a5b347eac8029b",
        "v24186_owic_after_quality_chain_activation_audit",
    ),
}


def _payload_seal(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha(unsigned)


def _manifest(
    root: Path,
    owner_path: Path,
    value: dict[str, Any],
) -> tuple[str, dict[str, str], str | None, tuple[str, ...]]:
    control = value.get("control_surface")
    if isinstance(control, dict) and isinstance(control.get("manifest"), dict):
        return (
            "control_surface.manifest",
            control["manifest"],
            control.get("manifest_sha256"),
            tuple(str(name) for name in control.get("must_remain_absent", [])),
        )
    if isinstance(value.get("stable_manifest"), dict):
        return (
            "stable_manifest",
            value["stable_manifest"],
            value.get("stable_manifest_sha256"),
            (),
        )
    if isinstance(value.get("control_manifest"), dict):
        return (
            "control_manifest",
            value["control_manifest"],
            value.get("control_manifest_sha256"),
            (),
        )
    if isinstance(value.get("frozen_dependencies"), dict):
        dependencies: dict[str, str] = {}
        for relative, record in value["frozen_dependencies"].items():
            if not isinstance(record, dict) or not isinstance(record.get("sha256"), str):
                raise RuntimeError(f"V2.41.88 invalid frozen dependency: {owner_path}")
            dependencies[str(relative)] = record["sha256"]
        return "frozen_dependencies", dependencies, None, ()
    return "artifact_sha_only", {}, None, ()


def replay_manifest(
    root: Path, owner_path: Path, value: dict[str, Any]
) -> dict[str, Any]:
    kind, manifest, declared, absent = _manifest(root, owner_path, value)
    if kind != "artifact_sha_only" and not manifest:
        raise RuntimeError(f"V2.41.88 empty parent manifest: {owner_path}")
    computed = payload_sha(manifest) if manifest else None
    declared_valid = declared is None or declared == computed
    drift: list[str] = []
    for relative, digest in manifest.items():
        try:
            ordinary(root, relative, digest)
        except RuntimeError:
            drift.append(relative)
    absence_violations = [
        relative
        for relative in absent
        if (root / relative).exists() or (root / relative).is_symlink()
    ]
    if not declared_valid or drift or absence_violations:
        raise RuntimeError(f"V2.41.88 parent manifest replay failed: {owner_path}")
    return {
        "path": str(owner_path),
        "manifest_kind": kind,
        "manifest_entry_count": len(manifest),
        "declared_manifest_sha256_present": declared is not None,
        "declared_manifest_sha256_valid": declared_valid,
        "entry_byte_drift_count": 0,
        "absence_guard_violation_count": 0,
        "entry_paths_emitted": False,
        "contents_emitted": False,
    }


def _activation(
    root: Path, name: str, path: Path, digest: str, role: str
) -> dict[str, Any]:
    target = ordinary(root, path, digest)
    value = read_object(target)
    receipt = value.get("handoff_receipt") or {}
    receipt_path = Path(str(receipt.get("path", "")))
    receipt_digest = receipt.get("sha256")
    if (
        value.get("role") != role
        or value.get("activation_valid") is not True
        or not _payload_seal(value, "audit_payload_sha256")
        or not isinstance(receipt_digest, str)
    ):
        raise RuntimeError(f"V2.41.88 activation seal drifted: {name}")
    receipt_target = ordinary(root, receipt_path, receipt_digest)
    receipt_value = read_object(receipt_target)
    receipt_field = next(
        (
            field
            for field in ("receipt_payload_sha256",)
            if field in receipt_value
        ),
        None,
    )
    if receipt_field is None or not _payload_seal(receipt_value, receipt_field):
        raise RuntimeError(f"V2.41.88 handoff receipt seal drifted: {name}")
    frozen = value.get("control_surface") or {}
    frozen_records = 0
    for record in frozen.values():
        if not isinstance(record, dict):
            continue
        relative = record.get("path")
        expected = record.get("sha256")
        if isinstance(relative, str) and isinstance(expected, str):
            ordinary(root, relative, expected)
            frozen_records += 1
    protocol_record = value.get("protocol") or {}
    if isinstance(protocol_record.get("path"), str) and isinstance(
        protocol_record.get("sha256"), str
    ):
        ordinary(root, protocol_record["path"], protocol_record["sha256"])
        frozen_records += 1
    return {
        "path": str(path),
        "sha256": digest,
        "role": role,
        "activation_payload_seal_valid": True,
        "handoff_receipt_payload_seal_valid": True,
        "frozen_control_records_live_validated": frozen_records,
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
    v87_path = ordinary(root, V24187_PROTOCOL, V24187_PROTOCOL_SHA256)
    v87 = read_object(v87_path)
    activation_path = ordinary(root, V24187_ACTIVATION, V24187_ACTIVATION_SHA256)
    activation = read_object(activation_path)
    if (
        not _payload_seal(activation, "audit_payload_sha256")
        or activation.get("activation_valid") is not True
    ):
        raise RuntimeError("V2.41.88 V2.41.87 activation seal drifted")
    v87_control = replay_manifest(root, V24187_PROTOCOL, v87)
    parents: dict[str, Any] = {}
    entries = 0
    artifact_only = 0
    for relative, record in v87.get("parents", {}).items():
        if not isinstance(record, dict):
            raise RuntimeError("V2.41.88 V2.41.87 parent record drifted")
        path = ordinary(root, relative, str(record.get("sha256", "")))
        value = read_object(path)
        if value.get("role") != record.get("role"):
            raise RuntimeError("V2.41.88 V2.41.87 parent role drifted")
        report = replay_manifest(root, Path(relative), value)
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
        "correction": {
            "superseded_claim_path": str(V24187_ACTIVATION),
            "superseded_field": "boundary.immutable_parent_and_control_bytes_live_revalidated",
            "superseded_value": True,
            "reason": "V2.41.87 validated parent artifact SHA/role and its own control manifest, but did not itself replay every parent control manifest entry",
            "replacement_claim": "V2.41.88 now live-replays every supported parent manifest entry; artifact-only parents remain artifact-SHA sealed and are separately activation/receipt-seal checked where applicable",
            "v24187_phase_state_process_and_no_mutation_findings_unchanged": True,
            "v24187_source_or_artifact_modified": False,
        },
        "v24187_control_manifest": v87_control,
        "parent_manifest_replay": parents,
        "activation_and_handoff_seals": activations,
        "summary": {
            "v24187_parent_artifact_count": len(parents),
            "parent_manifest_entries_live_replayed": entries,
            "artifact_sha_only_parent_count": artifact_only,
            "activation_payload_seals_validated": len(activations) + 1,
            "handoff_receipt_payload_seals_validated": len(activations),
            "control_byte_drift_count": 0,
            "absence_guard_violation_count": 0,
            "closure_valid": True,
        },
        "source_policy": {
            "immutable_protocol_control_and_receipt_bytes_only": True,
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
        raise RuntimeError("V2.41.88 emitted forbidden content")
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
        raise RuntimeError("V2.41.88 result path is noncanonical")
    value = read_object(raw)
    if (
        value.get("role") != ROLE
        or value.get("audit_valid") is not True
        or not _payload_seal(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.41.88 result seal is invalid")
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
        raise RuntimeError("V2.41.88 output path is noncanonical")
    value = build_audit(root, protocol_path=Path(args.protocol))
    publish_new(output, value)
    print(
        json.dumps(
            {
                "output": str(output),
                "sha256": sha256(output),
                "summary": value["summary"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
