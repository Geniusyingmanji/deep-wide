from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v24325_shared_prefix_revision_runtime as base  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24348_structural_table_normalizer import (  # noqa: E402
    build_stage_receipt,
    normalize_baseline_table,
    semantic_targets,
    validate_normalization_result,
    validate_stage_receipt,
)


def table(rows: list[list[str]]) -> str:
    return base._render_table(["Entity", "A", "B"], rows)


def receipt_for(value: str) -> dict:
    limits = ScoreFirstLimits(
        wall_seconds=180,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        plan_output_tokens=4_000,
        synthesis_output_tokens=30_000,
        repair_output_tokens=12_000,
    )
    budget = base._PairBudget(limits, 0.0, lambda: 0.0)
    budget.model_effects.extend(("plan", "baseline_synthesis"))
    return base._receipt(
        prefix_status="unavailable",
        prefix_bundle=None,
        baseline=value,
        candidate=value,
        admissions=[],
        proposed_changes=0,
        admitted_changes=0,
        budget=budget,
        core_queries=0,
        reserve_queries=0,
        core_search_provider_effects=0,
        reserve_search_provider_effects=0,
        core_fetch_targets=0,
        reserve_fetch_targets=0,
        core_network_fetch_effects=0,
        reserve_network_fetch_effects=0,
        core_pages=[],
        reserve_pages=[],
        fallback_type=None,
        provider_model_requests=2,
        provider_model_attempts=2,
    )


class V24348StructuralTableNormalizerTests(unittest.TestCase):
    def test_unique_rows_are_byte_stable_and_targets_complete(self) -> None:
        raw = table([["Alpha", "One", "Unknown"], ["Beta", "Two", "Three"]])
        value = normalize_baseline_table(raw)
        self.assertEqual(value["normalized_table"], raw)
        receipt = value["normalization_receipt"]
        self.assertEqual(receipt["duplicate_identity_group_count"], 0)
        self.assertEqual(receipt["safe_semantic_target_count"], 4)
        self.assertEqual(len(semantic_targets(value)), 4)

    def test_exact_duplicate_uses_most_complete_and_consensus_fill(self) -> None:
        raw = table(
            [
                ["Alpha", "Unknown", "Three"],
                ["Alpha", "One", "Unknown"],
                ["Beta", "Two", "Four"],
            ]
        )
        value = normalize_baseline_table(raw)
        _, rows = base._table_matrix(value["normalized_table"])
        self.assertEqual(rows[0], ["Alpha", "One", "Three"])
        self.assertEqual(rows[1], ["Beta", "Two", "Four"])
        receipt = value["normalization_receipt"]
        self.assertEqual(receipt["merged_duplicate_row_count"], 1)
        self.assertEqual(receipt["consensus_filled_unknown_cell_count"], 1)

    def test_normalized_duplicate_conflict_is_quarantined_not_selected(self) -> None:
        raw = table(
            [
                ["Alpha-A", "One", "Three"],
                ["Alpha A", "Two", "Three"],
            ]
        )
        value = normalize_baseline_table(raw)
        _, rows = base._table_matrix(value["normalized_table"])
        self.assertEqual(rows, [["Alpha-A", "Unknown", "Three"]])
        receipt = value["normalization_receipt"]
        self.assertEqual(receipt["conflicting_known_cell_count"], 1)
        self.assertEqual(
            receipt["conflicting_known_cells_quarantined_to_unknown_count"], 1
        )
        self.assertFalse(receipt["conflicting_known_value_selected_as_truth"])

    def test_empty_identity_is_quarantined_and_excluded_from_semantic_targets(self) -> None:
        raw = table([["", "One", "Two"], ["Alpha", "Three", "Four"]])
        value = normalize_baseline_table(raw)
        receipt = value["normalization_receipt"]
        self.assertEqual(receipt["empty_identity_group_count"], 1)
        self.assertEqual(receipt["empty_identity_row_count"], 1)
        self.assertEqual(receipt["empty_identity_rows_quarantined_count"], 1)
        self.assertEqual(receipt["empty_identity_cells_excluded_from_semantic_targets"], 2)
        self.assertEqual(len(semantic_targets(value)), 2)

    def test_duplicate_empty_identities_are_all_quarantined(self) -> None:
        raw = table(
            [["", "One", "Two"], ["---", "Three", "Four"], ["Alpha", "Five", "Six"]]
        )
        value = normalize_baseline_table(raw)
        receipt = value["normalization_receipt"]
        self.assertEqual(receipt["empty_identity_group_count"], 1)
        self.assertEqual(receipt["empty_identity_row_count"], 2)
        self.assertEqual(receipt["merged_duplicate_row_count"], 0)
        _, rows = base._table_matrix(value["normalized_table"])
        self.assertEqual(rows, [["Alpha", "Five", "Six"]])

    def test_unknown_identity_is_quarantined_like_empty_identity(self) -> None:
        raw = table([["Unknown", "One", "Two"], ["Alpha", "Three", "Four"]])
        value = normalize_baseline_table(raw)
        receipt = value["normalization_receipt"]
        self.assertEqual(receipt["empty_identity_row_count"], 1)
        _, rows = base._table_matrix(value["normalized_table"])
        self.assertEqual(rows, [["Alpha", "Three", "Four"]])

    def test_non_english_unknown_marker_replays_exactly(self) -> None:
        raw = table([["Alpha-A", "一", "三"], ["Alpha A", "二", "三"]])
        value = normalize_baseline_table(raw, unknown_marker="未知")
        validate_normalization_result(value, unknown_marker="未知")
        self.assertEqual(value["unknown_marker"], "未知")
        self.assertIn("| Alpha-A | 未知 | 三 |", value["normalized_table"])
        with self.assertRaises(ValueError):
            validate_normalization_result(value, unknown_marker="Unknown")

    def test_normalized_result_passes_legacy_candidate_row_preservation(self) -> None:
        raw = table([["Alpha-A", "One", "Three"], ["Alpha A", "Two", "Three"]])
        normalized = normalize_baseline_table(raw)["normalized_table"]
        core = base._result(
            visible={"opaque_id": "task_" + "0" * 24, "question": "visible"},
            columns=["Entity", "A", "B"],
            baseline=normalized,
            candidate=normalized,
            receipt=receipt_for(normalized),
            cost={
                "model": {"requests": 2, "attempts": 2},
                "search": {"calls": 0, "fetch_calls": 0},
            },
            elapsed=1.0,
            completion_kind="identity_no_reserve",
        )
        base.validate_result(core)

    def test_replay_and_stage_receipt_tamper_fail(self) -> None:
        value = normalize_baseline_table(table([["Alpha", "One", "Two"]]))
        altered = copy.deepcopy(value)
        altered["normalization_receipt"]["merged_duplicate_row_count"] = 1
        altered["normalization_receipt"].pop("receipt_sha256")
        altered["normalization_receipt"]["receipt_sha256"] = payload_sha256(
            altered["normalization_receipt"]
        )
        altered.pop("result_sha256")
        altered["result_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_normalization_result(altered)

        stage = build_stage_receipt(
            stage="duplicate_identity_normalization",
            reason="duplicate_identity_detected",
            effect_accounting_complete=True,
            model_requests_lower_bound=2,
            model_attempts_lower_bound=2,
            search_calls_lower_bound=1,
            fetch_calls_lower_bound=10,
        )
        validate_stage_receipt(stage)
        stage["reason"] = "free-form secret"
        stage.pop("receipt_sha256")
        stage["receipt_sha256"] = payload_sha256(stage)
        with self.assertRaises(ValueError):
            validate_stage_receipt(stage)

    def test_receipts_are_content_free_and_label_blind(self) -> None:
        value = normalize_baseline_table(table([["Alpha", "One", "Two"]]))
        encoded = json.dumps(value["normalization_receipt"], ensure_ascii=False)
        self.assertNotIn("Alpha", encoded)
        self.assertNotIn("One", encoded)
        self.assertFalse(
            value["normalization_receipt"][
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(
            value["normalization_receipt"][
                "file_environment_network_model_search_fetch_process_or_evaluator_accessed"
            ]
        )


if __name__ == "__main__":
    unittest.main()
