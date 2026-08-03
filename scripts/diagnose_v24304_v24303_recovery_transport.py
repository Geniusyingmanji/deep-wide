#!/usr/bin/env python3
"""Content-free post-terminal diagnosis of V2.43.03 recovery reliability.

This script is deliberately downstream of the frozen prediction and evaluator
artifacts.  It projects only positions, counters, durations, and coarse error
types.  Questions, opaque identifiers, predictions, URLs, pages, gold values,
and benchmark labels are never written to the diagnosis.
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
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    validate_receipt as validate_slot_receipt,
)
from deepwide_agent.v24303_forward_contract import (  # noqa: E402
    payload_sha256,
    sha256,
)
from deepwide_agent.v24303_paired_dev_runtime import (  # noqa: E402
    RECEIPT_FIELD,
    validate_v24303_result,
)


OUTPUT = Path(
    "results/v24304_v24303_recovery_transport_postterminal_diagnosis_v1_20260803.json"
)
RESULT = Path("results/v24303_paired_dev64_result_v1_20260803.json")
POSTAUDIT = Path("results/v24303_paired_dev64_postresult_audit_v1_20260803.json")
FORWARD_RESULT = Path("results/v24303_paired_dev64_forward_result_v1_20260803.json")
FORWARD_CONTRACT = Path("results/v24303_paired_dev64_forward_contract_v1_20260803.json")
CAPACITY_AUDIT = Path(
    "results/v24262_score_first_capacity_postresult_audit_v1_20260802.json"
)
OUTPUT_ROOT = Path("outputs/v24303_paired_dev64_v1_20260803")
TASK_ROOT = OUTPUT_ROOT / "tasks"
EVAL_ROOT = OUTPUT_ROOT / "fresh_both_arm_evaluator"
SUMMARY = {
    arm: EVAL_ROOT / arm / "conservative_summary.json"
    for arm in ("baseline", "candidate")
}
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.43.04 path is noncanonical")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.43.04 expected ordinary file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.43.04 expected object: {relative}")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.43.04 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.43.04 {label} is invalid")
    return number


def _validate_parents(root: Path) -> tuple[dict[str, Any], ...]:
    result = _read(root, RESULT)
    post = _read(root, POSTAUDIT)
    forward = _read(root, FORWARD_RESULT)
    contract = _read(root, FORWARD_CONTRACT)
    capacity = _read(root, CAPACITY_AUDIT)
    levels = capacity.get("result", {}).get("levels")
    if (
        result.get("role") != "v24303_synthesis_recovery_paired_dev64_result"
        or result.get("status") != "development_gate_no_go"
        or result.get("selected_per_arm") != 64
        or result.get("failure_as_zero") is not True
        or result.get("decision", {}).get("passed") is not False
        or not _sealed(result, "result_payload_sha256")
        or post.get("role") != "v24303_paired_dev64_postresult_audit"
        or post.get("audit_valid") is not True
        or post.get("findings") != []
        or not _sealed(post, "audit_payload_sha256")
        or post.get("forward_result_sha256") != sha256(root / FORWARD_RESULT)
        or post.get("final_result_sha256") != sha256(root / RESULT)
        or forward.get("role") != "v24303_paired_dev64_forward_result"
        or forward.get("terminal_predictions_per_arm")
        != {"baseline": 64, "candidate": 64}
        or forward.get("official_evaluator_called") is not False
        or not _sealed(forward, "result_payload_sha256")
        or contract.get("role") != "v24303_paired_dev64_forward_contract"
        or contract.get("execution", {}).get("total_executor_concurrency") != 8
        or contract.get("execution", {}).get("model_slot_cap") != 8
        or not _sealed(contract, "forward_contract_payload_sha256")
        or capacity.get("role")
        != "v24262_score_first_capacity_postresult_audit"
        or capacity.get("audit_valid") is not True
        or not _sealed(capacity, "audit_payload_sha256")
        or not isinstance(levels, list)
        or [level.get("concurrency") for level in levels] != [1, 2, 4]
        or [level.get("passed") for level in levels] != [True, True, False]
    ):
        raise RuntimeError("V2.43.04 frozen parent evidence drifted")
    return result, post, forward, contract, capacity


def _candidate_telemetry(root: Path, position: int) -> dict[str, Any]:
    relative = TASK_ROOT / "candidate" / f"task_{position:04d}" / "result.json"
    envelope = _read(root, relative)
    unsigned = dict(envelope)
    seal = unsigned.pop("envelope_payload_sha256", None)
    value = envelope.get("result")
    if (
        envelope.get("role") != "v24303_paired_dev64_task_envelope"
        or envelope.get("arm") != "candidate"
        or envelope.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
        or not isinstance(value, dict)
    ):
        raise RuntimeError("V2.43.04 candidate envelope drifted")
    validate_v24303_result(value, "candidate")
    recovery = value[RECEIPT_FIELD]
    requests = int(recovery["provider_requests_delta"])
    receipt_relative = relative.with_name("model_slot_receipt.json")
    slot = validate_slot_receipt(
        _read(root, receipt_relative),
        expected_cap=8,
        expected_acquisitions=requests,
    )
    timing = value.get("attributed_timing") or {}
    model_seconds = timing.get("model_seconds") or {}
    return {
        "position": position,
        "completion_kind": str(value["completion_kind"]),
        "recovery_attempted": bool(recovery["synthesis_recovery_attempted"]),
        "recovery_succeeded": bool(recovery["synthesis_recovery_succeeded"]),
        "recovery_provider_failure": bool(
            recovery["synthesis_recovery_model_request_error"]
        ),
        "logical_provider_requests": requests,
        "provider_attempts": int(recovery["provider_attempts_delta"]),
        "task_wall_seconds": _finite(
            value.get("budget", {}).get("elapsed_seconds"), "task wall seconds"
        ),
        "synthesis_model_seconds": _finite(
            model_seconds.get("synthesis", 0), "synthesis model seconds"
        ),
        "slot_wait_seconds": _finite(
            slot["total_wait_seconds"], "slot wait seconds"
        ),
        "slot_max_wait_seconds": _finite(
            slot["max_wait_seconds"], "slot max wait seconds"
        ),
    }


def _error_taxonomy(error: object) -> str:
    text = str(error or "")
    if "internal error" in text.lower():
        return "official_evaluator_internal_error"
    if not text:
        return "missing_or_not_run"
    return "other_evaluator_error"


def _evaluator_health(root: Path, arm: str) -> dict[str, Any]:
    summary = _read(root, SUMMARY[arm])
    rows = summary.get("per_task")
    if not isinstance(rows, list) or len(rows) != 64:
        raise RuntimeError("V2.43.04 evaluator summary drifted")
    invalid = [
        {
            "position": position,
            "taxonomy": _error_taxonomy(row.get("evaluator_error")),
        }
        for position, row in enumerate(rows, start=1)
        if row.get("evaluator_valid") is not True
    ]
    return {
        "selected": len(rows),
        "valid": len(rows) - len(invalid),
        "invalid_or_not_run": len(invalid),
        "invalid_positions": [row["position"] for row in invalid],
        "taxonomy": dict(sorted(Counter(row["taxonomy"] for row in invalid).items())),
        "selective_revaluation_performed": False,
    }


def _distribution(values: list[float]) -> dict[str, Any]:
    return {
        "count": len(values),
        "minimum": min(values) if values else 0.0,
        "median": statistics.median(values) if values else 0.0,
        "maximum": max(values) if values else 0.0,
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result, post, forward, contract, capacity = _validate_parents(root)
    telemetry = [_candidate_telemetry(root, position) for position in range(1, 65)]
    recovery = [row for row in telemetry if row["recovery_attempted"]]
    successes = [row for row in recovery if row["recovery_succeeded"]]
    failures = [row for row in recovery if row["recovery_provider_failure"]]
    if (
        len(recovery) != 7
        or len(successes) != 4
        or len(failures) != 3
        or [row["position"] for row in failures] != [2, 14, 20]
        or [row["position"] for row in successes] != [4, 13, 18, 19]
    ):
        raise RuntimeError("V2.43.04 recovery event set drifted")

    evaluator = {
        arm: _evaluator_health(root, arm) for arm in ("baseline", "candidate")
    }
    if (
        evaluator["baseline"]["invalid_or_not_run"]
        != result["baseline"]["evaluator_invalid_or_not_run"]
        or evaluator["candidate"]["invalid_or_not_run"]
        != result["candidate"]["evaluator_invalid_or_not_run"]
    ):
        raise RuntimeError("V2.43.04 evaluator count drifted")

    levels = capacity["result"]["levels"]
    cap2 = levels[1]
    cap4 = levels[2]
    value = {
        "artifact_version": 1,
        "role": "v24304_v24303_recovery_transport_postterminal_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "v24303_result_sha256": sha256(root / RESULT),
            "v24303_postresult_audit_sha256": sha256(root / POSTAUDIT),
            "v24303_forward_result_sha256": sha256(root / FORWARD_RESULT),
            "v24303_forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "v24262_capacity_postresult_audit_sha256": sha256(
                root / CAPACITY_AUDIT
            ),
        },
        "boundary": {
            "postterminal_only": True,
            "parent_decision": "no_go",
            "fixed_denominator_failure_as_zero": True,
            "fed_back_into_v24303_forward": False,
            "v24303_rerun_resume_skip_or_selective_retry": False,
            "evaluator_error_revaluation": False,
            "question_prediction_answer_opaque_id_url_page_gold_or_label_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "recovery_transport": {
            "attempts": len(recovery),
            "successes": len(successes),
            "provider_failures": len(failures),
            "success_positions": [row["position"] for row in successes],
            "failure_positions": [row["position"] for row in failures],
            "success_provider_attempts": [row["provider_attempts"] for row in successes],
            "failure_provider_attempts": [row["provider_attempts"] for row in failures],
            "success_task_wall_seconds": _distribution(
                [row["task_wall_seconds"] for row in successes]
            ),
            "failure_task_wall_seconds": _distribution(
                [row["task_wall_seconds"] for row in failures]
            ),
            "success_synthesis_model_seconds": _distribution(
                [row["synthesis_model_seconds"] for row in successes]
            ),
            "failure_synthesis_model_seconds": _distribution(
                [row["synthesis_model_seconds"] for row in failures]
            ),
            "all_recovery_slot_wait_seconds": _distribution(
                [row["slot_wait_seconds"] for row in recovery]
            ),
            "all_recovery_slot_max_wait_seconds": _distribution(
                [row["slot_max_wait_seconds"] for row in recovery]
            ),
            "all_failures_had_provider_internal_retries": all(
                row["provider_attempts"] > row["logical_provider_requests"]
                for row in failures
            ),
            "wall_clock_task_start_timestamps_available": False,
            "failure_burst_clustering_identifiable": False,
            "position_is_not_a_wall_clock_timestamp": True,
        },
        "concurrency_evidence": {
            "v24303_executor_workers": contract["execution"][
                "total_executor_concurrency"
            ],
            "v24303_global_model_slot_cap": contract["execution"][
                "model_slot_cap"
            ],
            "v24303_all_slot_acquisitions_match_requests": all(
                arm["all_acquisitions_match_actual_requests"]
                for arm in forward["shared_model_receipts"].values()
            ),
            "v24303_recovery_slot_waits_show_effective_throttling": max(
                row["slot_wait_seconds"] for row in recovery
            )
            >= 0.01,
            "v24262_cap2": {
                "executions": cap2["executions"],
                "fallbacks": cap2["fallbacks"],
                "stage_failures": cap2["stage_failures"],
                "passed": cap2["passed"],
            },
            "v24262_cap4": {
                "executions": cap4["executions"],
                "fallbacks": cap4["fallbacks"],
                "stage_failures": cap4["stage_failures"],
                "provider_attempts": capacity["failure_diagnosis"][
                    "provider_attempts_at_concurrency_4"
                ],
                "passed": cap4["passed"],
            },
            "cap8_caused_v24303_failures_proven": False,
            "cap2_is_best_supported_next_transport_setting": True,
        },
        "evaluator_health": evaluator,
        "conclusions": {
            "bounded_recovery_reduced_fallbacks": result["candidate"][
                "fallback_tables"
            ]
            < result["baseline"]["fallback_tables"],
            "recovery_path_fully_reliable": False,
            "failures_explained_by_absent_retries": False,
            "failure_time_burst_claim_supported": False,
            "historical_capacity_evidence_supports_global_model_cap2": True,
            "new_paired_dev64_authorized": False,
            "exact220_authorized": False,
            "sota_supported": False,
        },
        "next_experiment": {
            "stage": "benchmark_external_low_model_concurrency_recovery_reliability_gate",
            "executor_workers": 8,
            "global_model_slot_cap": 2,
            "recovery_only_independent_cap": None,
            "recovery_cooldown_seconds": 0,
            "model_calls_per_task": 3,
            "search_calls": 0,
            "fetch_calls": 0,
            "required_recovery_successes": 8,
            "required_recovery_provider_failures": 0,
            "required_peak_real_recovery_concurrency_at_most": 2,
            "benchmark_dev64_or_exact220_launch": False,
        },
        "authorization": {
            "one_benchmark_external_low_cap_reliability_gate_design": True,
            "one_benchmark_external_low_cap_reliability_gate_launch": False,
            "additional_dev64": False,
            "exact220": False,
            "evaluator_call": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET.search(encoded) or OPAQUE.search(encoded):
        raise RuntimeError("V2.43.04 diagnosis contains prohibited content")
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(root: Path, value: Mapping[str, Any]) -> None:
    expected = build_report(root, now=int(value.get("created_at_unix", -1)))
    if dict(value) != expected or not _sealed(value, "diagnosis_payload_sha256"):
        raise RuntimeError("V2.43.04 diagnosis drifted")


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
                "recovery_successes": report["recovery_transport"]["successes"],
                "recovery_provider_failures": report["recovery_transport"][
                    "provider_failures"
                ],
            },
            sort_keys=True,
        )
    )
