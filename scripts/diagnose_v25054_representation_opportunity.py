#!/usr/bin/env python3
"""Content-free diagnosis of the next representation opportunity.

This post-freeze script reads only aggregate result objects and V2.50.30's
content-free per-task receipts.  It never opens questions, task identifiers,
predictions, page text, URLs, evaluator rows, mapping, gold, or credentials.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v25048_atomic_pypi_representation_contract import (  # noqa: E402
    payload_sha256,
    sha256,
)


V25030_RECEIPTS = Path(
    "outputs/v25030_evidence_conditioned_exact220_v1_20260810/"
    "content_free_task_receipts.jsonl"
)
V25030_FREEZE = Path(
    "outputs/v25030_evidence_conditioned_exact220_v1_20260810/"
    "prediction_freeze.json"
)
V25030_FORWARD_AUDIT = Path(
    "results/v25030_evidence_conditioned_exact220_forward_audit_v1_20260810.json"
)
V25048_RESULT = Path("results/v25048_atomic_pypi_result_v1_20260811.json")
V25048_POSTAUDIT = Path(
    "results/v25048_atomic_pypi_postresult_audit_v1_20260811.json"
)
V25053_FORWARD = Path(
    "results/v25053_cran_unconditional_forward_result_v1_20260811.json"
)
V25053_FORWARD_AUDIT = Path(
    "results/v25053_cran_unconditional_forward_audit_v1_20260811.json"
)
OUTPUT = Path(
    "results/v25054_representation_opportunity_diagnosis_v1_20260811.json"
)


def _json(relative: Path) -> dict[str, Any]:
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.50.54 expected ordinary frozen JSON")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.54 expected JSON object")
    return value


def _receipts() -> list[dict[str, Any]]:
    path = ROOT / V25030_RECEIPTS
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.50.54 expected frozen receipt JSONL")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if len(rows) != 220 or not all(isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.50.54 receipt denominator drifted")
    return rows


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    rows = _receipts()
    freeze = _json(V25030_FREEZE)
    forward_audit = _json(V25030_FORWARD_AUDIT)
    pypi = _json(V25048_RESULT)
    pypi_audit = _json(V25048_POSTAUDIT)
    cran = _json(V25053_FORWARD)
    cran_audit = _json(V25053_FORWARD_AUDIT)
    if (
        freeze.get("terminal") != 220
        or freeze.get("content_free_task_receipts_sha256")
        != sha256(ROOT / V25030_RECEIPTS)
        or forward_audit.get("audit_valid") is not True
        or forward_audit.get("findings") != []
        or pypi.get("passed") is not True
        or pypi_audit.get("audit_valid") is not True
        or pypi_audit.get("findings") != []
        or cran_audit.get("audit_valid") is not True
        or cran_audit.get("findings") != []
    ):
        raise RuntimeError("V2.50.54 parent evidence is not closed")
    waves: dict[str, Counter[str]] = {
        "first_wave": Counter(),
        "second_wave": Counter(),
    }
    task_counts = Counter()
    for row in rows:
        if row.get(
            "contains_question_query_url_title_page_record_value_prediction_answer_hash_opaque_id_or_credential"
        ) is not False:
            raise RuntimeError("V2.50.54 receipt is not content-free")
        any_late = any_mechanism = any_change = False
        for output_name, receipt_name in (
            ("first_wave", "first_wave_receipt"),
            ("second_wave", "second_wave_receipt"),
        ):
            wave = row.get(receipt_name)
            fetch = wave.get("fetch_receipt") if isinstance(wave, dict) else None
            if not isinstance(fetch, dict):
                continue
            values = waves[output_name]
            for key in (
                "projected_page_count",
                "input_content_characters",
                "input_characters_beyond_parent_prefix",
                "candidate_evidence_changed_page_count",
                "mechanism_engaged_page_count",
                "exact_parent_prefix_handoff_page_count",
                "discovered_record_count",
                "admissible_record_count",
                "retained_record_count",
                "retained_bound_observation_count",
            ):
                values[key] += int(fetch.get(key, 0))
            any_late |= int(fetch.get("input_characters_beyond_parent_prefix", 0)) > 0
            any_mechanism |= int(fetch.get("mechanism_engaged_page_count", 0)) > 0
            any_change |= int(fetch.get("candidate_evidence_changed_page_count", 0)) > 0
        task_counts["tasks"] += 1
        task_counts["tasks_with_late_characters"] += int(any_late)
        task_counts["tasks_with_mechanism_exposure"] += int(any_mechanism)
        task_counts["tasks_with_candidate_evidence_change"] += int(any_change)
    production_pages = sum(
        values["projected_page_count"] for values in waves.values()
    )
    production_late_chars = sum(
        values["input_characters_beyond_parent_prefix"]
        for values in waves.values()
    )
    pypi_metrics = pypi["metrics"]["arms"]
    cran_aggregate = cran["aggregate"]
    value = {
        "artifact_version": 1,
        "role": "v25054_representation_opportunity_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "v25030_content_free_receipts_sha256": sha256(
                ROOT / V25030_RECEIPTS
            ),
            "v25030_prediction_freeze_sha256": sha256(ROOT / V25030_FREEZE),
            "v25030_forward_audit_sha256": sha256(ROOT / V25030_FORWARD_AUDIT),
            "v25048_result_sha256": sha256(ROOT / V25048_RESULT),
            "v25048_postaudit_sha256": sha256(ROOT / V25048_POSTAUDIT),
            "v25053_forward_result_sha256": sha256(ROOT / V25053_FORWARD),
            "v25053_forward_audit_sha256": sha256(ROOT / V25053_FORWARD_AUDIT),
        },
        "v25030_production_opportunity": {
            "tasks": dict(task_counts),
            "waves": {name: dict(values) for name, values in waves.items()},
            "projected_pages": production_pages,
            "characters_beyond_5k_prefix": production_late_chars,
            "old_identity_required_projector_exposed_pages": sum(
                values["mechanism_engaged_page_count"]
                for values in waves.values()
            ),
            "old_candidate_evidence_changed_pages": sum(
                values["candidate_evidence_changed_page_count"]
                for values in waves.values()
            ),
        },
        "v25048_late_structured_quality": {
            "control_exact": pypi_metrics["raw_pypi_json_prefix"][
                "exact_table_successes"
            ],
            "candidate_exact": pypi_metrics[
                "identity_bound_current_release_record"
            ]["exact_table_successes"],
            "control_composite": pypi_metrics["raw_pypi_json_prefix"][
                "composite"
            ],
            "candidate_composite": pypi_metrics[
                "identity_bound_current_release_record"
            ]["composite"],
            "quality_gate_go": pypi["decision"][
                "pypi_current_record_representation_quality_gate_go"
            ],
        },
        "v25053_short_ordinary_html": {
            "ready_tasks": cran_aggregate["ready_tasks"],
            "preparation_failure_tasks": cran_aggregate[
                "preparation_failure_tasks"
            ],
            "terminal_arm_predictions": cran_aggregate[
                "terminal_arm_predictions"
            ],
            "prediction_changed_tasks": cran_aggregate[
                "prediction_changed_tasks"
            ],
            "mechanism_gate_passed": cran["mechanism_decision"][
                "mechanism_gate_passed"
            ],
        },
        "decision": {
            "short_registry_page_gate_retired": True,
            "page_self_identity_production_integration_design_supported": (
                production_pages > 0
                and production_late_chars > 0
                and pypi["decision"][
                    "pypi_current_record_representation_quality_gate_go"
                ]
                is True
            ),
            "new_exact220_launch_authorized_by_diagnosis_alone": False,
            "required_next_gate": (
                "append_only_label_blind_production_integration_with_exact_"
                "parent_prefix_handoff_and_nonzero_natural_page_self_exposure"
            ),
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "question_task_id_prediction_page_url_query_record_value_or_gold_read": False,
            "evaluator_rows_or_mapping_read": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "only_postfreeze_content_free_counts_and_aggregate_results_read": True,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: dict[str, Any]) -> dict[str, Any]:
    copied = json.loads(json.dumps(value))
    seal_value = copied.pop("diagnosis_payload_sha256", None)
    opportunity = copied.get("v25030_production_opportunity") or {}
    decision = copied.get("decision") or {}
    policy = copied.get("content_policy") or {}
    if (
        value.get("role") != "v25054_representation_opportunity_diagnosis"
        or opportunity.get("projected_pages") != 1534
        or opportunity.get("characters_beyond_5k_prefix") != 23595703
        or opportunity.get("old_identity_required_projector_exposed_pages") != 0
        or opportunity.get("old_candidate_evidence_changed_pages") != 0
        or decision.get("short_registry_page_gate_retired") is not True
        or decision.get("page_self_identity_production_integration_design_supported")
        is not True
        or decision.get("new_exact220_launch_authorized_by_diagnosis_alone")
        is not False
        or decision.get("entropy_or_information_gain_signed_credit") != 0
        or any(policy.get(name) is not False for name in (
            "question_task_id_prediction_page_url_query_record_value_or_gold_read",
            "evaluator_rows_or_mapping_read",
            "network_model_search_fetch_or_evaluator_called",
        ))
        or policy.get(
            "only_postfreeze_content_free_counts_and_aggregate_results_read"
        ) is not True
        or seal_value != payload_sha256(copied)
    ):
        raise RuntimeError("V2.50.54 diagnosis drifted")
    return value


def publish_exclusive(path: Path, value: dict[str, Any]) -> None:
    """Durably publish one immutable diagnosis without a check/write race."""

    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V2.50.54 diagnosis publication made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent_descriptor = os.open(
        path.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )
    try:
        os.fsync(parent_descriptor)
    finally:
        os.close(parent_descriptor)


def main() -> None:
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "projected_pages": value["v25030_production_opportunity"][
                    "projected_pages"
                ],
                "late_characters": value["v25030_production_opportunity"][
                    "characters_beyond_5k_prefix"
                ],
                "old_exposure_pages": value["v25030_production_opportunity"][
                    "old_identity_required_projector_exposed_pages"
                ],
                "next_design_supported": value["decision"][
                    "page_self_identity_production_integration_design_supported"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
