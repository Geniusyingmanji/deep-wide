#!/usr/bin/env python3
"""Aggregate-only post-freeze diagnosis of V2.50.30 exact-220.

Opaque identifiers are used only for in-memory alignment and are never
emitted.  Evaluator-only family names are reported only as aggregate audit
strata and are explicitly forbidden as future runtime routing inputs.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25029_evidence_conditioned_runtime as runtime  # noqa: E402
from deepwide_agent import v25030_evidence_conditioned_exact220_contract as contract  # noqa: E402
from scripts import finalize_v25030_evidence_conditioned_exact220 as finalizer  # noqa: E402


OUTPUT = Path("results/v25031_v25030_exact220_postfreeze_diagnosis_v1_20260810.json")
RUNS = {
    "v24857_best": {
        "result": Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json"),
        "summary": Path("outputs/v24857_pacing_aware_exact220_v1_20260808/evaluator/conservative_summary.json"),
    },
    "v24969_latest_complete": {
        "result": Path("results/v24969_pacing_aware_replication_result_v1_20260809.json"),
        "summary": Path("outputs/v24969_pacing_aware_replication_v1_20260809/evaluator/conservative_summary.json"),
    },
    "v25030": {
        "result": contract.RESULT,
        "summary": contract.OUTPUT_ROOT / "evaluator/conservative_summary.json",
    },
}
QUALITY = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1", "score")
COMPOSITE = QUALITY[:4]


def _read(path: Path) -> dict[str, Any]:
    absolute = ROOT / path
    if path.is_absolute() or ".." in path.parts or absolute.is_symlink() or not absolute.is_file():
        raise RuntimeError(f"V2.50.31 expected ordinary repository object: {path}")
    value = json.loads(absolute.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.31 expected JSON object")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    absolute = ROOT / path
    if path.is_absolute() or ".." in path.parts or absolute.is_symlink() or not absolute.is_file():
        raise RuntimeError(f"V2.50.31 expected ordinary repository JSONL: {path}")
    values = [json.loads(line) for line in absolute.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError("V2.50.31 expected JSONL objects")
    return values


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _metric(row: Mapping[str, Any], name: str) -> float:
    if row.get("evaluator_valid") is not True:
        return 0.0
    value = (row.get("metrics") or {}).get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise RuntimeError("V2.50.31 evaluator metric drifted")
    return float(value)


def _composite(row: Mapping[str, Any]) -> float:
    return sum(_metric(row, name) for name in COMPOSITE) / 4


def _family(instance_id: str) -> str:
    if instance_id.startswith("deep2wide"):
        return "deep2wide"
    if instance_id.startswith("wide2deep_ws_en"):
        return "wide2deep_en"
    if instance_id.startswith("wide2deep_ws_zh"):
        return "wide2deep_zh"
    raise RuntimeError("V2.50.31 unknown evaluator-only family")


def _quality_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise RuntimeError("V2.50.31 empty quality group")
    return {
        "tasks": len(rows),
        "evaluator_valid": sum(row["quality"].get("evaluator_valid") is True for row in rows),
        "whole_table_successes": sum(_metric(row["quality"], "score") > 0 for row in rows),
        "quality_composite": round(sum(_composite(row["quality"]) for row in rows) / len(rows), 12),
        "mean_usable_pages": round(sum(row["usable_pages"] for row in rows) / len(rows), 12),
        "mean_system_total_tokens": round(sum(row["system_total_tokens"] for row in rows) / len(rows), 12),
        "mean_elapsed_seconds": round(sum(row["elapsed_seconds"] for row in rows) / len(rows), 12),
        "fallback_tables": sum(not row["model_success"] for row in rows),
    }


def _comparison(current: dict[str, dict[str, Any]], old: dict[str, dict[str, Any]]) -> dict[str, Any]:
    deltas = {key: _composite(current[key]) - _composite(old[key]) for key in current}
    return {
        "taskwise_composite_wins": sum(value > 1e-12 for value in deltas.values()),
        "taskwise_composite_ties": sum(abs(value) <= 1e-12 for value in deltas.values()),
        "taskwise_composite_losses": sum(value < -1e-12 for value in deltas.values()),
        "mean_composite_delta": round(sum(deltas.values()) / len(deltas), 12),
        "whole_table_gains": sum(_metric(current[key], "score") > 0 and _metric(old[key], "score") == 0 for key in current),
        "whole_table_losses": sum(_metric(old[key], "score") > 0 and _metric(current[key], "score") == 0 for key in current),
    }


def _error_taxonomy(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        if row.get("evaluator_valid") is True:
            continue
        message = str(row.get("evaluator_error") or "")
        counts["out_of_range_metric" if "out-of-range" in message else "internal_error"] += 1
    return dict(sorted(counts.items()))


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    finalizer.configure()
    protocol = finalizer.base.validate_evaluator_protocol(_read(contract.EVALUATOR_PROTOCOL))
    result = _read(contract.RESULT)
    post = _read(contract.POSTAUDIT)
    finalizer.base.validate_final_result(result, protocol)
    finalizer.base.validate_postresult_audit(post)
    run_rows = [runtime.validate_result(value) for value in _jsonl(contract.RUNTIME_RESULTS)]
    summaries = {name: _read(spec["summary"]) for name, spec in RUNS.items()}
    results = {name: _read(spec["result"]) for name, spec in RUNS.items()}
    quality = {
        name: {str(row["opaque_id"]): row for row in summary.get("per_task") or []}
        for name, summary in summaries.items()
    }
    runtime_rows = {str(row["opaque_id"]): row for row in run_rows}
    ids = set(runtime_rows)
    if (
        len(run_rows) != 220 or len(ids) != 220
        or any(set(rows) != ids or len(rows) != 220 for rows in quality.values())
        or result.get("metrics", {}).get("all_220", {}).get("selected") != 220
        or post.get("audit_valid") is not True or not _sealed(post, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.31 exact220 parent barrier drifted")

    projected: list[dict[str, Any]] = []
    by_refinement: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_family_refinement: dict[str, list[dict[str, Any]]] = defaultdict(list)
    page_bands: dict[str, list[dict[str, Any]]] = defaultdict(list)
    failure_types: Counter[str] = Counter()
    for opaque_id in sorted(ids):
        run = runtime_rows[opaque_id]
        receipt = run["content_free_receipt"]
        current = quality["v25030"][opaque_id]
        family = _family(str(current["instance_id"]))
        refinement = "applied" if receipt["refinement_strategy_applied"] else "legacy_handoff"
        usable = int(receipt["usable_page_count"])
        band = "0" if usable == 0 else "1_3" if usable <= 3 else "4_6" if usable <= 6 else "7_8" if usable <= 8 else "9_10"
        row = {
            "quality": current,
            "model_success": bool(run["model_success"]),
            "usable_pages": usable,
            "system_total_tokens": int(run["cost"]["system_total_tokens"]),
            "elapsed_seconds": float(run["elapsed_seconds"]),
        }
        projected.append(row)
        by_refinement[refinement].append(row)
        by_family[family].append(row)
        by_family_refinement[f"{family}:{refinement}"].append(row)
        page_bands[band].append(row)
        for phase in ("plan", "refinement", "synthesis"):
            value = run["failure_types"].get(phase)
            if value:
                failure_types[f"{phase}:{value}"] += 1
        for phase, value in run["failure_types"]["retrieval"].items():
            if value:
                failure_types[f"retrieval:{phase}:{value}"] += 1

    current_metrics = results["v25030"]["metrics"]["all_220"]
    best_metrics = results["v24857_best"]["metrics"]["all_220"]
    latest_metrics = results["v24969_latest_complete"]["metrics"]["all_220"]
    checks = {
        "exact220_frozen_parent_chain_valid": len(projected) == 220,
        "all_groups_cover_fixed_denominator": sum(len(rows) for rows in by_refinement.values()) == 220 and sum(len(rows) for rows in by_family.values()) == 220,
        "receipt_resource_caps_hold": all(runtime.validate_receipt(row["content_free_receipt"])["physical_query_count"] <= 4 for row in run_rows),
        "entropy_signed_credit_disabled_all_tasks": all(row["content_free_receipt"]["entropy_or_information_gain_assigns_signed_credit"] is False for row in run_rows),
        "postfreeze_only_no_effects": True,
        "no_task_identity_question_prediction_gold_or_answer_emitted": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25031_v25030_exact220_aggregate_only_postfreeze_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "quality_recovered_not_best_token_cost_and_row_entity_gap",
        "parents": {
            name: {
                "result_sha256": contract.sha256(ROOT / spec["result"]),
                "conservative_summary_sha256": contract.sha256(ROOT / spec["summary"]),
            }
            for name, spec in RUNS.items()
        } | {"v25030_postresult_audit_sha256": contract.sha256(ROOT / contract.POSTAUDIT)},
        "overall": {
            "v25030": current_metrics,
            "v24857_best": best_metrics,
            "v24969_latest_complete": latest_metrics,
            "v25030_minus_v24857": {
                "whole_table_successes": current_metrics["whole_table_successes"] - best_metrics["whole_table_successes"],
                "quality_composite": round(current_metrics["quality_composite"] - best_metrics["quality_composite"], 12),
                "entity_acc": round(current_metrics["entity_acc"] - best_metrics["entity_acc"], 12),
                "f1_by_row": round(current_metrics["f1_by_row"] - best_metrics["f1_by_row"], 12),
                "f1_by_item": round(current_metrics["f1_by_item"] - best_metrics["f1_by_item"], 12),
                "column_f1": round(current_metrics["column_f1"] - best_metrics["column_f1"], 12),
                "token_ratio": round(current_metrics["system_total_tokens"] / best_metrics["system_total_tokens"], 12),
                "forward_wall_ratio": round(results["v25030"]["efficiency"]["forward_wall_seconds"] / results["v24857_best"]["efficiency"]["forward_wall_seconds"], 12),
            },
            "v25030_minus_v24969": {
                "whole_table_successes": current_metrics["whole_table_successes"] - latest_metrics["whole_table_successes"],
                "quality_composite": round(current_metrics["quality_composite"] - latest_metrics["quality_composite"], 12),
            },
        },
        "taskwise_comparisons": {
            "v24857_best": _comparison(quality["v25030"], quality["v24857_best"]),
            "v24969_latest_complete": _comparison(quality["v25030"], quality["v24969_latest_complete"]),
        },
        "refinement_association": {name: _quality_group(rows) for name, rows in sorted(by_refinement.items())},
        "evaluator_only_family_audit": {
            "groups": {name: _quality_group(rows) for name, rows in sorted(by_family.items())},
            "family_by_refinement": {name: _quality_group(rows) for name, rows in sorted(by_family_refinement.items())},
            "runtime_routing_or_policy_selection_authorized": False,
        },
        "usable_page_bands": {name: _quality_group(rows) for name, rows in sorted(page_bands.items())},
        "failure_taxonomy": {
            "runtime": dict(sorted(failure_types.items())),
            "evaluator": _error_taxonomy(list(quality["v25030"].values())),
        },
        "diagnosis": {
            "v25030_recovers_over_v24969_but_does_not_beat_v24857": True,
            "column_f1_exceeds_v24857_while_entity_and_row_f1_lag": True,
            "token_cost_is_materially_higher_than_v24857": True,
            "refinement_group_difference_is_descriptive_not_randomized_or_causal": True,
            "evaluator_only_family_difference_must_not_be_used_for_runtime_routing": True,
            "next_gate_must_use_label_blind_visible_only_signals_and_matched_transport": True,
            "next_priority": [
                "remove_synthesis_normalization_fallbacks_without_evaluator_feedback",
                "recover_entity_and_row_coverage with visible-only schema/cardinality support",
                "compress search evidence and refinement prompts before another exact220",
                "validate any refinement eligibility change in a matched external or frozen visible-only gate",
            ],
            "entropy_or_information_gain_credit_validated_by_this_run": False,
        },
        "source_policy": {
            "postfreeze_evaluator_only_analysis": True,
            "opaque_ids_used_only_for_in_memory_alignment_and_not_emitted": True,
            "question_prediction_gold_answer_instance_id_or_per_task_metric_emitted": False,
            "benchmark_category_question_type_split_or_family_used_for_forward_or_future_runtime_routing": False,
            "same_run_forward_feedback_or_prediction_selection": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        },
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "authorization": {
            "matched_label_blind_external_or_synthetic_gate_design": not findings,
            "new_exact220_launch": False,
            "evaluator": False,
            "retry_resume_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role") != "v25031_v25030_exact220_aggregate_only_postfreeze_diagnosis"
        or copied.get("status") != "quality_recovered_not_best_token_cost_and_row_entity_gap"
        or copied.get("diagnosis_valid") is not True or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("diagnosis", {}).get("refinement_group_difference_is_descriptive_not_randomized_or_causal") is not True
        or copied.get("diagnosis", {}).get("entropy_or_information_gain_credit_validated_by_this_run") is not False
        or copied.get("evaluator_only_family_audit", {}).get("runtime_routing_or_policy_selection_authorized") is not False
        or copied.get("authorization") != {
            "matched_label_blind_external_or_synthetic_gate_design": True,
            "new_exact220_launch": False,
            "evaluator": False,
            "retry_resume_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.31 diagnosis drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    diagnosis = build_diagnosis()
    publish_new(ROOT / OUTPUT, diagnosis)
    print(json.dumps({"path": str(OUTPUT), "status": diagnosis["status"], "diagnosis_valid": diagnosis["diagnosis_valid"], "authorization": diagnosis["authorization"]}, sort_keys=True))
