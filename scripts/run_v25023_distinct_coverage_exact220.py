#!/usr/bin/env python3
"""Run one label-blind V2.50.23 exact-220 forward."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25023_distinct_coverage_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24981_late_page_bound_fetch import validate_receipt as validate_projection_receipt  # noqa: E402
from deepwide_agent.v25019_production_distinct_coverage_selection import validate_receipt as validate_distinct_receipt  # noqa: E402
from scripts import run_v24800_exact220 as engine  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220 as pacing  # noqa: E402


def _read(path: Path) -> dict[str, Any]:
    return engine._read(path)


def _validate_bundle(value: dict[str, Any], directory: Path) -> None:
    pacing._validate_bundle(value, directory)
    validate_distinct_receipt(_read(directory / contract.DISTINCT_RECEIPT_NAME))
    validate_projection_receipt(_read(directory / contract.PROJECTION_RECEIPT_NAME))


def _distinct_totals(root: Path) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    missing = invalid = 0
    for position in range(1, contract.SELECTED_COUNT + 1):
        path = root / contract.TASK_ROOT / f"task_{position:04d}" / contract.DISTINCT_RECEIPT_NAME
        if not path.exists() and not path.is_symlink():
            missing += 1
            continue
        try:
            receipts.append(validate_distinct_receipt(_read(path)))
        except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            invalid += 1
    sums = (
        "visible_identity_count",
        "legacy_control_selected_url_count",
        "candidate_selected_url_count",
        "available_attested_child_link_count",
        "prior_covered_distinct_identity_count",
        "control_new_distinct_identity_count",
        "candidate_new_distinct_identity_count",
        "new_distinct_identity_gain",
        "selection_changed",
    )
    return {
        "task_receipts": contract.SELECTED_COUNT,
        "valid_receipts": len(receipts),
        "invalid_receipts": invalid,
        "missing_receipts": missing,
        "invalid_or_missing_receipts": invalid + missing,
        "strategy_eligible_tasks": sum(row["strategy_eligible"] for row in receipts),
        "mechanism_engaged_tasks": sum(row["mechanism_engaged"] for row in receipts),
        **{name: sum(int(row[name]) for row in receipts) for name in sums},
        "control_exactly_replays_frozen_v24857_lead_prefix": all(
            row["control_exactly_replays_frozen_v24857_lead_prefix"] for row in receipts
        ),
        "candidate_fetch_count_equals_control": all(
            row["candidate_fetch_count_equals_control"] for row in receipts
        ),
        "entropy_or_information_gain_assigns_signed_credit": False,
        "question_identity_query_url_page_prediction_answer_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }


def _projection_totals(root: Path) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    missing = invalid = 0
    for position in range(1, contract.SELECTED_COUNT + 1):
        path = root / contract.TASK_ROOT / f"task_{position:04d}" / contract.PROJECTION_RECEIPT_NAME
        if not path.exists() and not path.is_symlink():
            missing += 1
            continue
        try:
            receipts.append(validate_projection_receipt(_read(path)))
        except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            invalid += 1
    sums = (
        "fetch_calls_snapshot",
        "fetch_failures_snapshot",
        "helper_result_count",
        "projected_page_count",
        "mechanism_engaged_page_count",
        "exact_parent_prefix_handoff_page_count",
        "candidate_evidence_changed_page_count",
        "discovered_record_count",
        "admissible_record_count",
        "retained_record_count",
        "retained_bound_observation_count",
        "positive_signed_credit_count",
    )
    return {
        "task_receipts": contract.SELECTED_COUNT,
        "valid_receipts": len(receipts),
        "invalid_receipts": invalid,
        "missing_receipts": missing,
        "invalid_or_missing_receipts": invalid + missing,
        **{name: sum(int(row[name]) for row in receipts) for name in sums},
        "parent_page_character_cap": 5_000,
        "maximum_network_response_bytes_per_fetch": 3_000_000,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "question_identity_url_page_record_value_prediction_answer_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }


def configure() -> None:
    pacing.contract = contract
    pacing.configure()
    inherited_totals = engine._direct_search_totals

    def direct_search_totals(root: Path) -> dict[str, Any]:
        value = inherited_totals(root)
        value["distinct_coverage_selection"] = _distinct_totals(root)
        value["multi_identity_projection"] = _projection_totals(root)
        return value

    engine._validate_bundle = _validate_bundle
    engine._direct_search_totals = direct_search_totals


def main() -> None:
    configure()
    engine.main()


if __name__ == "__main__":
    main()
