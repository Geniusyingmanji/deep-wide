#!/usr/bin/env python3
"""Aggregate-only post-result diagnosis of V2.48.54 rate-aware exact-220.

This script aligns three already frozen and audited exact-220 runs in memory.
It publishes population aggregates only.  Historical correctness, the old
429 cohort, and the new latency-stop cohort are explicitly forbidden as
future runtime routes.

The key diagnostic question is whether the provider-wide pacing wait added by
V2.48.52 was mixed into the legacy 30-second first-wave latency ceiling.  The
counterfactual subtracts only the content-free provider-gate wait from the
same-pass first-wave elapsed time.  It is descriptive: gate wait consumes real
wall time, and this analysis does not claim that executing wave two would have
improved benchmark quality.
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

from deepwide_agent import v24854_rate_aware_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24796_deadline_tavily_search import (  # noqa: E402
    validate_receipt as validate_direct_receipt,
)
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    validate_receipt as validate_rate_receipt,
)


DATE = "20260808"
OUTPUT = Path(
    f"results/v24855_v24854_rate_aware_quality_diagnosis_v1_{DATE}.json"
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
    "projected_chars",
    "system_total_tokens",
    "task_wall_seconds",
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
INSTANCE = re.compile(r"overall_(?:test|dev|validation)_\d+")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)

RUNS: dict[str, dict[str, Any]] = {
    "v24800": {
        "protocol_id": "v24800_fixed_full_budget_no_entropy_exact220_v1",
        "root": Path("outputs/v24800_exact220_v1_20260807"),
        "result": Path("results/v24800_exact220_result_v1_20260807.json"),
        "forward_audit": Path(
            "results/v24800_exact220_forward_audit_v1_20260807.json"
        ),
        "postaudit": Path(
            "results/v24800_exact220_postresult_audit_v1_20260807.json"
        ),
    },
    "v24850": {
        "protocol_id": (
            "v24850_fresh_v24800_fixed_full_budget_replication_exact220_v1"
        ),
        "root": Path(
            "outputs/v24850_v24800_replication_exact220_v1_20260808"
        ),
        "result": Path(
            "results/v24850_v24800_replication_exact220_result_v1_20260808.json"
        ),
        "forward_audit": Path(
            "results/v24850_v24800_replication_exact220_forward_audit_v1_20260808.json"
        ),
        "postaudit": Path(
            "results/v24850_v24800_replication_exact220_postresult_audit_v1_20260808.json"
        ),
    },
    "v24854": {
        "protocol_id": contract.PROTOCOL_ID,
        "root": contract.OUTPUT_ROOT,
        "result": Path(
            "results/v24854_rate_aware_exact220_result_v1_20260808.json"
        ),
        "forward_audit": contract.FORWARD_AUDIT,
        "postaudit": Path(
            "results/v24854_rate_aware_exact220_postresult_audit_v1_20260808.json"
        ),
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
        raise RuntimeError(f"V2.48.55 expected ordinary repository file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.55 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_parents() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for name, spec in RUNS.items():
        result = _read(spec["result"])
        forward = _read(spec["forward_audit"])
        post = _read(spec["postaudit"])
        run_root: Path = spec["root"]
        runtime = run_root / "runtime_predictions.jsonl"
        summary = run_root / "run_summary.json"
        evaluation = run_root / "evaluator/conservative_summary.json"
        if (
            result.get("protocol_id") != spec["protocol_id"]
            or result.get("selected") != SELECTED
            or result.get("failure_as_zero") is not True
            or result.get("exact220_prediction_freeze_before_evaluator") is not True
            or not _sealed(result, "result_payload_sha256")
            or forward.get("protocol_id") != spec["protocol_id"]
            or forward.get("audit_valid") is not True
            or forward.get("findings") != []
            or not _sealed(forward, "audit_payload_sha256")
            or post.get("protocol_id") != spec["protocol_id"]
            or post.get("audit_valid") is not True
            or post.get("findings") != []
            or not _sealed(post, "audit_payload_sha256")
            or forward.get("runtime_predictions_sha256")
            != contract.sha256(ROOT / runtime)
            or post.get("provenance", {}).get("conservative_summary_sha256")
            != contract.sha256(ROOT / evaluation)
        ):
            raise RuntimeError(f"V2.48.55 frozen parent chain drifted: {name}")
        output[name] = {
            "result": result,
            "summary": _read(summary),
            "result_sha256": contract.sha256(ROOT / spec["result"]),
            "forward_audit_sha256": contract.sha256(
                ROOT / spec["forward_audit"]
            ),
            "postaudit_sha256": contract.sha256(ROOT / spec["postaudit"]),
            "runtime_predictions_sha256": contract.sha256(ROOT / runtime),
            "run_summary_sha256": contract.sha256(ROOT / summary),
            "conservative_summary_sha256": contract.sha256(ROOT / evaluation),
        }
    return output


def _runtime(name: str) -> dict[str, dict[str, Any]]:
    root: Path = RUNS[name]["root"]
    lines = [
        line
        for line in _ordinary(root / "runtime_predictions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if len(lines) != SELECTED:
        raise RuntimeError("V2.48.55 runtime denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    for position, line in enumerate(lines, 1):
        row = json.loads(line)
        opaque_id = row.get("opaque_id") if isinstance(row, Mapping) else None
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or row.get("status") != "completed"
            or row.get("label_blind") is not True
            or row.get(
                "mapping_gold_category_question_type_split_evaluator_score_read"
            )
            is not False
            or not isinstance(row.get("prediction_sha256"), str)
            or len(row["prediction_sha256"]) != 64
        ):
            raise RuntimeError("V2.48.55 runtime row drifted")
        direct = validate_direct_receipt(
            _read(
                root
                / "tasks"
                / f"task_{position:04d}"
                / "direct_search_receipt.json"
            )
        )
        output[opaque_id] = {
            "prediction_sha256": row["prediction_sha256"],
            "completion_kind": row.get("completion_kind"),
            "direct": {
                key: int(direct[key])
                for key in (
                    "provider_attempts",
                    "successful_queries",
                    "failed_queries",
                    "status_429",
                    "projected_url_leads",
                    "slot_timeouts",
                    "transport_failures",
                )
            },
        }
    return output


def _metrics(name: str) -> dict[str, dict[str, Any]]:
    root: Path = RUNS[name]["root"]
    rows = _read(root / "evaluator/conservative_summary.json").get("per_task")
    if not isinstance(rows, list) or len(rows) != SELECTED:
        raise RuntimeError("V2.48.55 evaluator denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        opaque_id = row.get("opaque_id") if isinstance(row, Mapping) else None
        metrics = row.get("metrics") if isinstance(row, Mapping) else None
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or not isinstance(row.get("evaluator_valid"), bool)
            or not isinstance(metrics, Mapping)
            or any(
                isinstance(metrics.get(metric), bool)
                or not isinstance(metrics.get(metric), (int, float))
                or not math.isfinite(float(metrics[metric]))
                for metric in QUALITY
            )
        ):
            raise RuntimeError("V2.48.55 evaluator row drifted")
        output[opaque_id] = {
            "valid": row["evaluator_valid"],
            "metrics": {metric: float(metrics[metric]) for metric in QUALITY},
        }
    return output


def _mechanism(name: str) -> dict[str, dict[str, Any]]:
    root: Path = RUNS[name]["root"]
    output: dict[str, dict[str, Any]] = {}
    for position in range(1, SELECTED + 1):
        envelope = _read(root / "tasks" / f"task_{position:04d}" / "result.json")
        inner = envelope.get("result") or {}
        opaque_id = inner.get("opaque_id")
        retrieval = inner.get("two_wave_retrieval") or {}
        receipt = retrieval.get("receipt") or {}
        total = receipt.get("total") or {}
        wave1 = receipt.get("wave1") or {}
        controller = receipt.get("controller") or {}
        evidence = inner.get("evidence") or {}
        cost = inner.get("cost") or {}
        timing = inner.get("attributed_timing") or {}
        values = {
            "queries_executed": total.get("queries_executed"),
            "fetches_attempted": total.get("fetches_attempted"),
            "usable_pages": total.get("usable_pages"),
            "novel_pages": total.get("novel_pages"),
            "unique_hosts": total.get("unique_hosts"),
            "content_chars": total.get("content_chars"),
            "projected_chars": evidence.get("projected_chars"),
            "system_total_tokens": cost.get("system_total_tokens"),
            "task_wall_seconds": timing.get("task_wall_seconds"),
            "wave1_search_seconds": wave1.get("search_seconds"),
            "wave1_fetch_seconds": wave1.get("fetch_seconds"),
        }
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or retrieval.get("status") != "completed"
            or controller.get("decision") not in {"expand", "stop"}
            or controller.get("reason")
            not in {"positive_entropy_voc", "latency_ceiling", "no_delta_budget"}
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0
                for value in values.values()
            )
        ):
            raise RuntimeError("V2.48.55 mechanism row drifted")
        output[opaque_id] = {
            **{key: float(values[key]) for key in MECHANISM},
            "decision": controller["decision"],
            "reason": controller["reason"],
            "wave1_elapsed_seconds": float(values["wave1_search_seconds"])
            + float(values["wave1_fetch_seconds"]),
            "provider_gate_wait_seconds": 0.0,
            "provider_start_reservations": 0,
        }
        if name == "v24854":
            rate = validate_rate_receipt(
                _read(
                    root
                    / "tasks"
                    / f"task_{position:04d}"
                    / contract.RATE_RECEIPT_NAME
                )
            )
            output[opaque_id]["provider_gate_wait_seconds"] = float(
                rate["total_provider_gate_wait_seconds"]
            )
            output[opaque_id]["provider_start_reservations"] = int(
                rate["provider_start_reservations"]
            )
    return output


def _aggregate(
    ids: Iterable[str], values: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    selected = sorted(ids)
    if not selected:
        raise RuntimeError("V2.48.55 empty metric aggregate")
    metrics = {
        metric: sum(values[item]["metrics"][metric] for item in selected)
        / len(selected)
        for metric in QUALITY
    }
    metrics["quality_composite"] = sum(metrics[name] for name in COMPOSITE) / 4
    return {
        "n": len(selected),
        "evaluator_valid": sum(values[item]["valid"] for item in selected),
        "whole_table_successes": sum(
            values[item]["metrics"]["score"] > 0 for item in selected
        ),
        "metrics": metrics,
    }


def _means(
    ids: Iterable[str], values: Mapping[str, Mapping[str, Any]]
) -> dict[str, float]:
    selected = sorted(ids)
    if not selected:
        raise RuntimeError("V2.48.55 empty mechanism aggregate")
    keys = (
        *MECHANISM,
        "wave1_elapsed_seconds",
        "provider_gate_wait_seconds",
        "provider_start_reservations",
    )
    return {
        key: sum(float(values[item][key]) for item in selected) / len(selected)
        for key in keys
    }


def _bootstrap(
    ids: Iterable[str],
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    seed: int,
) -> dict[str, Any]:
    selected = sorted(ids)
    deltas = [
        sum(
            after[item]["metrics"][metric]
            - before[item]["metrics"][metric]
            for metric in COMPOSITE
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


def _pair(
    ids: set[str],
    before_name: str,
    after_name: str,
    metrics: Mapping[str, Mapping[str, Any]],
    *,
    seed: int,
) -> dict[str, Any]:
    before = _aggregate(ids, metrics[before_name])
    after = _aggregate(ids, metrics[after_name])
    transitions = Counter(
        f"before_{'success' if metrics[before_name][item]['metrics']['score'] > 0 else 'failure'}_"
        f"after_{'success' if metrics[after_name][item]['metrics']['score'] > 0 else 'failure'}"
        for item in ids
    )
    return {
        "before": before,
        "after": after,
        "delta": {
            "evaluator_valid": after["evaluator_valid"] - before["evaluator_valid"],
            "whole_table_successes": after["whole_table_successes"]
            - before["whole_table_successes"],
            "metrics": {
                metric: after["metrics"][metric] - before["metrics"][metric]
                for metric in (*QUALITY, "quality_composite")
            },
        },
        "whole_table_transitions": dict(sorted(transitions.items())),
        "paired_composite_bootstrap": _bootstrap(
            ids, metrics[before_name], metrics[after_name], seed=seed
        ),
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    parents = _validate_parents()
    runtime = {name: _runtime(name) for name in RUNS}
    metrics = {name: _metrics(name) for name in RUNS}
    mechanism = {name: _mechanism(name) for name in RUNS}
    ids = set(runtime["v24800"])
    if any(
        set(values) != ids or len(values) != SELECTED
        for family in (runtime, metrics, mechanism)
        for values in family.values()
    ):
        raise RuntimeError("V2.48.55 aligned population drifted")

    old_429 = {
        item for item in ids if runtime["v24850"][item]["direct"]["status_429"] > 0
    }
    v54_stop = {
        item for item in ids if mechanism["v24854"][item]["decision"] == "stop"
    }
    pacing_mixed = {
        item
        for item in v54_stop
        if mechanism["v24854"][item]["wave1_elapsed_seconds"]
        - mechanism["v24854"][item]["provider_gate_wait_seconds"]
        < 30.0
    }
    residual_slow = v54_stop - pacing_mixed
    distinct_hashes = Counter(
        len({runtime[name][item]["prediction_sha256"] for name in RUNS})
        for item in ids
    )
    exact_frequency = Counter(
        sum(metrics[name][item]["metrics"]["score"] > 0 for name in RUNS)
        for item in ids
    )

    value = {
        "artifact_version": 1,
        "role": "v24855_v24854_rate_aware_quality_aggregate_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "transport_storm_fixed_but_provider_wait_mixed_into_wave1_latency_and_quality_gain_not_established",
        "parents": {
            name: {
                key: parents[name][key]
                for key in (
                    "result_sha256",
                    "forward_audit_sha256",
                    "postaudit_sha256",
                    "runtime_predictions_sha256",
                    "run_summary_sha256",
                    "conservative_summary_sha256",
                )
            }
            for name in RUNS
        },
        "boundary": {
            "all_three_exact220_prediction_freezes_evaluators_and_audits_complete": True,
            "offline_alignment_uses_opaque_id_in_memory_only": True,
            "question_prediction_answer_query_url_page_evaluator_text_or_credential_accessed": False,
            "task_identifier_or_per_task_metric_emitted": False,
            "mapping_gold_category_question_type_or_split_resource_opened": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "historical_correctness_429_or_latency_cohort_authorized_as_runtime_route": False,
            "counterfactual_subtracts_content_free_same_pass_provider_gate_wait_only": True,
            "counterfactual_claims_quality_causality": False,
        },
        "overall": {
            "runs": {name: _aggregate(ids, metrics[name]) for name in RUNS},
            "pairwise": {
                "v24854_minus_v24800": _pair(
                    ids, "v24800", "v24854", metrics, seed=24855
                ),
                "v24854_minus_v24850": _pair(
                    ids, "v24850", "v24854", metrics, seed=24856
                ),
            },
            "mechanism_by_run": {
                name: _means(ids, mechanism[name]) for name in RUNS
            },
            "distinct_prediction_hash_count_distribution": {
                str(key): distinct_hashes[key] for key in sorted(distinct_hashes)
            },
            "whole_table_success_run_frequency": {
                str(key): exact_frequency[key] for key in sorted(exact_frequency)
            },
        },
        "transport": {
            "v24850_status_429_total": sum(
                runtime["v24850"][item]["direct"]["status_429"] for item in ids
            ),
            "v24854_status_429_total": sum(
                runtime["v24854"][item]["direct"]["status_429"] for item in ids
            ),
            "v24850_failed_query_total": sum(
                runtime["v24850"][item]["direct"]["failed_queries"] for item in ids
            ),
            "v24854_failed_query_total": sum(
                runtime["v24854"][item]["direct"]["failed_queries"] for item in ids
            ),
            "v24854_slot_timeout_total": sum(
                runtime["v24854"][item]["direct"]["slot_timeouts"] for item in ids
            ),
            "v24854_transport_failure_total": sum(
                runtime["v24854"][item]["direct"]["transport_failures"]
                for item in ids
            ),
            "v24850_old_429_cohort": {
                "n": len(old_429),
                "metrics_by_run": {
                    name: _aggregate(old_429, metrics[name]) for name in RUNS
                },
                "mechanism_by_run": {
                    name: _means(old_429, mechanism[name]) for name in RUNS
                },
                "historical_cohort_membership_for_runtime_routing": False,
                "causal_effect_claimed": False,
            },
        },
        "pacing_latency_mixture": {
            "legacy_first_wave_ceiling_seconds": 30.0,
            "v24800_latency_stop_count": sum(
                mechanism["v24800"][item]["reason"] == "latency_ceiling"
                for item in ids
            ),
            "v24850_latency_stop_count": sum(
                mechanism["v24850"][item]["reason"] == "latency_ceiling"
                for item in ids
            ),
            "v24854_latency_stop_count": len(v54_stop),
            "pacing_mixed_stop_count": len(pacing_mixed),
            "residual_slow_stop_count": len(residual_slow),
            "all_v24854_stops_have_positive_provider_gate_wait": all(
                mechanism["v24854"][item]["provider_gate_wait_seconds"] > 0
                for item in v54_stop
            ),
            "stop_cohort": {
                "n": len(v54_stop),
                "metrics_by_run": {
                    name: _aggregate(v54_stop, metrics[name]) for name in RUNS
                },
                "mechanism_by_run": {
                    name: _means(v54_stop, mechanism[name]) for name in RUNS
                },
                "historical_cohort_membership_for_runtime_routing": False,
            },
            "pacing_mixed_counterfactual_cohort": {
                "n": len(pacing_mixed),
                "metrics_by_run": {
                    name: _aggregate(pacing_mixed, metrics[name]) for name in RUNS
                },
                "mechanism_by_run": {
                    name: _means(pacing_mixed, mechanism[name]) for name in RUNS
                },
                "provider_wait_exclusion_would_have_moved_elapsed_below_30_seconds": True,
                "wave2_execution_or_quality_gain_observed": False,
                "historical_cohort_membership_for_runtime_routing": False,
            },
        },
        "conclusions": {
            "provider_429_storm_eliminated_in_v24854": True,
            "v24854_improved_composite_over_v24850": (
                _aggregate(ids, metrics["v24854"])["metrics"]["quality_composite"]
                > _aggregate(ids, metrics["v24850"])["metrics"]["quality_composite"]
            ),
            "v24854_improved_exact_over_v24850": False,
            "v24854_improved_composite_or_exact_over_v24800": False,
            "v24854_pairwise_composite_interval_excludes_zero": False,
            "provider_pacing_wait_is_mixed_into_legacy_latency_decision": True,
            "pacing_mixture_proves_wave2_quality_gain": False,
            "raw_more_evidence_is_universally_better": False,
            "transport_fix_is_sufficient_for_sota": False,
            "leaderboard_or_external_sota_established": False,
        },
        "next_work": {
            "build_same_pass_content_free_pacing_aware_admission_adapter": True,
            "separate_provider_queue_wait_from_evidence_work_latency_for_admission": True,
            "retain_absolute_240_second_task_deadline_and_cleanup_reserve": True,
            "retain_provider_pacing_cooldown_and_two_attempt_cap": True,
            "do_not_simply_raise_evidence_budget_or_context": True,
            "validate_on_fresh_shared_prefix_external_tasks_before_public_benchmark": True,
            "required_external_arms": [
                "rate_aware_legacy_elapsed_admission",
                "rate_aware_pacing_aware_admission",
            ],
            "required_external_go": [
                "candidate_exact_strictly_improves",
                "candidate_composite_and_item_f1_do_not_regress",
                "candidate_fallback_and_invalid_counts_do_not_increase",
                "candidate_total_wall_and_hard_caps_remain_bounded",
                "candidate_429_and_transport_failures_do_not_increase",
            ],
            "entropy_information_gain_remains_shadow_only": True,
        },
        "authorization": {
            "pacing_aware_admission_adapter_build": True,
            "fresh_shared_prefix_external_protocol_design": True,
            "fresh_external_launch": False,
            "new_public_dev64_or_exact220": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    pair_00 = value["overall"]["pairwise"]["v24854_minus_v24800"]
    pair_50 = value["overall"]["pairwise"]["v24854_minus_v24850"]
    checks = {
        "all_run_denominators_exact220": all(
            value["overall"]["runs"][name]["n"] == SELECTED for name in RUNS
        ),
        "hash_distribution_reconciles": sum(distinct_hashes.values()) == SELECTED,
        "exact_frequency_reconciles": sum(exact_frequency.values()) == SELECTED,
        "v24854_stop_partition_reconciles": (
            len(pacing_mixed) + len(residual_slow) == len(v54_stop)
        ),
        "v24854_429_eliminated": value["transport"]["v24854_status_429_total"] == 0,
        "v24854_no_slot_or_transport_failure": (
            value["transport"]["v24854_slot_timeout_total"] == 0
            and value["transport"]["v24854_transport_failure_total"] == 0
        ),
        "pacing_mixture_is_material": len(pacing_mixed) > 0,
        "pair_v24800_interval_contains_zero": pair_00[
            "paired_composite_bootstrap"
        ]["interval_excludes_zero"]
        is False,
        "pair_v24850_interval_contains_zero": pair_50[
            "paired_composite_bootstrap"
        ]["interval_excludes_zero"]
        is False,
        "final_result_composites_reconcile": all(
            value["overall"]["runs"][name]["metrics"]["quality_composite"]
            == parents[name]["result"]["metrics"]["all_220"][
                "quality_composite"
            ]
            for name in RUNS
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
        raise RuntimeError("V2.48.55 diagnosis emitted prohibited content")
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate(value, rebuild=False)


def validate(
    value: Mapping[str, Any], *, rebuild: bool = True
) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role")
        != "v24855_v24854_rate_aware_quality_aggregate_diagnosis"
        or copied.get("status")
        != "transport_storm_fixed_but_provider_wait_mixed_into_wave1_latency_and_quality_gain_not_established"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("boundary", {}).get(
            "historical_correctness_429_or_latency_cohort_authorized_as_runtime_route"
        )
        is not False
        or copied.get("authorization")
        != {
            "pacing_aware_admission_adapter_build": True,
            "fresh_shared_prefix_external_protocol_design": True,
            "fresh_external_launch": False,
            "new_public_dev64_or_exact220": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.55 diagnosis drifted")
    if rebuild:
        expected = build(now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.48.55 diagnosis is not reproducible")
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
                "exact": {
                    name: report["overall"]["runs"][name][
                        "whole_table_successes"
                    ]
                    for name in RUNS
                },
                "composite": {
                    name: report["overall"]["runs"][name]["metrics"][
                        "quality_composite"
                    ]
                    for name in RUNS
                },
                "v24854_latency_stops": report["pacing_latency_mixture"][
                    "v24854_latency_stop_count"
                ],
                "pacing_mixed_stops": report["pacing_latency_mixture"][
                    "pacing_mixed_stop_count"
                ],
                "authorization": report["authorization"],
            },
            sort_keys=True,
        )
    )
