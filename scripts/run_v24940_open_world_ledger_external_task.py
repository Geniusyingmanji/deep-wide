#!/usr/bin/env python3
"""Run one frozen V2.49.40 matched-cost open-world task."""

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

from deepwide_agent import v24933_contextual_record_value_projector as parent  # noqa: E402
from deepwide_agent import v24939_schema_bound_record_ledger as candidate  # noqa: E402
from deepwide_agent import v24940_open_world_ledger_external_contract as contract  # noqa: E402
from scripts import run_v24923_target_value_external_task as base  # noqa: E402


def _prompt(question: str, evidence: str) -> str:
    return (
        "Return exactly one Markdown table and no prose. Discover all rows "
        "satisfying the visible cohort predicate from the supplied frozen "
        "public-derived page. Preserve their page order, the exact requested "
        "column order, and the numeric decimal spelling. Do not include rows "
        "from another cohort and do not invent records.\n\nVISIBLE TASK:\n"
        + question
        + "\n\nFROZEN PUBLIC-DERIVED PAGE:\n"
        + evidence
    )


def _baseline_receipt(value: dict[str, Any]) -> dict[str, Any]:
    content_free = copy.deepcopy(value["content_free_receipt"])
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24940_content_free_contextual_parent_receipt",
        "policy_id": parent.POLICY_ID,
        "parent_receipt": content_free,
        "supported_target_value_pair_count": int(
            content_free["supported_bound_target_value_pair_count"]
        ),
        "retained_target_value_pair_count": int(
            content_free["retained_bound_target_value_pair_count"]
        ),
        "admissible_bound_observation_count": 0,
        "retained_admissible_bound_observation_count": 0,
        "discovered_row_key_count": 0,
        "same_forward_page_bytes_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "contains_question_query_url_host_page_projection_prediction_or_hash": False,
        "benchmark_metadata_answer_evaluator_score_reward_read": False,
    }
    receipt["receipt_payload_sha256"] = contract.payload_sha256(receipt)
    return receipt


def _candidate_receipt(value: dict[str, Any]) -> dict[str, Any]:
    content_free = copy.deepcopy(value["content_free_receipt"])
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24940_content_free_schema_bound_candidate_receipt",
        "policy_id": candidate.POLICY_ID,
        "candidate_receipt": content_free,
        "supported_target_value_pair_count": int(
            content_free["admissible_bound_observation_count"]
        ),
        "retained_target_value_pair_count": int(
            content_free["retained_admissible_bound_observation_count"]
        ),
        "admissible_bound_observation_count": int(
            content_free["admissible_bound_observation_count"]
        ),
        "retained_admissible_bound_observation_count": int(
            content_free["retained_admissible_bound_observation_count"]
        ),
        "discovered_row_key_count": int(content_free["discovered_row_key_count"]),
        "same_forward_page_bytes_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "contains_question_query_url_host_page_projection_prediction_or_hash": False,
        "benchmark_metadata_answer_evaluator_score_reward_read": False,
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
        raise RuntimeError("V2.49.40 child task order binding is absent") from None
    contract.ARMS = contract.arm_order(opaque_id)
    base.main()


if __name__ == "__main__":
    main()
