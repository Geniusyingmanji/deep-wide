#!/usr/bin/env python3
"""Content-free post-terminal diagnosis of the V2.43.06 low-cap NO-GO."""

from __future__ import annotations

import json
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

from deepwide_agent.v24306_forward_contract import payload_sha256, sha256  # noqa: E402


OUTPUT = Path("results/v24307_v24306_postterminal_diagnosis_v1_20260803.json")
RESULT = Path("results/v24306_paired_dev64_result_v1_20260803.json")
POSTAUDIT = Path("results/v24306_paired_dev64_postresult_audit_v1_20260803.json")
FORWARD = Path("results/v24306_paired_dev64_forward_result_v1_20260803.json")
OUTPUT_ROOT = Path("outputs/v24306_paired_dev64_v1_20260803")
RUNTIME = {
    arm: OUTPUT_ROOT / f"{arm}_runtime_predictions.jsonl"
    for arm in ("baseline", "candidate")
}
SUMMARY = {
    arm: OUTPUT_ROOT
    / "fresh_both_arm_evaluator"
    / arm
    / "conservative_summary.json"
    for arm in ("baseline", "candidate")
}
MODEL_GENERATED = frozenset(
    {"primary", "repaired", "normalized_primary", "normalized_repaired"}
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.43.07 expected ordinary file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.43.07 expected object: {relative}")
    return value


def _jsonl(root: Path, relative: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _ordinary(root, relative).read_text(encoding="utf-8").splitlines()
        if line
    ]


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parents(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    result = _read(root, RESULT)
    post = _read(root, POSTAUDIT)
    forward = _read(root, FORWARD)
    if (
        result.get("role") != "v24306_synthesis_recovery_paired_dev64_result"
        or result.get("status") != "development_gate_no_go"
        or result.get("selected_per_arm") != 64
        or result.get("failure_as_zero") is not True
        or result.get("decision", {}).get("passed") is not False
        or not _sealed(result, "result_payload_sha256")
        or post.get("role") != "v24306_paired_dev64_postresult_audit"
        or post.get("findings") != []
        or post.get("audit_valid") is not True
        or post.get("forward_result_sha256") != sha256(root / FORWARD)
        or post.get("final_result_sha256") != sha256(root / RESULT)
        or not _sealed(post, "audit_payload_sha256")
        or forward.get("role") != "v24306_paired_dev64_forward_result"
        or forward.get("terminal_predictions_per_arm")
        != {"baseline": 64, "candidate": 64}
        or not _sealed(forward, "result_payload_sha256")
    ):
        raise RuntimeError("V2.43.07 frozen parent drifted")
    return result, post, forward


def _file_state(root: Path, arm: str, position: int) -> dict[str, bool]:
    directory = root / OUTPUT_ROOT / "tasks" / arm / f"task_{position:04d}"
    return {
        name: (directory / name).is_file() and not (directory / name).is_symlink()
        for name in (
            "visible_task.json",
            "safe_progress.json",
            "result.json",
            "model_slot_receipt.json",
            "transport_health.json",
        )
    }


def _fallbacks(root: Path, arm: str) -> list[dict[str, Any]]:
    rows = _jsonl(root, RUNTIME[arm])
    if len(rows) != 64:
        raise RuntimeError("V2.43.07 runtime denominator drifted")
    output: list[dict[str, Any]] = []
    for position, row in enumerate(rows, start=1):
        if row.get("completion_kind") in MODEL_GENERATED:
            continue
        telemetry = row.get("mechanism_telemetry") or {}
        cost = row.get("cost") or {}
        files = _file_state(root, arm, position)
        zero_effect = int(cost.get("model_calls", -1)) == 0 and int(
            cost.get("search_calls", -1)
        ) == 0
        if zero_effect and not files["result.json"]:
            taxonomy = "parent_worker_or_envelope_failure_zero_effect_unobservable"
        elif telemetry.get("synthesis_initial_model_request_error") is True:
            taxonomy = "synthesis_provider_failure"
        else:
            taxonomy = "other_fallback"
        output.append(
            {
                "position": position,
                "completion_kind": str(row["completion_kind"]),
                "taxonomy": taxonomy,
                "elapsed_seconds": float(row["elapsed_seconds"]),
                "model_calls": int(cost.get("model_calls", 0)),
                "model_attempts": int(cost.get("model_attempts", 0)),
                "search_calls": int(cost.get("search_calls", 0)),
                "fetch_calls": int(cost.get("search_fetch_calls", 0)),
                "zero_effect": zero_effect,
                "files": files,
            }
        )
    return output


def _deadline_positions(root: Path, arm: str) -> list[int]:
    positions: list[int] = []
    for position in range(1, 65):
        relative = (
            OUTPUT_ROOT
            / "tasks"
            / arm
            / f"task_{position:04d}"
            / "transport_health.json"
        )
        path = root / relative
        if not path.is_file() or path.is_symlink():
            continue
        health = _read(root, relative)
        if int(health.get("hard_fetch_deadline_failures", 0)) > 0:
            positions.append(position)
    return positions


def _evaluator_errors(root: Path, arm: str) -> dict[str, Any]:
    rows = _read(root, SUMMARY[arm]).get("per_task")
    if not isinstance(rows, list) or len(rows) != 64:
        raise RuntimeError("V2.43.07 evaluator denominator drifted")
    values = [
        {
            "position": position,
            "taxonomy": (
                "official_evaluator_internal_error"
                if "internal error" in str(row.get("evaluator_error") or "").lower()
                else "other_evaluator_error"
            ),
        }
        for position, row in enumerate(rows, start=1)
        if row.get("evaluator_valid") is not True
    ]
    return {
        "count": len(values),
        "positions": [row["position"] for row in values],
        "taxonomy": dict(sorted(Counter(row["taxonomy"] for row in values).items())),
        "selective_revaluation": False,
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result, post, forward = _parents(root)
    fallback = {arm: _fallbacks(root, arm) for arm in ("baseline", "candidate")}
    deadlines = {
        arm: _deadline_positions(root, arm) for arm in ("baseline", "candidate")
    }
    evaluator = {
        arm: _evaluator_errors(root, arm) for arm in ("baseline", "candidate")
    }
    if (
        [row["position"] for row in fallback["baseline"]] != [18, 26, 51, 55]
        or fallback["candidate"] != []
        or deadlines != {"baseline": [1, 4, 16, 21, 25], "candidate": [4, 29]}
        or evaluator["baseline"]["positions"] != [42, 50]
        or evaluator["candidate"]["positions"] != [50]
    ):
        raise RuntimeError("V2.43.07 failure set drifted")
    zero_effect = [
        row
        for row in fallback["baseline"]
        if row["taxonomy"]
        == "parent_worker_or_envelope_failure_zero_effect_unobservable"
    ]
    synthesis = [
        row
        for row in fallback["baseline"]
        if row["taxonomy"] == "synthesis_provider_failure"
    ]
    value = {
        "artifact_version": 1,
        "role": "v24307_v24306_postterminal_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result_sha256": sha256(root / RESULT),
            "postresult_audit_sha256": sha256(root / POSTAUDIT),
            "forward_result_sha256": sha256(root / FORWARD),
        },
        "boundary": {
            "postterminal_only": True,
            "fixed_denominator_failure_as_zero": True,
            "fed_back_into_v24306_forward": False,
            "v24306_rerun_resume_skip_or_selective_retry": False,
            "evaluator_error_revaluation": False,
            "question_prediction_answer_opaque_id_url_page_gold_or_label_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "quality_summary": {
            "decision": "no_go",
            "failed_checks": result["decision"]["failed_checks"],
            "candidate_minus_baseline": result["decision"][
                "candidate_minus_baseline"
            ],
            "paired_uncertainty": result["paired_uncertainty"],
            "candidate_fallback_tables": result["candidate"]["fallback_tables"],
            "baseline_fallback_tables": result["baseline"]["fallback_tables"],
            "shared_forward_wall_seconds": result["efficiency"][
                "shared_both_arm_forward_wall_seconds"
            ],
            "shared_forward_wall_ratio_vs_v24303": result["decision"][
                "shared_forward_wall_seconds_vs_v24303_ratio"
            ],
        },
        "forward_failure_taxonomy": {
            "baseline": fallback["baseline"],
            "candidate": fallback["candidate"],
            "baseline_zero_effect_unobservable_positions": [
                row["position"] for row in zero_effect
            ],
            "baseline_synthesis_provider_failure_positions": [
                row["position"] for row in synthesis
            ],
            "candidate_recovery_natural_engagement": 0,
            "candidate_recovery_provider_failures": 0,
        },
        "transport": {
            "hard_fetch_deadline_positions": deadlines,
            "hard_fetch_deadline_counts": {
                arm: len(positions) for arm, positions in deadlines.items()
            },
            "fetch_helper_failures": {
                arm: result["arm_health"][arm]["fetch_helper_failures"]
                for arm in ("baseline", "candidate")
            },
            "deadline_events_overlap_fallback_positions": {
                arm: sorted(
                    set(deadlines[arm])
                    & {row["position"] for row in fallback[arm]}
                )
                for arm in ("baseline", "candidate")
            },
        },
        "evaluator_health": evaluator,
        "conclusions": {
            "candidate_point_estimate_positive": result["decision"][
                "candidate_minus_baseline"
            ]["quality_composite"]
            > 0,
            "candidate_bootstrap_lower_bound_passed": result["decision"][
                "checks"
            ]["paired_bootstrap_lower_bound"],
            "candidate_bootstrap_interval_width_passed": result["decision"][
                "checks"
            ]["paired_bootstrap_interval_width"],
            "quality_gain_attributable_to_recovery": False,
            "cap2_transport_reliability_regressed": False,
            "parent_zero_effect_observability_complete": False,
            "hard_fetch_deadline_is_primary_fallback_cause": False,
            "exact220_authorized": False,
            "sota_supported": False,
        },
        "next_work": {
            "priority": "content_free_child_exit_observability_before_new_benchmark",
            "required_receipt": [
                "child_return_code",
                "timed_out",
                "receipt_present",
                "transport_present",
                "result_envelope_present",
                "failure_taxonomy",
            ],
            "prohibited_receipt_content": [
                "question",
                "opaque_id",
                "prompt",
                "response",
                "prediction",
                "url",
                "page",
                "credential",
                "gold",
                "category",
            ],
            "no_budget_or_policy_change": True,
            "benchmark_external_fault_injection_first": True,
            "additional_dev64_or_exact220": False,
        },
        "authorization": {
            "child_exit_observability_design": True,
            "child_exit_observability_benchmark_external_test": True,
            "additional_dev64": False,
            "exact220": False,
            "evaluator_call": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET.search(encoded) or OPAQUE.search(encoded):
        raise RuntimeError("V2.43.07 diagnosis contains prohibited content")
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(root: Path, value: Mapping[str, Any]) -> None:
    expected = build_report(root, now=int(value.get("created_at_unix", -1)))
    if dict(value) != expected or not _sealed(value, "diagnosis_payload_sha256"):
        raise RuntimeError("V2.43.07 diagnosis drifted")


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
                "zero_effect_unobservable": report["forward_failure_taxonomy"][
                    "baseline_zero_effect_unobservable_positions"
                ],
                "synthesis_provider_failure": report["forward_failure_taxonomy"][
                    "baseline_synthesis_provider_failure_positions"
                ],
            },
            sort_keys=True,
        )
    )
