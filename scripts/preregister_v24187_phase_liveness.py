#!/usr/bin/env python3
"""Freeze the observation-only V2.41.87 phase-aware campaign liveness audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROLE = "v24187_phase_liveness_preregistration"
PROTOCOL_ID = "v24187_phase_aware_campaign_liveness_v1"
DEFAULT_PROTOCOL = Path(
    "results/v24187_phase_liveness_preregistration_v1_20260730.json"
)
DEFAULT_STATE = Path(
    "outputs/v24187_phase_liveness_watcher_state_v1_20260730.json"
)
DEFAULT_ACTIVATION = Path(
    "results/v24187_phase_liveness_activation_audit_v1_20260730.json"
)

PARENTS: dict[str, tuple[str, str]] = {
    "results/v24118_r1_finalization_watchdog_preregistration_v1_20260728.json": (
        "afced234f409356d019e087ca7d329535796a27e5d6c7a82bdf9a03b8c1fd720",
        "v24118_r1_finalization_watchdog_preregistration",
    ),
    "results/v24164_scope_capacity_preregistration_v1_20260729.json": (
        "387abe873c1b5de0eabd0182b4cbbf9c4dfe44a84b3245eab7c3217fadf0edb2",
        "v24164_scope_capacity_preregistration",
    ),
    "results/v24107_paired_dev_liveness_preregistration_v1_20260729.json": (
        "581cd277ef9a2ae179764405407cd5bb27a5c3afb4a53ac60f1245cb4ac7c02b",
        "v24107_paired_dev_liveness_preregistration",
    ),
    "results/v24176_predicate_completion_paired_dev_preregistration_v1_20260730.json": (
        "8c1c3c4d9f7ed8604258fa301ea931a6425cf6c189c5e1c30c0ee387eddd1f1e",
        "v24176_predicate_completion_paired_dev_preregistration",
    ),
    "results/v24180_predicate_search_yield_preregistration_v1_20260730.json": (
        "1274fe4a9b7801d96dd5265443cb3f6b837edd469be3fe85bef1c3d71ebdf5e4",
        "v24180_predicate_search_yield_preregistration",
    ),
    "results/v24183_search_yield_launcher_activation_audit_v1_20260730.json": (
        "5e27fc01b5dc8cdc5a8312973f570ac4f5add6deab15f79b17252d704dd99295",
        "v24183_search_yield_launcher_activation_audit",
    ),
    "results/v24185_markdown_priority_activation_audit_v1_20260730.json": (
        "0ae94c7fac5f2fb4ba0ae3dea5a5385b560155f58da8b830f202f1e3d082c6af",
        "v24185_markdown_priority_activation_audit",
    ),
    "results/v24186_owic_after_quality_chain_activation_audit_v1_20260730.json": (
        "3726a4209761d24ad81eb2967c9ded80613257000bfd01c713a5b347eac8029b",
        "v24186_owic_after_quality_chain_activation_audit",
    ),
    "outputs/v2410_p13_failure_taxonomy_v2_controller_freeze.json": (
        "3a88e64b6f97755c86c65da388051ee387f751a1a7f9322bfcfc095ea6c3dab6",
        "v2410_p13_failure_taxonomy_v2_monitor_controller_freeze",
    ),
    "results/v2410_leaderboard_postprocess_preregistration_v4_20260727.json": (
        "f1cef5ad3266a5aad2dbdfe770f1d889e0fb2875ac202eb790998176864fe8d8",
        "v2410_leaderboard_postprocess_preregistration",
    ),
    "results/v24114_scheduling_disclosure_preregistration_v1_20260728.json": (
        "0adf7140c9c9e214b47cc6791a1bfff7f964b75cc8affd28612ce0fff4f16043",
        "v24114_scheduling_disclosure_preregistration",
    ),
}

CONTROL_FILES = (
    "scripts/preregister_v24187_phase_liveness.py",
    "scripts/audit_v24187_phase_liveness.py",
    "scripts/watch_v24187_phase_liveness.py",
    "scripts/audit_v24187_phase_liveness_activation.py",
    "tests/test_preregister_v24187_phase_liveness.py",
    "tests/test_audit_v24187_phase_liveness.py",
    "tests/test_watch_v24187_phase_liveness.py",
    "tests/test_audit_v24187_phase_liveness_activation.py",
)
MUST_REMAIN_ABSENT = (
    "scripts/__init__.py",
    "sitecustomize.py",
    "usercustomize.py",
)
DECISION_FIELDS = (
    "protocol_id",
    "parents",
    "execution",
    "phase_contract",
    "source_contract",
    "control_surface",
    "authorization",
    "claims",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.41.87 expected a JSON object")
    return value


def _ordinary(root: Path, relative: str, digest: str | None = None) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.41.87 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.is_relative_to(root)
    ):
        raise RuntimeError(f"V2.41.87 expected an ordinary file: {relative}")
    if digest is not None and sha256(path) != digest:
        raise RuntimeError(f"V2.41.87 frozen parent drifted: {relative}")
    return path


def _parents(root: Path) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for relative, (digest, role) in PARENTS.items():
        path = _ordinary(root, relative, digest)
        value = read_object(path)
        if value.get("role") != role:
            raise RuntimeError(f"V2.41.87 parent role drifted: {relative}")
        records[relative] = {
            "sha256": digest,
            "role": role,
            "decision_contract_sha256": value.get("decision_contract_sha256"),
            "contents_emitted": False,
        }
    return records


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    require_pristine_outputs: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    parents = _parents(root)
    if any(
        (root / relative).exists() or (root / relative).is_symlink()
        for relative in MUST_REMAIN_ABSENT
    ):
        raise RuntimeError("V2.41.87 unattested Python bootstrap path appeared")
    if require_pristine_outputs and any(
        (root / relative).exists() or (root / relative).is_symlink()
        for relative in (DEFAULT_STATE, DEFAULT_ACTIVATION)
    ):
        raise FileExistsError("V2.41.87 state or activation output is not pristine")
    manifest = {
        relative: sha256(_ordinary(root, relative)) for relative in CONTROL_FILES
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "label_blind": True,
        "mapping_gold_category_question_type_evaluator_score_prediction_or_outcome_read": False,
        "runtime_task_state_question_answer_evidence_or_prediction_rows_opened": False,
        "credential_value_or_keyring_read": False,
        "network_or_api_called": False,
        "parents": parents,
        "execution": {
            "python_flags": ["-I", "-B"],
            "state_path": str(DEFAULT_STATE),
            "activation_path": str(DEFAULT_ACTIVATION),
            "poll_seconds": 60,
            "state_freshness_seconds": 180,
            "transition_grace_seconds": 180,
            "proc_root": "/proc",
            "atomic_state_replace": True,
            "terminal_watcher_exit_allowed": True,
        },
        "phase_contract": {
            "ordered_phases": [
                "r1_full220",
                "p12_schema76_and_official_avg4",
                "schema77_paired_dev64",
                "predicate_search_yield",
                "markdown_paired_dev64",
                "conditional_scope_open",
                "owic_gate1",
                "post_gate1_and_leaderboard_handoff",
            ],
            "current_authority_selected_from_safe_state_status_only": True,
            "terminal_state_permits_its_executor_to_exit": True,
            "preterminal_state_requires_fresh_envelope_and_unique_executor": True,
            "active_shared_lease_permits_only_owner_bound_freshness_exemption": True,
            "taxonomy_repeated_uncovered_is_manual_review_only": True,
            "taxonomy_status_never_authorizes_automatic_policy_change": True,
        },
        "source_contract": {
            "immutable_parent_bytes_live_revalidated": True,
            "mutable_sources": "safe JSON envelopes, file metadata, process identity, and shared-lease metadata only",
            "aggregate_counts_may_be_reported_before_exact220": True,
            "task_state_question_answer_evidence_prediction_mapping_gold_category_evaluator_or_score_forbidden": True,
            "mutable_source_contents_never_hashed_or_reemitted": True,
            "process_command_lines_and_environment_never_emitted": True,
        },
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha(manifest),
            "must_remain_absent": list(MUST_REMAIN_ABSENT),
        },
        "authorization": {
            "process_signal": False,
            "restart_resume_rerun_skip_or_selective_retry": False,
            "forward_code_prompt_model_search_budget_gate_threshold_or_controller_change": False,
            "credential_or_network_access": False,
            "mapping_gold_category_question_type_evaluator_or_score_read": False,
            "benchmark_model_search_fetch_evaluator_or_api_call": False,
            "candidate_prepare_or_downstream_launch": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "claims": {
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "avg_at_4_available": False,
            "entropy_or_credit_effect_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
    }
    value["decision_contract_sha256"] = payload_sha(
        {key: value[key] for key in DECISION_FIELDS}
    )
    return value


def validate_protocol(
    root: Path, path: Path = DEFAULT_PROTOCOL
) -> dict[str, Any]:
    root = root.resolve()
    raw = path if path.is_absolute() else root / path
    expected = (root / DEFAULT_PROTOCOL).resolve(strict=False)
    if (
        raw.resolve(strict=False) != expected
        or raw.is_symlink()
        or not raw.is_file()
        or not raw.is_relative_to(root / "results")
    ):
        raise RuntimeError("V2.41.87 protocol path is noncanonical")
    value = read_object(raw)
    created = value.get("created_at_unix")
    if not isinstance(created, int) or isinstance(created, bool):
        raise RuntimeError("V2.41.87 created_at is invalid")
    rebuilt = build_protocol(
        root,
        created_at_unix=created,
        require_pristine_outputs=False,
    )
    if value != rebuilt:
        raise RuntimeError("V2.41.87 protocol differs from live rebuild")
    return {"path": raw, "sha256": sha256(raw), "value": value}


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(DEFAULT_PROTOCOL))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    raw = Path(args.output)
    output = raw if raw.is_absolute() else root / raw
    if (
        root != ROOT.resolve()
        or output.resolve(strict=False)
        != (root / DEFAULT_PROTOCOL).resolve(strict=False)
        or output.is_symlink()
    ):
        raise RuntimeError("V2.41.87 output path is noncanonical")
    value = build_protocol(root)
    publish_new(output, value)
    print(
        json.dumps(
            {
                "output": str(output),
                "sha256": sha256(output),
                "decision_contract_sha256": value["decision_contract_sha256"],
                "control_manifest_sha256": value["control_surface"]["manifest_sha256"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
