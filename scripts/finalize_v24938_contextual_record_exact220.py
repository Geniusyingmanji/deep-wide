#!/usr/bin/env python3
"""Post-freeze mechanism audit and evaluator for V2.49.38 exact-220."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24938_contextual_record_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24932_unicode_total_exact220 as parent  # noqa: E402
from scripts import run_v24938_contextual_record_exact220_task as child  # noqa: E402


def _mechanism_aggregate() -> dict[str, Any]:
    names = (
        "input_page_count",
        "projected_page_count",
        "input_block_count",
        "projected_block_count",
        "visible_row_target_count",
        "visible_value_target_count",
        "value_bearing_row_block_count",
        "context_dependent_value_block_count",
        "supported_bound_target_value_pair_count",
        "retained_bound_target_value_pair_count",
        "missed_bound_target_value_pair_count",
        "supported_contextual_target_value_pair_count",
        "retained_contextual_target_value_pair_count",
        "missed_contextual_target_value_pair_count",
        "projected_rendered_characters",
        "selected_context_dependent_block_count",
        "context_dependency_addition_count",
        "orphan_selected_context_dependent_block_count",
        "selected_table_continuation_block_count",
        "table_header_dependency_addition_count",
        "orphan_selected_table_continuation_block_count",
    )
    totals = {name: 0 for name in names}
    present = 0
    mechanism_tasks = 0
    contextual_tasks = 0
    invalid: list[int] = []
    missing: list[int] = []
    for position in range(1, contract.SELECTED_COUNT + 1):
        path = (
            ROOT
            / contract.TASK_ROOT
            / f"task_{position:04d}"
            / contract.PROJECTION_RECEIPT_NAME
        )
        if path.is_symlink() or not path.is_file():
            missing.append(position)
            continue
        try:
            value = child.validate_runtime_receipt(parent.parent.base._read(path))
            receipt = value["candidate_receipt"]
        except (KeyError, OSError, RuntimeError, TypeError, ValueError):
            invalid.append(position)
            continue
        present += 1
        for name in names:
            totals[name] += int(receipt[name])
        if int(receipt["supported_bound_target_value_pair_count"]) > 0:
            mechanism_tasks += 1
        if int(receipt["supported_contextual_target_value_pair_count"]) > 0:
            contextual_tasks += 1
    return {
        "selected_tasks": contract.SELECTED_COUNT,
        "valid_content_free_receipts": present,
        "missing_receipts": len(missing),
        "invalid_receipts": len(invalid),
        "missing_task_positions": missing,
        "invalid_task_positions": invalid,
        "tasks_with_supported_bound_target_value_pair": mechanism_tasks,
        "tasks_with_supported_contextual_target_value_pair": contextual_tasks,
        "totals": totals,
        "mechanism_engaged": totals["supported_bound_target_value_pair_count"] > 0,
        "contextual_mechanism_engaged": totals[
            "supported_contextual_target_value_pair_count"
        ]
        > 0,
        "contains_question_query_url_host_page_projection_prediction_hash_or_opaque_id": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "entropy_or_information_gain_assigns_credit": False,
    }


def configure() -> None:
    parent.contract = contract
    parent.configure()
    engine = parent.parent.base
    date = contract.DATE
    evaluator_root = contract.OUTPUT_ROOT / "evaluator"
    engine.EVALUATOR_PROTOCOL = Path(
        f"results/v24938_contextual_record_exact220_evaluator_preregistration_v1_{date}.json"
    )
    engine.FINAL_RESULT = Path(
        f"results/v24938_contextual_record_exact220_result_v1_{date}.json"
    )
    engine.POSTAUDIT = Path(
        f"results/v24938_contextual_record_exact220_postresult_audit_v1_{date}.json"
    )
    engine.EVALUATOR_ROOT = evaluator_root
    engine.PREPARE_ATTESTATION = evaluator_root / "prepare_attestation.json"
    engine.JOINED_OUTCOMES = evaluator_root / "terminal_outcomes_evaluator_joined.jsonl"
    engine.OFFICIAL_PREDICTIONS = evaluator_root / "official_predictions.jsonl"
    engine.EVALUATOR_RUNS = evaluator_root / "official_eval_workers"
    engine.EVALUATOR_LOGS = evaluator_root / "logs"
    engine.MERGED_RESULTS = evaluator_root / "official_eval_results.jsonl"
    engine.MERGE_ATTESTATION = evaluator_root / "merge_attestation.json"
    engine.SUMMARY = evaluator_root / "conservative_summary.json"
    engine.EVALUATOR_OWNER = "v24938_contextual_record_exact220_evaluator_v1"
    engine.EVALUATOR_PURPOSE = (
        "postfreeze_fixed_partition_parallel_contextual_record_exact220_evaluator"
    )
    engine.CONTROL_FILES = tuple(
        dict.fromkeys(
            (
                str(contract.FINALIZER),
                str(contract.RUNNER),
                str(contract.CHILD),
                str(contract.CONTROL),
                str(contract.SOURCE),
                str(contract.PROJECTOR_SOURCE),
                str(contract.LEGACY_PROJECTOR_SOURCE),
                str(contract.TARGET_VALUE_SOURCE),
                str(contract.BINDING),
                str(contract.TEST),
                *engine.CONTROL_FILES,
            )
        )
    )
    engine.REFERENCES = {
        **engine.REFERENCES,
        "v24857": Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json"),
        "v24932": Path("results/v24932_unicode_total_exact220_result_v1_20260809.json"),
        "v24935": Path("results/v24935_unicode_total_replication_result_v1_20260809.json"),
    }

    inherited_build_forward_audit = engine.build_forward_audit

    def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
        value = copy.deepcopy(inherited_build_forward_audit(now=now))
        aggregate = _mechanism_aggregate()
        value["contextual_record_mechanism"] = aggregate
        value["checks"]["all_present_projection_receipts_valid"] = (
            aggregate["invalid_receipts"] == 0
        )
        value["checks"]["receipt_partition_exact220"] = (
            aggregate["valid_content_free_receipts"]
            + aggregate["missing_receipts"]
            + aggregate["invalid_receipts"]
            == 220
        )
        value["findings"] = sorted(
            name for name, passed in value["checks"].items() if not passed
        )
        value["audit_valid"] = not value["findings"]
        value["authorization"]["postfreeze_exact220_evaluator_protocol"] = value[
            "audit_valid"
        ]
        value.pop("audit_payload_sha256", None)
        value["audit_payload_sha256"] = contract.payload_sha256(value)
        return value

    engine.build_forward_audit = build_forward_audit


def main() -> None:
    configure()
    parent.parent.base.main()


if __name__ == "__main__":
    main()
