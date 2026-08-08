#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.48.44 exact-220 result.

All predictions and evaluator rows are terminal before this script runs.  It
joins opaque identifiers only in memory and emits aggregate counts, means,
bins, and paired uncertainty.  It emits no task identifier, question,
prediction, answer, query, URL, page, field name, evaluator message, or
credential, and performs no network/model/search/fetch/evaluator effect.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24844_atomic_table_header_exact220_contract as contract  # noqa: E402


OUTPUT = Path("results/v24845_v24844_evidence_supply_diagnosis_v1_20260808.json")
VERSIONS = {
    "v24800": {
        "root": Path("outputs/v24800_exact220_v1_20260807"),
        "result": Path("results/v24800_exact220_result_v1_20260807.json"),
        "post": Path("results/v24800_exact220_postresult_audit_v1_20260807.json"),
    },
    "v24840": {
        "root": Path("outputs/v24840_structure_preserving_exact220_v1_20260807"),
        "result": Path("results/v24840_structure_preserving_exact220_result_v1_20260807.json"),
        "post": Path("results/v24840_structure_preserving_exact220_postresult_audit_v1_20260807.json"),
    },
    "v24844": {
        "root": Path("outputs/v24844_atomic_table_header_exact220_v1_20260808"),
        "result": Path("results/v24844_atomic_table_header_exact220_result_v1_20260808.json"),
        "post": Path("results/v24844_atomic_table_header_exact220_postresult_audit_v1_20260808.json"),
    },
}
SELECTED = 220
QUALITY = ("score", "entity_acc", "f1_by_row", "f1_by_item", "column_f1")
COMPOSITE = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
MECHANISM = (
    "search_failures",
    "fetch_failures",
    "usable_pages",
    "unique_hosts",
    "raw_content_chars",
    "projected_chars",
    "synthesized_rows",
    "unknown_cell_ratio",
    "system_total_tokens",
    "task_wall_seconds",
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
INSTANCE = re.compile(r"(?:deep2wide_result|wide2deep_ws)_[^\"\\]+")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
BOOTSTRAP_SEED = 24845
BOOTSTRAP_RESAMPLES = 20_000


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.45 expected ordinary repository file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.45 expected JSON object")
    return value


def _jsonl(relative: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in _ordinary(relative).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.48.45 expected JSONL objects")
    return rows


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_parents() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for name, paths in VERSIONS.items():
        result = _read(paths["result"])
        post = _read(paths["post"])
        summary = _read(paths["root"] / "run_summary.json")
        if (
            result.get("selected") != SELECTED
            or result.get("failure_as_zero") is not True
            or not _sealed(result, "result_payload_sha256")
            or post.get("audit_valid") is not True
            or post.get("findings") != []
            or not _sealed(post, "audit_payload_sha256")
            or summary.get("selected") != SELECTED
            or summary.get("completed") != SELECTED
            or summary.get("failed") != 0
        ):
            raise RuntimeError(f"V2.48.45 frozen parent drifted: {name}")
        output[name] = {"result": result, "post": post, "summary": summary}
    return output


def _metric_rows(root: Path) -> dict[str, dict[str, Any]]:
    rows = _read(root / "evaluator/conservative_summary.json").get("per_task")
    if not isinstance(rows, list) or len(rows) != SELECTED:
        raise RuntimeError("V2.48.45 evaluator denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        opaque = row.get("opaque_id") if isinstance(row, Mapping) else None
        instance = row.get("instance_id") if isinstance(row, Mapping) else None
        metrics = row.get("metrics") if isinstance(row, Mapping) else None
        if (
            not isinstance(opaque, str)
            or OPAQUE.fullmatch(opaque) is None
            or opaque in output
            or not isinstance(instance, str)
            or not instance
            or not isinstance(metrics, Mapping)
            or not isinstance(row.get("evaluator_valid"), bool)
            or any(
                isinstance(metrics.get(key), bool)
                or not isinstance(metrics.get(key), (int, float))
                or not math.isfinite(float(metrics[key]))
                for key in QUALITY
            )
        ):
            raise RuntimeError("V2.48.45 evaluator row drifted")
        output[opaque] = {
            "instance": instance,
            "valid": bool(row["evaluator_valid"]),
            "error": str(row.get("evaluator_error") or ""),
            "metrics": {key: float(metrics[key]) for key in QUALITY},
        }
    return output


def _message_classes(root: Path) -> dict[str, str]:
    rows = _jsonl(root / "evaluator/official_eval_results.jsonl")
    if len(rows) != SELECTED:
        raise RuntimeError("V2.48.45 official evaluator denominator drifted")
    output: dict[str, str] = {}
    for row in rows:
        instance = row.get("instance_id")
        message = str(row.get("msg") or "")
        if not isinstance(instance, str) or not instance or instance in output:
            raise RuntimeError("V2.48.45 evaluator identity drifted")
        output[instance] = (
            "schema"
            if message.startswith("required_columns")
            else "entity"
            if message.startswith("the entity is wrong")
            else "other"
        )
    return output


def _task_rows(root: Path) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for position in range(1, SELECTED + 1):
        envelope = _read(root / "tasks" / f"task_{position:04d}" / "result.json")
        result = envelope.get("result") or {}
        opaque = result.get("opaque_id")
        receipt = ((result.get("two_wave_retrieval") or {}).get("receipt") or {})
        total = receipt.get("total") or {}
        cost = result.get("cost") or {}
        search = cost.get("search") or {}
        evidence = result.get("evidence") or {}
        table = (result.get("telemetry") or {}).get("table") or {}
        timing = result.get("attributed_timing") or {}
        values: dict[str, Any] = {
            "search_failures": search.get("failures"),
            "fetch_failures": search.get("fetch_failures"),
            "usable_pages": total.get("usable_pages"),
            "unique_hosts": total.get("unique_hosts"),
            "raw_content_chars": total.get("content_chars"),
            "projected_chars": evidence.get("projected_chars"),
            "synthesized_rows": table.get("row_count"),
            "system_total_tokens": cost.get("system_total_tokens"),
        }
        if (
            not isinstance(opaque, str)
            or OPAQUE.fullmatch(opaque) is None
            or opaque in output
            or any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in values.values()
            )
        ):
            raise RuntimeError("V2.48.45 task integer receipt drifted")
        unknown = table.get("unknown_cell_ratio")
        wall = timing.get("task_wall_seconds")
        if (
            isinstance(unknown, bool)
            or not isinstance(unknown, (int, float))
            or not 0 <= float(unknown) <= 1
            or isinstance(wall, bool)
            or not isinstance(wall, (int, float))
            or not math.isfinite(float(wall))
            or float(wall) < 0
        ):
            raise RuntimeError("V2.48.45 task continuous receipt drifted")
        output[opaque] = {
            **values,
            "unknown_cell_ratio": float(unknown),
            "task_wall_seconds": float(wall),
        }
    return output


def _failure_class(metric: Mapping[str, Any], message: str) -> str:
    if metric["valid"] is not True:
        return "evaluator_invalid"
    if float(metric["metrics"]["score"]) > 0:
        return "whole_table_success"
    if message == "schema":
        return "visible_schema_mismatch"
    if message == "entity" or float(metric["metrics"]["entity_acc"]) == 0:
        return "entity_anchor_failure"
    return "partial_quality"


def _aggregate(
    ids: set[str], metrics: Mapping[str, Mapping[str, Any]],
    tasks: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if not ids:
        raise RuntimeError("V2.48.45 cannot aggregate empty group")
    quality = {
        key: sum(float(metrics[item]["metrics"][key]) for item in ids) / len(ids)
        for key in QUALITY
    }
    quality["quality_composite"] = sum(quality[key] for key in COMPOSITE) / 4
    return {
        "n": len(ids),
        "evaluator_valid": sum(bool(metrics[item]["valid"]) for item in ids),
        "metrics": quality,
        "mechanism_means": {
            key: sum(float(tasks[item][key]) for item in ids) / len(ids)
            for key in MECHANISM
        },
    }


def _paired(
    ids: set[str], control: Mapping[str, Mapping[str, Any]],
    candidate: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    exact: Counter[str] = Counter()
    deltas: list[float] = []
    for item in sorted(ids):
        before = float(control[item]["metrics"]["score"]) > 0
        after = float(candidate[item]["metrics"]["score"]) > 0
        exact[
            "both_exact"
            if before and after
            else "lost_exact"
            if before
            else "gained_exact"
            if after
            else "neither_exact"
        ] += 1
        deltas.append(
            sum(
                float(candidate[item]["metrics"][key])
                - float(control[item]["metrics"][key])
                for key in COMPOSITE
            )
            / 4
        )
    rng = random.Random(BOOTSTRAP_SEED)
    means = sorted(
        sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas)
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    return {
        "n": len(ids),
        "exact_transitions": dict(sorted(exact.items())),
        "composite_delta": sum(deltas) / len(deltas),
        "composite_task_cluster_bootstrap": {
            "seed": BOOTSTRAP_SEED,
            "resamples": BOOTSTRAP_RESAMPLES,
            "percentile_95_interval": [means[500], means[19499]],
            "direction_counts": {
                "improved": sum(value > 0 for value in deltas),
                "tied": sum(value == 0 for value in deltas),
                "worsened": sum(value < 0 for value in deltas),
            },
        },
    }


def _bin_aggregate(
    values: Mapping[str, Mapping[str, Any]], key: str,
    intervals: tuple[tuple[int, int], ...],
) -> list[dict[str, Any]]:
    output = []
    for lower, upper in intervals:
        rows = [row for row in values.values() if lower <= float(row[key]) < upper]
        if not rows:
            continue
        output.append(
            {
                "lower_inclusive": lower,
                "upper_exclusive": upper,
                "n": len(rows),
                "whole_table_successes": sum(bool(row["exact"]) for row in rows),
                "quality_composite": sum(float(row["composite"]) for row in rows)
                / len(rows),
                "entity_acc": sum(float(row["entity_acc"]) for row in rows)
                / len(rows),
            }
        )
    return output


def build(*, now: int | None = None) -> dict[str, Any]:
    parents = _validate_parents()
    metrics = {name: _metric_rows(paths["root"]) for name, paths in VERSIONS.items()}
    messages = {name: _message_classes(paths["root"]) for name, paths in VERSIONS.items()}
    tasks = {name: _task_rows(paths["root"]) for name, paths in VERSIONS.items()}
    ids = set(metrics["v24800"])
    if any(ids != set(value) for value in (*metrics.values(), *tasks.values())):
        raise RuntimeError("V2.48.45 paired identity population drifted")
    groups: dict[str, dict[str, set[str]]] = {}
    aggregates: dict[str, dict[str, Any]] = {}
    joined: dict[str, dict[str, dict[str, Any]]] = {}
    for name in VERSIONS:
        if {row["instance"] for row in metrics[name].values()} != set(messages[name]):
            raise RuntimeError("V2.48.45 evaluator message join drifted")
        current: dict[str, set[str]] = defaultdict(set)
        joined[name] = {}
        for item in ids:
            metric = metrics[name][item]
            failure = _failure_class(metric, messages[name][metric["instance"]])
            current[failure].add(item)
            joined[name][item] = {
                **tasks[name][item],
                "exact": float(metric["metrics"]["score"]) > 0,
                "composite": sum(float(metric["metrics"][key]) for key in COMPOSITE)
                / 4,
                "entity_acc": float(metric["metrics"]["entity_acc"]),
            }
        groups[name] = current
        aggregates[name] = {
            key: _aggregate(members, metrics[name], tasks[name])
            for key, members in sorted(current.items())
        }
    paired = {
        "v24800_to_v24844": _paired(ids, metrics["v24800"], metrics["v24844"]),
        "v24840_to_v24844": _paired(ids, metrics["v24840"], metrics["v24844"]),
    }
    bins = {
        "fetch_failures": _bin_aggregate(
            joined["v24844"], "fetch_failures", ((0, 1), (1, 3), (3, 5), (5, 8), (8, 1000))
        ),
        "usable_pages": _bin_aggregate(
            joined["v24844"], "usable_pages", ((0, 3), (3, 6), (6, 9), (9, 1000))
        ),
        "projected_chars": _bin_aggregate(
            joined["v24844"], "projected_chars",
            ((0, 4000), (4000, 8000), (8000, 12000), (12000, 15000), (15000, 1000000)),
        ),
        "synthesized_rows": _bin_aggregate(
            joined["v24844"], "synthesized_rows", ((0, 2), (2, 5), (5, 10), (10, 20), (20, 1000000))
        ),
    }
    v44_result = parents["v24844"]["result"]["metrics"]["all_220"]
    v00_result = parents["v24800"]["result"]["metrics"]["all_220"]
    v44_summary = parents["v24844"]["summary"]
    v00_summary = parents["v24800"]["summary"]
    checks = {
        "all_three_parent_chains_valid": len(parents) == 3,
        "all_three_denominators_exact220": all(
            sum(value["n"] for value in aggregates[name].values()) == SELECTED
            for name in VERSIONS
        ),
        "v24844_failure_partition_reconciles": {
            key: value["n"] for key, value in aggregates["v24844"].items()
        }
        == {
            "entity_anchor_failure": 54,
            "evaluator_invalid": 11,
            "partial_quality": 142,
            "visible_schema_mismatch": 8,
            "whole_table_success": 5,
        },
        "paired_transitions_reconcile_exact220": all(
            sum(value["exact_transitions"].values()) == SELECTED
            for value in paired.values()
        ),
        "v24844_result_metrics_reconcile": v44_result["whole_table_successes"] == 5
        and abs(v44_result["quality_composite"] - 0.4496195144415094) < 1e-15,
        "transport_totals_reconcile": v44_summary["search_calls"] == 408
        and v44_summary["search_fetch_calls"] == 1995,
        "tavily_and_keyless_search_surfaces_differ": "direct_search_totals" in v00_summary
        and "direct_search_totals" not in v44_summary,
        "projection_trigger_telemetry_absent": all(
            "table_header_dependency" not in json.dumps(tasks["v24844"][item])
            for item in ids
        ),
        "opaque_identifier_not_emitted": OPAQUE.search(json.dumps({"a": aggregates, "p": paired, "b": bins})) is None,
        "credential_literal_not_emitted": SECRET.search(json.dumps({"a": aggregates, "p": paired, "b": bins})) is None,
    }
    value = {
        "artifact_version": 1,
        "role": "v24845_v24844_aggregate_evidence_supply_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "atomic_header_exact_regressed_composite_partially_recovered_evidence_supply_is_primary_observed_gradient",
        "parents": {
            name: {
                "result_sha256": contract.sha256(ROOT / paths["result"]),
                "postresult_audit_sha256": contract.sha256(ROOT / paths["post"]),
                "run_summary_sha256": contract.sha256(ROOT / paths["root"] / "run_summary.json"),
                "conservative_summary_sha256": contract.sha256(
                    ROOT / paths["root"] / "evaluator/conservative_summary.json"
                ),
            }
            for name, paths in VERSIONS.items()
        },
        "boundary": {
            "all_predictions_and_evaluators_terminal_before_analysis": True,
            "offline_alignment_uses_identifiers_in_memory_only": True,
            "task_identifier_question_prediction_answer_query_url_page_field_or_evaluator_text_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_feedback_retry_resume_or_selective_revaluation": False,
            "failure_class_bin_or_historical_score_authorized_as_future_runtime_route": False,
        },
        "failure_class_aggregates": aggregates,
        "paired": paired,
        "v24844_observational_bins": bins,
        "search_surface_comparison": {
            "v24800": {
                "provider_family": "tavily_url_lead_deterministic_fetch",
                "search_calls": v00_summary["search_calls"],
                "search_fetch_calls": v00_summary["search_fetch_calls"],
                "system_total_tokens": v00_result["system_total_tokens"],
                "whole_table_successes": v00_result["whole_table_successes"],
                "quality_composite": v00_result["quality_composite"],
                "mean_projected_chars": sum(
                    float(tasks["v24800"][item]["projected_chars"]) for item in ids
                ) / SELECTED,
            },
            "v24844": {
                "provider_family": "keyless_hosted_search_deterministic_fetch",
                "search_calls": v44_summary["search_calls"],
                "search_fetch_calls": v44_summary["search_fetch_calls"],
                "system_total_tokens": v44_result["system_total_tokens"],
                "whole_table_successes": v44_result["whole_table_successes"],
                "quality_composite": v44_result["quality_composite"],
                "mean_projected_chars": sum(
                    float(tasks["v24844"][item]["projected_chars"]) for item in ids
                ) / SELECTED,
            },
        },
        "conclusions": {
            "v24844_exceeds_v24840_composite_point_estimate": paired["v24840_to_v24844"]["composite_delta"] > 0,
            "v24844_exceeds_v24840_exact": False,
            "v24844_exceeds_internal_v24800_exact_or_composite": False,
            "v24844_atomic_header_causal_quality_gain_established": False,
            "atomic_header_dependency_actual_trigger_rate_observable": False,
            "fetch_failure_and_context_volume_are_strong_observational_quality_gradients": True,
            "observational_bins_establish_causal_budget_gain": False,
            "v24800_to_v24844_changes_are_confounded_by_search_provider_and_projection_budget": True,
            "entropy_or_information_gain_credit_validated": False,
            "leaderboard_or_sota_established": False,
        },
        "next_work": {
            "candidate": "v24842_atomic_header_closure_with_30000_rendered_character_cap",
            "single_behavior_change": "rendered_projection_cap_16000_to_30000",
            "required_content_free_projection_receipt": [
                "projected_rendered_characters",
                "selected_table_continuation_block_count",
                "table_header_dependency_addition_count",
                "orphan_selected_table_continuation_block_count",
                "supported_and_retained_visible_requirement_counts",
            ],
            "required_external_shared_prefix_gate": True,
            "same_raw_page_bytes_before_16k_versus_30k_branch": True,
            "matched_search_model_prompt_and_synthesis": True,
            "entropy_information_gain_weight": 0.0,
            "public_exact220_before_external_gate": False,
        },
        "authorization": {
            "thirty_k_atomic_projector_and_observability_build": all(checks.values()),
            "fresh_external_shared_prefix_protocol_design": all(checks.values()),
            "external_launch": False,
            "public_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
    }
    value["diagnosis_valid"] = not value["findings"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if (
        OPAQUE.search(encoded)
        or INSTANCE.search(encoded)
        or SECRET.search(encoded)
        or "required_columns" in encoded
        or "the entity is wrong" in encoded
    ):
        raise RuntimeError("V2.48.45 emitted prohibited task-level content")
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate(value, rebuild=False)


def validate(value: Mapping[str, Any], *, rebuild: bool = True) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role") != "v24845_v24844_aggregate_evidence_supply_diagnosis"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization")
        != {
            "thirty_k_atomic_projector_and_observability_build": True,
            "fresh_external_shared_prefix_protocol_design": True,
            "external_launch": False,
            "public_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.45 diagnosis drifted")
    if rebuild:
        expected = build(now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.48.45 diagnosis is not reproducible")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    artifact = build()
    publish(ROOT / OUTPUT, artifact)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "status": artifact["status"],
                "v24844_classes": {
                    key: value["n"]
                    for key, value in artifact["failure_class_aggregates"]["v24844"].items()
                },
                "authorization": artifact["authorization"],
            },
            sort_keys=True,
        )
    )
