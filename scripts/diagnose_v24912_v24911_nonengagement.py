#!/usr/bin/env python3
"""Aggregate-only diagnosis of the V2.49.11 long-page treatment.

Both compared exact-220 prediction and evaluator chains are already terminal.
Private task artifacts are read only to aggregate content-free counters.  The
report emits no question, query, URL, page, prediction, identifier, or
per-task score, and cannot authorize benchmark-specific routing.
"""

from __future__ import annotations

import ast
import hashlib
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

from deepwide_agent import v24287_forward_contract as helper_contract  # noqa: E402
from deepwide_agent import v24287_hard_deadline_fetch as fetch_boundary  # noqa: E402
from deepwide_agent import v24909_keyless_fixed_budget_exact220_contract as control  # noqa: E402
from deepwide_agent import v24911_long_page_exact220_contract as candidate  # noqa: E402
from deepwide_agent.v24839_structure_preserving_projector import (  # noqa: E402
    visible_requirement_groups,
)


DATE = "20260808"
OUTPUT = Path(f"results/v24912_v24911_nonengagement_diagnosis_v1_{DATE}.json")
SELECTED = 220
LEGACY_PAGE_CAP = 5_000
CANDIDATE_DECLARED_INPUT_CAP = 12_000
DIAGNOSIS = Path("scripts/diagnose_v24912_v24911_nonengagement.py")
TEST = Path("tests/test_diagnose_v24912_v24911_nonengagement.py")
HELPER = Path("scripts/run_v24287_fetch_helper.py")
HELPER_CONTRACT = Path("src/deepwide_agent/v24287_forward_contract.py")
FETCH_BOUNDARY = Path("src/deepwide_agent/v24287_hard_deadline_fetch.py")
CANDIDATE_CHILD = Path("scripts/run_v24911_long_page_exact220_task.py")
CANDIDATE_CONTRACT = Path(
    "src/deepwide_agent/v24911_long_page_exact220_contract.py"
)
PACKER = Path("src/deepwide_agent/v24911_long_page_evidence_packer.py")
SOURCES = (
    DIAGNOSIS,
    TEST,
    HELPER,
    HELPER_CONTRACT,
    FETCH_BOUNDARY,
    CANDIDATE_CHILD,
    CANDIDATE_CONTRACT,
    PACKER,
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
INSTANCE = re.compile(r"(?:deep2wide_result_|wide2deep_ws_)")

RUNS: dict[str, dict[str, Any]] = {
    "v24909": {
        "protocol_id": control.PROTOCOL_ID,
        "root": control.OUTPUT_ROOT,
        "result": Path(
            "results/v24909_keyless_fixed_budget_exact220_result_v1_20260808.json"
        ),
        "forward": control.FORWARD_AUDIT,
        "post": Path(
            "results/v24909_keyless_fixed_budget_exact220_postresult_audit_v1_20260808.json"
        ),
        "declared_page_cap": 5_000,
        "projector": "stable_prefix",
    },
    "v24911": {
        "protocol_id": candidate.PROTOCOL_ID,
        "root": candidate.OUTPUT_ROOT,
        "result": Path(
            "results/v24911_long_page_exact220_result_v1_20260808.json"
        ),
        "forward": candidate.FORWARD_AUDIT,
        "post": Path(
            "results/v24911_long_page_exact220_postresult_audit_v1_20260808.json"
        ),
        "declared_page_cap": 12_000,
        "projector": "visible_question_long_page_packer",
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
        raise RuntimeError(f"V2.49.12 expected ordinary repository file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.12 expected JSON object")
    return value


def _sha(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == candidate.payload_sha256(unsigned)


def _validate_parents() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for name, spec in RUNS.items():
        result = _read(spec["result"])
        forward = _read(spec["forward"])
        post = _read(spec["post"])
        summary_path = spec["root"] / "run_summary.json"
        summary = _read(summary_path)
        metrics = (result.get("metrics") or {}).get("all_220") or {}
        if (
            result.get("protocol_id") != spec["protocol_id"]
            or result.get("status") != "exact220_single_rollout_complete"
            or result.get("selected") != SELECTED
            or metrics.get("selected") != SELECTED
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
            raise RuntimeError(f"V2.49.12 frozen parent chain drifted: {name}")
        output[name] = {
            "result": result,
            "summary": summary,
            "result_sha256": _sha(spec["result"]),
            "forward_audit_sha256": _sha(spec["forward"]),
            "postresult_audit_sha256": _sha(spec["post"]),
            "run_summary_sha256": _sha(summary_path),
        }
    return output


def _number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise RuntimeError(f"V2.49.12 invalid content-free counter: {label}")
    return float(value)


def _task_aggregates(root: Path) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    completion: Counter[str] = Counter()
    observable = 0
    missing_telemetry = 0
    legacy_envelope_violations = 0
    visible_group_zero = 0
    receipt_files = 0
    prediction_hashes: list[str] = []
    for position in range(1, SELECTED + 1):
        directory = root / "tasks" / f"task_{position:04d}"
        envelope = _read(directory / "result.json")
        task = _read(directory / "visible_task.json")
        result = envelope.get("result") or {}
        if set(task) != {"opaque_id", "question"}:
            raise RuntimeError("V2.49.12 visible runtime input drifted")
        visible_group_zero += int(
            len(visible_requirement_groups(str(task["question"]))) == 0
        )
        prediction_hash = result.get("prediction_sha256")
        if not isinstance(prediction_hash, str) or len(prediction_hash) != 64:
            raise RuntimeError("V2.49.12 prediction hash binding drifted")
        prediction_hashes.append(prediction_hash)
        completion[str(result.get("completion_kind"))] += 1
        receipt_files += int((ROOT / directory / "projection_receipt.json").is_file())
        retrieval = result.get("two_wave_retrieval") or {}
        total = ((retrieval.get("receipt") or {}).get("total") or {})
        if not total:
            missing_telemetry += 1
            continue
        observable += 1
        usable = int(_number(total.get("usable_pages"), "usable_pages"))
        content = int(_number(total.get("content_chars"), "content_chars"))
        legacy_envelope_violations += int(content > LEGACY_PAGE_CAP * usable)
        evidence = result.get("evidence") or {}
        cost = result.get("cost") or {}
        model = cost.get("model") or {}
        search = cost.get("search") or {}
        table = ((result.get("telemetry") or {}).get("table") or {})
        timing = result.get("attributed_timing") or {}
        fields = {
            "queries_executed": total.get("queries_executed"),
            "fetches_attempted": total.get("fetches_attempted"),
            "usable_pages": usable,
            "unique_hosts": total.get("unique_hosts"),
            "content_chars": content,
            "projected_evidence_chars": evidence.get("projected_chars"),
            "synthesized_rows": table.get("row_count"),
            "unknown_cell_ratio_sum": table.get("unknown_cell_ratio"),
            "model_total_tokens": model.get("total_tokens"),
            "search_total_tokens": search.get("total_tokens"),
            "task_wall_seconds": timing.get("task_wall_seconds"),
        }
        for key, raw in fields.items():
            totals[key] += _number(raw, key)
    if sum(completion.values()) != SELECTED or observable + missing_telemetry != SELECTED:
        raise RuntimeError("V2.49.12 task denominator drifted")
    values = {name: round(float(value), 6) for name, value in sorted(totals.items())}
    for total_name, mean_name in (
        ("usable_pages", "mean_usable_pages"),
        ("unique_hosts", "mean_unique_hosts"),
        ("content_chars", "mean_content_chars"),
        ("projected_evidence_chars", "mean_projected_evidence_chars"),
        ("synthesized_rows", "mean_synthesized_rows"),
        ("unknown_cell_ratio_sum", "mean_unknown_cell_ratio"),
    ):
        values[mean_name] = round(
            values.get(total_name, 0.0) / observable if observable else 0.0, 12
        )
    values.pop("unknown_cell_ratio_sum", None)
    return {
        "observable_task_telemetry": observable,
        "missing_task_telemetry": missing_telemetry,
        "completion_kinds": dict(sorted(completion.items())),
        "visible_requirement_group_zero_task_count": visible_group_zero,
        "legacy_5000_character_per_usable_page_envelope_violation_count": (
            legacy_envelope_violations
        ),
        "content_free_projection_receipt_file_count": receipt_files,
        "prediction_hashes": prediction_hashes,
        "totals_and_means": values,
    }


def _helper_ast_binding() -> dict[str, Any]:
    tree = ast.parse(_ordinary(HELPER).read_text(encoding="utf-8"), str(HELPER))
    imported_limits = False
    max_page_chars_bound_to_limits = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported_limits |= (
                node.module == "deepwide_agent.v24287_forward_contract"
                and any(alias.name == "LIMITS" for alias in node.names)
            )
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            value = keyword.value
            max_page_chars_bound_to_limits |= (
                keyword.arg == "max_page_chars"
                and isinstance(value, ast.Subscript)
                and isinstance(value.value, ast.Name)
                and value.value.id == "LIMITS"
                and isinstance(value.slice, ast.Constant)
                and value.slice.value == "page_chars"
            )
    rejected_5001 = False
    try:
        fetch_boundary.validate_fetch_result(
            {
                "status": "ok",
                "url": "",
                "title": "",
                "text": "x" * (LEGACY_PAGE_CAP + 1),
                "links": [],
            }
        )
    except ValueError:
        rejected_5001 = True
    accepted_5000 = fetch_boundary.validate_fetch_result(
        {
            "status": "ok",
            "url": "",
            "title": "",
            "text": "x" * LEGACY_PAGE_CAP,
            "links": [],
        }
    )["status"] == "ok"
    return {
        "candidate_declared_input_page_character_cap": candidate.LIMITS[
            "page_chars"
        ],
        "legacy_helper_contract_page_character_cap": helper_contract.LIMITS[
            "page_chars"
        ],
        "helper_imports_limits_from_legacy_v24287_contract": imported_limits,
        "helper_max_page_chars_keyword_reads_legacy_limits": (
            max_page_chars_bound_to_limits
        ),
        "parent_fetch_validator_accepts_5000_characters": accepted_5000,
        "parent_fetch_validator_rejects_5001_characters": rejected_5001,
        "candidate_12000_cap_reaches_helper_process": False,
    }


def _quality(result: Mapping[str, Any]) -> dict[str, Any]:
    metrics = result["metrics"]["all_220"]
    names = (
        "selected",
        "evaluator_valid",
        "evaluator_invalid_or_not_run",
        "whole_table_successes",
        "score",
        "entity_acc",
        "f1_by_row",
        "f1_by_item",
        "column_f1",
        "quality_composite",
        "model_generated_tables",
        "fallback_tables",
        "system_total_tokens",
    )
    return {name: metrics[name] for name in names}


def _delta(after: Mapping[str, Any], before: Mapping[str, Any]) -> dict[str, Any]:
    names = (
        "whole_table_successes",
        "score",
        "entity_acc",
        "f1_by_row",
        "f1_by_item",
        "column_f1",
        "quality_composite",
        "evaluator_valid",
        "fallback_tables",
        "system_total_tokens",
    )
    return {
        name: round(float(after[name]) - float(before[name]), 12)
        for name in names
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    parents = _validate_parents()
    tasks = {name: _task_aggregates(spec["root"]) for name, spec in RUNS.items()}
    quality = {name: _quality(parents[name]["result"]) for name in RUNS}
    helper = _helper_ast_binding()
    hash_identity = sum(
        left == right
        for left, right in zip(
            tasks["v24909"].pop("prediction_hashes"),
            tasks["v24911"].pop("prediction_hashes"),
            strict=True,
        )
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24912_v24911_long_page_nonengagement_aggregate_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": (
            "valid_exact220_score_but_declared_12000_character_long_page_treatment_did_not_reach_fetch_helper"
        ),
        "parents": {
            name: {
                "protocol_id": RUNS[name]["protocol_id"],
                "result_sha256": parents[name]["result_sha256"],
                "forward_audit_sha256": parents[name]["forward_audit_sha256"],
                "postresult_audit_sha256": parents[name][
                    "postresult_audit_sha256"
                ],
                "run_summary_sha256": parents[name]["run_summary_sha256"],
            }
            for name in RUNS
        },
        "boundary": {
            "both_prediction_and_evaluator_chains_terminal_before_diagnosis": True,
            "offline_private_artifacts_used_only_for_content_free_aggregation": True,
            "question_query_url_page_prediction_answer_identifier_or_per_task_score_emitted": False,
            "benchmark_category_question_type_mapping_gold_split_or_reward_used_for_grouping": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "historical_correctness_or_score_authorized_as_future_runtime_input": False,
            "cross_run_quality_differences_are_descriptive_not_causal": True,
        },
        "helper_cap_binding": helper,
        "runs": {
            name: {
                "declared_page_cap": RUNS[name]["declared_page_cap"],
                "projector": RUNS[name]["projector"],
                "quality": quality[name],
                "mechanism": tasks[name],
                "forward_wall_seconds": parents[name]["result"]["efficiency"][
                    "forward_wall_seconds"
                ],
            }
            for name in RUNS
        },
        "comparisons": {
            "v24911_minus_v24909": {
                "quality_delta": _delta(quality["v24911"], quality["v24909"]),
                "prediction_hash_identity_count": hash_identity,
                "prediction_hash_difference_count": SELECTED - hash_identity,
                "same_fetch_bytes_or_random_seed_shared": False,
                "causal_packer_effect_estimate": False,
            }
        },
        "conclusions": {
            "v24911_benchmark_score_chain_valid": True,
            "v24911_tests_declared_12000_character_long_page_window": False,
            "long_page_window_mechanism_engagement_measured": False,
            "projection_receipt_observability_missing": (
                tasks["v24911"]["content_free_projection_receipt_file_count"] == 0
            ),
            "v24911_exact_below_v24909": (
                quality["v24911"]["whole_table_successes"]
                < quality["v24909"]["whole_table_successes"]
            ),
            "v24911_composite_above_v24909": (
                quality["v24911"]["quality_composite"]
                > quality["v24909"]["quality_composite"]
            ),
            "quality_difference_attributable_to_long_page_window": False,
            "public_benchmark_visible_requirement_parser_tuning_authorized": False,
            "entropy_or_information_gain_credit_validated": False,
        },
        "required_fix": {
            "new_fetch_helper_namespace_with_explicit_frozen_page_cap": True,
            "helper_result_validator_must_bind_the_same_cap": True,
            "candidate_child_must_persist_content_free_projection_receipt": True,
            "receipt_must_measure_long_pages_packed_prefix_fallback_and_late_block_selection": True,
            "same_forward_fetched_page_bytes_only": True,
            "no_additional_search_fetch_model_call_or_wall_cap": True,
        },
        "next_gate": {
            "benchmark_external_shared_prefix_required": True,
            "baseline_and_candidate_share_identical_12000_character_fetch_bytes": True,
            "baseline_projects_first_5000_characters_per_page": True,
            "candidate_projects_at_most_5000_characters_per_page_from_same_12000": True,
            "same_question_prompt_model_output_budget_and_renderer": True,
            "prediction_freeze_before_gold_or_quality_read": True,
            "gate_requires_mechanism_engagement_and_quality_nonregression": True,
        },
        "authorization": {
            "fetch_cap_binding_and_projection_receipt_build": True,
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
        "candidate_declares_12000": helper[
            "candidate_declared_input_page_character_cap"
        ]
        == CANDIDATE_DECLARED_INPUT_CAP,
        "helper_imports_legacy_limits": helper[
            "helper_imports_limits_from_legacy_v24287_contract"
        ],
        "helper_uses_legacy_page_cap": helper[
            "legacy_helper_contract_page_character_cap"
        ]
        == LEGACY_PAGE_CAP
        and helper["helper_max_page_chars_keyword_reads_legacy_limits"],
        "fetch_boundary_rejects_5001": helper[
            "parent_fetch_validator_rejects_5001_characters"
        ],
        "candidate_observable_tasks_obey_legacy_envelope": tasks["v24911"][
            "legacy_5000_character_per_usable_page_envelope_violation_count"
        ]
        == 0,
        "candidate_projection_receipts_absent": tasks["v24911"][
            "content_free_projection_receipt_file_count"
        ]
        == 0,
        "candidate_exact_is_six": quality["v24911"]["whole_table_successes"] == 6,
        "control_exact_is_seven": quality["v24909"]["whole_table_successes"] == 7,
        "rollouts_are_not_shared_predictions": hash_identity == 11,
        "no_public_benchmark_launch_authorized": value["authorization"][
            "public_dev64_or_exact220"
        ]
        is False,
    }
    value["checks"] = checks
    value["findings"] = sorted(name for name, passed in checks.items() if not passed)
    value["diagnosis_valid"] = not value["findings"]
    value["source_manifest"] = {str(path): _sha(path) for path in SOURCES}
    value["source_manifest_sha256"] = candidate.payload_sha256(
        value["source_manifest"]
    )
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if (
        OPAQUE.search(encoded)
        or INSTANCE.search(encoded)
        or SECRET.search(encoded)
        or "| Result |" in encoded
    ):
        raise RuntimeError("V2.49.12 diagnosis emitted prohibited content")
    value["diagnosis_payload_sha256"] = candidate.payload_sha256(value)
    return validate(value, rebuild=False)


def validate(value: Mapping[str, Any], *, rebuild: bool = True) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role")
        != "v24912_v24911_long_page_nonengagement_aggregate_diagnosis"
        or copied.get("status")
        != "valid_exact220_score_but_declared_12000_character_long_page_treatment_did_not_reach_fetch_helper"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("conclusions", {}).get(
            "v24911_tests_declared_12000_character_long_page_window"
        )
        is not False
        or copied.get("conclusions", {}).get(
            "quality_difference_attributable_to_long_page_window"
        )
        is not False
        or copied.get("boundary", {}).get(
            "historical_correctness_or_score_authorized_as_future_runtime_input"
        )
        is not False
        or copied.get("authorization", {}).get("public_dev64_or_exact220")
        is not False
        or copied.get("authorization", {}).get("sota_claim") is not False
        or seal != candidate.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.49.12 diagnosis drifted")
    if rebuild:
        expected = build(now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.49.12 diagnosis is not reproducible")
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
