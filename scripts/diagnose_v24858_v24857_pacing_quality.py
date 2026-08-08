#!/usr/bin/env python3
"""Aggregate-only diagnosis of the complete V2.48.57 exact-220 rollout.

All compared prediction vectors and evaluator outputs were frozen before this
analysis.  Opaque identifiers are used only for in-memory alignment and are
never emitted.  The pacing intervention cohort is descriptive because each
version is an independent search, generation, and judge sample; no historical
cohort or evaluator signal is authorized as a future runtime input.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import sys
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24857_pacing_aware_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24856_pacing_aware_admission import (  # noqa: E402
    validate_receipt as validate_pacing_receipt,
)


DATE = "20260808"
OUTPUT = Path(
    f"results/v24858_v24857_pacing_quality_diagnosis_v1_{DATE}.json"
)
SELECTED = 220
BOOTSTRAP_RESAMPLES = 20_000
QUALITY = ("score", "entity_acc", "f1_by_row", "f1_by_item", "column_f1")
COMPOSITE = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
MECHANISM = (
    "queries_executed",
    "fetches_attempted",
    "usable_pages",
    "novel_pages",
    "unique_hosts",
    "content_chars",
    "wave2_usable_pages",
    "wave2_novel_pages",
    "wave2_new_unique_hosts",
    "wave2_content_chars",
    "projected_chars",
    "synthesized_rows",
    "system_total_tokens",
    "task_wall_seconds",
    "credited_provider_wait_seconds",
    "raw_wave1_elapsed_seconds",
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
INSTANCE = re.compile(r"(?:deep2wide|wide2deep)_[A-Za-z0-9_\-\u4e00-\u9fff]+")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)

RUNS: dict[str, dict[str, Any]] = {
    "v24800": {
        "protocol_id": "v24800_fixed_full_budget_no_entropy_exact220_v1",
        "root": Path("outputs/v24800_exact220_v1_20260807"),
        "result": Path("results/v24800_exact220_result_v1_20260807.json"),
        "forward": Path("results/v24800_exact220_forward_audit_v1_20260807.json"),
        "post": Path("results/v24800_exact220_postresult_audit_v1_20260807.json"),
    },
    "v24850": {
        "protocol_id": "v24850_fresh_v24800_fixed_full_budget_replication_exact220_v1",
        "root": Path("outputs/v24850_v24800_replication_exact220_v1_20260808"),
        "result": Path("results/v24850_v24800_replication_exact220_result_v1_20260808.json"),
        "forward": Path("results/v24850_v24800_replication_exact220_forward_audit_v1_20260808.json"),
        "post": Path("results/v24850_v24800_replication_exact220_postresult_audit_v1_20260808.json"),
    },
    "v24854": {
        "protocol_id": "v24854_rate_aware_fixed_full_budget_exact220_v1",
        "root": Path("outputs/v24854_rate_aware_exact220_v1_20260808"),
        "result": Path("results/v24854_rate_aware_exact220_result_v1_20260808.json"),
        "forward": Path("results/v24854_rate_aware_exact220_forward_audit_v1_20260808.json"),
        "post": Path("results/v24854_rate_aware_exact220_postresult_audit_v1_20260808.json"),
    },
    "v24857": {
        "protocol_id": contract.PROTOCOL_ID,
        "root": contract.OUTPUT_ROOT,
        "result": Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json"),
        "forward": contract.FORWARD_AUDIT,
        "post": Path("results/v24857_pacing_aware_exact220_postresult_audit_v1_20260808.json"),
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
        raise RuntimeError(f"V2.48.58 expected ordinary repository file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.58 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_parents() -> dict[str, Any]:
    output: dict[str, Any] = {}
    for name, spec in RUNS.items():
        result = _read(spec["result"])
        forward = _read(spec["forward"])
        post = _read(spec["post"])
        root: Path = spec["root"]
        summary = root / "run_summary.json"
        evaluation = root / "evaluator/conservative_summary.json"
        if (
            result.get("protocol_id") != spec["protocol_id"]
            or result.get("selected") != SELECTED
            or result.get("failure_as_zero") is not True
            or not _sealed(result, "result_payload_sha256")
            or forward.get("protocol_id") != spec["protocol_id"]
            or forward.get("audit_valid") is not True
            or forward.get("findings") != []
            or not _sealed(forward, "audit_payload_sha256")
            or post.get("protocol_id") != spec["protocol_id"]
            or post.get("audit_valid") is not True
            or post.get("findings") != []
            or not _sealed(post, "audit_payload_sha256")
            or post.get("provenance", {}).get("conservative_summary_sha256")
            != contract.sha256(ROOT / evaluation)
        ):
            raise RuntimeError(f"V2.48.58 frozen parent chain drifted: {name}")
        output[name] = {
            "result": result,
            "summary": _read(summary),
            "result_sha256": contract.sha256(ROOT / spec["result"]),
            "forward_audit_sha256": contract.sha256(ROOT / spec["forward"]),
            "postresult_audit_sha256": contract.sha256(ROOT / spec["post"]),
            "conservative_summary_sha256": contract.sha256(ROOT / evaluation),
            "run_summary_sha256": contract.sha256(ROOT / summary),
        }
    return output


def _metrics(name: str) -> dict[str, dict[str, Any]]:
    root: Path = RUNS[name]["root"]
    rows = _read(root / "evaluator/conservative_summary.json").get("per_task")
    if not isinstance(rows, list) or len(rows) != SELECTED:
        raise RuntimeError("V2.48.58 evaluator denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        opaque_id = row.get("opaque_id") if isinstance(row, Mapping) else None
        metric = row.get("metrics") if isinstance(row, Mapping) else None
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or not isinstance(metric, Mapping)
            or not isinstance(row.get("evaluator_valid"), bool)
            or any(
                isinstance(metric.get(key), bool)
                or not isinstance(metric.get(key), (int, float))
                or not math.isfinite(float(metric[key]))
                for key in QUALITY
            )
        ):
            raise RuntimeError("V2.48.58 evaluator row drifted")
        output[opaque_id] = {
            "valid": row["evaluator_valid"],
            "metrics": {key: float(metric[key]) for key in QUALITY},
        }
    return output


def _candidate_tasks() -> dict[str, dict[str, Any]]:
    root = contract.OUTPUT_ROOT
    output: dict[str, dict[str, Any]] = {}
    for position in range(1, SELECTED + 1):
        directory = root / "tasks" / f"task_{position:04d}"
        envelope = _read(directory / "result.json")
        result = envelope.get("result") or {}
        opaque_id = result.get("opaque_id")
        retrieval = result.get("two_wave_retrieval") or {}
        receipt = retrieval.get("receipt") or {}
        controller = receipt.get("controller") or {}
        total = receipt.get("total") or {}
        wave2 = receipt.get("wave2") or {}
        evidence = result.get("evidence") or {}
        table = (result.get("telemetry") or {}).get("table") or {}
        cost = result.get("cost") or {}
        timing = result.get("attributed_timing") or {}
        pacing = validate_pacing_receipt(
            _read(directory / contract.PACING_RECEIPT_NAME)
        )
        values = {
            "queries_executed": total.get("queries_executed"),
            "fetches_attempted": total.get("fetches_attempted"),
            "usable_pages": total.get("usable_pages"),
            "novel_pages": total.get("novel_pages"),
            "unique_hosts": total.get("unique_hosts"),
            "content_chars": total.get("content_chars"),
            "wave2_usable_pages": wave2.get("usable_pages"),
            "wave2_novel_pages": wave2.get("novel_pages"),
            "wave2_new_unique_hosts": wave2.get("new_unique_hosts"),
            "wave2_content_chars": wave2.get("content_chars"),
            "projected_chars": evidence.get("projected_chars"),
            "synthesized_rows": table.get("row_count"),
            "system_total_tokens": cost.get("system_total_tokens"),
            "task_wall_seconds": timing.get("task_wall_seconds"),
            "credited_provider_wait_seconds": pacing.get(
                "credited_provider_wait_seconds"
            ),
            "raw_wave1_elapsed_seconds": pacing.get("raw_wave1_elapsed_seconds"),
        }
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or retrieval.get("status") != "completed"
            or pacing["pacing_aware_decision"] != controller.get("decision")
            or pacing["pacing_aware_reason"] != controller.get("reason")
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0
                for value in values.values()
            )
        ):
            raise RuntimeError("V2.48.58 candidate mechanism row drifted")
        output[opaque_id] = {
            **{key: float(values[key]) for key in MECHANISM},
            "decision_changed": bool(pacing["decision_changed"]),
            "legacy_reason": str(pacing["legacy_reason"]),
            "pacing_reason": str(pacing["pacing_aware_reason"]),
        }
    return output


def _aggregate(
    ids: Iterable[str], metrics: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    selected = sorted(ids)
    if not selected:
        raise RuntimeError("V2.48.58 cannot aggregate an empty cohort")
    values = {
        key: sum(metrics[item]["metrics"][key] for item in selected)
        / len(selected)
        for key in QUALITY
    }
    values["quality_composite"] = sum(values[key] for key in COMPOSITE) / 4
    return {
        "n": len(selected),
        "evaluator_valid": sum(metrics[item]["valid"] for item in selected),
        "whole_table_successes": sum(
            metrics[item]["metrics"]["score"] > 0 for item in selected
        ),
        "metrics": values,
    }


def _mechanism_mean(
    ids: Iterable[str], tasks: Mapping[str, Mapping[str, Any]]
) -> dict[str, float]:
    selected = sorted(ids)
    return {
        key: sum(float(tasks[item][key]) for item in selected) / len(selected)
        for key in MECHANISM
    }


def _bootstrap(
    ids: Iterable[str],
    before: Mapping[str, Mapping[str, Any]],
    after: Mapping[str, Mapping[str, Any]],
    *,
    seed: int,
) -> dict[str, Any]:
    selected = sorted(ids)
    deltas = [
        sum(
            after[item]["metrics"][key] - before[item]["metrics"][key]
            for key in COMPOSITE
        )
        / 4
        for item in selected
    ]
    rng = random.Random(seed)
    means = sorted(
        sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas)
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    lower = means[int(0.025 * BOOTSTRAP_RESAMPLES)]
    upper = means[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]
    return {
        "unit": "task_cluster",
        "seed": seed,
        "resamples": BOOTSTRAP_RESAMPLES,
        "mean_delta": sum(deltas) / len(deltas),
        "percentile_95_interval": [lower, upper],
        "interval_excludes_zero": lower > 0 or upper < 0,
        "direction_counts": {
            "improved": sum(value > 0 for value in deltas),
            "tied": sum(value == 0 for value in deltas),
            "worsened": sum(value < 0 for value in deltas),
        },
    }


def _exact_test(
    ids: Iterable[str],
    before: Mapping[str, Mapping[str, Any]],
    after: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    selected = sorted(ids)
    gains = sum(
        before[item]["metrics"]["score"] == 0
        and after[item]["metrics"]["score"] > 0
        for item in selected
    )
    losses = sum(
        before[item]["metrics"]["score"] > 0
        and after[item]["metrics"]["score"] == 0
        for item in selected
    )
    discordant = gains + losses
    if discordant:
        tail = sum(
            math.comb(discordant, index)
            for index in range(min(gains, losses) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    else:
        p_value = 1.0
    return {
        "gains": gains,
        "losses": losses,
        "discordant": discordant,
        "exact_two_sided_mcnemar_p": p_value,
        "significant_at_0_05": p_value < 0.05,
    }


def _pair(
    ids: set[str],
    before_name: str,
    metrics: Mapping[str, Mapping[str, Mapping[str, Any]]],
    *,
    seed: int,
) -> dict[str, Any]:
    before = _aggregate(ids, metrics[before_name])
    after = _aggregate(ids, metrics["v24857"])
    return {
        "before": before,
        "after": after,
        "delta": {
            "evaluator_valid": after["evaluator_valid"] - before["evaluator_valid"],
            "whole_table_successes": after["whole_table_successes"]
            - before["whole_table_successes"],
            "metrics": {
                key: after["metrics"][key] - before["metrics"][key]
                for key in (*QUALITY, "quality_composite")
            },
        },
        "paired_composite_bootstrap": _bootstrap(
            ids, metrics[before_name], metrics["v24857"], seed=seed
        ),
        "paired_exact_test": _exact_test(
            ids, metrics[before_name], metrics["v24857"]
        ),
    }


def _recorded_complete_rollout_rank() -> dict[str, Any]:
    rows: list[tuple[int, float, str]] = []
    for path in sorted((ROOT / "results").glob("*exact220*result*.json")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            metric = value.get("metrics", {}).get("all_220", {})
            selected = value.get("selected")
            exact = metric.get("whole_table_successes")
            composite = metric.get("quality_composite")
        except (AttributeError, json.JSONDecodeError, OSError):
            continue
        if (
            selected != SELECTED
            or isinstance(exact, bool)
            or not isinstance(exact, int)
            or isinstance(composite, bool)
            or not isinstance(composite, (int, float))
            or not math.isfinite(float(composite))
        ):
            continue
        rows.append((exact, float(composite), path.name))
    target = next(
        (row for row in rows if row[2] == RUNS["v24857"]["result"].name),
        None,
    )
    if target is None:
        raise RuntimeError("V2.48.58 candidate missing from recorded rollouts")
    return {
        "recorded_complete_rollouts": len(rows),
        "candidate_exact_rank": 1
        + sum((exact, composite) > target[:2] for exact, composite, _ in rows),
        "candidate_composite_rank": 1
        + sum(composite > target[1] for _, composite, _ in rows),
        "candidate_is_unique_exact_maximum": sum(
            exact == target[0] for exact, _, _ in rows
        )
        == 1,
        "candidate_is_unique_composite_maximum": sum(
            composite == target[1] for _, composite, _ in rows
        )
        == 1,
        "task_or_result_identifiers_emitted": False,
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    parents = _validate_parents()
    metrics = {name: _metrics(name) for name in RUNS}
    tasks = _candidate_tasks()
    ids = set(metrics["v24857"])
    if any(set(value) != ids for value in (*metrics.values(), tasks)):
        raise RuntimeError("V2.48.58 aligned population drifted")
    changed = {item for item in ids if tasks[item]["decision_changed"]}
    unchanged = ids - changed
    legacy_latency = {
        item for item in ids if tasks[item]["legacy_reason"] == "latency_ceiling"
    }
    residual_latency = {
        item for item in ids if tasks[item]["pacing_reason"] == "latency_ceiling"
    }
    recovered_latency = legacy_latency - residual_latency
    if recovered_latency != changed:
        raise RuntimeError("V2.48.58 decision-change cohort drifted")

    pairwise = {
        f"v24857_minus_{name}": _pair(
            ids, name, metrics, seed=248580 + index
        )
        for index, name in enumerate(("v24800", "v24850", "v24854"))
    }
    changed_pairs = {
        f"v24857_minus_{name}": _pair(
            changed, name, metrics, seed=248590 + index
        )
        for index, name in enumerate(("v24800", "v24850", "v24854"))
    }
    changed_exact = {
        name: _aggregate(changed, metrics[name])["whole_table_successes"]
        for name in RUNS
    }
    run_summary = parents["v24857"]["summary"]
    recorded_rank = _recorded_complete_rollout_rank()
    rate = run_summary["direct_search_totals"]["rate_aware"]
    pacing = run_summary["direct_search_totals"]["pacing_aware_admission"]
    value = {
        "artifact_version": 1,
        "role": "v24858_v24857_pacing_quality_aggregate_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "new_observed_best_but_overall_gain_not_statistically_established_and_exact_gain_not_attributable_to_pacing",
        "parents": {
            name: {
                key: parents[name][key]
                for key in (
                    "result_sha256",
                    "forward_audit_sha256",
                    "postresult_audit_sha256",
                    "conservative_summary_sha256",
                    "run_summary_sha256",
                )
            }
            for name in RUNS
        },
        "boundary": {
            "all_four_prediction_vectors_and_evaluators_frozen_before_analysis": True,
            "offline_alignment_uses_opaque_id_in_memory_only": True,
            "question_prediction_answer_query_url_page_evaluator_text_or_credential_emitted": False,
            "task_identifier_or_per_task_metric_emitted": False,
            "mapping_gold_category_question_type_or_split_resource_opened_directly": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "historical_score_transition_or_cohort_authorized_as_future_runtime_input": False,
            "independent_search_fetch_generation_and_judge_samples_remain_confounders": True,
            "causal_effect_claimed": False,
        },
        "overall": {
            "runs": {name: _aggregate(ids, metrics[name]) for name in RUNS},
            "v24857_pairwise": pairwise,
            "recorded_complete_rollout_rank": recorded_rank,
        },
        "pacing_mechanism": {
            "legacy_latency_stop_tasks": len(legacy_latency),
            "pacing_aware_latency_stop_tasks": len(residual_latency),
            "decision_changed_tasks": len(changed),
            "recovered_latency_tasks": len(recovered_latency),
            "second_wave_executed_tasks": run_summary[
                "fixed_full_budget_control_totals"
            ]["second_wave_executed_tasks"],
            "provider_attempts": run_summary["direct_search_totals"][
                "provider_attempts"
            ],
            "provider_2xx": run_summary["direct_search_totals"]["status_2xx"],
            "provider_429": run_summary["direct_search_totals"]["status_429"],
            "provider_transport_failures": run_summary["direct_search_totals"][
                "transport_failures"
            ],
            "provider_slot_timeouts": run_summary["direct_search_totals"][
                "slot_timeouts"
            ],
            "rate_receipts_valid": rate["valid_receipts"],
            "pacing_receipts_valid": pacing["valid_receipts"],
            "decision_change_cohort": {
                "n": len(changed),
                "metrics_by_run": {
                    name: _aggregate(changed, metrics[name]) for name in RUNS
                },
                "v24857_pairwise": changed_pairs,
                "v24857_mechanism_mean": _mechanism_mean(changed, tasks),
                "whole_table_successes_by_run": changed_exact,
                "historical_cohort_membership_for_runtime_routing": False,
                "causal_effect_claimed": False,
            },
            "unchanged_admission_cohort": {
                "n": len(unchanged),
                "v24857_mechanism_mean": _mechanism_mean(unchanged, tasks),
                "v24857_whole_table_successes": _aggregate(
                    unchanged, metrics["v24857"]
                )["whole_table_successes"],
                "historical_cohort_membership_for_runtime_routing": False,
            },
        },
        "conclusions": {
            "v24857_is_highest_observed_exact_and_composite_among_recorded_complete_rollouts": (
                recorded_rank["candidate_exact_rank"] == 1
                and recorded_rank["candidate_composite_rank"] == 1
                and recorded_rank["candidate_is_unique_exact_maximum"]
                and recorded_rank["candidate_is_unique_composite_maximum"]
            ),
            "v24857_overall_composite_interval_excludes_zero_vs_any_reference": all(
                pair["paired_composite_bootstrap"]["interval_excludes_zero"]
                for pair in pairwise.values()
            ),
            "v24857_overall_exact_test_significant_vs_any_reference": all(
                pair["paired_exact_test"]["significant_at_0_05"]
                for pair in pairwise.values()
            ),
            "pacing_changed_admission_on_nonzero_tasks": len(changed) > 0,
            "pacing_change_cohort_gained_any_exact_table": any(
                value > 0 for value in changed_exact.values()
            ),
            "observed_exact_gain_attributable_to_pacing": False,
            "decision_change_cohort_composite_interval_excludes_zero_vs_v24854": changed_pairs[
                "v24857_minus_v24854"
            ]["paired_composite_bootstrap"]["interval_excludes_zero"],
            "decision_change_cohort_posthoc_independent_rollout_cannot_establish_causality": True,
            "more_retrieval_alone_is_sufficient_for_exact_table_improvement": False,
            "sota_or_leaderboard_claim_established": False,
        },
        "next_work": {
            "primary_bottleneck": "evidence_to_complete_table_conversion_not_raw_retrieval_admission",
            "candidate": "visible_question_conditioned_coverage_utility_lead_selection",
            "candidate_design": [
                "preserve the current four-query ten-fetch absolute cap",
                "replace stable-first-seen lead truncation only after a shared discovery prefix",
                "score leads by visible required-column and row-coverage utility plus source novelty",
                "use entropy or information gain only as shadow credit until fresh paired evidence supports routing",
                "emit task-local content-free selection and coverage receipts",
            ],
            "required_external_gate_controls": [
                "fresh benchmark-external target-cell-disjoint population",
                "same discovered lead vector and raw page byte prefix for both arms",
                "legacy stable-first-seen versus coverage-utility selection",
                "same model prompt output cap concurrency and total query-fetch-token-wall caps",
                "prediction freeze before evaluator access",
                "failure-as-zero no resume retry skip selective rerun or revaluation",
            ],
            "strict_go_conditions": [
                "candidate exact-table count strictly improves",
                "candidate quality composite and item F1 do not regress",
                "candidate evaluator-invalid and fallback counts do not increase",
                "candidate retrieved usable pages and wall remain within frozen caps",
                "candidate visible required-column and row-coverage receipt strictly improves",
                "candidate 429 slot-timeout and transport-failure counts do not increase",
            ],
            "public_exact220_authorized_after_this_diagnosis": False,
        },
        "authorization": {
            "coverage_utility_selector_build": True,
            "fresh_benchmark_external_shared_prefix_gate_design": True,
            "fresh_external_activation_or_launch": False,
            "public_dev64_or_exact220": False,
            "same_run_retry_resume_or_selective_revaluation": False,
            "historical_cohort_runtime_routing": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    checks = {
        "all_run_denominators_exact220": all(
            value["overall"]["runs"][name]["n"] == SELECTED for name in RUNS
        ),
        "pacing_partition_reconciles": len(changed) + len(unchanged) == SELECTED,
        "latency_partition_reconciles": len(changed) + len(residual_latency)
        == len(legacy_latency),
        "decision_change_count_matches_summary": len(changed)
        == pacing["decision_changed_tasks"],
        "receipt_denominators_exact220": rate["valid_receipts"]
        == pacing["valid_receipts"]
        == SELECTED,
        "provider_attempts_all_2xx": value["pacing_mechanism"]["provider_attempts"]
        == value["pacing_mechanism"]["provider_2xx"],
        "provider_failures_zero": all(
            value["pacing_mechanism"][name] == 0
            for name in (
                "provider_429",
                "provider_transport_failures",
                "provider_slot_timeouts",
            )
        ),
        "changed_cohort_exact_zero_all_runs": all(
            value == 0 for value in changed_exact.values()
        ),
        "overall_intervals_contain_zero": all(
            not pair["paired_composite_bootstrap"]["interval_excludes_zero"]
            for pair in pairwise.values()
        ),
        "overall_exact_tests_not_significant": all(
            not pair["paired_exact_test"]["significant_at_0_05"]
            for pair in pairwise.values()
        ),
        "result_metrics_reconcile": all(
            math.isclose(
                value["overall"]["runs"][name]["metrics"]["quality_composite"],
                parents[name]["result"]["metrics"]["all_220"][
                    "quality_composite"
                ],
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            for name in RUNS
        ),
        "recorded_rollout_rank_reconciles": (
            recorded_rank["recorded_complete_rollouts"] >= len(RUNS)
            and recorded_rank["candidate_exact_rank"] == 1
            and recorded_rank["candidate_composite_rank"] == 1
            and recorded_rank["candidate_is_unique_exact_maximum"]
            and recorded_rank["candidate_is_unique_composite_maximum"]
        ),
    }
    value["checks"] = checks
    value["findings"] = sorted(name for name, passed in checks.items() if not passed)
    value["diagnosis_valid"] = not value["findings"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if (
        OPAQUE.search(encoded)
        or INSTANCE.search(encoded)
        or SECRET.search(encoded)
        or "| Result |" in encoded
    ):
        raise RuntimeError("V2.48.58 diagnosis emitted prohibited content")
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate(value, rebuild=False)


def validate(
    value: Mapping[str, Any], *, rebuild: bool = True
) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role") != "v24858_v24857_pacing_quality_aggregate_diagnosis"
        or copied.get("status")
        != "new_observed_best_but_overall_gain_not_statistically_established_and_exact_gain_not_attributable_to_pacing"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("conclusions", {}).get(
            "observed_exact_gain_attributable_to_pacing"
        )
        is not False
        or copied.get("boundary", {}).get(
            "historical_score_transition_or_cohort_authorized_as_future_runtime_input"
        )
        is not False
        or copied.get("authorization", {}).get("public_dev64_or_exact220")
        is not False
        or copied.get("authorization", {}).get("sota_claim") is not False
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.58 diagnosis drifted")
    if rebuild:
        expected = build(now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.48.58 diagnosis is not reproducible")
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
                "decision_changed_tasks": report["pacing_mechanism"][
                    "decision_changed_tasks"
                ],
                "changed_cohort_exact_by_run": report["pacing_mechanism"][
                    "decision_change_cohort"
                ]["whole_table_successes_by_run"],
                "authorization": report["authorization"],
            },
            sort_keys=True,
        )
    )
