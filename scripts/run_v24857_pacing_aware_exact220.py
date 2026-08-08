#!/usr/bin/env python3
"""Run one fresh label-blind V2.48.57 exact-220 forward."""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24857_pacing_aware_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    prepare_rate_aware_key_slots,
    validate_receipt as validate_rate_receipt,
)
from deepwide_agent.v24856_pacing_aware_admission import (  # noqa: E402
    validate_receipt as validate_pacing_receipt,
)
from scripts import run_v24800_exact220 as base  # noqa: E402
from scripts import run_v24635_exact220 as algorithm  # noqa: E402


def _validate_bundle(value: dict[str, Any], directory: Path) -> None:
    algorithm._v24857_parent_validate_bundle(value, directory)
    validate_rate_receipt(base._read(directory / contract.RATE_RECEIPT_NAME))
    validate_pacing_receipt(base._read(directory / contract.PACING_RECEIPT_NAME))


def _rate_aware_totals(root: Path) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    missing = 0
    invalid = 0
    for position in range(1, contract.SELECTED_COUNT + 1):
        path = root / contract.TASK_ROOT / f"task_{position:04d}" / contract.RATE_RECEIPT_NAME
        if not path.exists() and not path.is_symlink():
            missing += 1
            continue
        try:
            receipts.append(validate_rate_receipt(base._read(path)))
        except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            invalid += 1
    integer_fields = (
        "provider_start_reservations", "provider_gate_timeouts",
        "provider_pacing_wait_events", "provider_cooldown_wait_events",
        "provider_cooldown_activations", "retry_after_values_honored",
        "provider_429_responses", "provider_non429_retryable_responses",
        "provider_transport_retry_events",
    )
    return {
        "task_receipts": contract.SELECTED_COUNT,
        "valid_receipts": len(receipts),
        "invalid_receipts": invalid,
        "missing_receipts": missing,
        "invalid_or_missing_receipts": invalid + missing,
        **{name: sum(int(item[name]) for item in receipts) for name in integer_fields},
        "total_provider_gate_wait_seconds": round(sum(float(item["total_provider_gate_wait_seconds"]) for item in receipts), 6),
        "max_provider_gate_wait_seconds": max((float(item["max_provider_gate_wait_seconds"]) for item in receipts), default=0.0),
        "provider_wide_429_rotates_all_keys_immediately": False,
        "credential_local_statuses_remain_key_local": True,
        "provider_answer_snippet_raw_content_or_score_forwarded": False,
        "credential_value_persisted_hashed_emitted_or_in_error": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }


def _pacing_totals(root: Path) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    missing = 0
    invalid = 0
    for position in range(1, contract.SELECTED_COUNT + 1):
        path = root / contract.TASK_ROOT / f"task_{position:04d}" / contract.PACING_RECEIPT_NAME
        if not path.exists() and not path.is_symlink():
            missing += 1
            continue
        try:
            receipts.append(validate_pacing_receipt(base._read(path)))
        except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            invalid += 1
    legacy = Counter(str(item["legacy_reason"]) for item in receipts)
    pacing = Counter(str(item["pacing_aware_reason"]) for item in receipts)
    return {
        "task_receipts": contract.SELECTED_COUNT,
        "valid_receipts": len(receipts),
        "invalid_receipts": invalid,
        "missing_receipts": missing,
        "invalid_or_missing_receipts": invalid + missing,
        "decision_changed_tasks": sum(bool(item["decision_changed"]) for item in receipts),
        "legacy_reason_counts": dict(sorted(legacy.items())),
        "pacing_aware_reason_counts": dict(sorted(pacing.items())),
        "credited_provider_wait_seconds_total": round(sum(float(item["credited_provider_wait_seconds"]) for item in receipts), 6),
        "max_credited_provider_wait_seconds": max((float(item["credited_provider_wait_seconds"]) for item in receipts), default=0.0),
        "raw_first_wave_elapsed_rewritten": False,
        "absolute_task_deadline_changed": False,
        "query_fetch_model_token_or_context_cap_changed": False,
        "same_pass_content_free_transport_telemetry_only": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }


def _fixed_full_budget_totals(outcomes: list[Any]) -> dict[str, Any]:
    def bounded_integer(value: object, maximum: int) -> bool:
        return (
            not isinstance(value, bool)
            and isinstance(value, int)
            and 0 <= value <= maximum
        )

    def numeric_zero(value: object) -> bool:
        return (
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and float(value) == 0.0
        )

    decisions: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    valid = 0
    second_wave = 0
    zero_entropy = 0
    total_queries = 0
    total_fetches = 0
    changed = 0
    for position, item in enumerate(outcomes, start=1):
        try:
            pacing = validate_pacing_receipt(
                base._read(
                    ROOT
                    / contract.TASK_ROOT
                    / f"task_{position:04d}"
                    / contract.PACING_RECEIPT_NAME
                )
            )
        except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            continue
        result = item.result
        retrieval = result.get("two_wave_retrieval") or {}
        receipt = retrieval.get("receipt") or {}
        controller = receipt.get("controller") or {}
        wave2 = receipt.get("wave2") or {}
        total = receipt.get("total") or {}
        policy = controller.get("policy") or {}
        reason = controller.get("reason")
        decision = controller.get("decision")
        policy_is_fixed_control = (
            policy.get("information_gain_weight") == 0
            and policy.get("latency_loss_per_second") == 0
            and policy.get("minimum_net_value") == -1.0
            and float(policy.get("maximum_wave1_seconds", -1))
            == float(pacing["effective_wave1_ceiling_seconds"])
            and bounded_integer(policy.get("wave1_queries"), 2)
            and bounded_integer(policy.get("wave1_fetches"), 6)
            and bounded_integer(policy.get("wave2_queries"), 2)
            and bounded_integer(policy.get("wave2_fetches"), 4)
        )
        decision_is_consistent = (
            decision == "expand"
            and reason == "positive_entropy_voc"
            and wave2.get("executed") is True
        ) or (
            decision == "stop"
            and reason in {"latency_ceiling", "no_delta_budget"}
            and wave2.get("executed") is False
        )
        pacing_is_bound = (
            pacing["pacing_aware_decision"] == decision
            and pacing["pacing_aware_reason"] == reason
            and math.isclose(
                float(pacing["raw_wave1_elapsed_seconds"]),
                float((controller.get("first_wave") or {}).get("search_seconds", -1))
                + float((controller.get("first_wave") or {}).get("fetch_seconds", -1)),
                abs_tol=1e-6,
            )
        )
        if (
            retrieval.get("status") != "completed"
            or not policy_is_fixed_control
            or not pacing_is_bound
            or controller.get(
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ) is not False
            or controller.get("question_text_or_content_read_by_kernel") is not False
            or not decision_is_consistent
            or not isinstance(wave2.get("executed"), bool)
            or not numeric_zero(controller.get("entropy_value"))
            or not numeric_zero(controller.get("latency_cost"))
            or not bounded_integer(total.get("queries_executed"), 4)
            or not bounded_integer(total.get("fetches_attempted"), 10)
        ):
            continue
        valid += 1
        decisions[str(decision)] += 1
        reasons[str(reason)] += 1
        second_wave += int(wave2["executed"])
        zero_entropy += int(numeric_zero(controller["entropy_value"]))
        total_queries += int(total["queries_executed"])
        total_fetches += int(total["fetches_attempted"])
        changed += int(bool(pacing["decision_changed"]))
    return {
        "task_results": len(outcomes),
        "valid_control_receipts": valid,
        "invalid_or_missing_control_receipts": len(outcomes) - valid,
        "decision_counts": dict(sorted(decisions.items())),
        "reason_counts": dict(sorted(reasons.items())),
        "second_wave_executed_tasks": second_wave,
        "zero_entropy_value_tasks": zero_entropy,
        "total_queries_executed": total_queries,
        "total_fetches_attempted": total_fetches,
        "pacing_aware_decision_changed_tasks": changed,
        "entropy_or_information_gain_used_for_admission": False,
        "same_pass_content_free_provider_wait_used_for_admission": True,
        "question_query_url_page_prediction_answer_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }


def configure() -> None:
    base.contract = contract
    if not hasattr(algorithm, "_v24857_parent_validate_bundle"):
        algorithm._v24857_parent_validate_bundle = algorithm._validate_bundle
    base._validate_bundle = _validate_bundle
    inherited_summary = base._direct_search_totals

    def direct_search_totals(root: Path) -> dict[str, Any]:
        value = inherited_summary(root)
        value["rate_aware"] = _rate_aware_totals(root)
        value["pacing_aware_admission"] = _pacing_totals(root)
        return value

    base._direct_search_totals = direct_search_totals
    base.prepare_key_slots = prepare_rate_aware_key_slots
    base._fixed_full_budget_totals = _fixed_full_budget_totals

def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
