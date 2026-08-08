#!/usr/bin/env python3
"""Aggregate-only diagnosis of three frozen V2.48.00-policy rollouts.

The three complete exact-220 runs were already prediction-frozen, evaluated,
audited, and pushed before this script was written.  This offline analysis
aligns rows in memory by opaque id, but emits only population aggregates.  It
also inspects content-free direct-search receipts to distinguish ordinary
rollout variance from the provider-429 storm observed in V2.48.50.

No task identifier, question, prediction, answer, query, URL, page, evaluator
text, credential, or per-task metric is published.  Historical outcomes and
the derived 429 cohort are explicitly forbidden as future runtime routes.
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

from deepwide_agent import (  # noqa: E402
    v24850_v24800_replication_exact220_contract as contract,
)
from deepwide_agent.v24796_deadline_tavily_search import (  # noqa: E402
    validate_receipt,
)


DATE = "20260808"
OUTPUT = Path(
    f"results/v24851_v24800_v24807_v24850_transport_repeatability_diagnosis_v1_{DATE}.json"
)
SELECTED = 220
BOOTSTRAP_RESAMPLES = 20_000
QUALITY = ("score", "entity_acc", "f1_by_row", "f1_by_item", "column_f1")
COMPOSITE = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
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
    "v24807": {
        "protocol_id": "v24807_fixed_full_budget_exact220_v1",
        "root": Path("outputs/v24807_exact220_v1_20260807"),
        "result": Path("results/v24807_exact220_result_v1_20260807.json"),
        "forward_audit": Path(
            "results/v24807_exact220_forward_audit_v1_20260807.json"
        ),
        "postaudit": Path(
            "results/v24807_exact220_postresult_audit_v1_20260807.json"
        ),
    },
    "v24850": {
        "protocol_id": contract.PROTOCOL_ID,
        "root": contract.OUTPUT_ROOT,
        "result": Path(
            "results/v24850_v24800_replication_exact220_result_v1_20260808.json"
        ),
        "forward_audit": contract.FORWARD_AUDIT,
        "postaudit": Path(
            "results/v24850_v24800_replication_exact220_postresult_audit_v1_20260808.json"
        ),
    },
}


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.48.51 expected ordinary repository file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.51 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_parents(root: Path) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for name, spec in RUNS.items():
        result = _read(root, spec["result"])
        forward = _read(root, spec["forward_audit"])
        post = _read(root, spec["postaudit"])
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
            != contract.sha256(root / runtime)
            or post.get("provenance", {}).get("conservative_summary_sha256")
            != contract.sha256(root / evaluation)
        ):
            raise RuntimeError(f"V2.48.51 frozen parent chain drifted: {name}")
        output[name] = {
            "result": result,
            "run_summary": _read(root, summary),
            "result_sha256": contract.sha256(root / spec["result"]),
            "forward_audit_sha256": contract.sha256(root / spec["forward_audit"]),
            "postaudit_sha256": contract.sha256(root / spec["postaudit"]),
            "runtime_predictions_sha256": contract.sha256(root / runtime),
            "run_summary_sha256": contract.sha256(root / summary),
            "conservative_summary_sha256": contract.sha256(root / evaluation),
        }
    return output


def _runtime_and_transport(
    root: Path, name: str
) -> dict[str, dict[str, Any]]:
    run_root: Path = RUNS[name]["root"]
    runtime_path = _ordinary(root, run_root / "runtime_predictions.jsonl")
    lines = [line for line in runtime_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != SELECTED:
        raise RuntimeError("V2.48.51 runtime denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    summed = Counter()
    for position, line in enumerate(lines, 1):
        row = json.loads(line)
        opaque_id = row.get("opaque_id")
        receipt_path = (
            run_root
            / "tasks"
            / f"task_{position:04d}"
            / "direct_search_receipt.json"
        )
        receipt = validate_receipt(_read(root, receipt_path))
        if (
            not isinstance(row, dict)
            or not isinstance(opaque_id, str)
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
            or not isinstance(row.get("completion_kind"), str)
        ):
            raise RuntimeError("V2.48.51 runtime projection drifted")
        fields = {
            key: int(receipt[key])
            for key in (
                "provider_attempts",
                "successful_queries",
                "failed_queries",
                "retryable_responses",
                "status_429",
                "projected_url_leads",
                "slot_timeouts",
                "transport_failures",
            )
        }
        summed.update(fields)
        output[opaque_id] = {
            "prediction_sha256": row["prediction_sha256"],
            "completion_kind": row["completion_kind"],
            "transport": fields,
        }
    summary = _read(root, run_root / "run_summary.json")
    direct = summary.get("direct_search_totals") or {}
    if any(int(direct.get(key, -1)) != summed[key] for key in summed):
        raise RuntimeError(f"V2.48.51 direct-search total drifted: {name}")
    return output


def _metrics(root: Path, name: str) -> dict[str, dict[str, Any]]:
    run_root: Path = RUNS[name]["root"]
    rows = _read(root, run_root / "evaluator/conservative_summary.json").get(
        "per_task"
    )
    if not isinstance(rows, list) or len(rows) != SELECTED:
        raise RuntimeError("V2.48.51 evaluator denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        opaque_id = row.get("opaque_id")
        metrics = row.get("metrics")
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or not isinstance(row.get("evaluator_valid"), bool)
            or not isinstance(metrics, dict)
            or any(
                isinstance(metrics.get(metric), bool)
                or not isinstance(metrics.get(metric), (int, float))
                or not math.isfinite(float(metrics[metric]))
                for metric in QUALITY
            )
        ):
            raise RuntimeError("V2.48.51 evaluator projection drifted")
        output[opaque_id] = {
            "valid": row["evaluator_valid"],
            "metrics": {metric: float(metrics[metric]) for metric in QUALITY},
        }
    return output


def _mechanism(root: Path, name: str) -> dict[str, dict[str, Any]]:
    """Read only content-free runtime telemetry from post-freeze envelopes."""

    run_root: Path = RUNS[name]["root"]
    output: dict[str, dict[str, Any]] = {}
    for position in range(1, SELECTED + 1):
        envelope = _read(
            root,
            run_root / "tasks" / f"task_{position:04d}" / "result.json",
        )
        inner = envelope.get("result")
        if not isinstance(inner, dict):
            raise RuntimeError("V2.48.51 task envelope result absent")
        opaque_id = inner.get("opaque_id")
        evidence = inner.get("evidence") or {}
        total = (
            ((inner.get("two_wave_retrieval") or {}).get("receipt") or {}).get(
                "total"
            )
            or {}
        )
        timing = inner.get("attributed_timing") or {}
        cost = inner.get("cost") or {}
        values = {
            "queries_executed": total.get("queries_executed"),
            "fetches_attempted": total.get("fetches_attempted"),
            "usable_pages": total.get("usable_pages"),
            "novel_pages": total.get("novel_pages"),
            "unique_hosts": total.get("unique_hosts"),
            "projected_chars": evidence.get("projected_chars"),
            "system_total_tokens": cost.get("system_total_tokens"),
            "task_wall_seconds": timing.get("task_wall_seconds"),
        }
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0
                for value in values.values()
            )
        ):
            raise RuntimeError("V2.48.51 content-free mechanism telemetry drifted")
        output[opaque_id] = {key: float(value) for key, value in values.items()}
    return output


def _aggregate(
    ids: Iterable[str], values: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    selected = sorted(ids)
    if not selected:
        raise RuntimeError("V2.48.51 empty aggregate")
    metrics = {
        metric: sum(float(values[item]["metrics"][metric]) for item in selected)
        / len(selected)
        for metric in QUALITY
    }
    metrics["quality_composite"] = sum(metrics[name] for name in COMPOSITE) / 4
    return {
        "n": len(selected),
        "evaluator_valid": sum(values[item]["valid"] is True for item in selected),
        "whole_table_successes": sum(
            values[item]["metrics"]["score"] > 0 for item in selected
        ),
        "metrics": metrics,
    }


def _means(
    ids: Iterable[str], values: Mapping[str, Mapping[str, float]]
) -> dict[str, float]:
    selected = sorted(ids)
    if not selected:
        raise RuntimeError("V2.48.51 empty mechanism aggregate")
    keys = tuple(next(iter(values.values())))
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
    values = [
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
        sum(values[rng.randrange(len(values))] for _ in values) / len(values)
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    interval = [
        means[int(0.025 * BOOTSTRAP_RESAMPLES)],
        means[int(0.975 * BOOTSTRAP_RESAMPLES) - 1],
    ]
    return {
        "unit": "task_cluster",
        "seed": seed,
        "resamples": BOOTSTRAP_RESAMPLES,
        "mean_delta": sum(values) / len(values),
        "percentile_95_interval": interval,
        "interval_excludes_zero": interval[0] > 0 or interval[1] < 0,
        "direction_counts": {
            "improved": sum(value > 0 for value in values),
            "tied": sum(value == 0 for value in values),
            "worsened": sum(value < 0 for value in values),
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
            "whole_table_successes": (
                after["whole_table_successes"] - before["whole_table_successes"]
            ),
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


def build(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parents = _validate_parents(root)
    runtime = {name: _runtime_and_transport(root, name) for name in RUNS}
    metrics = {name: _metrics(root, name) for name in RUNS}
    mechanism = {name: _mechanism(root, name) for name in RUNS}
    ids = set(runtime["v24800"])
    if any(
        set(values) != ids or len(values) != SELECTED
        for family in (runtime, metrics, mechanism)
        for values in family.values()
    ):
        raise RuntimeError("V2.48.51 triple population drifted")

    rate_limited = {
        item for item in ids if runtime["v24850"][item]["transport"]["status_429"] > 0
    }
    not_rate_limited = ids - rate_limited
    rate_distribution = Counter(
        runtime["v24850"][item]["transport"]["status_429"]
        for item in rate_limited
    )
    storm_429 = sum(
        runtime["v24850"][item]["transport"]["status_429"]
        for item in rate_limited
    )
    storm_failed = sum(
        runtime["v24850"][item]["transport"]["failed_queries"]
        for item in rate_limited
    )

    unique_hashes = Counter(
        len({runtime[name][item]["prediction_sha256"] for name in RUNS})
        for item in ids
    )
    exact_frequency = Counter(
        sum(metrics[name][item]["metrics"]["score"] > 0 for name in RUNS)
        for item in ids
    )
    valid_frequency = Counter(
        sum(metrics[name][item]["valid"] is True for name in RUNS)
        for item in ids
    )

    transport_totals = {
        name: {
            key: int(parents[name]["run_summary"]["direct_search_totals"][key])
            for key in (
                "provider_attempts",
                "successful_queries",
                "failed_queries",
                "retryable_responses",
                "status_429",
                "projected_url_leads",
                "slot_timeouts",
                "transport_failures",
            )
        }
        for name in RUNS
    }
    for name in RUNS:
        transport_totals[name].update(
            {
                "system_total_tokens": int(
                    parents[name]["run_summary"]["system_total_tokens"]
                ),
                "forward_wall_seconds": float(
                    parents[name]["result"]["efficiency"]["forward_wall_seconds"]
                ),
            }
        )

    value = {
        "artifact_version": 1,
        "role": "v24851_v24800_v24807_v24850_aggregate_transport_repeatability_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "same_policy_variance_and_v24850_provider_429_storm_both_material",
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
            "same_forward_policy_task_vector_model_search_hard_caps_and_concurrency": True,
            "offline_alignment_uses_opaque_id_in_memory_only": True,
            "postfreeze_task_envelopes_opened_only_for_content_free_telemetry": True,
            "question_prediction_answer_query_url_page_evaluator_text_or_credential_accessed": False,
            "task_identifier_or_per_task_metric_emitted": False,
            "mapping_gold_category_question_type_or_split_resource_opened": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "historical_metric_correctness_or_429_cohort_authorized_as_future_runtime_route": False,
            "same_run_feedback_retry_resume_skip_or_selective_revaluation": False,
        },
        "overall": {
            "runs": {name: _aggregate(ids, metrics[name]) for name in RUNS},
            "pairwise": {
                "v24807_minus_v24800": _pair(
                    ids, "v24800", "v24807", metrics, seed=24808
                ),
                "v24850_minus_v24800": _pair(
                    ids, "v24800", "v24850", metrics, seed=24851
                ),
                "v24850_minus_v24807": _pair(
                    ids, "v24807", "v24850", metrics, seed=24852
                ),
            },
            "distinct_prediction_hash_count_distribution": {
                str(key): unique_hashes[key] for key in sorted(unique_hashes)
            },
            "whole_table_success_run_frequency": {
                str(key): exact_frequency[key] for key in sorted(exact_frequency)
            },
            "evaluator_valid_run_frequency": {
                str(key): valid_frequency[key] for key in sorted(valid_frequency)
            },
        },
        "transport": {
            "run_totals": transport_totals,
            "v24850_provider_429_storm": {
                "rate_limited_task_count": len(rate_limited),
                "non_rate_limited_task_count": len(not_rate_limited),
                "status_429_total": storm_429,
                "rate_limited_failed_query_count": storm_failed,
                "status_429_count_per_rate_limited_task": {
                    str(key): rate_distribution[key]
                    for key in sorted(rate_distribution)
                },
                "key_slot_cap": int(
                    parents["v24850"]["run_summary"]["direct_search_totals"][
                        "key_slot_cap"
                    ]
                ),
                "status_429_per_failed_query": storm_429 / storm_failed,
                "every_rate_limited_failed_query_rotated_across_full_key_cap": (
                    storm_failed > 0
                    and storm_429
                    == storm_failed
                    * int(
                        parents["v24850"]["run_summary"][
                            "direct_search_totals"
                        ]["key_slot_cap"]
                    )
                ),
                "descriptive_not_causal": True,
            },
            "v24850_429_cohort_postfreeze_aggregate": {
                "n": len(rate_limited),
                "metrics_by_run": {
                    name: _aggregate(rate_limited, metrics[name]) for name in RUNS
                },
                "mechanism_by_run": {
                    name: _means(rate_limited, mechanism[name]) for name in RUNS
                },
                "historical_cohort_membership_for_runtime_routing": False,
                "causal_effect_of_429_claimed": False,
            },
            "v24850_non429_cohort_postfreeze_aggregate": {
                "n": len(not_rate_limited),
                "metrics_by_run": {
                    name: _aggregate(not_rate_limited, metrics[name]) for name in RUNS
                },
                "mechanism_by_run": {
                    name: _means(not_rate_limited, mechanism[name]) for name in RUNS
                },
                "historical_cohort_membership_for_runtime_routing": False,
            },
        },
        "conclusions": {
            "same_policy_predictions_are_byte_stable": False,
            "v24800_single_rollout_peak_replicated_by_v24850": False,
            "provider_429_storm_present_in_v24850": storm_429 > 0,
            "provider_429_storm_is_uniform_across_all_tasks": False,
            "full_key_rotation_amplified_each_rate_limited_failed_query": (
                storm_429
                == storm_failed
                * int(
                    parents["v24850"]["run_summary"]["direct_search_totals"][
                        "key_slot_cap"
                    ]
                )
            ),
            "provider_429_is_proven_cause_of_all_cross_run_quality_variance": False,
            "fixed_budget_or_entropy_causal_effect_established": False,
            "leaderboard_or_external_sota_established": False,
        },
        "next_work": {
            "transport_successor_before_quality_selector_external": True,
            "provider_wide_429_circuit_breaker_or_shared_cooldown_design": True,
            "neutral_nonbenchmark_transport_health_gate_before_any_benchmark": True,
            "do_not_rotate_all_keys_immediately_after_provider_wide_429": True,
            "do_not_launch_another_unchanged_public_exact220": True,
            "quality_dependency_selector_must_remain_visible_only": True,
            "entropy_information_gain_shadow_only": True,
        },
        "authorization": {
            "transport_successor_build": True,
            "neutral_nonbenchmark_transport_gate_design": True,
            "visible_quality_dependency_selector_build": True,
            "fresh_shared_prefix_external_protocol": False,
            "new_public_exact220": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    checks = {
        "all_run_denominators_exact220": all(
            value["overall"]["runs"][name]["n"] == SELECTED for name in RUNS
        ),
        "hash_distribution_reconciles": sum(unique_hashes.values()) == SELECTED,
        "exact_frequency_reconciles": sum(exact_frequency.values()) == SELECTED,
        "validity_frequency_reconciles": sum(valid_frequency.values()) == SELECTED,
        "v24850_rate_partition_reconciles": (
            len(rate_limited) + len(not_rate_limited) == SELECTED
        ),
        "v24850_429_receipts_reconcile": (
            storm_429 == transport_totals["v24850"]["status_429"]
        ),
        "v24850_full_key_rotation_arithmetic_reconciles": (
            value["transport"]["v24850_provider_429_storm"][
                "every_rate_limited_failed_query_rotated_across_full_key_cap"
            ]
            is True
        ),
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
        raise RuntimeError("V2.48.51 diagnosis emitted prohibited content")
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate(value, root=root, rebuild=False)


def validate(
    value: Mapping[str, Any], *, root: Path = ROOT, rebuild: bool = True
) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role")
        != "v24851_v24800_v24807_v24850_aggregate_transport_repeatability_diagnosis"
        or copied.get("status")
        != "same_policy_variance_and_v24850_provider_429_storm_both_material"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("boundary", {}).get(
            "historical_metric_correctness_or_429_cohort_authorized_as_future_runtime_route"
        )
        is not False
        or copied.get("authorization")
        != {
            "transport_successor_build": True,
            "neutral_nonbenchmark_transport_gate_design": True,
            "visible_quality_dependency_selector_build": True,
            "fresh_shared_prefix_external_protocol": False,
            "new_public_exact220": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.51 diagnosis drifted")
    if rebuild:
        expected = build(root, now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.48.51 diagnosis is not reproducible")
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
                "exact_runs": {
                    name: report["overall"]["runs"][name][
                        "whole_table_successes"
                    ]
                    for name in RUNS
                },
                "v24850_rate_limited_tasks": report["transport"][
                    "v24850_provider_429_storm"
                ]["rate_limited_task_count"],
                "v24850_status_429": report["transport"][
                    "v24850_provider_429_storm"
                ]["status_429_total"],
                "authorization": report["authorization"],
            },
            sort_keys=True,
        )
    )
