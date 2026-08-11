#!/usr/bin/env python3
"""Aggregate-only strategy diagnosis for three frozen exact-220 runs.

V2.50.64 compares only already-frozen content-free aggregate receipts and
all-220 aggregate result metrics.  It never opens a task, question, query,
URL, page, prediction, evaluator row, gold value, benchmark category, split,
or per-task score.  In particular, no task identifier is materialized and no
cross-run per-task join is possible.

The output is a strategy-level diagnosis, not a benchmark transformation.  It
performs no network, model, search, fetch, evaluator, or benchmark effect and
does not authorize a new external or exact-220 run.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.diagnose_v25063_three_run_output_structure import (
    selected_top_level_fields,
)


DATE = "20260811"
OUTPUT = Path(f"results/v25064_three_run_strategy_diagnosis_v1_{DATE}.json")
SOURCE = Path("scripts/diagnose_v25064_three_run_strategy.py")
TEST = Path("tests/test_diagnose_v25064_three_run_strategy.py")

RUNS = {
    "v24857": {
        "forward": Path("results/v24857_pacing_aware_exact220_forward_result_v1_20260808.json"),
        "result": Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json"),
        "postaudit": Path("results/v24857_pacing_aware_exact220_postresult_audit_v1_20260808.json"),
    },
    "v25030": {
        "forward": Path("results/v25030_evidence_conditioned_exact220_forward_result_v1_20260810.json"),
        "summary": Path("outputs/v25030_evidence_conditioned_exact220_v1_20260810/run_summary.json"),
        "receipts": Path("outputs/v25030_evidence_conditioned_exact220_v1_20260810/content_free_task_receipts.jsonl"),
        "result": Path("results/v25030_evidence_conditioned_exact220_result_v1_20260810.json"),
        "postaudit": Path("results/v25030_evidence_conditioned_exact220_postresult_audit_v1_20260810.json"),
    },
    "v25057": {
        "forward": Path("results/v25057_page_self_exact220_forward_result_r2_20260811.json"),
        "summary": Path("outputs/v25057_page_self_exact220_r2_20260811/run_summary.json"),
        "receipts": Path("outputs/v25057_page_self_exact220_r2_20260811/content_free_task_receipts.jsonl"),
        "result": Path("results/v25057_page_self_exact220_result_r2_20260811.json"),
        "postaudit": Path("results/v25057_page_self_exact220_postresult_audit_r2_20260811.json"),
    },
}

EXPECTED_SHA256 = {
    "v24857": {
        "forward": "1b03564da3dae00bbbfb75e1fd68f425e2fd12c40eac615b6a69558040680581",
        "result": "a9e51c5c479a79e46f74574dac905bc607032be501b8a21a696106172f59f1d9",
        "postaudit": "cf49f952533656d805ca13e807689ea1cd07215553b3f3f9b2dbbf11c115ca20",
    },
    "v25030": {
        "forward": "0f8e65e1799b0ed1470dfed788334ba1a2046f54360288f7c78006b0923a8a0d",
        "summary": "7ca392d80059e286a912cf8d585a08a016e63e40464ca24641c02eeda25d9435",
        "receipts": "f823c3bc10f7a72c0892355087092aed7434f16f82f29689fdd34ba97c784b23",
        "result": "2d5aa05c1005b79a33bcafe4a2d16cb614df67e2091006de9716ae75cc1703b6",
        "postaudit": "ebae2aeb6e2a0c3b3abf0552891f6f4e289e7ae94330d97ddf549209acad21d9",
    },
    "v25057": {
        "forward": "b1a074983eb4313046859b87c83c7cdd1a3369b18e73337af221fb03eb928e7b",
        "summary": "a653d4dc4147669971f8ac21b3b1c33e0c6d0c6903e6ddaebe1c9b31671b0202",
        "receipts": "c24f6f0c17ad87414d9e42936baf26155010d8db34a51909dc32ba249555cf37",
        "result": "f62eb33e2a95585c6342dc2de9c227e72cfa2c6a48417379e00456748a9456f1",
        "postaudit": "8f83db539b8bc52e8ab08cef0406d7446c0e706f664273d929e8e2153a707f16",
    },
}

FORWARD_FIELDS = frozenset(
    {
        "selected",
        "terminal_predictions",
        "model_generated_tables",
        "fallback_tables",
        "forward_wall_seconds",
        "system_total_tokens",
        "official_evaluator_called",
    }
)
RESULT_FIELDS = frozenset({"selected", "metrics", "efficiency", "claims"})
POSTAUDIT_FIELDS = frozenset({"audit_valid", "findings"})
SUMMARY_FIELDS = frozenset(
    {
        "selected",
        "physical_query_count",
        "physical_fetch_count",
        "usable_page_count",
        "evidence_characters",
        "model_logical_call_count",
        "model_provider_request_count",
        "model_provider_attempt_count",
        "refinement_attempted_tasks",
        "refinement_applied_tasks",
        "legacy_second_wave_handoff_tasks",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "official_evaluator_called",
    }
)
V25057_SUMMARY_FIELDS = SUMMARY_FIELDS | frozenset({"page_self_projection"})
RECEIPT_FIELDS = frozenset(
    {
        "first_wave_receipt",
        "second_wave_receipt",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
    }
)
WAVE_FIELDS = frozenset(
    {
        "discovered_records",
        "admissible_records",
        "retained_records",
        "stable_first_seen_selection_without_content_score_or_metadata",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.50.64 expected ordinary repository file")
    return path


def sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _selected_file(relative: Path, fields: frozenset[str]) -> dict[str, Any]:
    return selected_top_level_fields(
        _ordinary(relative).read_text(encoding="utf-8"), fields
    )


def _parents() -> dict[str, dict[str, str]]:
    observed = {
        run: {name: sha256(path) for name, path in paths.items()}
        for run, paths in RUNS.items()
    }
    if observed != EXPECTED_SHA256:
        raise RuntimeError("V2.50.64 frozen parent hash drifted")
    for run, paths in RUNS.items():
        post = _selected_file(paths["postaudit"], POSTAUDIT_FIELDS)
        if post != {"audit_valid": True, "findings": []}:
            raise RuntimeError(f"V2.50.64 {run} parent audit drifted")
    return observed


def _bounded_nonnegative(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"V2.50.64 invalid {name}")
    return value


def _wave_counts(receipts: Path) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    rows = 0
    for line in _ordinary(receipts).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        selected = selected_top_level_fields(line, RECEIPT_FIELDS)
        if (
            selected[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
            is not False
            or selected["entropy_or_information_gain_assigns_signed_credit"] is not False
        ):
            raise RuntimeError("V2.50.64 receipt privilege drifted")
        rows += 1
        for phase in ("first_wave_receipt", "second_wave_receipt"):
            wave = selected[phase]
            if not isinstance(wave, dict) or not WAVE_FIELDS.issubset(wave):
                raise RuntimeError("V2.50.64 wave receipt schema drifted")
            if (
                wave[
                    "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
                ]
                is not False
                or wave["entropy_or_information_gain_assigns_signed_credit"] is not False
                or wave["stable_first_seen_selection_without_content_score_or_metadata"]
                is not True
            ):
                raise RuntimeError("V2.50.64 wave policy drifted")
            for name in ("discovered_records", "admissible_records", "retained_records"):
                totals[name] += _bounded_nonnegative(wave[name], name=name)
    if rows != 220:
        raise RuntimeError("V2.50.64 receipt denominator drifted")
    return {
        "task_receipts": rows,
        "discovered_records": totals["discovered_records"],
        "admissible_records": totals["admissible_records"],
        "retained_records": totals["retained_records"],
        "selection_policy": "stable_first_seen_without_content_score_or_metadata",
    }


def _run(run: str) -> dict[str, Any]:
    paths = RUNS[run]
    forward = _selected_file(paths["forward"], FORWARD_FIELDS)
    result = _selected_file(paths["result"], RESULT_FIELDS)
    metrics = dict(result["metrics"]["all_220"])
    efficiency = dict(result["efficiency"])
    if (
        forward["selected"] != 220
        or forward["terminal_predictions"] != 220
        or result["selected"] != 220
        or metrics.get("selected") != 220
        or forward["official_evaluator_called"] is not False
        or result["claims"].get("sota") is not False
    ):
        raise RuntimeError("V2.50.64 frozen aggregate barrier drifted")
    base: dict[str, Any] = {
        "selected": 220,
        "terminal_predictions": 220,
        "whole_table_successes": int(metrics["whole_table_successes"]),
        "quality_composite": float(metrics["quality_composite"]),
        "entity_acc": float(metrics["entity_acc"]),
        "f1_by_row": float(metrics["f1_by_row"]),
        "f1_by_item": float(metrics["f1_by_item"]),
        "column_f1": float(metrics["column_f1"]),
        "evaluator_valid": int(metrics["evaluator_valid"]),
        "evaluator_error_as_zero": int(metrics["evaluator_invalid_or_not_run"]),
        "model_generated_tables": int(forward["model_generated_tables"]),
        "fallback_tables": int(forward["fallback_tables"]),
        "system_total_tokens": int(forward["system_total_tokens"]),
        "forward_wall_seconds": float(efficiency["forward_wall_seconds"]),
    }
    if run == "v24857":
        raw = selected_top_level_fields(
            _ordinary(paths["forward"]).read_text(encoding="utf-8"),
            frozenset({"fixed_full_budget_control_totals"}),
        )["fixed_full_budget_control_totals"]
        base["retrieval"] = {
            "physical_query_count": int(raw["total_queries_executed"]),
            "physical_fetch_count": int(raw["total_fetches_attempted"]),
            "second_wave_tasks": int(raw["second_wave_executed_tasks"]),
            "usable_page_count": None,
            "evidence_characters": None,
            "model_logical_call_count": None,
            "refinement_attempted_tasks": 0,
            "refinement_applied_tasks": 0,
            "record_binding_receipt_available": False,
            "record_binding_counts": None,
        }
    else:
        summary = _selected_file(
            paths["summary"],
            V25057_SUMMARY_FIELDS if run == "v25057" else SUMMARY_FIELDS,
        )
        if (
            summary["selected"] != 220
            or summary[
                "mapping_gold_category_question_type_split_evaluator_score_reward_read"
            ]
            is not False
            or summary["entropy_or_information_gain_assigns_signed_credit"] is not False
            or summary["official_evaluator_called"] is not False
        ):
            raise RuntimeError("V2.50.64 run summary privilege drifted")
        record_counts = _wave_counts(paths["receipts"])
        base["retrieval"] = {
            "physical_query_count": int(summary["physical_query_count"]),
            "physical_fetch_count": int(summary["physical_fetch_count"]),
            "second_wave_tasks": 220,
            "usable_page_count": int(summary["usable_page_count"]),
            "evidence_characters": int(summary["evidence_characters"]),
            "model_logical_call_count": int(summary["model_logical_call_count"]),
            "refinement_attempted_tasks": int(summary["refinement_attempted_tasks"]),
            "refinement_applied_tasks": int(summary["refinement_applied_tasks"]),
            "record_binding_receipt_available": True,
            "record_binding_counts": record_counts,
        }
        if run == "v25057":
            projection = dict(summary["page_self_projection"])
            expected = {
                "projected_pages",
                "characters_beyond_5k_prefix",
                "mechanism_exposed_pages",
                "changed_evidence_pages",
                "exact_parent_prefix_handoff_pages",
                "positive_signed_credit_count",
            }
            if set(projection) != expected:
                raise RuntimeError("V2.50.64 page-self aggregate schema drifted")
            base["page_self_projection"] = projection
    return base


def _comparison(candidate: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "whole_table_success_delta": candidate["whole_table_successes"]
        - baseline["whole_table_successes"],
        "quality_composite_delta": candidate["quality_composite"]
        - baseline["quality_composite"],
        "system_total_token_ratio": candidate["system_total_tokens"]
        / baseline["system_total_tokens"],
        "forward_wall_ratio": candidate["forward_wall_seconds"]
        / baseline["forward_wall_seconds"],
        "query_ratio": candidate["retrieval"]["physical_query_count"]
        / baseline["retrieval"]["physical_query_count"],
        "fetch_ratio": candidate["retrieval"]["physical_fetch_count"]
        / baseline["retrieval"]["physical_fetch_count"],
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    runs = {name: _run(name) for name in RUNS}
    comparisons = {
        "v25030_minus_v24857": _comparison(runs["v25030"], runs["v24857"]),
        "v25057_minus_v24857": _comparison(runs["v25057"], runs["v24857"]),
        "v25057_minus_v25030": _comparison(runs["v25057"], runs["v25030"]),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25064_three_run_content_free_strategy_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "three_frozen_exact220_strategy_aggregates_audited",
        "parents": _parents(),
        "fixed_denominator": {"runs": 3, "tasks_per_run": 220},
        "runs": runs,
        "comparisons": comparisons,
        "diagnosis": {
            "more_queries_or_fetches_established_as_quality_improvement": False,
            "evidence_conditioned_query_refinement_established_as_quality_improvement": False,
            "deterministic_record_binding_naturally_engaged_in_v25030_or_v25057": False,
            "v25057_page_self_treatment_naturally_engaged": False,
            "record_binding_or_grounded_synthesis_remains_untested_at_natural_reach": True,
            "next_candidate_reallocates_existing_model_call_to_record_proposal_and_deterministic_quote_verification": True,
            "next_candidate_must_not_increase_query_fetch_model_context_token_or_wall_caps": True,
            "next_candidate_must_preserve_unknown_instead_of_deleting_generated_rows": True,
            "entropy_or_information_gain_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "top_level_fields_decoded": {
                "forward": sorted(FORWARD_FIELDS),
                "result": sorted(RESULT_FIELDS),
                "postaudit": sorted(POSTAUDIT_FIELDS),
                "summary": sorted(SUMMARY_FIELDS),
                "v25057_summary_additional": ["page_self_projection"],
                "receipt": sorted(RECEIPT_FIELDS),
            },
            "only_content_free_wave_count_fields_used": sorted(WAVE_FIELDS),
            "task_question_query_url_page_prediction_evaluator_row_gold_category_split_or_per_task_score_decoded": False,
            "task_identifier_materialized_or_cross_run_per_task_joined": False,
            "network_model_search_fetch_evaluator_benchmark_or_credential_accessed": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "authorization": {
            "source_record_binding_build_design": True,
            "fresh_external_protocol_publication": False,
            "fresh_external_launch": False,
            "new_exact220_launch": False,
            "retry_resume_or_selective_rerun": False,
            "postprocessor_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    runs = copied.get("runs") or {}
    comparisons = copied.get("comparisons") or {}
    diagnosis = copied.get("diagnosis") or {}
    policy = copied.get("content_policy") or {}
    authorization = copied.get("authorization") or {}
    expected_scores = {
        "v24857": (9, 0.45724897824812605, 3_781_060, 0),
        "v25030": (7, 0.45029083584190965, 13_973_126, 5),
        "v25057": (6, 0.4499596032520462, 14_302_160, 6),
    }
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "status",
            "parents",
            "fixed_denominator",
            "runs",
            "comparisons",
            "diagnosis",
            "content_policy",
            "authorization",
            "diagnosis_payload_sha256",
        }
        or copied.get("role") != "v25064_three_run_content_free_strategy_diagnosis"
        or copied.get("parents") != EXPECTED_SHA256
        or copied.get("fixed_denominator") != {"runs": 3, "tasks_per_run": 220}
        or set(runs) != set(RUNS)
        or any(
            (
                runs[name].get("whole_table_successes"),
                runs[name].get("quality_composite"),
                runs[name].get("system_total_tokens"),
                runs[name].get("fallback_tables"),
            )
            != expected
            for name, expected in expected_scores.items()
        )
        or runs["v25030"]["retrieval"]["record_binding_counts"]["retained_records"] != 0
        or runs["v25057"]["retrieval"]["record_binding_counts"]["retained_records"] != 0
        or runs["v25057"]["page_self_projection"]["mechanism_exposed_pages"] != 0
        or runs["v25057"]["page_self_projection"]["changed_evidence_pages"] != 0
        or comparisons["v25030_minus_v24857"]["whole_table_success_delta"] != -2
        or comparisons["v25057_minus_v24857"]["whole_table_success_delta"] != -3
        or comparisons["v25030_minus_v24857"]["quality_composite_delta"] >= 0
        or comparisons["v25057_minus_v24857"]["quality_composite_delta"] >= 0
        or comparisons["v25030_minus_v24857"]["system_total_token_ratio"] <= 3.0
        or comparisons["v25057_minus_v24857"]["system_total_token_ratio"] <= 3.0
        or diagnosis.get("more_queries_or_fetches_established_as_quality_improvement") is not False
        or diagnosis.get("record_binding_or_grounded_synthesis_remains_untested_at_natural_reach") is not True
        or diagnosis.get("next_candidate_reallocates_existing_model_call_to_record_proposal_and_deterministic_quote_verification") is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or policy.get("task_question_query_url_page_prediction_evaluator_row_gold_category_split_or_per_task_score_decoded") is not False
        or policy.get("task_identifier_materialized_or_cross_run_per_task_joined") is not False
        or policy.get("network_model_search_fetch_evaluator_benchmark_or_credential_accessed") is not False
        or authorization.get("source_record_binding_build_design") is not True
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "source_record_binding_build_design"
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.64 strategy diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    payload = (json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V2.50.64 publication made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("diagnose",))
    parser.parse_args()
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
