from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diagnose_v25063_three_run_output_structure as target  # noqa: E402


class V25063ThreeRunOutputStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_selected_field_scanner_never_decodes_unselected_values(self) -> None:
        raw = json.dumps(
            {
                "instance_id": "row-1",
                "question": {"must_not_decode": [1, 2, {"gold": "hidden"}]},
                "prediction": "| A | B |\n| --- | --- |\n| x | y |",
                "score": [1, 2, 3],
            },
            ensure_ascii=False,
        )
        original = json.loads
        decoded: list[str] = []

        def observed(value: str, *args, **kwargs):
            decoded.append(value)
            return original(value, *args, **kwargs)

        with mock.patch.object(target.json, "loads", side_effect=observed):
            selected = target.selected_top_level_fields(
                raw, frozenset({"instance_id", "prediction"})
            )
        self.assertEqual(set(selected), {"instance_id", "prediction"})
        self.assertEqual(len(decoded), 2)
        self.assertFalse(any("must_not_decode" in value for value in decoded))
        self.assertFalse(any("hidden" in value for value in decoded))

    def test_lexical_skip_handles_nested_strings_brackets_and_escapes(self) -> None:
        raw = (
            '{"instance_id":"row-2","ignored":{"x":["}","\\\""]},'
            '"prediction":"| A | B |\\n| --- | --- |\\n| x | y |",'
            '"error":null}'
        )
        selected = target.selected_top_level_fields(
            raw, frozenset({"instance_id", "prediction"})
        )
        self.assertEqual(selected["instance_id"], "row-2")
        self.assertIn("| x | y |", selected["prediction"])

    def test_three_frozen_runs_have_expected_aggregate_structure(self) -> None:
        self.assertEqual(
            self.value["fixed_denominator"],
            {"runs": 3, "tasks_per_run": 220, "total_task_rows": 660},
        )
        expected = {
            "v24857": {
                "tasks_with_duplicate_identity": 67,
                "duplicate_identity_extra_rows": 1696,
                "exact_duplicate_extra_rows": 38,
                "evaluator_error_count": 10,
            },
            "v25030": {
                "tasks_with_duplicate_identity": 65,
                "duplicate_identity_extra_rows": 1793,
                "exact_duplicate_extra_rows": 0,
                "evaluator_error_count": 12,
            },
            "v25057": {
                "tasks_with_duplicate_identity": 64,
                "duplicate_identity_extra_rows": 1476,
                "exact_duplicate_extra_rows": 0,
                "evaluator_error_count": 11,
            },
        }
        for run, counts in expected.items():
            aggregate = self.value["runs"][run]["aggregate"]
            self.assertEqual(aggregate["parseable_unique_table_tasks"], 220)
            for name, expected_value in counts.items():
                self.assertEqual(aggregate[name], expected_value, (run, name))

    def test_structural_signals_do_not_identify_evaluator_errors(self) -> None:
        for run in target.RUNS:
            duplicate = self.value["runs"][run]["structure_error_crosstabs"][
                "duplicate_identity"
            ]
            self.assertGreater(duplicate.get("no_signal__error", 0), 0)
            self.assertLessEqual(duplicate.get("signal__error", 0), 1)
        diagnosis = self.value["diagnosis"]
        self.assertFalse(
            diagnosis["structural_signals_identify_evaluator_internal_errors"]
        )
        self.assertFalse(diagnosis["generic_structural_postprocessor_supported"])

    def test_unsafe_generic_transformations_and_exact220_are_forbidden(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertFalse(
            diagnosis["duplicate_first_column_identity_is_safe_generic_merge_key"]
        )
        self.assertFalse(
            diagnosis["all_unknown_nonkey_row_is_safe_generic_deletion_target"]
        )
        self.assertEqual(diagnosis["entropy_or_information_gain_signed_credit"], 0)
        self.assertTrue(all(value is False for value in self.value["authorization"].values()))

    def test_output_policy_is_aggregate_only_and_selected_field_exact(self) -> None:
        policy = self.value["content_policy"]
        self.assertEqual(policy["prediction_fields_decoded"], ["instance_id", "prediction"])
        self.assertEqual(policy["evaluator_fields_decoded"], ["instance_id", "error"])
        self.assertEqual(
            policy["freeze_fields_decoded"], ["selected", "terminal", "label_blind"]
        )
        self.assertEqual(
            policy["postaudit_fields_decoded"], ["audit_valid", "findings"]
        )
        self.assertTrue(
            policy["all_other_parent_prediction_and_evaluator_values_skipped_lexically"]
        )
        self.assertFalse(policy["mapping_gold_category_question_type_split_score_or_reward_decoded"])
        self.assertFalse(
            policy[
                "question_id_header_row_cell_prediction_gold_category_split_or_per_task_score_emitted"
            ]
        )

    def test_resealed_result_or_authorization_tamper_fails(self) -> None:
        for mutation in ("dedup", "launch", "per_task", "extra"):
            changed = copy.deepcopy(self.value)
            if mutation == "dedup":
                changed["authorization"]["first_column_deduplication"] = True
            elif mutation == "launch":
                changed["authorization"]["new_exact220_launch"] = True
            elif mutation == "per_task":
                changed["content_policy"][
                    "question_id_header_row_cell_prediction_gold_category_split_or_per_task_score_emitted"
                ] = True
            else:
                changed["runs"]["v25057"]["per_task"] = []
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "diagnosis.json"
            target.publish_exclusive(path, self.value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), self.value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, self.value)


if __name__ == "__main__":
    unittest.main()
