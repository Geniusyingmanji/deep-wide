#!/usr/bin/env python3
"""Diagnose the content-free failure-observability gap in V2.43.95.

The V2.43.95 result is immutable and remains a valid NO-GO.  This diagnostic
proves that its fifteen synthetic ``local_failure`` rows do not preserve the
underlying child/parent exit taxonomy or partial provider effects.  It reads
only sealed public artifacts and frozen source code, and performs one fully
local controlled reproduction with no model, search, fetch, or evaluator.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import parent_receipt  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import ObservedChildOutcome  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24393_uncertainty_external_projection as projection  # noqa: E402
from scripts import v24395_uncertainty_external_gate as parent_gate  # noqa: E402


DATE = "20260804"
RESULT = Path(f"results/v24395_uncertainty_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24395_uncertainty_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24395_uncertainty_external_postresult_audit_v1_{DATE}.json"
)
DIAGNOSIS = Path(
    f"results/v24396_v24395_failure_observability_diagnosis_v1_{DATE}.json"
)
BOUND_SOURCES = (
    Path("scripts/v24393_uncertainty_external_projection.py"),
    Path("scripts/v24395_uncertainty_external_gate.py"),
    Path("src/deepwide_agent/v24308_child_exit_observability.py"),
    Path("src/deepwide_agent/v24309_runner_exit_integration.py"),
    Path("scripts/diagnose_v24396_v24395_failure_observability.py"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    target = path.resolve(strict=False)
    if path.is_symlink() or not path.is_file() or not target.is_relative_to(root):
        raise RuntimeError(f"V2.43.96 expected repository file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.43.96 expected object: {relative}")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _failure_parent() -> dict[str, Any]:
    return parent_receipt(
        return_code=1,
        timed_out=False,
        elapsed_seconds=12.5,
        subprocess_exception=False,
        child_terminal_receipt_present=True,
        child_terminal_receipt_valid=True,
        result_envelope_present=False,
        result_envelope_valid=False,
        model_receipt_present=False,
        model_receipt_valid=False,
        transport_receipt_present=False,
        transport_receipt_valid=False,
    )


def reproduce_projection_collapse(root: Path) -> dict[str, Any]:
    """Reproduce the failing branch without starting a subprocess or network."""

    receipt = _failure_parent()
    original = parent_gate.run_observed_subprocess

    def fake_observed_subprocess(**_: Any) -> ObservedChildOutcome:
        return ObservedChildOutcome(
            return_code=1,
            timed_out=False,
            subprocess_exception=False,
            receipt=receipt,
        )

    raised = None
    with tempfile.TemporaryDirectory(dir=root / "outputs") as temporary:
        output = Path(temporary)
        directory = output / "task_01"
        slots = output / "slots"
        directory.mkdir()
        slots.mkdir()
        parent_gate.run_observed_subprocess = fake_observed_subprocess
        try:
            parent_gate._run_one(root, output, slots, directory, 1)
        except Exception as error:  # Expected controlled reproduction.
            raised = type(error).__name__
        finally:
            parent_gate.run_observed_subprocess = original

    synthetic = projection.local_failure(1)
    return {
        "injected_parent_taxonomy": receipt["failure_taxonomy"],
        "run_one_raised_exception_type": raised,
        "outer_replacement_taxonomy": synthetic["parent_taxonomy"],
        "outer_replacement_deadline_exhausted": synthetic["deadline_exhausted"],
        "outer_replacement_effect_counts_zero": all(
            synthetic[name] == 0
            for name in (
                "model_requests",
                "slot_acquisitions",
                "slot_timeouts",
                "provider_deadline_failures",
                "hosted_search_attempts",
                "hard_fetch_helper_calls",
            )
        ),
        "underlying_taxonomy_preserved": synthetic["parent_taxonomy"]
        == receipt["failure_taxonomy"],
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = parent_gate.validate_public_result(_read(root, RESULT))
    decision = parent_gate.validate_decision(root, value=_read(root, DECISION))
    postaudit = parent_gate.validate_postaudit(root, value=_read(root, POSTAUDIT))
    aggregate = result["aggregate"]
    reproduction = reproduce_projection_collapse(root)
    fallback_count = int(aggregate["completion_kinds"].get("None", 0))
    if (
        result["passed"] is not False
        or decision["status"] != "fresh_uncertainty_external_no_go"
        or postaudit["audit_valid"] is not True
        or aggregate["selected"] != 16
        or aggregate["terminal_success_tasks"] != 1
        or fallback_count != 15
        or aggregate["deadline_exhausted_tasks"] != fallback_count
        or reproduction
        != {
            "injected_parent_taxonomy": "child_nonzero_with_terminal_receipt",
            "run_one_raised_exception_type": "ValueError",
            "outer_replacement_taxonomy": "local_projection_failure",
            "outer_replacement_deadline_exhausted": True,
            "outer_replacement_effect_counts_zero": True,
            "underlying_taxonomy_preserved": False,
        }
    ):
        raise RuntimeError("V2.43.96 diagnostic premise drifted")
    source_manifest = {
        str(path): sha256(_ordinary(root, path)) for path in BOUND_SOURCES
    }
    value = {
        "artifact_version": 1,
        "role": "v24396_v24395_failure_observability_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            str(RESULT): sha256(root / RESULT),
            str(DECISION): sha256(root / DECISION),
            str(POSTAUDIT): sha256(root / POSTAUDIT),
        },
        "source_manifest": source_manifest,
        "source_manifest_sha256": payload_sha256(source_manifest),
        "observed": {
            "selected": 16,
            "terminal_success_tasks": 1,
            "synthetic_local_failure_rows": fallback_count,
            "reported_deadline_exhausted_tasks": aggregate[
                "deadline_exhausted_tasks"
            ],
            "observable_success_model_requests": aggregate["model_requests"],
            "observable_success_hosted_search_attempts": aggregate[
                "hosted_search_attempts"
            ],
            "observable_success_epistemic_credit_nats": aggregate[
                "epistemic_credit_total_nats"
            ],
        },
        "controlled_reproduction": reproduction,
        "mechanical_conclusion": {
            "v24395_no_go_remains_valid": True,
            "non_success_parent_enters_success_only_projection_with_none_envelope": True,
            "success_only_projection_raises_before_preserving_parent_taxonomy": True,
            "outer_handler_replaces_any_exception_with_one_synthetic_row": True,
            "synthetic_row_forces_deadline_exhausted_true": True,
            "synthetic_row_zeros_partial_model_search_fetch_effects": True,
            "temporary_task_directory_deleted_after_aggregation": True,
            "underlying_fifteen_exit_taxonomies_recoverable_posthoc": False,
        },
        "claim_audit": {
            "supported": [
                "v24395_external_gate_is_no_go",
                "one_of_sixteen_tasks_has_a_valid_mechanism_projection",
                "fifteen_rows_are_synthetic_local_projection_failures",
                "the_one_observable_task_has_zero_epistemic_credit",
            ],
            "not_supported": [
                "all_fifteen_failures_were_real_deadline_exhaustions",
                "failed_tasks_made_no_model_search_or_fetch_effects",
                "model_slot_capacity_is_the_root_cause",
                "provider_or_search_health_is_proven_for_failed_tasks",
                "population_level_entropy_mechanism_failure_is_proven",
            ],
        },
        "required_fix": {
            "branch_on_parent_taxonomy_before_success_envelope_projection": True,
            "persist_content_free_child_stage_and_coarse_exception": True,
            "persist_partial_model_and_transport_receipts_on_child_exception": True,
            "aggregate_failure_taxonomy_and_partial_effect_counts_before_cleanup": True,
            "keep_task_text_query_url_page_prediction_and_response_private": True,
        },
        "source_policy": {
            "runtime_input_or_task_private_content_read": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_resume_retry_rerun_or_revaluation": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
        },
        "findings": ["failure_taxonomy_and_partial_effects_collapsed"],
        "diagnosis_valid": True,
        "authorization": {
            "append_only_failure_observability_fix_design": True,
            "new_external_probe": False,
            "benchmark_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    validate_report(root, value=value)
    return value


def validate_report(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    report = dict(value) if value is not None else _read(root, DIAGNOSIS)
    unsigned = dict(report)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    conclusion = report.get("mechanical_conclusion")
    policy = report.get("source_policy")
    authorization = report.get("authorization")
    required = report.get("required_fix")
    if (
        report.get("artifact_version") != 1
        or report.get("role")
        != "v24396_v24395_failure_observability_diagnosis"
        or report.get("parents")
        != {
            str(RESULT): sha256(root / RESULT),
            str(DECISION): sha256(root / DECISION),
            str(POSTAUDIT): sha256(root / POSTAUDIT),
        }
        or report.get("source_manifest")
        != {str(path): sha256(_ordinary(root, path)) for path in BOUND_SOURCES}
        or report.get("source_manifest_sha256")
        != payload_sha256(report["source_manifest"])
        or report.get("observed", {}).get("synthetic_local_failure_rows") != 15
        or report.get("controlled_reproduction", {}).get(
            "underlying_taxonomy_preserved"
        )
        is not False
        or not isinstance(conclusion, Mapping)
        or any(item is not True for item in conclusion.values() if item is not False)
        or conclusion.get("underlying_fifteen_exit_taxonomies_recoverable_posthoc")
        is not False
        or not isinstance(required, Mapping)
        or any(item is not True for item in required.values())
        or not isinstance(policy, Mapping)
        or any(item is not False for item in policy.values())
        or report.get("findings")
        != ["failure_taxonomy_and_partial_effects_collapsed"]
        or report.get("diagnosis_valid") is not True
        or not isinstance(authorization, Mapping)
        or authorization.get("append_only_failure_observability_fix_design")
        is not True
        or any(
            authorization.get(name) is not False
            for name in (
                "new_external_probe",
                "benchmark_launch",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.96 diagnosis drifted")
    return report


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
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
    artifact = build_report()
    publish_new(ROOT / DIAGNOSIS, artifact)
    print(json.dumps({"path": str(DIAGNOSIS), "diagnosis_valid": True}))
