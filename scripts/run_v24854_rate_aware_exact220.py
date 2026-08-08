#!/usr/bin/env python3
"""Run one fresh label-blind V2.48.54 rate-aware exact-220 forward."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24854_rate_aware_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    prepare_rate_aware_key_slots,
    validate_receipt as validate_rate_receipt,
)
from scripts import run_v24800_exact220 as base  # noqa: E402
from scripts import run_v24635_exact220 as algorithm  # noqa: E402


def _validate_bundle(value: dict[str, Any], directory: Path) -> None:
    algorithm._v24854_parent_validate_bundle(value, directory)
    validate_rate_receipt(base._read(directory / contract.RATE_RECEIPT_NAME))


def _rate_aware_totals(root: Path) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    missing = 0
    invalid = 0
    for position in range(1, contract.SELECTED_COUNT + 1):
        path = (
            root
            / contract.TASK_ROOT
            / f"task_{position:04d}"
            / contract.RATE_RECEIPT_NAME
        )
        if not path.exists() and not path.is_symlink():
            missing += 1
            continue
        try:
            receipts.append(validate_rate_receipt(base._read(path)))
        except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            invalid += 1
    integer_fields = (
        "provider_start_reservations",
        "provider_gate_timeouts",
        "provider_pacing_wait_events",
        "provider_cooldown_wait_events",
        "provider_cooldown_activations",
        "retry_after_values_honored",
        "provider_429_responses",
        "provider_non429_retryable_responses",
        "provider_transport_retry_events",
    )
    return {
        "task_receipts": contract.SELECTED_COUNT,
        "valid_receipts": len(receipts),
        "invalid_receipts": invalid,
        "missing_receipts": missing,
        "invalid_or_missing_receipts": invalid + missing,
        **{
            name: sum(int(item[name]) for item in receipts)
            for name in integer_fields
        },
        "total_provider_gate_wait_seconds": round(
            sum(
                float(item["total_provider_gate_wait_seconds"])
                for item in receipts
            ),
            6,
        ),
        "max_provider_gate_wait_seconds": max(
            (
                float(item["max_provider_gate_wait_seconds"])
                for item in receipts
            ),
            default=0.0,
        ),
        "provider_wide_429_rotates_all_keys_immediately": False,
        "credential_local_statuses_remain_key_local": True,
        "provider_answer_snippet_raw_content_or_score_forwarded": False,
        "credential_value_persisted_hashed_emitted_or_in_error": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }


def configure() -> None:
    base.contract = contract
    if not hasattr(algorithm, "_v24854_parent_validate_bundle"):
        algorithm._v24854_parent_validate_bundle = algorithm._validate_bundle
    base._validate_bundle = _validate_bundle
    inherited_summary = base._direct_search_totals

    def direct_search_totals(root: Path) -> dict[str, Any]:
        value = inherited_summary(root)
        value["rate_aware"] = _rate_aware_totals(root)
        return value

    base._direct_search_totals = direct_search_totals
    base.prepare_key_slots = prepare_rate_aware_key_slots


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
