#!/usr/bin/env python3
"""Aggregate post-freeze diagnosis of the V2.49.54/V2.49.64 replication.

Both exact-220 predictions and evaluator outputs were frozen, audited, and
pushed before this script existed.  This module may therefore compare paired
outcomes offline, but it publishes aggregate counters only and grants no
forward-routing, rerun, evaluator, leaderboard, or SOTA authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24964_partial_signature_replication_contract as contract  # noqa: E402
from scripts.run_v24954_partial_signature_exact220_task import (  # noqa: E402
    validate_runtime_receipt,
)


DATE = "20260809"
PROTOCOL_ID = "v24965_v24954_v24964_postfreeze_replication_diagnosis_v1"
RESULT = Path(f"results/v24965_v24954_v24964_replication_diagnosis_v1_{DATE}.json")
AUDIT = Path(
    f"results/v24965_v24954_v24964_replication_diagnosis_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/diagnose_v24965_v24954_v24964_replication.py")
TEST = Path("tests/test_diagnose_v24965_v24954_v24964_replication.py")

ARMS = {
    "v24954": {
        "protocol_id": "v24954_keyless_mutual_partial_signature_exact220_v1",
        "result": Path("results/v24954_partial_signature_exact220_result_v1_20260809.json"),
        "audit": Path(
            "results/v24954_partial_signature_exact220_postresult_audit_v1_20260809.json"
        ),
        "runtime": Path(
            "outputs/v24954_partial_signature_exact220_v1_20260809/runtime_predictions.jsonl"
        ),
        "summary": Path(
            "outputs/v24954_partial_signature_exact220_v1_20260809/evaluator/conservative_summary.json"
        ),
        "tasks": Path("outputs/v24954_partial_signature_exact220_v1_20260809/tasks"),
    },
    "v24964": {
        "protocol_id": contract.PROTOCOL_ID,
        "result": Path(
            "results/v24964_partial_signature_replication_result_v1_20260809.json"
        ),
        "audit": Path(
            "results/v24964_partial_signature_replication_postresult_audit_v1_20260809.json"
        ),
        "runtime": Path(
            "outputs/v24964_partial_signature_replication_v1_20260809/runtime_predictions.jsonl"
        ),
        "summary": Path(
            "outputs/v24964_partial_signature_replication_v1_20260809/evaluator/conservative_summary.json"
        ),
        "tasks": Path("outputs/v24964_partial_signature_replication_v1_20260809/tasks"),
    },
}

METRICS = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
RECEIPT_FIELDS = (
    "input_page_count",
    "pipe_group_count",
    "pipe_line_count",
    "schema_touching_pipe_line_count",
    "partial_candidate_edge_count",
    "partial_ambiguous_header_mapping_count",
    "partial_header_bound_table_count",
    "admissible_bound_observation_count",
    "retained_admissible_bound_observation_count",
)


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.49.65 requires clean pushed HEAD")


def _ordinary(path: Path) -> Path:
    value = (ROOT / path).resolve(strict=False)
    if (
        path.is_absolute()
        or ".." in path.parts
        or (ROOT / path).is_symlink()
        or not value.is_file()
        or not value.is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.49.65 expected ordinary repository file: {path}")
    return value


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.65 expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in _ordinary(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.49.65 expected JSONL objects")
    return rows


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_arm(name: str) -> dict[str, Any]:
    spec = ARMS[name]
    result = _read(spec["result"])
    audit = _read(spec["audit"])
    runtime = _read_jsonl(spec["runtime"])
    summary = _read(spec["summary"])
    per_task = summary.get("per_task")
    group = (summary.get("groups") or {}).get("all_220") or {}
    if (
        result.get("protocol_id") != spec["protocol_id"]
        or result.get("status") != "exact220_single_rollout_complete"
        or result.get("selected") != 220
        or result.get("failure_as_zero") is not True
        or not _sealed(result, "result_payload_sha256")
        or audit.get("protocol_id") != spec["protocol_id"]
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or len(runtime) != 220
        or not isinstance(per_task, list)
        or len(per_task) != 220
        or group.get("selected") != 220
        or (group.get("conservative_all_selected") or {}).get("denominator") != 220
        or any(
            row.get("status") != "completed"
            or row.get("label_blind") is not True
            or row.get(
                "mapping_gold_category_question_type_split_evaluator_score_read"
            )
            is not False
            for row in runtime
        )
    ):
        raise RuntimeError(f"V2.49.65 invalid frozen arm: {name}")
    runtime_by_id = {str(row["opaque_id"]): row for row in runtime}
    summary_by_id = {str(row["opaque_id"]): row for row in per_task}
    if len(runtime_by_id) != 220 or set(runtime_by_id) != set(summary_by_id):
        raise RuntimeError(f"V2.49.65 arm identity drifted: {name}")
    return {
        "result": result,
        "audit": audit,
        "runtime": runtime_by_id,
        "summary": summary_by_id,
    }


def _metric_value(row: Mapping[str, Any], name: str) -> float:
    metrics = row.get("metrics") or {}
    value = float(metrics.get(name, 0.0))
    if not math.isfinite(value) or value < 0.0:
        raise RuntimeError("V2.49.65 invalid conservative metric")
    return value


def _task_composite(row: Mapping[str, Any]) -> float:
    return sum(_metric_value(row, name) for name in METRICS) / len(METRICS)


def paired_quality(
    control_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(control_rows) != len(candidate_rows) or not control_rows:
        raise ValueError("V2.49.65 paired quality requires equal nonempty vectors")
    output: dict[str, Any] = {}
    for name in (*METRICS, "quality_composite"):
        left = [
            _task_composite(row) if name == "quality_composite" else _metric_value(row, name)
            for row in control_rows
        ]
        right = [
            _task_composite(row) if name == "quality_composite" else _metric_value(row, name)
            for row in candidate_rows
        ]
        deltas = [candidate - control for control, candidate in zip(left, right)]
        output[name] = {
            "control_mean": sum(left) / len(left),
            "candidate_mean": sum(right) / len(right),
            "mean_delta": sum(deltas) / len(deltas),
            "candidate_wins": sum(delta > 0 for delta in deltas),
            "ties": sum(delta == 0 for delta in deltas),
            "candidate_losses": sum(delta < 0 for delta in deltas),
        }
    return output


def exact_transitions(
    control_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    pairs = [
        (
            _metric_value(control, "score") > 0.0,
            _metric_value(candidate, "score") > 0.0,
        )
        for control, candidate in zip(control_rows, candidate_rows)
    ]
    return {
        "both_exact": sum(control and candidate for control, candidate in pairs),
        "candidate_only_exact": sum(not control and candidate for control, candidate in pairs),
        "control_only_exact": sum(control and not candidate for control, candidate in pairs),
        "neither_exact": sum(not control and not candidate for control, candidate in pairs),
    }


def validity_transitions(
    control_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    pairs = [
        (bool(control.get("evaluator_valid")), bool(candidate.get("evaluator_valid")))
        for control, candidate in zip(control_rows, candidate_rows)
    ]
    return {
        "both_valid": sum(control and candidate for control, candidate in pairs),
        "candidate_only_valid": sum(not control and candidate for control, candidate in pairs),
        "control_only_valid": sum(control and not candidate for control, candidate in pairs),
        "both_invalid": sum(not control and not candidate for control, candidate in pairs),
    }


def _receipt_aggregate(name: str) -> dict[str, Any]:
    task_root = ROOT / ARMS[name]["tasks"]
    totals = {field: 0 for field in RECEIPT_FIELDS}
    engaged = partial_engaged = 0
    hashes: list[str] = []
    for position in range(1, 221):
        path = task_root / f"task_{position:04d}" / "partial_signature_projection_receipt.json"
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"V2.49.65 missing projection receipt: {name}/{position}")
        value = validate_runtime_receipt(json.loads(path.read_text(encoding="utf-8")))
        receipt = value["candidate_receipt"]
        hashes.append(sha256(path))
        for field in RECEIPT_FIELDS:
            totals[field] += int(receipt[field])
        engaged += int(int(receipt["admissible_bound_observation_count"]) > 0)
        partial_engaged += int(int(receipt["partial_header_bound_table_count"]) > 0)
    return {
        "valid_receipts": 220,
        "tasks_with_admissible_observation": engaged,
        "tasks_with_partial_header_binding": partial_engaged,
        "totals": totals,
        "receipt_hash_vector_sha256": payload_sha256(hashes),
    }


def build_result(*, now: int | None = None) -> dict[str, Any]:
    arms = {name: _validate_arm(name) for name in ARMS}
    ids = list(arms["v24954"]["runtime"])
    if set(ids) != set(arms["v24964"]["runtime"]):
        raise RuntimeError("V2.49.65 paired opaque-id set drifted")
    control_runtime = [arms["v24954"]["runtime"][item] for item in ids]
    candidate_runtime = [arms["v24964"]["runtime"][item] for item in ids]
    control_summary = [arms["v24954"]["summary"][item] for item in ids]
    candidate_summary = [arms["v24964"]["summary"][item] for item in ids]
    quality = paired_quality(control_summary, candidate_summary)
    exact = exact_transitions(control_summary, candidate_summary)
    validity = validity_transitions(control_summary, candidate_summary)
    receipts = {name: _receipt_aggregate(name) for name in ARMS}
    changed = sum(
        left["prediction_sha256"] != right["prediction_sha256"]
        for left, right in zip(control_runtime, candidate_runtime)
    )
    same = 220 - changed
    control_result = arms["v24954"]["result"]["metrics"]["all_220"]
    candidate_result = arms["v24964"]["result"]["metrics"]["all_220"]
    partial_exposure = sum(
        int(receipts[name]["totals"]["partial_header_bound_table_count"])
        for name in ARMS
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24965_v24954_v24964_postfreeze_replication_diagnosis",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "paired_task_count": 220,
        "prediction_change": {
            "changed": changed,
            "unchanged": same,
            "changed_fraction": changed / 220,
        },
        "exact_transitions": exact,
        "validity_transitions": validity,
        "paired_quality": quality,
        "aggregate_result_comparison": {
            "control_exact": int(control_result["whole_table_successes"]),
            "candidate_exact": int(candidate_result["whole_table_successes"]),
            "exact_delta": int(candidate_result["whole_table_successes"])
            - int(control_result["whole_table_successes"]),
            "control_composite": float(control_result["quality_composite"]),
            "candidate_composite": float(candidate_result["quality_composite"]),
            "composite_delta": float(candidate_result["quality_composite"])
            - float(control_result["quality_composite"]),
            "control_evaluator_invalid": int(
                control_result["evaluator_invalid_or_not_run"]
            ),
            "candidate_evaluator_invalid": int(
                candidate_result["evaluator_invalid_or_not_run"]
            ),
            "control_system_total_tokens": int(control_result["system_total_tokens"]),
            "candidate_system_total_tokens": int(candidate_result["system_total_tokens"]),
        },
        "mechanism_exposure": receipts,
        "diagnosis": {
            "same_frozen_algorithm_reexecuted": True,
            "same_page_bytes_or_provider_responses_between_runs": False,
            "partial_signature_exposure_across_both_runs": partial_exposure,
            "partial_signature_mechanism_engaged": partial_exposure > 0,
            "exact_improved": exact["candidate_only_exact"]
            > exact["control_only_exact"],
            "aggregate_exact_delta_zero": (
                int(candidate_result["whole_table_successes"])
                == int(control_result["whole_table_successes"])
            ),
            "algorithmic_gain_attributable_to_partial_signature": False,
            "observed_score_delta_is_replication_variation_not_treatment_effect": True,
            "public_exact220_successor_authorized": False,
            "next_required_evidence": (
                "fresh benchmark-external same-response same-page-byte paired "
                "source-fair synthesis quality gate"
            ),
        },
        "provenance": {
            name: {
                key: sha256(ROOT / spec[key])
                for key in ("result", "audit", "runtime", "summary")
            }
            for name, spec in ARMS.items()
        },
        "source_policy": {
            "postfreeze_offline_analysis_only": True,
            "question_prediction_page_gold_category_question_type_split_or_per_task_score_persisted": False,
            "diagnosis_used_for_same_run_forward_routing_or_prediction_selection": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "benchmark_external_quality_gate_design": True,
            "public_exact220_or_other_benchmark_launch": False,
            "retry_resume_selective_rerun_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    exact = copied.get("exact_transitions") or {}
    validity = copied.get("validity_transitions") or {}
    exposure = copied.get("mechanism_exposure") or {}
    if (
        copied.get("role")
        != "v24965_v24954_v24964_postfreeze_replication_diagnosis"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("paired_task_count") != 220
        or sum(int(exact.get(name, -999)) for name in exact) != 220
        or sum(int(validity.get(name, -999)) for name in validity) != 220
        or set(exposure) != set(ARMS)
        or any(exposure[name].get("valid_receipts") != 220 for name in ARMS)
        or copied.get("diagnosis", {}).get(
            "algorithmic_gain_attributable_to_partial_signature"
        )
        is not False
        or copied.get("diagnosis", {}).get("public_exact220_successor_authorized")
        is not False
        or copied.get("source_policy", {}).get(
            "question_prediction_page_gold_category_question_type_split_or_per_task_score_persisted"
        )
        is not False
        or copied.get("authorization", {}).get(
            "public_exact220_or_other_benchmark_launch"
        )
        is not False
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.49.65 diagnosis result drifted")
    return copied


def build_audit(result: Mapping[str, Any], *, now: int | None = None) -> dict[str, Any]:
    result = validate_result(result)
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
    checks = {
        "result_valid": True,
        "paired_partition_exact220": sum(result["exact_transitions"].values()) == 220,
        "validity_partition_exact220": sum(result["validity_transitions"].values())
        == 220,
        "all_projection_receipts_valid": all(
            result["mechanism_exposure"][name]["valid_receipts"] == 220
            for name in ARMS
        ),
        "no_per_task_or_content_payload": all(
            token not in serialized
            for token in (
                '"opaque_id"',
                '"instance_id"',
                '"question"',
                '"prediction"',
                '"page"',
                '"gold"',
                '"category"',
                '"question_type"',
                '"per_task"',
            )
        ),
        "no_network_or_evaluator_effect": result["source_policy"][
            "network_model_search_fetch_or_evaluator_called"
        ]
        is False,
        "no_public_launch_authority": result["authorization"][
            "public_exact220_or_other_benchmark_launch"
        ]
        is False,
        "algorithmic_attribution_rejected": result["diagnosis"][
            "algorithmic_gain_attributable_to_partial_signature"
        ]
        is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24965_v24954_v24964_replication_diagnosis_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(ROOT / RESULT)
        if (ROOT / RESULT).is_file()
        else payload_sha256(result),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "benchmark_external_quality_gate_design": not findings,
            "public_exact220_or_other_benchmark_launch": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role")
        != "v24965_v24954_v24964_replication_diagnosis_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization", {}).get(
            "public_exact220_or_other_benchmark_launch"
        )
        is not False
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.65 diagnosis audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("run", "audit"))
    args = parser.parse_args()
    _clean_pushed()
    if args.command == "run":
        if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (RESULT, AUDIT)):
            raise RuntimeError("V2.49.65 diagnosis surface is not pristine")
        value = build_result()
        publish_new(ROOT / RESULT, value)
        output = {"path": str(RESULT), "diagnosis": value["diagnosis"]}
    else:
        if (ROOT / AUDIT).exists() or (ROOT / AUDIT).is_symlink():
            raise RuntimeError("V2.49.65 audit surface is not pristine")
        value = build_audit(_read(RESULT))
        publish_new(ROOT / AUDIT, value)
        output = {"path": str(AUDIT), "audit_valid": value["audit_valid"]}
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
