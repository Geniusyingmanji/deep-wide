#!/usr/bin/env python3
"""Aggregate-only diagnosis of the complete V2.49.09 exact-220 rollout.

The three compared prediction/evaluator chains are already terminal.  This
script reads private task artifacts only to aggregate content-free counters;
it emits no question, query, URL, page, prediction, task identifier, or
per-task score.  Cross-run differences are descriptive, not causal.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24909_keyless_fixed_budget_exact220_contract as contract  # noqa: E402


DATE = "20260808"
OUTPUT = Path(f"results/v24910_v24909_resource_quality_diagnosis_v1_{DATE}.json")
SELECTED = 220
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")

RUNS: dict[str, dict[str, Any]] = {
    "v24857": {
        "protocol_id": "v24857_same_pass_pacing_aware_fixed_full_budget_exact220_v1",
        "root": Path("outputs/v24857_pacing_aware_exact220_v1_20260808"),
        "result": Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json"),
        "forward": Path("results/v24857_pacing_aware_exact220_forward_audit_v1_20260808.json"),
        "post": Path("results/v24857_pacing_aware_exact220_postresult_audit_v1_20260808.json"),
        "transport": "rate_aware_tavily",
        "policy": "pacing_aware_fixed_full_budget",
    },
    "v24906": {
        "protocol_id": "v24906_stable_keyless_gpt56_exact220_replication_v1",
        "root": Path("outputs/v24906_stable_keyless_exact220_v1_20260808"),
        "result": Path("results/v24906_stable_keyless_exact220_result_v1_20260808.json"),
        "forward": Path("results/v24906_stable_keyless_exact220_forward_audit_v1_20260808.json"),
        "post": Path("results/v24906_stable_keyless_exact220_postresult_audit_v1_20260808.json"),
        "transport": "keyless_gpt56_hosted_search",
        "policy": "legacy_entropy_voc_admission",
    },
    "v24909": {
        "protocol_id": contract.PROTOCOL_ID,
        "root": contract.OUTPUT_ROOT,
        "result": Path("results/v24909_keyless_fixed_budget_exact220_result_v1_20260808.json"),
        "forward": contract.FORWARD_AUDIT,
        "post": Path("results/v24909_keyless_fixed_budget_exact220_postresult_audit_v1_20260808.json"),
        "transport": "keyless_gpt56_hosted_search",
        "policy": "fixed_full_budget_no_entropy",
    },
}


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.49.10 expected ordinary repository file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.10 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_parents() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for name, spec in RUNS.items():
        result = _read(spec["result"])
        forward = _read(spec["forward"])
        post = _read(spec["post"])
        root: Path = spec["root"]
        summary_path = root / "run_summary.json"
        summary = _read(summary_path)
        metrics = (result.get("metrics") or {}).get("all_220") or {}
        if (
            result.get("protocol_id") != spec["protocol_id"]
            or result.get("selected") != SELECTED
            or metrics.get("selected") != SELECTED
            or result.get("status") != "exact220_single_rollout_complete"
            or not _sealed(result, "result_payload_sha256")
            or forward.get("protocol_id") != spec["protocol_id"]
            or forward.get("audit_valid") is not True
            or forward.get("findings") != []
            or not _sealed(forward, "audit_payload_sha256")
            or post.get("protocol_id") != spec["protocol_id"]
            or post.get("audit_valid") is not True
            or post.get("findings") != []
            or not _sealed(post, "audit_payload_sha256")
            or summary.get("selected") != SELECTED
            or summary.get("completed") != SELECTED
        ):
            raise RuntimeError(f"V2.49.10 frozen parent chain drifted: {name}")
        output[name] = {
            "result": result,
            "summary": summary,
            "result_sha256": contract.sha256(ROOT / spec["result"]),
            "forward_audit_sha256": contract.sha256(ROOT / spec["forward"]),
            "postresult_audit_sha256": contract.sha256(ROOT / spec["post"]),
            "run_summary_sha256": contract.sha256(ROOT / summary_path),
        }
    return output


def _number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise RuntimeError(f"V2.49.10 invalid content-free counter: {label}")
    return float(value)


def _task_aggregates(root: Path) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    decisions: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    completion: Counter[str] = Counter()
    for position in range(1, SELECTED + 1):
        envelope = _read(root / "tasks" / f"task_{position:04d}" / "result.json")
        result = envelope.get("result") or {}
        retrieval = result.get("two_wave_retrieval") or {}
        receipt = retrieval.get("receipt") or {}
        controller = receipt.get("controller") or {}
        total = receipt.get("total") or {}
        evidence = result.get("evidence") or {}
        cost = result.get("cost") or {}
        model = cost.get("model") or {}
        search = cost.get("search") or {}
        table = (result.get("telemetry") or {}).get("table") or {}
        timing = result.get("attributed_timing") or {}
        decision = str(controller.get("decision"))
        reason = str(controller.get("reason"))
        kind = str(result.get("completion_kind"))
        if decision not in {"expand", "stop"} or not reason or not kind:
            raise RuntimeError("V2.49.10 task telemetry identity drifted")
        decisions[decision] += 1
        reasons[reason] += 1
        completion[kind] += 1
        fields = {
            "queries_executed": total.get("queries_executed"),
            "fetches_attempted": total.get("fetches_attempted"),
            "usable_pages": total.get("usable_pages"),
            "novel_pages": total.get("novel_pages"),
            "unique_hosts": total.get("unique_hosts"),
            "content_chars": total.get("content_chars"),
            "projected_evidence_chars": evidence.get("projected_chars"),
            "synthesized_rows": table.get("row_count"),
            "unknown_cell_ratio_sum": table.get("unknown_cell_ratio"),
            "model_requests": model.get("requests"),
            "model_input_tokens": model.get("input_tokens"),
            "model_output_tokens": model.get("output_tokens"),
            "model_total_tokens": model.get("total_tokens"),
            "search_calls": search.get("calls"),
            "search_fetch_calls": search.get("fetch_calls"),
            "search_input_tokens": search.get("input_tokens"),
            "search_output_tokens": search.get("output_tokens"),
            "search_total_tokens": search.get("total_tokens"),
            "task_wall_seconds": timing.get("task_wall_seconds"),
        }
        for key, raw in fields.items():
            totals[key] += _number(raw, key)
    if sum(decisions.values()) != SELECTED or sum(completion.values()) != SELECTED:
        raise RuntimeError("V2.49.10 task denominator drifted")
    numeric = {
        name: round(float(value), 6)
        for name, value in sorted(totals.items())
    }
    numeric["mean_usable_pages"] = round(
        numeric["usable_pages"] / SELECTED, 12
    )
    numeric["mean_unique_hosts"] = round(
        numeric["unique_hosts"] / SELECTED, 12
    )
    numeric["mean_projected_evidence_chars"] = round(
        numeric["projected_evidence_chars"] / SELECTED, 12
    )
    numeric["mean_synthesized_rows"] = round(
        numeric["synthesized_rows"] / SELECTED, 12
    )
    numeric["mean_unknown_cell_ratio"] = round(
        numeric.pop("unknown_cell_ratio_sum") / SELECTED, 12
    )
    system_tokens = numeric["model_total_tokens"] + numeric["search_total_tokens"]
    numeric["search_token_share"] = round(
        numeric["search_total_tokens"] / system_tokens if system_tokens else 0.0,
        12,
    )
    return {
        "decision_counts": dict(sorted(decisions.items())),
        "reason_counts": dict(sorted(reasons.items())),
        "completion_kinds": dict(sorted(completion.items())),
        "totals_and_means": numeric,
    }


def _quality(result: Mapping[str, Any]) -> dict[str, Any]:
    metrics = result["metrics"]["all_220"]
    names = (
        "selected", "evaluator_valid", "evaluator_invalid_or_not_run",
        "whole_table_successes", "score", "entity_acc", "f1_by_row",
        "f1_by_item", "column_f1", "quality_composite",
        "model_generated_tables", "fallback_tables", "system_total_tokens",
    )
    return {name: metrics[name] for name in names}


def _delta(after: Mapping[str, Any], before: Mapping[str, Any]) -> dict[str, Any]:
    names = (
        "whole_table_successes", "score", "entity_acc", "f1_by_row",
        "f1_by_item", "column_f1", "quality_composite",
        "evaluator_valid", "fallback_tables", "system_total_tokens",
    )
    return {
        name: round(float(after[name]) - float(before[name]), 12)
        for name in names
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    parents = _validate_parents()
    tasks = {
        name: _task_aggregates(spec["root"]) for name, spec in RUNS.items()
    }
    quality = {
        name: _quality(parents[name]["result"]) for name in RUNS
    }
    v24909 = tasks["v24909"]["totals_and_means"]
    v24906 = tasks["v24906"]["totals_and_means"]
    v24857 = tasks["v24857"]["totals_and_means"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24910_v24909_resource_quality_aggregate_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "fixed_budget_keyless_improves_one_rollout_but_remains_below_pacing_tavily_frontier_and_is_search_token_dominated",
        "parents": {
            name: {
                "protocol_id": RUNS[name]["protocol_id"],
                "result_sha256": parents[name]["result_sha256"],
                "forward_audit_sha256": parents[name]["forward_audit_sha256"],
                "postresult_audit_sha256": parents[name]["postresult_audit_sha256"],
                "run_summary_sha256": parents[name]["run_summary_sha256"],
            }
            for name in RUNS
        },
        "boundary": {
            "all_three_prediction_and_evaluator_chains_terminal_before_diagnosis": True,
            "offline_private_artifacts_used_only_for_content_free_aggregation": True,
            "question_query_url_page_prediction_answer_task_identifier_or_per_task_score_emitted": False,
            "benchmark_category_question_type_mapping_gold_split_or_reward_used": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "cross_run_differences_are_independent_rollout_descriptions_not_causal_effects": True,
            "historical_correctness_or_score_authorized_as_future_runtime_input": False,
        },
        "runs": {
            name: {
                "transport": RUNS[name]["transport"],
                "policy": RUNS[name]["policy"],
                "quality": quality[name],
                "mechanism": tasks[name],
                "forward_wall_seconds": parents[name]["result"]["efficiency"][
                    "forward_wall_seconds"
                ],
            }
            for name in RUNS
        },
        "comparisons": {
            "v24909_minus_v24906": {
                "quality_delta": _delta(quality["v24909"], quality["v24906"]),
                "query_delta": v24909["queries_executed"] - v24906["queries_executed"],
                "fetch_delta": v24909["fetches_attempted"] - v24906["fetches_attempted"],
                "usable_page_delta": v24909["usable_pages"] - v24906["usable_pages"],
                "unique_host_delta": v24909["unique_hosts"] - v24906["unique_hosts"],
                "search_token_delta": v24909["search_total_tokens"] - v24906["search_total_tokens"],
            },
            "v24909_minus_v24857": {
                "quality_delta": _delta(quality["v24909"], quality["v24857"]),
                "query_delta": v24909["queries_executed"] - v24857["queries_executed"],
                "fetch_delta": v24909["fetches_attempted"] - v24857["fetches_attempted"],
                "usable_page_delta": v24909["usable_pages"] - v24857["usable_pages"],
                "unique_host_delta": v24909["unique_hosts"] - v24857["unique_hosts"],
                "search_token_delta": v24909["search_total_tokens"] - v24857["search_total_tokens"],
            },
        },
        "conclusions": {
            "v24909_complete_exact220_valid": True,
            "fixed_budget_keyless_observed_exact_and_composite_above_v24906": (
                quality["v24909"]["whole_table_successes"]
                > quality["v24906"]["whole_table_successes"]
                and quality["v24909"]["quality_composite"]
                > quality["v24906"]["quality_composite"]
            ),
            "v24909_below_v24857_exact_and_composite": (
                quality["v24909"]["whole_table_successes"]
                < quality["v24857"]["whole_table_successes"]
                and quality["v24909"]["quality_composite"]
                < quality["v24857"]["quality_composite"]
            ),
            "v24909_search_tokens_are_majority_of_system_tokens": (
                v24909["search_token_share"] > 0.5
            ),
            "v24909_has_fewer_usable_pages_and_hosts_than_v24857": (
                v24909["usable_pages"] < v24857["usable_pages"]
                and v24909["unique_hosts"] < v24857["unique_hosts"]
            ),
            "more_keyless_search_compute_proven_as_general_quality_cause": False,
            "entropy_or_information_gain_credit_validated": False,
            "current_high_leverage_hypothesis": (
                "query_aware_structure_preserving_evidence_packing_on_stable_pacing_transport"
            ),
        },
        "next_gate": {
            "candidate": "deterministic_query_aware_structure_preserving_evidence_packer",
            "same_retrieved_page_byte_prefix_for_baseline_and_candidate": True,
            "same_question_model_prompt_output_budget_and_renderer": True,
            "no_additional_search_fetch_model_call_or_wall_cap": True,
            "benchmark_external_shared_prefix_quality_gate_required": True,
            "public_exact220_requires_gate_go_and_fresh_preregistration": True,
            "benchmark_score_or_correctness_may_not_route_or_tune_runtime": True,
        },
        "authorization": {
            "query_aware_evidence_packer_build": True,
            "benchmark_external_shared_prefix_gate_design": True,
            "external_gate_launch": False,
            "public_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    checks = {
        "parent_denominators_exact220": all(
            quality[name]["selected"] == SELECTED for name in RUNS
        ),
        "task_telemetry_denominators_exact220": all(
            sum(tasks[name]["decision_counts"].values()) == SELECTED
            for name in RUNS
        ),
        "v24909_exact_is_seven": quality["v24909"]["whole_table_successes"] == 7,
        "v24906_exact_is_four": quality["v24906"]["whole_table_successes"] == 4,
        "v24857_exact_is_nine": quality["v24857"]["whole_table_successes"] == 9,
        "v24909_search_tokens_reconcile": math.isclose(
            v24909["search_total_tokens"], 8_547_691.0, abs_tol=0.0
        ),
        "v24909_query_count_reconciles": v24909["queries_executed"] == 770.0,
        "v24909_fetch_count_reconciles": v24909["fetches_attempted"] == 1897.0,
        "v24857_usable_page_count_reconciles": v24857["usable_pages"] == 1627.0,
        "no_benchmark_launch_authorized": value["authorization"][
            "public_dev64_or_exact220"
        ] is False,
    }
    value["checks"] = checks
    value["findings"] = sorted(name for name, passed in checks.items() if not passed)
    value["diagnosis_valid"] = not value["findings"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if OPAQUE.search(encoded) or SECRET.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.49.10 diagnosis emitted prohibited content")
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate(value, rebuild=False)


def validate(value: Mapping[str, Any], *, rebuild: bool = True) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role") != "v24910_v24909_resource_quality_aggregate_diagnosis"
        or copied.get("status")
        != "fixed_budget_keyless_improves_one_rollout_but_remains_below_pacing_tavily_frontier_and_is_search_token_dominated"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("conclusions", {}).get(
            "more_keyless_search_compute_proven_as_general_quality_cause"
        ) is not False
        or copied.get("boundary", {}).get(
            "historical_correctness_or_score_authorized_as_future_runtime_input"
        ) is not False
        or copied.get("authorization", {}).get("public_dev64_or_exact220")
        is not False
        or copied.get("authorization", {}).get("sota_claim") is not False
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.49.10 diagnosis drifted")
    if rebuild:
        expected = build(now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.49.10 diagnosis is not reproducible")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
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


if __name__ == "__main__":
    report = build()
    publish(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "status": report["status"],
                "diagnosis_valid": report["diagnosis_valid"],
                "authorization": report["authorization"],
            },
            sort_keys=True,
        )
    )
