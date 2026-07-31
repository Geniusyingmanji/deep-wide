#!/usr/bin/env python3
"""Run the frozen V2.42.19 post-terminal, label-blind STC audit once."""

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
from deepwide_agent.v24219_search_time_contamination import (  # noqa: E402
    MIN_QCL_CHARS,
    PRIMARY_QCL_RATIO,
    QCL_SENSITIVITY_RATIOS,
    aggregate_task_scans,
    payload_sha256,
    scan_task,
)


PROTOCOL = Path(
    "results/v24219_search_time_contamination_preregistration_v1_20260731.json"
)
RESULT = Path("results/v24218_exact220_result_v1_20260731.json")
FORWARD_BARRIER = Path("results/v24218_exact220_forward_barrier_v1_20260731.json")
MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
DETAIL = Path("outputs/v24219_search_time_contamination_detail_v1_20260731.json")
REPORT = Path("results/v24219_search_time_contamination_report_v1_20260731.json")
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

FORBIDDEN_INPUT_KEYS = frozenset(
    {
        "category",
        "task_category",
        "question_type",
        "split",
        "subset",
        "topic",
        "language",
        "ground_truth",
        "gold",
        "gold_answer",
        "answer_key",
        "reference_answer",
        "reward",
        "score",
        "evaluator_score",
        "correct",
        "prediction",
        "queries",
        "query",
    }
)
EVIDENCE_KEYS = (
    "id",
    "kind",
    "url",
    "source_family",
    "title",
    "text",
    "fingerprint",
)


def _present(root: Path, relative: Path) -> bool:
    path = root / relative
    return path.exists() or path.is_symlink()


def _ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.19 path is noncanonical")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or path.resolve() != path.absolute()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.42.19 expected an ordinary file: {relative}")
    return path


def _read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.19 expected an ordinary JSON object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.19 JSON root is not an object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError("V2.42.19 JSONL row is not an object")
        rows.append(value)
    return rows


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
                raise RuntimeError(f"V2.42.19 forbidden input field at {path}")
            _reject_forbidden_keys(child, path=f"{path}.{folded}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_keys(child, path=f"{path}[{index}]")


def validate_protocol(root: Path = ROOT) -> dict[str, Any]:
    value = _read_object(_ordinary(root, PROTOCOL))
    manifest = (value.get("control_surface") or {}).get("manifest")
    unsigned = dict(value)
    decision = unsigned.pop("decision_contract_sha256", None)
    if (
        value.get("role") != "v24219_search_time_contamination_preregistration"
        or value.get("protocol_id")
        != "v24219_post_terminal_label_blind_stc_audit_v1"
        or not isinstance(manifest, dict)
        or value.get("control_surface", {}).get("file_count") != len(manifest)
        or value.get("control_surface", {}).get("manifest_sha256")
        != payload_sha256(manifest)
        or decision != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.19 protocol is invalid")
    for relative, digest in manifest.items():
        target = _ordinary(root, Path(relative))
        if file_sha256(target) != digest:
            raise RuntimeError("V2.42.19 control bytes drifted")
    return {"value": value, "sha256": file_sha256(root / PROTOCOL)}


def validate_terminal_authority(root: Path = ROOT) -> dict[str, Any]:
    """Validate sealed exact-220 identities without opening evaluator rows."""

    barrier = _read_object(_ordinary(root, FORWARD_BARRIER))
    result = _read_object(_ordinary(root, RESULT))
    if (
        barrier.get("role") != "v24218_exact220_forward_terminal_barrier"
        or not sealed(barrier, "barrier_payload_sha256")
        or barrier.get("selected") != 220
        or barrier.get("completed", -1) + barrier.get("failed", -1) != 220
        or barrier.get("all_four_shards_exact_terminal") is not True
        or barrier.get("mapping_path_opened_or_hashed") is not False
        or barrier.get("evaluator_input_result_or_score_opened") is not False
        or result.get("role") != "v24218_exact220_released_local_result"
        or not sealed(result, "result_payload_sha256")
        or result.get("selected") != 220
        or result.get("runtime_completed", -1) + result.get("runtime_failed", -1)
        != 220
        or result.get("forward_barrier")
        != {"path": str(FORWARD_BARRIER), "sha256": file_sha256(root / FORWARD_BARRIER)}
        or result.get("resume_or_selective_rerun_used") is not False
        or result.get(
            "mapping_gold_category_question_type_evaluator_score_used_for_forward_routing"
        )
        is not False
        or result.get("sota") is not False
    ):
        raise RuntimeError("V2.42.19 exact-220 terminal authority is invalid")
    return {
        "result": {"path": str(RESULT), "sha256": file_sha256(root / RESULT)},
        "forward_barrier": {
            "path": str(FORWARD_BARRIER),
            "sha256": file_sha256(root / FORWARD_BARRIER),
        },
        "runtime_completed": int(result["runtime_completed"]),
        "runtime_failed": int(result["runtime_failed"]),
    }


def _manifest(root: Path) -> tuple[dict[str, str], str]:
    path = _ordinary(root, MANIFEST)
    rows = _read_jsonl(path)
    if (
        len(rows) != 220
        or any(set(row) != {"opaque_id", "question"} for row in rows)
        or len({row.get("opaque_id") for row in rows}) != 220
        or any(not isinstance(row.get("question"), str) or not row["question"].strip() for row in rows)
    ):
        raise RuntimeError("V2.42.19 runtime manifest is not exact label-blind 220")
    return {str(row["opaque_id"]): str(row["question"]) for row in rows}, file_sha256(path)


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
    # A terminal runtime state naturally has sibling fields such as a rendered
    # prediction.  Do not traverse or read them: project only the evidence
    # ledger, then apply a recursive forbidden-field check to that projection.
    rows = state.get("evidence")
    if not isinstance(rows, list):
        return []
    output: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        # Live evidence rows contain the queries that discovered them.  Their
        # values are intentionally not indexed here: project only approved
        # page fields so query/question overlap cannot become a detector.
        projection = {key: row[key] for key in EVIDENCE_KEYS if key in row}
        _reject_forbidden_keys(projection)
        output.append(projection)
    return output


def _task_receipt(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "opaque_id_sha256": str(row["opaque_id_sha256"]),
        "evidence_items_scanned": row["evidence_items_scanned"],
        "finding_count": len(row["findings"]),
        "flags": row["flags"],
        "qcl_sensitivity": row["qcl_sensitivity"],
    }


def run_audit(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.19 canonical execution boundary drifted")
    protocol = validate_protocol(root)
    authority = validate_terminal_authority(root)
    manifest, manifest_sha = _manifest(root)
    partition = _partition(root)
    if set(manifest) != {opaque_id for ids in partition.values() for opaque_id in ids}:
        raise RuntimeError("V2.42.19 manifest and canonical partition differ")

    task_rows: list[dict[str, Any]] = []
    state_files_opened = 0
    missing_state_files = 0
    for tag in EXPECTED_SHARDS:
        for opaque_id in partition[tag]:
            path = _state_path(tag, opaque_id)
            if path.is_symlink():
                raise RuntimeError("V2.42.19 task state is a symlink")
            if path.is_file():
                state = _read_object(path)
                if state.get("opaque_id") != opaque_id:
                    raise RuntimeError("V2.42.19 task-state identity drifted")
                state_files_opened += 1
                evidence = _evidence_projection(state)
            elif path.exists():
                raise RuntimeError("V2.42.19 task state path is noncanonical")
            else:
                missing_state_files += 1
                evidence = []
            task_rows.append(
                scan_task(
                    opaque_id=opaque_id,
                    question=manifest[opaque_id],
                    evidence=evidence,
                )
            )
    if len(task_rows) != 220 or state_files_opened + missing_state_files != 220:
        raise RuntimeError("V2.42.19 audit did not cover exact-220")
    if missing_state_files > authority["runtime_failed"]:
        raise RuntimeError("V2.42.19 a completed task lacks its terminal state")
    aggregate = aggregate_task_scans(task_rows)
    if aggregate["tasks_scanned"] != 220:
        raise RuntimeError("V2.42.19 aggregate denominator drifted")

    detail: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24219_search_time_contamination_private_detail",
        "protocol": {"path": str(PROTOCOL), "sha256": protocol["sha256"]},
        "parent": authority,
        "runtime_manifest_sha256": manifest_sha,
        "detector": {
            "primary_qcl_ratio": PRIMARY_QCL_RATIO,
            "minimum_qcl_contiguous_chars": MIN_QCL_CHARS,
            "qcl_sensitivity_ratios": list(QCL_SENSITIVITY_RATIOS),
            "query_question_overlap_is_not_a_contamination_signal": True,
            "confirmed_eal_requires_exact_question_and_corresponding_gold_pair": True,
            "gold_unavailable_so_eal_is_candidate_only": True,
        },
        "state_files_opened": state_files_opened,
        "missing_state_files_scanned_as_zero_evidence": missing_state_files,
        "tasks": task_rows,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "forward_result_or_evaluator_modified": False,
        "question_query_page_text_or_answer_emitted": False,
    }
    detail["detail_payload_sha256"] = payload_sha256(detail)
    report: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24219_search_time_contamination_public_aggregate",
        "status": "post_terminal_label_blind_audit_complete_eal_unconfirmed",
        "protocol": {"path": str(PROTOCOL), "sha256": protocol["sha256"]},
        "parent": authority,
        "runtime_manifest": {"path": str(MANIFEST), "sha256": manifest_sha},
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
        "contamination_sensitive_subset_is_separate_not_primary": True,
        "sample_exclusion_or_score_recomputation_performed": False,
        "confirmed_eal": None,
        "manual_review_required_for_eal_candidates": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "shared_api_lease_acquired": False,
        "forward_result_evaluator_or_watcher_modified": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "question_query_page_text_url_or_task_id_emitted": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    report["report_payload_sha256"] = payload_sha256(report)
    return detail, report


def validate_report(root: Path = ROOT) -> dict[str, Any]:
    protocol = validate_protocol(root)
    authority = validate_terminal_authority(root)
    detail_path = _ordinary(root, DETAIL)
    report = _read_object(_ordinary(root, REPORT))
    aggregate = report.get("aggregate") or {}
    if (
        report.get("role") != "v24219_search_time_contamination_public_aggregate"
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
        or report.get("contamination_sensitive_subset_is_separate_not_primary")
        is not True
        or report.get("sample_exclusion_or_score_recomputation_performed") is not False
        or report.get("confirmed_eal") is not None
        or report.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or report.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or report.get("shared_api_lease_acquired") is not False
        or report.get("forward_result_evaluator_or_watcher_modified") is not False
        or report.get(
            "process_signal_restart_resume_rerun_skip_or_selective_retry"
        )
        is not False
        or report.get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.42.19 report differs from its frozen safety contract")
    return report


def publish_audit(root: Path = ROOT) -> dict[str, Any]:
    if _present(root, DETAIL) or _present(root, REPORT):
        raise RuntimeError("V2.42.19 audit output already exists; rerun is forbidden")
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
                "confirmed_eal": None,
            }
        )
    )


if __name__ == "__main__":
    main()
