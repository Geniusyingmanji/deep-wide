#!/usr/bin/env python3
"""Apply V2.43.32 stratified accounting to the frozen V2.43.30 receipts."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model_receipt,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24326_runner_integration import (  # noqa: E402
    validate_envelope,
    validate_observed_bundle,
)
from deepwide_agent.v24330_forward_contract import (  # noqa: E402
    MODEL_SLOT_CAP,
    PROTOCOL_ID,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    read_object,
    sha256,
)
from deepwide_agent.v24332_stratified_effect_aggregate import (  # noqa: E402
    DEFAULT_MAXIMUM_INCOMPLETE_TASKS,
    build_aggregate,
    build_task_receipt,
    validate_aggregate,
)
from scripts import diagnose_v24331_v24330_postterminal as taxonomy  # noqa: E402


OUTPUT = Path("results/v24332_v24330_stratified_effect_aggregate_v1_20260803.json")
SOURCE = Path("src/deepwide_agent/v24332_stratified_effect_aggregate.py")
FAULT_TEST = Path("tests/test_v24332_stratified_effect_aggregate.py")
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _task_directories(root: Path) -> list[Path]:
    base = root / TASK_ROOT
    if base.is_symlink() or not base.is_dir():
        raise RuntimeError("V2.43.32 frozen task root is absent")
    expected = [base / f"task_{index:04d}" for index in range(1, SELECTED_COUNT + 1)]
    if any(path.is_symlink() or not path.is_dir() for path in expected):
        raise RuntimeError("V2.43.32 frozen task partition is incomplete")
    present = sorted(path for path in base.glob("task_*") if path.is_dir())
    if present != expected:
        raise RuntimeError("V2.43.32 frozen task partition drifted")
    return expected


def _receipts(root: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for directory in _task_directories(root):
        result_path = directory / "result.json"
        model_path = directory / "model_slot_receipt.json"
        transport_path = directory / "transport_health.json"
        if any(
            path.is_symlink() or not path.is_file()
            for path in (result_path, model_path, transport_path)
        ):
            raise RuntimeError("V2.43.32 frozen task effect artifact is absent")
        envelope = validate_envelope(read_object(result_path))
        model = validate_model_receipt(
            read_object(model_path), expected_cap=MODEL_SLOT_CAP
        )
        transport = validate_transport_health(read_object(transport_path))
        validate_observed_bundle(
            envelope,
            model_slot_receipt=model,
            transport_health=transport,
            expected_cap=MODEL_SLOT_CAP,
        )
        result = envelope["result"]
        receipt = result["shared_prefix_revision_receipt"]
        complete = receipt["effect_accounting_complete"] is True
        terminal_kind = (
            "incomplete_fallback"
            if not complete
            else "complete_fallback"
            if result["completion_kind"] == "identity_fallback"
            else "complete_success"
        )
        output.append(
            build_task_receipt(
                terminal_kind=terminal_kind,
                effect_accounting_complete=complete,
                logical_model_admissions=int(receipt["logical_model_admissions"]),
                provider_model_requests=int(receipt["provider_model_requests"]),
                provider_model_attempts=int(receipt["provider_model_attempts"]),
                pre_provider_model_rejections=int(
                    receipt["pre_provider_model_rejections"]
                ),
                slot_acquisitions=int(model["acquisitions"]),
                slot_timeouts=int(model["slot_timeouts"]),
                provider_deadline_failures=int(model["provider_deadline_failures"]),
                hosted_search_attempts=int(transport["hosted_search_attempts"]),
                hosted_search_deadline_failures=int(
                    transport["hosted_search_deadline_failures"]
                ),
                hard_fetch_helper_calls=int(transport["hard_fetch_helper_calls"]),
                hard_fetch_deadline_failures=int(
                    transport["hard_fetch_deadline_failures"]
                ),
                fetch_helper_failures=int(transport["fetch_helper_failures"]),
                fetch_deadline_rejections=int(
                    transport["fetch_deadline_rejections"]
                ),
                deadline_exhausted_tasks=int(
                    transport["deadline_exhausted"] is True
                ),
                unattributed_model_effects_lower_bound=int(
                    receipt["unattributed_model_effects_lower_bound"]
                ),
                unattributed_model_attempts_lower_bound=int(
                    receipt["unattributed_model_attempts_lower_bound"]
                ),
                unattributed_search_effects_lower_bound=int(
                    receipt["unattributed_search_effects_lower_bound"]
                ),
                unattributed_fetch_effects_lower_bound=int(
                    receipt["unattributed_fetch_effects_lower_bound"]
                ),
            )
        )
    return output


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parent = read_object(root / taxonomy.OUTPUT)
    taxonomy.validate_report(root, parent)
    aggregate = build_aggregate(
        _receipts(root),
        maximum_incomplete_tasks=DEFAULT_MAXIMUM_INCOMPLETE_TASKS,
    )
    validate_aggregate(aggregate)
    parent_effect = parent["aggregate"]["effect_accounting"]
    if (
        aggregate["selected_tasks"] != SELECTED_COUNT
        or aggregate["complete_tasks"] != parent_effect["complete_tasks"]
        or aggregate["incomplete_tasks"] != parent_effect["incomplete_tasks"]
        or aggregate["complete_task_totals"]
        != parent_effect["complete_task_totals"]
        or aggregate["incomplete_task_independent_lower_bounds"]
        != {
            **parent_effect["incomplete_task_independent_lower_bounds"],
            "provider_deadline_failures": 4,
            "hosted_search_attempts": 84,
            "hosted_search_deadline_failures": 0,
            "hard_fetch_helper_calls": 583,
            "hard_fetch_deadline_failures": 4,
            "fetch_helper_failures": 1,
            "fetch_deadline_rejections": 0,
            "deadline_exhausted_tasks": 15,
        }
        or aggregate["promotion_passed"] is not False
        or aggregate["promotion_checks"]["incomplete_task_count"] is not False
    ):
        raise RuntimeError("V2.43.32 V2.43.30 projection drifted")
    value = {
        "artifact_version": 1,
        "role": "v24332_v24330_stratified_effect_aggregate_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "v24331_taxonomy_path": str(taxonomy.OUTPUT),
            "v24331_taxonomy_sha256": sha256(root / taxonomy.OUTPUT),
            "v24330_forward_nogo_sha256": sha256(root / taxonomy.parent.RESULT),
        },
        "source": {
            "path": str(SOURCE),
            "sha256": sha256(root / SOURCE),
        },
        "aggregate": aggregate,
        "decision": {
            "status": "validator_correct_forward_still_no_go",
            "structural_accounting_valid": True,
            "promotion_passed": aggregate["promotion_passed"],
            "failed_checks": sorted(
                name
                for name, passed in aggregate["promotion_checks"].items()
                if not passed
            ),
            "same_run_evaluation_authorized": False,
            "new_exact220_authorized": False,
        },
        "fault_matrix_contract": {
            "test_path": str(FAULT_TEST),
            "required_cases": [
                "complete_success",
                "complete_fallback",
                "incomplete_fallback_valid_lower_bounds",
                "tampered_lower_bound_rejection",
            ],
            "benchmark_external": True,
            "remote_effects": 0,
        },
        "boundary": {
            "postterminal_only": True,
            "task_receipts_projected_in_memory": SELECTED_COUNT,
            "per_task_receipt_identifier_position_hash_or_content_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_forward_resume_retry_rerun_or_selective_retry": False,
        },
        "claims": {
            "aggregate_validator_bug_fixed_append_only": True,
            "v24330_mechanism_activated": False,
            "quality_improvement_demonstrated": False,
            "benchmark_score_available": False,
            "sota": False,
        },
        "authorization": {
            "benchmark_external_evidence_admission_successor": True,
            "same_run_evaluator": False,
            "same_run_forward_resume_retry_or_rerun": False,
            "additional_dev64": False,
            "new_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if SECRET.search(encoded) or OPAQUE.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.43.32 aggregate result emitted prohibited content")
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    expected = build_report(root, now=int(value.get("created_at_unix", -1)))
    if dict(value) != expected or not _sealed(value, "result_payload_sha256"):
        raise RuntimeError("V2.43.32 aggregate result drifted")
    return dict(value)


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    validate_report(ROOT, report)
    publish_new(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "promotion_passed": report["decision"]["promotion_passed"],
                "failed_checks": report["decision"]["failed_checks"],
            },
            sort_keys=True,
        )
    )
