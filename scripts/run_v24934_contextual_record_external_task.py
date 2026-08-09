#!/usr/bin/env python3
"""Run one V2.49.34 paired task from frozen ordinary-text pages."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24928_unicode_total_visible_row_compactor as parent  # noqa: E402
from deepwide_agent import v24933_contextual_record_value_projector as candidate  # noqa: E402
from deepwide_agent import v24934_contextual_record_external_contract as contract  # noqa: E402
from scripts import run_v24923_target_value_external_task as base  # noqa: E402


def _prompt(question: str, evidence: str) -> str:
    return (
        "Return exactly one Markdown table and no prose. Preserve the exact "
        "requested column order and the eight requested entity rows in their "
        "visible order. Read values only from the supplied frozen official "
        "World Bank pages. Preserve the numeric decimal spelling shown in "
        "those pages; use Unknown only when a requested value is absent.\n\n"
        "VISIBLE TASK:\n"
        + question
        + "\n\nFROZEN OFFICIAL PAGES:\n"
        + evidence
    )


def _baseline_receipt(value: dict[str, Any]) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24934_content_free_unicode_total_baseline_receipt",
        "policy_id": parent.POLICY_ID,
        "policy": {
            "total_character_cap": 30_000,
            "maximum_page_chars": 5_000,
        },
        "projection_receipt": copy.deepcopy(value["projection_receipt"]),
        "compaction_receipt": copy.deepcopy(value["compaction_receipt"]),
        "supported_target_value_pair_count": int(
            value["projection_receipt"]["supported_target_value_pair_count"]
        ),
        "retained_target_value_pair_count": int(
            value["projection_receipt"]["retained_target_value_pair_count"]
        ),
        "same_forward_page_bytes_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "contains_question_query_url_host_page_projection_prediction_or_hash": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_read": False,
    }
    receipt["receipt_payload_sha256"] = contract.payload_sha256(receipt)
    return receipt


def _candidate_receipt(value: dict[str, Any]) -> dict[str, Any]:
    content_free = copy.deepcopy(value["content_free_receipt"])
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24934_content_free_contextual_candidate_receipt",
        "policy_id": candidate.POLICY_ID,
        "policy": copy.deepcopy(content_free["policy"]),
        "candidate_receipt": content_free,
        # Compatibility counters consumed by the inherited aggregate harness.
        "supported_target_value_pair_count": int(
            content_free["supported_bound_target_value_pair_count"]
        ),
        "retained_target_value_pair_count": int(
            content_free["retained_bound_target_value_pair_count"]
        ),
        "supported_contextual_target_value_pair_count": int(
            content_free["supported_contextual_target_value_pair_count"]
        ),
        "retained_contextual_target_value_pair_count": int(
            content_free["retained_contextual_target_value_pair_count"]
        ),
        "same_forward_page_bytes_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "contains_question_query_url_host_page_projection_prediction_or_hash": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_read": False,
    }
    receipt["receipt_payload_sha256"] = contract.payload_sha256(receipt)
    return receipt


def build_projections(
    question: str, pages: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    baseline = parent.build_projection(question, pages)
    treatment = candidate.build_projection(question, pages)
    return {
        "parent_30k": {
            "projection": str(baseline["projection"]),
            "receipt": _baseline_receipt(baseline),
        },
        "target_value_30k": {
            "projection": str(treatment["projection"]),
            "receipt": _candidate_receipt(treatment),
        },
    }


def configure() -> None:
    base.contract = contract
    base.parent = parent
    base.candidate = candidate
    base._prompt = _prompt
    base.build_projections = build_projections


def main() -> None:
    configure()
    try:
        task_path = Path(sys.argv[sys.argv.index("--task") + 1])
        raw = json.loads(task_path.read_text(encoding="utf-8"))
        opaque_id = str(raw["opaque_id"])
    except (IndexError, KeyError, ValueError, json.JSONDecodeError):
        raise RuntimeError("V2.49.34 child task order binding is absent") from None
    contract.ARMS = contract.arm_order(opaque_id)
    base.main()


if __name__ == "__main__":
    main()
