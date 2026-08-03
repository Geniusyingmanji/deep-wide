#!/usr/bin/env python3
"""Content-free post-terminal diagnosis for frozen V2.43.46.

This successor never resumes, retries, evaluates, or modifies V2.43.46.  It
validates the already sealed task receipts, emits aggregate structural and
transport counts, and runs a benchmark-external in-memory validator fault
matrix.  No task identifier, question, page, prediction, evaluator row, or
credential is emitted.
"""

from __future__ import annotations

import json
import math
import os
import re
import statistics
import subprocess
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

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
    validate_parent_receipt,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model_receipt,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent import v24325_shared_prefix_revision_runtime as base  # noqa: E402
from deepwide_agent.v24343_semantic_active_runner import (  # noqa: E402
    validate_envelope,
    validate_observed_bundle,
)
from deepwide_agent.v24346_forward_contract import (  # noqa: E402
    FORWARD_RESULT,
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    PAIR_SUMMARY,
    POSTAUDIT,
    PROTOCOL_ID,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    sha256,
)


OUTPUT = Path("results/v24347_v24346_content_free_diagnosis_v1_20260803.json")
PROTOCOL = Path("results/v24347_v24346_content_free_diagnosis_preregistration_v1_20260803.json")
SOURCE_FILES = (
    Path("scripts/diagnose_v24347_v24346_postterminal.py"),
    Path("tests/test_diagnose_v24347_v24346_postterminal.py"),
)
RESULT_NAME = "result.json"
MODEL_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
CHILD_NAME = "child_terminal_receipt.json"
PARENT_NAME = "parent_exit_receipt.json"
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.43.47 path is noncanonical")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.43.47 expected ordinary file: {relative}")
    return path


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _parents(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    forward = read_object(_ordinary(root, FORWARD_RESULT))
    pair = read_object(_ordinary(root, PAIR_SUMMARY))
    audit = read_object(_ordinary(root, POSTAUDIT))
    if (
        forward.get("selected_pair_tasks") != SELECTED_COUNT
        or forward.get("terminal_pair_tasks") != SELECTED_COUNT
        or forward.get("successful_pair_tasks") != SELECTED_COUNT
        or forward.get("failed_pair_tasks") != 0
        or forward.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or forward.get("pair_summary_sha256") != sha256(root / PAIR_SUMMARY)
        or pair.get("selected_pair_tasks") != SELECTED_COUNT
        or pair.get("terminal_pair_tasks") != SELECTED_COUNT
        or pair.get("label_blind") is not True
        or pair.get("official_evaluator_called") is not False
        or audit.get("result_status") != "development_gate_no_go"
        or not isinstance(audit.get("result_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", audit["result_sha256"]) is None
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("same_run_evaluator_feedback_used_for_forward_or_prediction_selection") is not False
        or not _sealed(forward, "result_payload_sha256")
        or not _sealed(pair, "summary_payload_sha256")
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.47 frozen parent drifted")
    return forward, pair, audit


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    forward, pair, audit = _parents(root)
    source_manifest = {
        str(path): sha256(_ordinary(root, path)) for path in SOURCE_FILES
    }
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    tracked = all(
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
        for path in SOURCE_FILES
    )
    findings: list[str] = []
    if head != remote:
        findings.append("implementation_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean_before_preregistration")
    if not tracked:
        findings.append("diagnosis_source_not_tracked")
    if (root / OUTPUT).exists() or (root / OUTPUT).is_symlink():
        findings.append("diagnosis_output_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24347_v24346_content_free_diagnosis_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "frozen" if not findings else "rejected",
        "findings": findings,
        "execution_authorized": not findings,
        "implementation_base_commit": head,
        "target_main_at_freeze": remote,
        "git_worktree_clean_before_freeze": clean,
        "all_sources_tracked": tracked,
        "source_manifest": source_manifest,
        "source_manifest_sha256": payload_sha256(source_manifest),
        "parents": {
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "pair_summary_sha256": sha256(root / PAIR_SUMMARY),
            "postresult_audit_sha256": sha256(root / POSTAUDIT),
            "final_result_sha256_inherited_from_postresult_audit": audit[
                "result_sha256"
            ],
            "forward_result_payload_sha256": forward["result_payload_sha256"],
            "pair_summary_payload_sha256": pair["summary_payload_sha256"],
            "postresult_audit_payload_sha256": audit["audit_payload_sha256"],
        },
        "frozen_expectations": {
            "selected_tasks": 64,
            "effect_complete_tasks": 43,
            "effect_incomplete_tasks": 21,
            "effect_incomplete_model_requests": 42,
            "effect_incomplete_slot_acquisitions": 42,
            "effect_incomplete_without_health_event": 18,
            "effect_incomplete_fallback_taxonomy": {"ValidationError": 21},
        },
        "boundary": {
            "postterminal_read_only": True,
            "task_private_bundle_opened_only_for_frozen_validator_replay": True,
            "task_private_content_used_for_aggregation_or_routing": False,
            "task_private_content_emitted": False,
            "final_evaluator_result_bytes_opened_or_hashed": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_opened": False,
            "external_network_provider_model_search_fetch_or_evaluator_called": False,
            "same_run_resume_retry_rerun_selective_retry_or_revaluation": False,
        },
        "authorization": {
            "one_content_free_report": not findings,
            "same_run_forward_or_evaluator": False,
            "additional_dev64": False,
            "new_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.43.47 preregistration rejected: " + ",".join(findings))
    return value


def validate_protocol(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = read_object(_ordinary(root, PROTOCOL))
    if (
        value.get("status") != "frozen"
        or value.get("findings") != []
        or value.get("execution_authorized") is not True
        or value.get("implementation_base_commit")
        != value.get("target_main_at_freeze")
        or value.get("git_worktree_clean_before_freeze") is not True
        or value.get("all_sources_tracked") is not True
        or value.get("source_manifest")
        != {str(path): sha256(_ordinary(root, path)) for path in SOURCE_FILES}
        or value.get("source_manifest_sha256")
        != payload_sha256(value.get("source_manifest"))
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.47 preregistration drifted")
    forward, pair, audit = _parents(root)
    expected_parents = {
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "pair_summary_sha256": sha256(root / PAIR_SUMMARY),
        "postresult_audit_sha256": sha256(root / POSTAUDIT),
        "final_result_sha256_inherited_from_postresult_audit": audit[
            "result_sha256"
        ],
        "forward_result_payload_sha256": forward["result_payload_sha256"],
        "pair_summary_payload_sha256": pair["summary_payload_sha256"],
        "postresult_audit_payload_sha256": audit["audit_payload_sha256"],
    }
    if value.get("parents") != expected_parents:
        raise RuntimeError("V2.43.47 preregistration parent drifted")
    return dict(value)


def _task_directories(root: Path) -> list[Path]:
    base_path = root / TASK_ROOT
    if base_path.is_symlink() or not base_path.is_dir():
        raise RuntimeError("V2.43.47 frozen task root is absent")
    expected = [base_path / f"task_{index:04d}" for index in range(1, SELECTED_COUNT + 1)]
    present = sorted(path for path in base_path.glob("task_*") if path.is_dir())
    if present != expected or any(path.is_symlink() for path in expected):
        raise RuntimeError("V2.43.47 frozen task partition drifted")
    return expected


def _distribution(values: Sequence[float]) -> dict[str, float]:
    numbers = [float(value) for value in values]
    if not numbers or any(not math.isfinite(value) for value in numbers):
        raise RuntimeError("V2.43.47 distribution input drifted")
    return {
        "minimum": round(min(numbers), 6),
        "median": round(statistics.median(numbers), 6),
        "maximum": round(max(numbers), 6),
        "mean": round(statistics.fmean(numbers), 6),
    }


def _health_pattern(model: Mapping[str, Any], transport: Mapping[str, Any]) -> str:
    active: list[str] = []
    if int(model["slot_timeouts"]) > 0:
        active.append("slot_timeout")
    if int(model["provider_deadline_failures"]) > 0:
        active.append("provider_deadline")
    if int(transport["hosted_search_deadline_failures"]) > 0:
        active.append("hosted_search_deadline")
    if int(transport["hard_fetch_deadline_failures"]) > 0:
        active.append("hard_fetch_deadline")
    if int(transport["fetch_helper_failures"]) > 0:
        active.append("fetch_helper_failure")
    if int(transport["fetch_deadline_rejections"]) > 0:
        active.append("fetch_deadline_rejection")
    if transport["deadline_exhausted"] is True:
        active.append("deadline_exhausted")
    return "+".join(active) if active else "none"


def _synthetic_receipt(table: str) -> dict[str, Any]:
    limits = ScoreFirstLimits(
        wall_seconds=180,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        plan_output_tokens=4_000,
        synthesis_output_tokens=30_000,
        repair_output_tokens=12_000,
    )
    budget = base._PairBudget(limits, 0.0, lambda: 0.0)
    budget.model_effects.extend(("plan", "baseline_synthesis"))
    return base._receipt(
        prefix_status="unavailable",
        prefix_bundle=None,
        baseline=table,
        candidate=table,
        admissions=[],
        proposed_changes=0,
        admitted_changes=0,
        budget=budget,
        core_queries=0,
        reserve_queries=0,
        core_search_provider_effects=0,
        reserve_search_provider_effects=0,
        core_fetch_targets=0,
        reserve_fetch_targets=0,
        core_network_fetch_effects=0,
        reserve_network_fetch_effects=0,
        core_pages=[],
        reserve_pages=[],
        fallback_type=None,
        provider_model_requests=2,
        provider_model_attempts=2,
    )


def _validator_outcome(rows: Sequence[Sequence[str]]) -> str:
    columns = ["Entity", "Attribute"]
    table = base._render_table(columns, rows)
    receipt = _synthetic_receipt(table)
    try:
        base._result(
            visible={"opaque_id": "task_" + "0" * 24, "question": "visible"},
            columns=columns,
            baseline=table,
            candidate=table,
            receipt=receipt,
            cost={
                "model": {"requests": 2, "attempts": 2},
                "search": {"calls": 0, "fetch_calls": 0},
            },
            elapsed=1.0,
            completion_kind="identity_no_reserve",
        )
    except ValueError:
        return "validation_rejected"
    return "validation_accepted"


def synthetic_fault_matrix() -> dict[str, Any]:
    value = {
        "unique_row_identity": _validator_outcome((("Alpha", "One"), ("Beta", "Two"))),
        "exact_duplicate_row_identity": _validator_outcome((("Alpha", "One"), ("Alpha", "Two"))),
        "normalized_duplicate_row_identity": _validator_outcome((("Alpha-A", "One"), ("Alpha A", "Two"))),
        "external_network_provider_model_search_fetch_or_evaluator_called": False,
        "benchmark_task_or_evaluator_resource_opened": False,
    }
    if value != {
        "unique_row_identity": "validation_accepted",
        "exact_duplicate_row_identity": "validation_rejected",
        "normalized_duplicate_row_identity": "validation_rejected",
        "external_network_provider_model_search_fetch_or_evaluator_called": False,
        "benchmark_task_or_evaluator_resource_opened": False,
    }:
        raise RuntimeError("V2.43.47 synthetic fault matrix drifted")
    return value


def _aggregate(root: Path) -> dict[str, Any]:
    completion: Counter[str] = Counter()
    prefixes: Counter[str] = Counter()
    fallbacks: Counter[str] = Counter()
    catalogs: Counter[str] = Counter()
    stages: Counter[str] = Counter()
    health_all: Counter[str] = Counter()
    health_by_stratum: dict[bool, Counter[str]] = {True: Counter(), False: Counter()}
    values: dict[bool, dict[str, list[float]]] = {
        True: {"elapsed": [], "slot_wait": [], "remaining": []},
        False: {"elapsed": [], "slot_wait": [], "remaining": []},
    }
    counts: dict[bool, Counter[str]] = {True: Counter(), False: Counter()}

    for directory in _task_directories(root):
        paths = {
            "result": directory / RESULT_NAME,
            "model": directory / MODEL_NAME,
            "transport": directory / TRANSPORT_NAME,
            "child": directory / CHILD_NAME,
            "parent": directory / PARENT_NAME,
        }
        if any(path.is_symlink() or not path.is_file() for path in paths.values()):
            raise RuntimeError("V2.43.47 frozen task artifact is absent")
        envelope = validate_envelope(read_object(paths["result"]))
        model = validate_model_receipt(read_object(paths["model"]), expected_cap=MODEL_SLOT_CAP)
        transport = validate_transport_health(read_object(paths["transport"]))
        validate_child_receipt(read_object(paths["child"]))
        parent = validate_parent_receipt(read_object(paths["parent"]))
        validate_observed_bundle(
            envelope,
            model_slot_receipt=model,
            transport_health=transport,
            expected_cap=MODEL_SLOT_CAP,
        )
        if parent["failure_taxonomy"] != "success":
            raise RuntimeError("V2.43.47 parent receipt is not success")

        result = envelope["result"]
        core = result["core_result"]
        receipt = core["shared_prefix_revision_receipt"]
        mechanism = result["semantic_active_receipt"]
        complete = receipt["effect_accounting_complete"] is True
        target = counts[complete]
        pattern = _health_pattern(model, transport)
        health_all[pattern] += 1
        health_by_stratum[complete][pattern] += 1
        completion[str(core["completion_kind"])] += 1
        prefixes[str(receipt["prefix_status"])] += 1
        fallbacks[str(receipt["fallback_type"] or "none")] += 1
        catalogs[str(mechanism["catalog_status"])] += 1
        stages["+".join(receipt["model_effect_stages"]) or "unattributed"] += 1
        target.update(
            {
                "tasks": 1,
                "model_requests": int(core["cost"]["model"]["requests"]),
                "model_attempts": int(core["cost"]["model"]["attempts"]),
                "slot_acquisitions": int(model["acquisitions"]),
                "slot_timeouts": int(model["slot_timeouts"]),
                "provider_deadline_failures": int(model["provider_deadline_failures"]),
                "hard_fetch_deadline_failures": int(transport["hard_fetch_deadline_failures"]),
                "deadline_exhausted_tasks": int(transport["deadline_exhausted"] is True),
                "recoverable_failure_records": len(receipt["recoverable_failures"]),
                "no_health_event_tasks": int(pattern == "none"),
            }
        )
        values[complete]["elapsed"].append(float(core["elapsed_seconds"]))
        values[complete]["slot_wait"].append(float(model["total_wait_seconds"]))
        values[complete]["remaining"].append(float(model["remaining_seconds_at_receipt"]))

    def stratum(complete: bool) -> dict[str, Any]:
        counter = counts[complete]
        return {
            **{name: int(value) for name, value in sorted(counter.items())},
            "elapsed_seconds": _distribution(values[complete]["elapsed"]),
            "model_slot_wait_seconds": _distribution(values[complete]["slot_wait"]),
            "remaining_effect_seconds_at_model_receipt": _distribution(values[complete]["remaining"]),
            "health_patterns": dict(sorted(health_by_stratum[complete].items())),
        }

    return {
        "selected_tasks": sum(completion.values()),
        "completion_kinds": dict(sorted(completion.items())),
        "prefix_status": dict(sorted(prefixes.items())),
        "fallback_types": dict(sorted(fallbacks.items())),
        "catalog_status": dict(sorted(catalogs.items())),
        "attributed_model_stage_vectors": dict(sorted(stages.items())),
        "effect_complete": stratum(True),
        "effect_incomplete": stratum(False),
        "all_health_patterns": dict(sorted(health_all.items())),
    }


def build_report(
    root: Path = ROOT,
    *,
    now: int | None = None,
    require_protocol: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root) if require_protocol else None
    forward, pair, audit = _parents(root)
    aggregate = _aggregate(root)
    incomplete = aggregate["effect_incomplete"]
    if (
        aggregate["selected_tasks"] != SELECTED_COUNT
        or aggregate["effect_complete"]["tasks"] != 43
        or incomplete["tasks"] != 21
        or incomplete["model_requests"] != 42
        or incomplete["model_attempts"] != 42
        or incomplete["slot_acquisitions"] != 42
    ):
        raise RuntimeError("V2.43.47 frozen aggregate drifted")
    if (
        aggregate["fallback_types"] != {"ValidationError": 21, "none": 43}
        or incomplete["slot_timeouts"] != 0
        or incomplete["provider_deadline_failures"] != 0
        or incomplete["deadline_exhausted_tasks"] != 0
        or incomplete["no_health_event_tasks"] != 18
        or incomplete["remaining_effect_seconds_at_model_receipt"]["minimum"] <= 40
    ):
        raise RuntimeError("V2.43.47 incomplete-task signature drifted")
    fault = synthetic_fault_matrix()
    value = {
        "artifact_version": 1,
        "role": "v24347_v24346_content_free_postterminal_diagnosis",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "pair_summary_sha256": sha256(root / PAIR_SUMMARY),
            "postresult_audit_sha256": sha256(root / POSTAUDIT),
            "final_result_sha256_inherited_from_postresult_audit": audit[
                "result_sha256"
            ],
            "forward_result_payload_sha256": forward["result_payload_sha256"],
            "pair_summary_payload_sha256": pair["summary_payload_sha256"],
            "postresult_audit_payload_sha256": audit["audit_payload_sha256"],
            "preregistration_sha256": (
                sha256(root / PROTOCOL) if protocol is not None else None
            ),
        },
        "boundary": {
            "postterminal_only": True,
            "both_arm_predictions_and_evaluation_preexisted": True,
            "same_run_forward_resume_retry_rerun_selective_retry_or_revaluation": False,
            "task_private_bundle_opened_only_for_frozen_validator_replay": True,
            "task_private_content_used_for_aggregation_or_routing": False,
            "final_evaluator_result_bytes_opened_or_hashed": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_opened": False,
            "external_network_provider_model_search_fetch_or_evaluator_called": False,
            "task_identifier_question_query_url_page_cell_value_evidence_id_prediction_or_credential_emitted": False,
            "per_task_position_or_hash_emitted": False,
        },
        "aggregate": aggregate,
        "benchmark_external_validator_fault_matrix": fault,
        "conclusions": {
            "task_deadline_exhaustion_explains_effect_incomplete_tasks": False,
            "transport_health_event_explains_all_effect_incomplete_tasks": False,
            "all_effect_incomplete_tasks_had_two_provider_model_requests": True,
            "all_effect_incomplete_tasks_lost_stage_attribution_in_total_fallback": True,
            "duplicate_normalized_row_identity_reproduces_the_same_coarse_validation_class": True,
            "duplicate_normalized_row_identity_proven_as_parent_cause": False,
            "exact_validation_subtype_recoverable_from_frozen_artifacts": False,
            "total_fallback_observability_is_insufficient": True,
            "quality_improvement_demonstrated": False,
            "sota_supported": False,
        },
        "next_work": {
            "append_only_structural_normalizer": (
                "deduplicate normalized first-column identities before semantic target "
                "construction; preserve the most complete row and only fill unknown cells "
                "when all duplicate alternatives agree"
            ),
            "stage_local_fault_receipt": (
                "preserve a fixed content-free validation stage and structural reason before "
                "total fallback without emitting task content"
            ),
            "benchmark_external_fault_matrix_required": [
                "unique_rows",
                "exact_duplicate_rows",
                "normalized_duplicate_rows",
                "conflicting_duplicate_cells",
                "empty_identity",
                "candidate_row_preservation",
            ],
            "deadline_work_after_structural_reliability": True,
        },
        "authorization": {
            "append_only_structural_normalizer_design": True,
            "benchmark_external_structural_fault_matrix": True,
            "append_only_content_free_stage_receipt_design": True,
            "same_run_forward_or_evaluator": False,
            "additional_dev64": False,
            "new_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "protected_watchers": protected_watcher_snapshot(),
    }
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if SECRET.search(encoded) or OPAQUE.search(encoded) or "| Entity |" in encoded:
        raise RuntimeError("V2.43.47 report emitted prohibited content")
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(
    root: Path,
    value: Mapping[str, Any],
    *,
    require_protocol: bool = True,
) -> dict[str, Any]:
    expected = build_report(
        root,
        now=int(value.get("created_at_unix", -1)),
        require_protocol=require_protocol,
    )
    if dict(value) != expected or not _sealed(value, "diagnosis_payload_sha256"):
        raise RuntimeError("V2.43.47 diagnosis drifted")
    return dict(value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "report"))
    args = parser.parse_args()
    if args.command == "protocol":
        protocol = build_protocol()
        publish(ROOT / PROTOCOL, protocol)
        print(json.dumps({"path": str(PROTOCOL)}, sort_keys=True))
    else:
        report = build_report()
        validate_report(ROOT, report)
        publish(ROOT / OUTPUT, report)
        print(
            json.dumps(
                {
                    "path": str(OUTPUT),
                    "effect_complete": report["aggregate"]["effect_complete"]["tasks"],
                    "effect_incomplete": report["aggregate"]["effect_incomplete"]["tasks"],
                    "incomplete_without_health_event": report["aggregate"]["effect_incomplete"]["no_health_event_tasks"],
                },
                sort_keys=True,
            )
        )
