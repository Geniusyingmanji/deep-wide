from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v25229_header_totality_successor as target  # noqa: E402


class V25229HeaderTotalityDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_design(now=1)

    def test_fixed_diagnosis_and_parent_sources_are_bound(self) -> None:
        self.assertEqual(target._parents(), target.EXPECTED_SHA256)
        self.assertEqual(
            self.value["problem_boundary"]["no_bindable_header_reject_tasks"], 4
        )
        self.assertEqual(
            self.value["problem_boundary"]["missing_data_rows_reject_tasks"], 1
        )

    def test_single_change_composes_only_parent_structural_operations(self) -> None:
        change = self.value["single_change"]
        self.assertEqual(
            change["mode"], "drop_explicit_generic_index_then_positional_header"
        )
        self.assertTrue(
            change["composes_parent_drop_index_and_positional_header_operations"]
        )
        self.assertTrue(change["exactly_one_structural_candidate_required"])
        self.assertTrue(
            change[
                "missing_data_rows_malformed_width_escaped_pipe_multiple_candidates_and_nonindex_extra_columns_fail_closed"
            ]
        )
        self.assertFalse(change["semantic_cell_edit_or_new_fact_invention"])

    def test_positive_and_negative_synthetic_contract_is_complete(self) -> None:
        positive = self.value["synthetic_positive_case"]
        self.assertTrue(positive["content_is_synthetic_and_not_from_benchmark"])
        self.assertEqual(positive["source_data_row_width"], 3)
        self.assertEqual(positive["expected_output_row_width"], 2)
        negatives = self.value["synthetic_negative_cases"]
        self.assertEqual(len(negatives), 10)
        self.assertIn("missing_data_rows", negatives)
        self.assertIn("multiple_admissible_table_candidates", negatives)
        self.assertIn("leading_extra_header_is_not_generic_index", negatives)

    def test_authority_stops_before_runtime_or_external_effect(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(
            authorization["header_totality_pure_implementation_build_only"]
        )
        self.assertFalse(authorization["runtime_integration_or_prediction_change"])
        self.assertFalse(authorization["fresh_external_protocol_or_launch"])
        self.assertFalse(
            authorization["old_fullset_retry_resume_replay_replacement_or_selective_rerun"]
        )
        self.assertFalse(
            authorization["evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"]
        )

    def test_source_has_no_privileged_runtime_field_access(self) -> None:
        tree = ast.parse((ROOT / target.SOURCE).read_text(encoding="utf-8"))
        keys = {
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        }
        self.assertTrue(
            keys.isdisjoint(
                {
                    "opaque_id",
                    "question",
                    "prediction",
                    "category",
                    "question_type",
                    "split",
                    "ground_truth",
                    "gold",
                    "answer_key",
                    "score",
                    "reward",
                }
            )
        )

    def test_resealed_mode_launch_credit_or_parent_tamper_fails(self) -> None:
        for kind in ("mode", "launch", "credit", "parent"):
            changed = copy.deepcopy(self.value)
            if kind == "mode":
                changed["single_change"]["mode"] = "accept_any_header"
            elif kind == "launch":
                changed["authorization"]["fresh_external_protocol_or_launch"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["fixed_artifact_hashes"][str(target.DIAGNOSIS)] = "0" * 64
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_design(changed)

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "design.json"
            target.publish_exclusive(path, self.value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), self.value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, self.value)


if __name__ == "__main__":
    unittest.main()
