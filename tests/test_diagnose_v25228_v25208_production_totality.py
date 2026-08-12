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

from scripts import (  # noqa: E402
    diagnose_v25228_v25208_production_totality as target,
)


class V25228ProductionTotalityDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_fixed_fullset_fallbacks_are_localized_content_free(self) -> None:
        aggregate = self.value["aggregate"]
        self.assertEqual(aggregate["runtime_rows"], 220)
        self.assertEqual(aggregate["completed_production_value_error_tasks"], 5)
        self.assertEqual(
            aggregate["disposition_counts"]["no_bindable_header_reject"], 4
        )
        self.assertEqual(
            aggregate["disposition_counts"]["missing_data_rows_reject"], 1
        )
        self.assertEqual(aggregate["provider_output_truncated_tasks"], 0)
        self.assertEqual(aggregate["frozen_synthesis_contract_accepted_tasks"], 0)

    def test_structural_funnel_stops_before_data_for_all_five(self) -> None:
        counts = self.value["aggregate"]["structural_count_totals"]
        self.assertEqual(counts["pipe_group_count"], 5)
        self.assertEqual(counts["separator_row_count"], 5)
        self.assertEqual(counts["header_bound_separator_count"], 1)
        self.assertEqual(counts["width_bound_separator_count"], 1)
        self.assertEqual(counts["data_bearing_separator_count"], 0)
        self.assertEqual(counts["malformed_candidate_count"], 0)
        self.assertEqual(counts["normalizer_candidate_count"], 0)

    def test_nested_projector_skips_siblings_and_rejects_duplicates(self) -> None:
        text = json.dumps(
            {
                "secret": {"never": "decode"},
                "parent_result": {
                    "prediction": "do-not-decode",
                    "content_free_receipt": {
                        "raw_normalizer_observation": {"safe": 1},
                        "other": "skip",
                    },
                },
            }
        )
        self.assertEqual(
            target._selected_nested_value(text, target.OBSERVATION_PATH),
            {"safe": 1},
        )
        duplicate = (
            '{"parent_result":{"content_free_receipt":'
            '{"raw_normalizer_observation":{},"raw_normalizer_observation":{}}}}'
        )
        with self.assertRaisesRegex(ValueError, "invalid nested JSON key"):
            target._selected_nested_value(duplicate, target.OBSERVATION_PATH)

    def test_diagnosis_preserves_fail_closed_and_fresh_gate_boundary(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertTrue(diagnosis["missing_data_rows_remain_fail_closed"])
        self.assertTrue(
            diagnosis["safe_header_totality_successor_requires_synthetic_adversarial_proof"]
        )
        self.assertFalse(
            diagnosis["old_fullset_receipts_prove_successor_recovery_coverage"]
        )
        self.assertFalse(
            diagnosis["quote_aware_successor_is_the_right_next_reliability_target"]
        )
        authorization = self.value["authorization"]
        self.assertTrue(authorization["synthetic_header_totality_successor_design_only"])
        self.assertFalse(authorization["runtime_integration_or_prediction_change"])
        self.assertFalse(authorization["fresh_external_protocol_or_launch"])
        self.assertFalse(
            authorization["evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"]
        )

    def test_source_has_no_privileged_or_prediction_subscript_access(self) -> None:
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
                    "instance_id",
                    "score",
                    "reward",
                }
            )
        )
        self.assertEqual(
            self.value["content_policy"]["only_nested_path_decoded"],
            list(target.OBSERVATION_PATH),
        )

    def test_resealed_count_launch_credit_or_policy_tamper_fails(self) -> None:
        for kind in ("count", "launch", "credit", "policy"):
            changed = copy.deepcopy(self.value)
            if kind == "count":
                changed["aggregate"]["disposition_counts"][
                    "no_bindable_header_reject"
                ] = 3
            elif kind == "launch":
                changed["authorization"]["fresh_external_protocol_or_launch"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["content_policy"]["all_sibling_values_skipped_lexically"] = False
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.parent.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
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
