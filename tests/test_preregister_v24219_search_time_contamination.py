from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from scripts import preregister_v24219_search_time_contamination as prereg


ROOT = Path(__file__).resolve().parents[1]


class PreregisterV24219SearchTimeContaminationTests(unittest.TestCase):
    def test_protocol_is_label_blind_post_terminal_and_no_api(self) -> None:
        value = prereg.build_protocol(ROOT, created_at_unix=1, require_pristine=True)
        self.assertEqual(value["input_contract"]["runtime_visible_fields"], ["opaque_id", "question"])
        self.assertFalse(value["input_contract"]["query_fields_read"])
        self.assertFalse(
            value["input_contract"][
                "mapping_gold_category_question_type_split_evaluator_score_read"
            ]
        )
        self.assertTrue(value["execution"]["post_terminal_only"])
        self.assertFalse(value["authorization"]["network_model_search_fetch_evaluator_or_api_call"])
        self.assertFalse(value["authorization"]["benchmark_forward_or_full220_launch"])
        self.assertEqual(value["reporting_contract"]["official_primary_denominator"], 220)
        self.assertFalse(
            value["detector_contract"]["gold_is_unavailable_so_automatic_eal_confirmation"]
        )

    def test_output_residue_breaks_pristine_freeze(self) -> None:
        with mock.patch.object(prereg, "_parent", return_value={}), mock.patch.object(
            prereg, "_ordinary", side_effect=lambda root, relative, digest=None: root / relative
        ), mock.patch.object(prereg, "_partition", return_value={}):
            with mock.patch.object(prereg.Path, "exists", return_value=True):
                with self.assertRaisesRegex(RuntimeError, "not pristine"):
                    prereg.build_protocol(ROOT, created_at_unix=1, require_pristine=True)

    def test_v24218_frozen_files_are_not_in_new_control_surface(self) -> None:
        self.assertFalse(
            any("v24218" in relative for relative in prereg.CONTROL_FILES)
        )


if __name__ == "__main__":
    unittest.main()
