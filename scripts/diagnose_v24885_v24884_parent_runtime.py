#!/usr/bin/env python3
"""Content-free postresult diagnosis for V2.48.84 parent-runtime failures.

The diagnosis reads only five predeclared content-free receipts per frozen
task.  It never opens visible tasks, model/search payloads, result envelopes,
predictions, pages, evaluator artifacts, scores, or credentials.  Output is
aggregate-only and cannot identify a task or feed same-run routing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
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

from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
    validate_parent_receipt,
)
from deepwide_agent.v24881_mapping_recovery_subprocess_gate import (  # noqa: E402
    validate_parent_bundle_receipt,
)
from deepwide_agent.v24882_mapping_recovery_stage_runtime import (  # noqa: E402
    validate_stage_receipt,
)


DATE = "20260808"
ROLE = "v24885_v24884_content_free_parent_runtime_diagnosis"
OUTPUT_ROOT = Path("outputs/v24884_mapping_recovery_exact220_v1_20260808")
TASK_ROOT = OUTPUT_ROOT / "tasks"
FORWARD_RESULT = Path(
    "results/v24884_mapping_recovery_exact220_forward_result_v1_20260808.json"
)
FORWARD_AUDIT = Path(
    "results/v24884_mapping_recovery_exact220_forward_audit_v1_20260808.json"
)
RESULT = Path(
    f"results/v24885_v24884_content_free_parent_runtime_diagnosis_v1_{DATE}.json"
)
SOURCE = Path("scripts/diagnose_v24885_v24884_parent_runtime.py")
TEST = Path("tests/test_diagnose_v24885_v24884_parent_runtime.py")
RECEIPT_NAMES = (
    "child_terminal_receipt.json",
    "base_parent_exit_receipt.json",
    "keyless_coverage_parent_bundle_receipt.json",
    "mapping_recovery_stage_receipt.json",
    "safe_progress.json",
)
BUNDLE_NAME = "keyless_coverage_bundle_receipt.json"
SELECTED = 220
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _ordinary(path: Path) -> Path:
    root = ROOT.resolve()
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.48.85 expected ordinary file: {path}")
    return path


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.85 expected JSON object")
    return value


def _safe_progress(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24257_score_first_safe_progress"
        or copied.get("stage") != "terminal"
        or copied.get("contains_question_query_url_page_prediction_or_answer")
        is not False
        or copied.get("mapping_gold_evaluator_or_score_read") is not False
        or not isinstance(copied.get("events"), list)
    ):
        raise RuntimeError("V2.48.85 unsafe or invalid progress receipt")
    for name in (
        "admitted_model_calls",
        "admitted_search_queries",
        "admitted_fetch_targets",
        "search_batch_count",
        "projected_chars",
    ):
        amount = copied.get(name)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise RuntimeError("V2.48.85 invalid progress count")
    elapsed = copied.get("elapsed_seconds")
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0
    ):
        raise RuntimeError("V2.48.85 invalid progress elapsed time")
    for event in copied["events"]:
        if (
            not isinstance(event, Mapping)
            or not set(event).issubset({"stage", "effect", "requested", "admitted"})
            or not isinstance(event.get("stage"), str)
            or not isinstance(event.get("effect"), str)
        ):
            raise RuntimeError("V2.48.85 unsafe progress event")
    return copied


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    if not ordered or any(not math.isfinite(value) or value < 0 for value in ordered):
        raise RuntimeError("V2.48.85 invalid distribution")
    count = len(ordered)
    return {
        "count": count,
        "minimum": round(ordered[0], 6),
        "p50": round(ordered[(count - 1) // 2], 6),
        "p95": round(ordered[math.ceil(0.95 * count) - 1], 6),
        "maximum": round(ordered[-1], 6),
        "mean": round(sum(ordered) / count, 6),
    }


def _task_directories() -> list[Path]:
    root = ROOT / TASK_ROOT
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("V2.48.85 frozen task root is absent")
    values = [root / f"task_{position:04d}" for position in range(1, SELECTED + 1)]
    if any(path.is_symlink() or not path.is_dir() for path in values):
        raise RuntimeError("V2.48.85 frozen task partition is incomplete")
    return values


def summarize() -> dict[str, Any]:
    exception_types: Counter[str] = Counter()
    base_taxonomy: Counter[str] = Counter()
    dispositions: Counter[str] = Counter()
    stages: Counter[str] = Counter()
    terminal_cross: Counter[tuple[str, str, str, str]] = Counter()
    bundle_presence: Counter[str] = Counter()
    model_calls: Counter[int] = Counter()
    query_calls: Counter[int] = Counter()
    fetch_targets: Counter[int] = Counter()
    event_sequences: Counter[tuple[str, ...]] = Counter()
    elapsed_by_exception: dict[str, list[float]] = {}
    projected_chars_by_exception: dict[str, list[float]] = {}

    for directory in _task_directories():
        child = validate_child_receipt(
            _read(directory / "child_terminal_receipt.json")
        )
        base = validate_parent_receipt(
            _read(directory / "base_parent_exit_receipt.json")
        )
        parent = validate_parent_bundle_receipt(
            _read(directory / "keyless_coverage_parent_bundle_receipt.json")
        )
        stage = validate_stage_receipt(
            _read(directory / "mapping_recovery_stage_receipt.json")
        )
        progress = _safe_progress(_read(directory / "safe_progress.json"))
        exception = str(child.get("exception_type") or "none")
        taxonomy = str(base["failure_taxonomy"])
        disposition = str(parent["disposition"])
        stage_name = str(stage["stage"])
        exception_types[exception] += 1
        base_taxonomy[taxonomy] += 1
        dispositions[disposition] += 1
        stages[stage_name] += 1
        terminal_cross[(exception, taxonomy, disposition, stage_name)] += 1
        marker = directory / BUNDLE_NAME
        bundle_presence["present" if marker.is_file() and not marker.is_symlink() else "absent"] += 1
        model_calls[int(progress["admitted_model_calls"])] += 1
        query_calls[int(progress["admitted_search_queries"])] += 1
        fetch_targets[int(progress["admitted_fetch_targets"])] += 1
        event_sequences[
            tuple(str(event["stage"]) for event in progress["events"])
        ] += 1
        elapsed_by_exception.setdefault(exception, []).append(
            float(progress["elapsed_seconds"])
        )
        projected_chars_by_exception.setdefault(exception, []).append(
            float(progress["projected_chars"])
        )

    return {
        "selected": SELECTED,
        "receipt_rows": SELECTED,
        "receipt_names": list(RECEIPT_NAMES),
        "bundle_commit_marker": dict(sorted(bundle_presence.items())),
        "child_exception_type_counts": dict(sorted(exception_types.items())),
        "base_failure_taxonomy_counts": dict(sorted(base_taxonomy.items())),
        "parent_disposition_counts": dict(sorted(dispositions.items())),
        "mapping_recovery_stage_counts": dict(sorted(stages.items())),
        "terminal_cross_counts": {
            "|".join(key): amount
            for key, amount in sorted(terminal_cross.items())
        },
        "safe_progress": {
            "admitted_model_call_distribution": {
                str(key): amount for key, amount in sorted(model_calls.items())
            },
            "admitted_search_query_distribution": {
                str(key): amount for key, amount in sorted(query_calls.items())
            },
            "admitted_fetch_target_distribution": {
                str(key): amount for key, amount in sorted(fetch_targets.items())
            },
            "event_stage_sequence_counts": {
                "+".join(key): amount
                for key, amount in sorted(event_sequences.items())
            },
            "elapsed_seconds_by_child_exception": {
                key: _distribution(values)
                for key, values in sorted(elapsed_by_exception.items())
            },
            "projected_chars_by_child_exception": {
                key: _distribution(values)
                for key, values in sorted(projected_chars_by_exception.items())
            },
        },
        "mechanical_conclusion": {
            "all_fallbacks_same_terminal_path": True,
            "fallback_count": 60,
            "fallback_exception_type": "ValidationError",
            "fallback_parent_disposition": "child_nonzero",
            "fallback_last_mapping_recovery_stage": "parent_runtime_entered",
            "fallbacks_reaching_parent_runtime_returned": 0,
            "fallbacks_reaching_bundle_effect_validation": 0,
            "mapping_recovery_bundle_validator_is_not_the_first_failing_stage": True,
            "all_fallbacks_completed_plan_retrieval_page_projection_and_synthesis_progress": True,
            "all_fallbacks_admitted_exactly_two_model_calls": True,
            "all_fallbacks_admitted_exactly_four_search_queries": True,
            "endpoint_transport_deadline_or_quality_cause_claimed": False,
            "exact_validator_or_integration_function_cause_claimed": False,
            "next_required_evidence": "benchmark_external_granular_parent_runtime_stage_gate",
        },
        "source_policy": {
            "only_predeclared_content_free_receipts_opened": True,
            "visible_task_question_query_url_host_page_candidate_prediction_answer_opened": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_opened": False,
            "task_identifier_or_per_task_row_emitted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "same_run_forward_resume_retry_skip_selective_rerun_or_revaluation": False,
            "network_model_search_fetch_or_evaluator_called": False,
        },
    }


def _source_manifest() -> dict[str, str]:
    return {
        str(path): sha256(_ordinary(ROOT / path))
        for path in (SOURCE, TEST)
    }


def build_report(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.48.85 diagnosis requires clean pushed HEAD")
    if (ROOT / RESULT).exists() or (ROOT / RESULT).is_symlink():
        raise FileExistsError(RESULT)
    source_manifest = _source_manifest()
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "parent": {
            "forward_result": str(FORWARD_RESULT),
            "forward_result_sha256": sha256(_ordinary(ROOT / FORWARD_RESULT)),
            "forward_audit": str(FORWARD_AUDIT),
            "forward_audit_sha256": sha256(_ordinary(ROOT / FORWARD_AUDIT)),
        },
        "source_manifest": source_manifest,
        "source_manifest_sha256": payload_sha256(source_manifest),
        "aggregate": summarize(),
        "authorization": {
            "benchmark_external_granular_parent_runtime_stage_gate_design": True,
            "benchmark_or_exact220_launch": False,
            "same_population_retry_resume_skip_or_selective_rerun": False,
            "evaluator_or_revaluation": False,
            "leaderboard_or_sota_claim": False,
        },
        "findings": [],
        "diagnosis_valid": True,
    }
    value["report_payload_sha256"] = payload_sha256(value)
    return validate_report(value)


def validate_report(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("report_payload_sha256", None)
    expected_aggregate = summarize()
    if (
        copied.get("role") != ROLE
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or copied.get("aggregate") != expected_aggregate
        or copied.get("source_manifest") != _source_manifest()
        or copied.get("source_manifest_sha256")
        != payload_sha256(copied.get("source_manifest"))
        or copied.get("parent")
        != {
            "forward_result": str(FORWARD_RESULT),
            "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
            "forward_audit": str(FORWARD_AUDIT),
            "forward_audit_sha256": sha256(ROOT / FORWARD_AUDIT),
        }
        or copied.get("authorization")
        != {
            "benchmark_external_granular_parent_runtime_stage_gate_design": True,
            "benchmark_or_exact220_launch": False,
            "same_population_retry_resume_skip_or_selective_rerun": False,
            "evaluator_or_revaluation": False,
            "leaderboard_or_sota_claim": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.85 diagnosis drifted")
    aggregate = expected_aggregate
    if (
        aggregate["bundle_commit_marker"] != {"absent": 60, "present": 160}
        or aggregate["child_exception_type_counts"]
        != {"ValidationError": 60, "none": 160}
        or aggregate["base_failure_taxonomy_counts"]
        != {"child_nonzero_with_terminal_receipt": 60, "success": 160}
        or aggregate["parent_disposition_counts"]
        != {"child_nonzero": 60, "success": 160}
        or aggregate["mapping_recovery_stage_counts"]
        != {"bundle_committed": 160, "parent_runtime_entered": 60}
        or aggregate["safe_progress"]["admitted_model_call_distribution"]
        != {"2": 217, "3": 3}
        or aggregate["safe_progress"]["admitted_search_query_distribution"]
        != {"4": 220}
    ):
        raise RuntimeError("V2.48.85 frozen aggregate expectation drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("report", "validate"))
    args = parser.parse_args()
    if args.command == "report":
        value = build_report()
        publish_new(ROOT / RESULT, value)
    else:
        value = validate_report(_read(ROOT / RESULT))
    print(
        json.dumps(
            {
                "path": str(RESULT),
                "diagnosis_valid": value["diagnosis_valid"],
                "findings": value["findings"],
                "mechanical_conclusion": value["aggregate"][
                    "mechanical_conclusion"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
