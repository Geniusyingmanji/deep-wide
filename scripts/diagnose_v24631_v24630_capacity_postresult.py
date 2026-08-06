#!/usr/bin/env python3
"""Content-free capacity diagnosis for the frozen V2.46.30 exact-220.

The script runs only after the exact-220 prediction freeze and post-result audit.
It validates sealed aggregate artifacts plus content-free execution receipts.  For
the 218 complete child bundles it opens the frozen result envelope only to run
the existing schema/cross-artifact validators and aggregate numeric runtime
fields.  It never reads visible_task.json, runtime_predictions.jsonl, mapping,
gold, category, split, evaluator details, or score rows, and it emits no task
position, task hash, question, query, URL, page, prediction, or credential.
"""

from __future__ import annotations

import json
import math
import os
import re
import statistics
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24280_task_union_single_shot import (  # noqa: E402
    validate_receipt as validate_single,
)
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
    validate_parent_receipt,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model_slot,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24318_deadline_conservation_runtime import (  # noqa: E402
    MODEL_FIELD,
    STAGES,
    validate_model_receipt,
)
from deepwide_agent.v24630_exact220_contract import (  # noqa: E402
    ARM,
    FORWARD_RESULT,
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    PREDICTION_FREEZE,
    PROTOCOL_ID,
    RUN_SUMMARY,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    read_object,
    sha256,
)
from deepwide_agent.v24630_exact220_task_integration import (  # noqa: E402
    validate_cross_artifacts,
    validate_envelope,
)
from deepwide_agent.v24630_thin_backfill_search import (  # noqa: E402
    validate_receipt as validate_backfill,
)


OUTPUT = Path(
    "results/v24631_v24630_content_free_capacity_diagnosis_v1_20260806.json"
)
FORWARD_AUDIT = Path("results/v24630_exact220_forward_audit_v1_20260806.json")
FINAL_RESULT = Path("results/v24630_exact220_result_v1_20260806.json")
POSTRESULT_AUDIT = Path(
    "results/v24630_exact220_postresult_audit_v1_20260806.json"
)
RESULT_NAME = "result.json"
MODEL_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
SINGLE_NAME = "search_single_shot_receipt.json"
BACKFILL_NAME = "citation_title_backfill_receipt.json"
CHILD_NAME = "child_terminal_receipt.json"
PARENT_NAME = "parent_exit_receipt.json"
VISIBLE_NAME = "visible_task.json"
SAFE_PROGRESS_NAME = "safe_progress.json"
MODEL_GENERATED = frozenset(
    {"primary", "normalized_primary", "repaired", "normalized_repaired"}
)
SECRET_PREFIXES = (
    "gh" + "p_",
    "github_" + "pat_",
    "tvly-" + "dev-",
    "s" + "k-",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _ordinary(path: Path) -> Path:
    root = ROOT.resolve()
    candidate = path.resolve(strict=False)
    if (
        path.is_symlink()
        or not path.is_file()
        or not candidate.is_relative_to(root)
    ):
        raise RuntimeError(f"V2.46.31 expected ordinary repository file: {path}")
    return path


def _absent(path: Path) -> bool:
    return not path.exists() and not path.is_symlink()


def _task_directories(root: Path) -> list[Path]:
    base = root / TASK_ROOT
    if base.is_symlink() or not base.is_dir():
        raise RuntimeError("V2.46.31 frozen task root is absent")
    expected = [
        base / f"task_{position:04d}"
        for position in range(1, SELECTED_COUNT + 1)
    ]
    if any(path.is_symlink() or not path.is_dir() for path in expected):
        raise RuntimeError("V2.46.31 exact-220 task partition is incomplete")
    present = sorted(path for path in base.glob("task_*") if path.is_dir())
    if present != expected:
        raise RuntimeError("V2.46.31 exact-220 task partition drifted")
    return expected


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("V2.46.31 cannot summarize an empty vector")
    position = (len(ordered) - 1) * float(probability)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _summary(values: Sequence[float]) -> dict[str, Any]:
    numbers = [float(value) for value in values]
    if not numbers or any(not math.isfinite(value) for value in numbers):
        raise ValueError("V2.46.31 invalid numeric summary input")
    return {
        "count": len(numbers),
        "sum": round(sum(numbers), 6),
        "mean": round(statistics.fmean(numbers), 6),
        "minimum": round(min(numbers), 6),
        "p50": round(_quantile(numbers, 0.50), 6),
        "p95": round(_quantile(numbers, 0.95), 6),
        "maximum": round(max(numbers), 6),
    }


def _validate_parents(root: Path) -> dict[str, dict[str, Any]]:
    forward = read_object(_ordinary(root / FORWARD_RESULT))
    forward_audit = read_object(_ordinary(root / FORWARD_AUDIT))
    summary = read_object(_ordinary(root / RUN_SUMMARY))
    freeze = read_object(_ordinary(root / PREDICTION_FREEZE))
    final = read_object(_ordinary(root / FINAL_RESULT))
    post = read_object(_ordinary(root / POSTRESULT_AUDIT))
    checks = forward_audit.get("checks")
    post_checks = post.get("checks")
    if (
        not _sealed(forward, "result_payload_sha256")
        or not _sealed(forward_audit, "audit_payload_sha256")
        or not _sealed(summary, "summary_payload_sha256")
        or not _sealed(freeze, "freeze_payload_sha256")
        or not _sealed(final, "result_payload_sha256")
        or not _sealed(post, "audit_payload_sha256")
        or forward.get("protocol_id") != PROTOCOL_ID
        or forward.get("selected") != SELECTED_COUNT
        or forward.get("terminal_predictions") != SELECTED_COUNT
        or forward.get("model_generated_tables") != 186
        or forward.get("fallback_tables") != 34
        or forward.get("resume_retry_skip_or_rerun_launched") is not False
        or summary.get("selected") != SELECTED_COUNT
        or summary.get("completed") != SELECTED_COUNT
        or summary.get("failed") != 0
        or summary.get("model_generated_tables") != 186
        or summary.get("fallback_tables") != 34
        or summary.get("completion_kinds")
        != {
            "best_effort_fallback": 32,
            "normalized_primary": 6,
            "primary": 179,
            "repaired": 1,
            "worker_failure_fallback": 2,
        }
        or summary.get("parent_exit_taxonomy")
        != {"child_nonzero_with_terminal_receipt": 2, "success": 218}
        or freeze.get("selected") != SELECTED_COUNT
        or freeze.get("terminal") != SELECTED_COUNT
        or freeze.get("label_blind") is not True
        or not isinstance(checks, Mapping)
        or not checks
        or not all(value is True for value in checks.values())
        or forward_audit.get("findings") != []
        or forward_audit.get("audit_valid") is not True
        or not isinstance(post_checks, Mapping)
        or len(post_checks) != 31
        or not all(value is True for value in post_checks.values())
        or post.get("findings") != []
        or post.get("audit_valid") is not True
        or post.get("provenance", {}).get("final_result_sha256")
        != sha256(root / FINAL_RESULT)
    ):
        raise RuntimeError("V2.46.31 frozen parent artifact drifted")
    return {
        "forward": forward,
        "forward_audit": forward_audit,
        "summary": summary,
        "freeze": freeze,
        "final": final,
        "post": post,
    }


def _validate_complete_bundle(directory: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    result_path = _ordinary(directory / RESULT_NAME)
    model_path = _ordinary(directory / MODEL_NAME)
    transport_path = _ordinary(directory / TRANSPORT_NAME)
    single_path = _ordinary(directory / SINGLE_NAME)
    backfill_path = _ordinary(directory / BACKFILL_NAME)
    envelope = validate_envelope(read_object(result_path))
    model = validate_model_slot(
        read_object(model_path), expected_cap=MODEL_SLOT_CAP
    )
    transport = validate_transport_health(read_object(transport_path))
    single = read_object(single_path)
    backfill = validate_backfill(read_object(backfill_path))
    validate_single(single)
    validate_cross_artifacts(
        envelope["result"],
        arm=ARM,
        model_slot_receipt=model,
        transport_health=transport,
        search_single_shot_receipt=single,
        citation_title_backfill_receipt=backfill,
        expected_cap=MODEL_SLOT_CAP,
    )
    if (
        envelope["model_slot_receipt"] != model
        or envelope["transport_health"] != transport
        or envelope["search_single_shot_receipt"] != single
        or envelope["citation_title_backfill_receipt"] != backfill
    ):
        raise RuntimeError("V2.46.31 complete bundle independent receipt drifted")
    return envelope["result"], model


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {name: int(counter[name]) for name in sorted(counter)}


def _stage_dict(counters: Mapping[str, Counter[str]]) -> dict[str, dict[str, int]]:
    return {
        group: {stage: int(counters[group][stage]) for stage in STAGES}
        for group in ("logical_admissions", "provider_requests", "provider_attempts", "pre_provider_rejections")
    }


def _aggregate(root: Path, parents: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    del parents
    completion: Counter[str] = Counter()
    parent_taxonomy: Counter[str] = Counter()
    child_stages: Counter[str] = Counter()
    exception_types: Counter[str] = Counter()
    complete_stage = {
        "logical_admissions": Counter(),
        "provider_requests": Counter(),
        "provider_attempts": Counter(),
        "pre_provider_rejections": Counter(),
    }
    complete_effect = Counter()
    model_totals = Counter()
    model_wait_seconds: list[float] = []
    model_max_wait_seconds: list[float] = []
    success_evidence_chars: list[float] = []
    fallback_evidence_chars: list[float] = []
    success_elapsed: list[float] = []
    fallback_elapsed: list[float] = []
    worker_parent_elapsed: list[float] = []
    timeout_contingency = {
        "model_generated": Counter(),
        "fallback": Counter(),
    }
    complete_bundles = 0
    terminal_worker_failures = 0
    worker_model = Counter()

    for directory in _task_directories(root):
        model = validate_model_slot(
            read_object(_ordinary(directory / MODEL_NAME)),
            expected_cap=MODEL_SLOT_CAP,
        )
        child = validate_child_receipt(
            read_object(_ordinary(directory / CHILD_NAME))
        )
        parent = validate_parent_receipt(
            read_object(_ordinary(directory / PARENT_NAME))
        )
        if not (directory / VISIBLE_NAME).is_file():
            raise RuntimeError("V2.46.31 task presence surface drifted")
        parent_taxonomy[str(parent["failure_taxonomy"])] += 1
        child_stages[str(child["stage"])] += 1
        exception_types[str(child["exception_type"] or "none")] += 1
        model_totals.update(
            {
                "acquisitions": int(model["acquisitions"]),
                "slot_timeouts": int(model["slot_timeouts"]),
                "provider_deadline_failures": int(model["provider_deadline_failures"]),
                "deadline_exhausted_tasks": int(model["deadline_exhausted"] is True),
                "tasks_with_slot_timeout": int(int(model["slot_timeouts"]) > 0),
            }
        )
        model_wait_seconds.append(float(model["total_wait_seconds"]))
        model_max_wait_seconds.append(float(model["max_wait_seconds"]))

        if parent["failure_taxonomy"] == "success":
            result, independent_model = _validate_complete_bundle(directory)
            if independent_model != model:
                raise RuntimeError("V2.46.31 model receipt changed across reads")
            receipt = validate_model_receipt(result[MODEL_FIELD])
            kind = str(result["completion_kind"])
            complete_bundles += 1
            completion[kind] += 1
            for stage in STAGES:
                complete_stage["logical_admissions"][stage] += int(
                    receipt["logical_admissions_by_stage"][stage]
                )
                complete_stage["provider_requests"][stage] += int(
                    receipt["provider_requests_by_stage"][stage]
                )
                complete_stage["provider_attempts"][stage] += int(
                    receipt["provider_attempts_by_stage"][stage]
                )
                complete_stage["pre_provider_rejections"][stage] += int(
                    receipt["pre_provider_rejections_by_stage"][stage]
                )
            complete_effect.update(
                {
                    "logical_admissions": int(receipt["logical_admissions_total"]),
                    "provider_requests": int(receipt["provider_requests_total"]),
                    "provider_attempts": int(receipt["provider_attempts_total"]),
                    "pre_provider_rejections": int(receipt["pre_provider_rejections_total"]),
                    "initial_synthesis_errors": int(receipt["synthesis_initial_model_request_error"]),
                    "recovery_attempted": int(receipt["synthesis_recovery_attempted"]),
                    "recovery_succeeded": int(receipt["synthesis_recovery_succeeded"]),
                    "recovery_failed": int(receipt["synthesis_recovery_model_request_error"]),
                    "repair_blocked_after_recovery": int(receipt["repair_blocked_after_recovery"]),
                }
            )
            projected = float(result["evidence"]["projected_chars"])
            elapsed = float(result["budget"]["elapsed_seconds"])
            if kind in MODEL_GENERATED:
                timeout_contingency["model_generated"][
                    "with_slot_timeout" if model["slot_timeouts"] else "without_slot_timeout"
                ] += 1
                success_evidence_chars.append(projected)
                success_elapsed.append(elapsed)
            elif kind == "best_effort_fallback":
                timeout_contingency["fallback"][
                    "with_slot_timeout" if model["slot_timeouts"] else "without_slot_timeout"
                ] += 1
                fallback_evidence_chars.append(projected)
                fallback_elapsed.append(elapsed)
            else:
                raise RuntimeError("V2.46.31 unknown complete terminal kind")
        else:
            terminal_worker_failures += 1
            worker_model.update(
                {
                    "acquisitions": int(model["acquisitions"]),
                    "slot_timeouts": int(model["slot_timeouts"]),
                    "provider_deadline_failures": int(
                        model["provider_deadline_failures"]
                    ),
                    "deadline_exhausted_tasks": int(
                        model["deadline_exhausted"] is True
                    ),
                }
            )
            completion["worker_failure_fallback"] += 1
            timeout_contingency["fallback"][
                "with_slot_timeout" if model["slot_timeouts"] else "without_slot_timeout"
            ] += 1
            worker_parent_elapsed.append(float(parent["elapsed_seconds"]))
            if (
                parent["failure_taxonomy"] != "child_nonzero_with_terminal_receipt"
                or child["stage"] != "child_exception"
                or child["exception_type"] != "ValidationError"
                or child["model_receipt_written"] is not True
                or child["result_envelope_written"] is not False
                or child["transport_receipt_written"] is not False
                or int(model["slot_timeouts"]) <= 0
                or model["deadline_exhausted"] is not True
                or not all(
                    _absent(directory / name)
                    for name in (RESULT_NAME, TRANSPORT_NAME, SINGLE_NAME, BACKFILL_NAME)
                )
            ):
                raise RuntimeError("V2.46.31 terminal worker-failure stratum drifted")

    complete_stage_totals = {
        group: sum(values.values()) for group, values in complete_stage.items()
    }
    complete_model_acquisitions = (
        model_totals["acquisitions"] - worker_model["acquisitions"]
    )
    complete_model_timeouts = (
        model_totals["slot_timeouts"] - worker_model["slot_timeouts"]
    )
    complete_conservation = (
        complete_effect["logical_admissions"]
        == complete_effect["provider_requests"]
        + complete_effect["pre_provider_rejections"]
        and complete_effect["provider_requests"] == complete_model_acquisitions
        and complete_effect["pre_provider_rejections"] == complete_model_timeouts
        and complete_stage_totals["logical_admissions"]
        == complete_effect["logical_admissions"]
        and complete_stage_totals["provider_requests"]
        == complete_effect["provider_requests"]
        and complete_stage_totals["provider_attempts"]
        == complete_effect["provider_attempts"]
        and complete_stage_totals["pre_provider_rejections"]
        == complete_effect["pre_provider_rejections"]
    )
    success_stats = _summary(success_evidence_chars)
    fallback_stats = _summary(fallback_evidence_chars)
    evidence_mean_ratio = fallback_stats["mean"] / success_stats["mean"]
    return {
        "denominators": {
            "terminal_tasks": SELECTED_COUNT,
            "complete_child_bundles": complete_bundles,
            "terminal_worker_failures": terminal_worker_failures,
            "model_generated_tables": int(
                sum(completion[name] for name in MODEL_GENERATED)
            ),
            "fallback_tables": int(
                completion["best_effort_fallback"]
                + completion["worker_failure_fallback"]
            ),
        },
        "completion_kinds": _counter_dict(completion),
        "parent_exit_taxonomy": _counter_dict(parent_taxonomy),
        "child_terminal_stages": _counter_dict(child_stages),
        "child_exception_types": _counter_dict(exception_types),
        "slot_timeout_contingency": {
            group: {
                "without_slot_timeout": int(values["without_slot_timeout"]),
                "with_slot_timeout": int(values["with_slot_timeout"]),
            }
            for group, values in timeout_contingency.items()
        },
        "complete_bundle_model_accounting": {
            "tasks": complete_bundles,
            "stage_totals": _stage_dict(complete_stage),
            "totals": {
                name: int(complete_effect[name])
                for name in (
                    "logical_admissions",
                    "provider_requests",
                    "provider_attempts",
                    "pre_provider_rejections",
                    "initial_synthesis_errors",
                    "recovery_attempted",
                    "recovery_succeeded",
                    "recovery_failed",
                    "repair_blocked_after_recovery",
                )
            },
            "model_slot_acquisitions": int(complete_model_acquisitions),
            "model_slot_timeouts": int(complete_model_timeouts),
            "conservation_verified": complete_conservation,
        },
        "terminal_model_slot_accounting": {
            "tasks": SELECTED_COUNT,
            "acquisitions": int(model_totals["acquisitions"]),
            "slot_timeouts": int(model_totals["slot_timeouts"]),
            "provider_deadline_failures": int(
                model_totals["provider_deadline_failures"]
            ),
            "tasks_with_slot_timeout": int(model_totals["tasks_with_slot_timeout"]),
            "deadline_exhausted_tasks": int(model_totals["deadline_exhausted_tasks"]),
            "total_wait_seconds": round(sum(model_wait_seconds), 6),
            "per_task_total_wait_seconds": _summary(model_wait_seconds),
            "per_effect_max_wait_seconds": _summary(model_max_wait_seconds),
        },
        "worker_failure_boundary": {
            "tasks": terminal_worker_failures,
            "model_slot_acquisitions": int(worker_model["acquisitions"]),
            "model_slot_timeouts": int(worker_model["slot_timeouts"]),
            "provider_deadline_failures": int(
                worker_model["provider_deadline_failures"]
            ),
            "deadline_exhausted_tasks": int(
                worker_model["deadline_exhausted_tasks"]
            ),
            "semantic_model_stage_from_unsealed_safe_progress_published": False,
            "parent_elapsed_seconds": _summary(worker_parent_elapsed),
        },
        "evidence_and_latency": {
            "model_generated_projected_chars": success_stats,
            "best_effort_fallback_projected_chars": fallback_stats,
            "best_effort_to_model_generated_mean_projected_chars_ratio": round(
                evidence_mean_ratio, 6
            ),
            "model_generated_elapsed_seconds": _summary(success_elapsed),
            "best_effort_fallback_elapsed_seconds": _summary(fallback_elapsed),
        },
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parents = _validate_parents(root)
    aggregate = _aggregate(root, parents)
    denominators = aggregate["denominators"]
    contingency = aggregate["slot_timeout_contingency"]
    complete = aggregate["complete_bundle_model_accounting"]
    terminal = aggregate["terminal_model_slot_accounting"]
    backfill = parents["summary"]["backfill_totals"]
    mechanism = parents["final"]["mechanism"]
    if (
        denominators
        != {
            "terminal_tasks": 220,
            "complete_child_bundles": 218,
            "terminal_worker_failures": 2,
            "model_generated_tables": 186,
            "fallback_tables": 34,
        }
        or aggregate["completion_kinds"]
        != {
            "best_effort_fallback": 32,
            "normalized_primary": 6,
            "primary": 179,
            "repaired": 1,
            "worker_failure_fallback": 2,
        }
        or contingency["model_generated"]
        != {"without_slot_timeout": 186, "with_slot_timeout": 0}
        or contingency["fallback"]
        != {"without_slot_timeout": 0, "with_slot_timeout": 34}
        or complete["totals"]
        != {
            "logical_admissions": 458,
            "provider_requests": 426,
            "provider_attempts": 443,
            "pre_provider_rejections": 32,
            "initial_synthesis_errors": 33,
            "recovery_attempted": 20,
            "recovery_succeeded": 2,
            "recovery_failed": 18,
            "repair_blocked_after_recovery": 0,
        }
        or complete["conservation_verified"] is not True
        or terminal["acquisitions"] != 427
        or terminal["slot_timeouts"] != 35
        or terminal["provider_deadline_failures"] != 18
        or terminal["tasks_with_slot_timeout"] != 34
        or terminal["deadline_exhausted_tasks"] != 34
        or backfill.get("backfilled_unique_url_count") != 40
        or backfill.get("query_local_shadowed_backfilled_url_count") != 40
        or backfill.get("surviving_backfilled_union_lead_count") != 0
        or mechanism.get("downstream_candidate_set_changed_by_backfill") is not False
    ):
        raise RuntimeError("V2.46.31 frozen capacity aggregate drifted")
    value = {
        "artifact_version": 1,
        "role": "v24631_v24630_content_free_capacity_postresult_diagnosis",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "forward_audit_sha256": sha256(root / FORWARD_AUDIT),
            "run_summary_sha256": sha256(root / RUN_SUMMARY),
            "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
            "exact220_result_sha256": sha256(root / FINAL_RESULT),
            "postresult_audit_sha256": sha256(root / POSTRESULT_AUDIT),
        },
        "boundary": {
            "postfreeze_postresult_only": True,
            "visible_task_files_read": False,
            "runtime_prediction_rows_read": False,
            "evaluator_detail_or_per_task_score_rows_read": False,
            "private_complete_result_envelopes_read_only_for_validation_and_numeric_runtime_aggregation": True,
            "mapping_gold_category_question_type_split_or_evaluator_feedback_used": False,
            "task_position_hash_identifier_question_query_url_page_prediction_or_credential_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_forward_resume_retry_skip_or_rerun": False,
            "selective_evaluation_or_revaluation": False,
        },
        "aggregate": aggregate,
        "backfill": {
            "backfilled_unique_urls": 40,
            "query_local_shadowed_backfilled_urls": 40,
            "surviving_downstream_leads": 0,
            "downstream_candidate_set_changed": False,
        },
        "conclusions": {
            "all_fallback_tasks_cooccurred_with_model_slot_timeout": True,
            "all_model_generated_tasks_had_zero_model_slot_timeout": True,
            "task_level_slot_timeout_fallback_association_is_perfect_in_this_run": True,
            "randomized_causal_effect_of_scheduling_established": False,
            "insufficient_search_depth_established_as_primary_bottleneck": False,
            "same_response_title_backfill_had_direct_downstream_effect": False,
            "synthesis_capacity_scheduling_is_next_intervention_target": True,
            "quality_improvement_demonstrated_by_diagnosis": False,
            "project_best_or_sota_reached": False,
        },
        "next_work": {
            "first": "deterministic content-free scheduling simulation",
            "candidate_schedules": [
                "eager_32_tasks_8_model_slots_150_second_deadline",
                "bounded_active_child_admission",
                "longer_task_deadline_without_more_model_search_or_fetch_work",
                "synthesis_and_repair_priority_model_slots",
            ],
            "second": "neutral non-benchmark keyless provider stress test",
            "mechanism_gate": {
                "pre_provider_synthesis_rejections": 0,
                "fallback_target": "zero_or_preregistered_near_zero_bound",
                "exact_effect_accounting": True,
                "additional_model_search_or_fetch_work": False,
                "competitive_projected_exact220_wall_time_required": True,
            },
            "new_label_blind_benchmark_only_after_mechanism_gate": True,
            "final_quality_confirmation_population": 220,
        },
        "authorization": {
            "deterministic_content_free_simulation": True,
            "neutral_non_benchmark_provider_stress_test_after_preregistration": True,
            "additional_dev64": False,
            "new_exact220": False,
            "same_run_evaluator_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if SECRET.search(encoded) or OPAQUE.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.46.31 diagnosis emitted prohibited content")
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    expected = build_report(root, now=int(value.get("created_at_unix", -1)))
    if dict(value) != expected or not _sealed(value, "diagnosis_payload_sha256"):
        raise RuntimeError("V2.46.31 diagnosis drifted")
    return dict(value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    validate_report(ROOT, report)
    publish(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "terminal_tasks": report["aggregate"]["denominators"][
                    "terminal_tasks"
                ],
                "fallback_tables": report["aggregate"]["denominators"][
                    "fallback_tables"
                ],
                "slot_timeouts": report["aggregate"][
                    "terminal_model_slot_accounting"
                ]["slot_timeouts"],
            },
            sort_keys=True,
        )
    )
