#!/usr/bin/env python3
"""Run the frozen V2.42.20 post-terminal source-dependency audit once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24218_exact220_executor import (  # noqa: E402
    EXPECTED_COUNTS,
    EXPECTED_SHARDS,
    file_sha256,
    read_opaque_ids,
    sealed,
    validate_exact_partition,
)
from deepwide_agent.v24220_source_dependency import (  # noqa: E402
    aggregate_tasks,
    analyze_task,
    payload_sha256,
)
from scripts.run_v24219_search_time_contamination import (  # noqa: E402
    validate_report as validate_parent_report,
)


PROTOCOL = Path("results/v24220_source_dependency_preregistration_v1_20260731.json")
PARENT_PROTOCOL = Path(
    "results/v24219_search_time_contamination_preregistration_v1_20260731.json"
)
PARENT_STATE = Path(
    "outputs/v24219_search_time_contamination_watcher_state_v1_20260731.json"
)
PARENT_REPORT = Path("results/v24219_search_time_contamination_report_v1_20260731.json")
MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
DETAIL = Path("outputs/v24220_source_dependency_detail_v1_20260731.json")
REPORT = Path("results/v24220_source_dependency_report_v1_20260731.json")
SHARD_IDS = {
    "test_s01": Path("configs/full220_v2403_r1_test_s01.ids"),
    "test_s02": Path("configs/full220_v2403_r1_test_s02.ids"),
    "test_s03": Path("configs/full220_v2403_r1_test_s03.ids"),
    "devval": Path("configs/full220_v2403_r1_devval_s04.ids"),
}
SHARD_ROOTS = {
    tag: ROOT / f"outputs/v24218_exact220_{tag}_root_v1_20260731"
    for tag in EXPECTED_SHARDS
}
TARGETS = {
    tag: f"v24218_joint_package_{tag}_v1_20260731" for tag in EXPECTED_SHARDS
}
EVIDENCE_KEYS = (
    "id",
    "kind",
    "url",
    "source_family",
    "title",
    "text",
    "fingerprint",
)
FORBIDDEN_INPUT_KEYS = frozenset(
    {
        "answer_key",
        "category",
        "correct",
        "evaluator_score",
        "gold",
        "gold_answer",
        "ground_truth",
        "language",
        "prediction",
        "queries",
        "query",
        "question",
        "question_type",
        "reference_answer",
        "reward",
        "score",
        "split",
        "subset",
        "task_category",
        "topic",
    }
)


def _present(root: Path, relative: Path) -> bool:
    path = root / relative
    return path.exists() or path.is_symlink()


def _ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.20 path is noncanonical")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or path.resolve() != path.absolute()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.42.20 expected an ordinary file: {relative}")
    return path


def _read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.20 expected an ordinary JSON object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.20 JSON root is not an object")
    return value


def _publish_new(path: Path, value: dict[str, Any]) -> None:
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


def _serialized_sha256(value: Mapping[str, Any]) -> str:
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _reject_forbidden_keys(value: object, *, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            folded = str(key).casefold()
            if folded in FORBIDDEN_INPUT_KEYS:
                raise RuntimeError(f"V2.42.20 forbidden input field at {path}")
            _reject_forbidden_keys(child, path=f"{path}.{folded}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_keys(child, path=f"{path}[{index}]")


def validate_protocol(root: Path = ROOT, path: Path = PROTOCOL) -> dict[str, Any]:
    value = _read_object(_ordinary(root, path))
    manifest = (value.get("control_surface") or {}).get("manifest")
    unsigned = dict(value)
    decision = unsigned.pop("decision_contract_sha256", None)
    if (
        value.get("role") != "v24220_source_dependency_preregistration"
        or value.get("protocol_id")
        != "v24220_post_terminal_label_blind_source_dependency_v1"
        or not isinstance(manifest, dict)
        or value.get("control_surface", {}).get("file_count") != len(manifest)
        or value.get("control_surface", {}).get("manifest_sha256")
        != payload_sha256(manifest)
        or decision != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.20 protocol is invalid")
    for relative, digest in manifest.items():
        target = _ordinary(root, Path(relative))
        if file_sha256(target) != digest:
            raise RuntimeError("V2.42.20 control bytes drifted")
    return {"value": value, "sha256": file_sha256(root / path)}


def validate_parent_terminal_authority(root: Path = ROOT) -> dict[str, Any]:
    """Validate V2.42.19 terminal artifacts without opening evaluator rows."""

    state = _read_object(_ordinary(root, PARENT_STATE))
    unsigned = dict(state)
    seal = unsigned.pop("state_payload_sha256", None)
    if (
        state.get("role") != "v24219_search_time_contamination_watcher_state"
        or seal != payload_sha256(unsigned)
        or state.get("status") != "complete_post_terminal_contamination_audit"
        or state.get("terminal") is not True
        or state.get("parent_terminal_result_and_barrier_validated") is not True
        or state.get("task_manifest_or_evidence_opened") is not True
        or state.get("report_created") is not True
        or state.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or state.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or state.get("shared_api_lease_acquired") is not False
        or state.get("forward_result_evaluator_or_watcher_modified") is not False
        or state.get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.42.20 parent state is not a safe terminal authority")
    report = validate_parent_report(root)
    report_path = _ordinary(root, PARENT_REPORT)
    if (
        report.get("role")
        != "v24219_search_time_contamination_public_aggregate"
        or report.get("aggregate", {}).get("tasks_scanned") != 220
        or report.get("official_primary_denominator") != 220
        or report.get("official_primary_result_unchanged") is not True
        or report.get("sample_exclusion_or_score_recomputation_performed") is not False
        or report.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or report.get("leaderboard_submission_or_sota_claim") is not False
        or state.get("report")
        != {"path": str(PARENT_REPORT), "sha256": file_sha256(report_path)}
    ):
        raise RuntimeError("V2.42.20 parent report identity drifted")
    parent = report.get("parent") or {}
    runtime_completed = parent.get("runtime_completed")
    runtime_failed = parent.get("runtime_failed")
    if (
        isinstance(runtime_completed, bool)
        or not isinstance(runtime_completed, int)
        or isinstance(runtime_failed, bool)
        or not isinstance(runtime_failed, int)
        or runtime_completed + runtime_failed != 220
    ):
        raise RuntimeError("V2.42.20 parent runtime counts drifted")
    return {
        "state": {"path": str(PARENT_STATE), "sha256": file_sha256(root / PARENT_STATE)},
        "report": {"path": str(PARENT_REPORT), "sha256": file_sha256(report_path)},
        "runtime_completed": runtime_completed,
        "runtime_failed": runtime_failed,
    }


def _partition(root: Path) -> dict[str, list[str]]:
    rows = {
        tag: read_opaque_ids(_ordinary(root, SHARD_IDS[tag]), EXPECTED_COUNTS[tag])
        for tag in EXPECTED_SHARDS
    }
    validate_exact_partition(rows)
    return rows


def _state_path(tag: str, opaque_id: str) -> Path:
    return (
        SHARD_ROOTS[tag]
        / "outputs"
        / f"{TARGETS[tag]}_forward"
        / "tasks"
        / opaque_id
        / "state.json"
    )


def _evidence_projection(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    # Do not traverse siblings such as question, prediction, or renderer output.
    rows = state.get("evidence")
    if not isinstance(rows, list):
        return []
    output: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        projection = {key: row[key] for key in EVIDENCE_KEYS if key in row}
        _reject_forbidden_keys(projection)
        output.append(projection)
    return output


def _task_receipt(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "opaque_id_sha256": row["opaque_id_sha256"],
        "raw_evidence_items": row["raw_evidence_items"],
        "eligible_page_items": row["eligible_page_items"],
        "nominal_evidence_width": row["nominal_evidence_width"],
        "hard_dependency_cluster_width": row["hard_dependency_cluster_width"],
        "dependency_graph_components": row["dependency_graph_components"],
        "dependency_adjusted_effective_width": row[
            "dependency_adjusted_effective_width"
        ],
        "nominal_to_effective_reduction": row["nominal_to_effective_reduction"],
        "unique_source_families": row["unique_source_families"],
        "hard_dependency_edge_pairs": row["hard_dependency_edge_pairs"],
        "soft_dependency_edge_pairs": row["soft_dependency_edge_pairs"],
        "hard_edge_reason_counts": row["hard_edge_reason_counts"],
        "soft_edge_reason_counts": row["soft_edge_reason_counts"],
    }


def run_audit(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.20 canonical execution boundary drifted")
    protocol = validate_protocol(root)
    authority = validate_parent_terminal_authority(root)
    partition = _partition(root)
    task_rows: list[dict[str, Any]] = []
    state_files_opened = 0
    missing_state_files = 0
    for tag in EXPECTED_SHARDS:
        for opaque_id in partition[tag]:
            path = _state_path(tag, opaque_id)
            if path.is_symlink():
                raise RuntimeError("V2.42.20 task state is a symlink")
            if path.is_file():
                state = _read_object(path)
                if state.get("opaque_id") != opaque_id:
                    raise RuntimeError("V2.42.20 task-state identity drifted")
                state_files_opened += 1
                evidence = _evidence_projection(state)
            elif path.exists():
                raise RuntimeError("V2.42.20 task state path is noncanonical")
            else:
                missing_state_files += 1
                evidence = []
            task_rows.append(analyze_task(opaque_id=opaque_id, evidence=evidence))
    if len(task_rows) != 220 or state_files_opened + missing_state_files != 220:
        raise RuntimeError("V2.42.20 audit did not cover exact-220")
    if missing_state_files > authority["runtime_failed"]:
        raise RuntimeError("V2.42.20 a completed task lacks its terminal state")
    aggregate = aggregate_tasks(task_rows)
    if aggregate["tasks_scanned"] != 220:
        raise RuntimeError("V2.42.20 aggregate denominator drifted")

    detail: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24220_source_dependency_private_detail",
        "protocol": {"path": str(PROTOCOL), "sha256": protocol["sha256"]},
        "parent": authority,
        "state_files_opened": state_files_opened,
        "missing_state_files_scanned_as_zero_evidence": missing_state_files,
        "tasks": [_task_receipt(row) for row in task_rows],
        "question_query_prediction_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "shared_api_lease_acquired": False,
        "forward_result_evaluator_or_watcher_modified": False,
        "official_score_or_prediction_recomputed": False,
        "page_text_raw_url_evidence_id_or_task_id_emitted": False,
    }
    detail["detail_payload_sha256"] = payload_sha256(detail)
    report: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24220_source_dependency_public_aggregate",
        "status": "post_terminal_label_blind_source_dependency_audit_complete",
        "protocol": {"path": str(PROTOCOL), "sha256": protocol["sha256"]},
        "parent": authority,
        "private_detail": {
            "path": str(DETAIL),
            "sha256": _serialized_sha256(detail),
            "git_commit_allowed": False,
        },
        "aggregate": aggregate,
        "state_files_opened": state_files_opened,
        "missing_state_files_scanned_as_zero_evidence": missing_state_files,
        "official_primary_denominator": 220,
        "official_primary_result_unchanged": True,
        "sample_exclusion_score_or_prediction_recomputation_performed": False,
        "dependency_adjusted_width_is_sensitivity_not_correctness": True,
        "query_focused_persisted_page_evidence_not_full_raw_page": True,
        "question_query_prediction_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "shared_api_lease_acquired": False,
        "forward_result_evaluator_or_watcher_modified": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "page_text_raw_url_evidence_id_or_task_id_emitted": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    report["report_payload_sha256"] = payload_sha256(report)
    return detail, report


def validate_report(root: Path = ROOT) -> dict[str, Any]:
    protocol = validate_protocol(root)
    authority = validate_parent_terminal_authority(root)
    detail_path = _ordinary(root, DETAIL)
    report = _read_object(_ordinary(root, REPORT))
    aggregate = report.get("aggregate") or {}
    if (
        report.get("role") != "v24220_source_dependency_public_aggregate"
        or not sealed(report, "report_payload_sha256")
        or report.get("protocol")
        != {"path": str(PROTOCOL), "sha256": protocol["sha256"]}
        or report.get("parent") != authority
        or report.get("private_detail")
        != {
            "path": str(DETAIL),
            "sha256": file_sha256(detail_path),
            "git_commit_allowed": False,
        }
        or aggregate.get("tasks_scanned") != 220
        or report.get("state_files_opened", -1)
        + report.get("missing_state_files_scanned_as_zero_evidence", -1)
        != 220
        or report.get("missing_state_files_scanned_as_zero_evidence", 221)
        > authority["runtime_failed"]
        or report.get("official_primary_denominator") != 220
        or report.get("official_primary_result_unchanged") is not True
        or report.get(
            "sample_exclusion_score_or_prediction_recomputation_performed"
        )
        is not False
        or report.get("dependency_adjusted_width_is_sensitivity_not_correctness")
        is not True
        or report.get(
            "question_query_prediction_mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or report.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or report.get("shared_api_lease_acquired") is not False
        or report.get("forward_result_evaluator_or_watcher_modified") is not False
        or report.get(
            "process_signal_restart_resume_rerun_skip_or_selective_retry"
        )
        is not False
        or report.get("page_text_raw_url_evidence_id_or_task_id_emitted") is not False
        or report.get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.42.20 report differs from its frozen safety contract")
    return report


def publish_audit(root: Path = ROOT) -> dict[str, Any]:
    if _present(root, DETAIL) or _present(root, REPORT):
        raise RuntimeError("V2.42.20 audit output already exists; rerun is forbidden")
    detail, report = run_audit(root)
    _publish_new(root / DETAIL, detail)
    try:
        _publish_new(root / REPORT, report)
    except BaseException:
        (root / DETAIL).unlink(missing_ok=True)
        raise
    return validate_report(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()
    value = publish_audit(Path(args.root))
    print(
        json.dumps(
            {
                "path": str(REPORT),
                "sha256": file_sha256(ROOT / REPORT),
                "tasks_scanned": value["aggregate"]["tasks_scanned"],
                "official_primary_result_unchanged": True,
            }
        )
    )


if __name__ == "__main__":
    main()
