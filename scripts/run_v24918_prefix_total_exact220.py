#!/usr/bin/env python3
"""Run one fresh label-blind V2.49.18 exact-220 forward."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24918_prefix_total_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24916_prefix_total_long_page_packer import validate_receipt  # noqa: E402
from scripts import run_v24831_keyless_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract


def validate_projection_receipts() -> dict[str, int]:
    counts = {
        "projection_receipts_present_and_valid": 0,
        "tasks_with_original_long_pages": 0,
        "tasks_with_engaged_mechanism": 0,
        "tasks_with_projection_difference": 0,
        "tasks_with_visible_requirement_gain": 0,
        "tasks_with_structural_totality_fallback": 0,
        "original_long_pages": 0,
        "final_query_aware_long_pages": 0,
        "input_characters_beyond_output_page_cap": 0,
        "prefix_safe_fallbacks": 0,
        "table_header_dependency_additions": 0,
        "orphan_selected_table_continuation_blocks": 0,
    }
    for position in range(1, contract.SELECTED_COUNT + 1):
        path = (
            ROOT
            / contract.TASK_ROOT
            / f"task_{position:04d}"
            / "projection_receipt.json"
        )
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"V2.49.18 projection receipt absent: {position}")
        value = validate_receipt(base.algorithm.read_object(path))
        counts["projection_receipts_present_and_valid"] += 1
        counts["tasks_with_original_long_pages"] += value[
            "original_long_page_count"
        ] > 0
        counts["tasks_with_engaged_mechanism"] += value["long_page_mechanism_engaged"]
        counts["tasks_with_projection_difference"] += value[
            "projection_differs_from_prefix_baseline"
        ]
        counts["tasks_with_visible_requirement_gain"] += (
            value["candidate_visible_requirement_gain_count"] > 0
        )
        counts["tasks_with_structural_totality_fallback"] += value[
            "structural_cap_totality_fallback_applied"
        ]
        counts["original_long_pages"] += value["original_long_page_count"]
        counts["final_query_aware_long_pages"] += value[
            "final_query_aware_long_page_count"
        ]
        counts["input_characters_beyond_output_page_cap"] += value[
            "input_characters_beyond_output_page_cap"
        ]
        counts["prefix_safe_fallbacks"] += value["prefix_safe_fallback_applied"]
        counts["table_header_dependency_additions"] += value[
            "table_header_dependency_addition_count"
        ]
        counts["orphan_selected_table_continuation_blocks"] += value[
            "orphan_selected_table_continuation_block_count"
        ]
    if (
        counts["projection_receipts_present_and_valid"] != contract.SELECTED_COUNT
        or counts["orphan_selected_table_continuation_blocks"] != 0
    ):
        raise RuntimeError("V2.49.18 projection receipt aggregate drifted")
    return counts


def main() -> None:
    configure()
    base.main()
    counts = validate_projection_receipts()
    summary_path = ROOT / contract.RUN_SUMMARY
    summary = base._read(summary_path)
    summary["projection_receipt_totals"] = counts
    summary.pop("summary_payload_sha256", None)
    summary["summary_payload_sha256"] = contract.payload_sha256(summary)
    base.algorithm._atomic_json(summary_path, summary)

    freeze_path = ROOT / contract.PREDICTION_FREEZE
    freeze = base._read(freeze_path)
    freeze["run_summary_sha256"] = contract.sha256(summary_path)
    freeze.pop("freeze_payload_sha256", None)
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    base.algorithm._atomic_json(freeze_path, freeze)

    forward_path = ROOT / contract.FORWARD_RESULT
    forward = base._read(forward_path)
    forward["run_summary_sha256"] = contract.sha256(summary_path)
    forward["prediction_freeze_sha256"] = contract.sha256(freeze_path)
    forward.pop("result_payload_sha256", None)
    forward["result_payload_sha256"] = contract.payload_sha256(forward)
    base.algorithm._atomic_json(forward_path, forward)


if __name__ == "__main__":
    main()
