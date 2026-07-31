from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from scripts import preregister_v24220_source_dependency as prereg


ROOT = Path(__file__).resolve().parents[1]


class PreregisterV24220SourceDependencyTests(unittest.TestCase):
    def test_protocol_is_label_blind_post_terminal_and_no_api(self) -> None:
        value = prereg.build_protocol(ROOT, created_at_unix=1, require_pristine=True)
        input_contract = value["input_contract"]
        self.assertFalse(input_contract["runtime_manifest_content_opened"])
        self.assertFalse(input_contract["question_query_prediction_or_renderer_output_read"])
        self.assertFalse(
            input_contract[
                "mapping_gold_category_question_type_split_evaluator_score_read"
            ]
        )
        self.assertTrue(value["execution"]["post_v24219_terminal_only"])
        self.assertFalse(
            value["authorization"]["network_model_search_fetch_evaluator_or_api_call"]
        )
        self.assertFalse(value["authorization"]["benchmark_forward_or_full220_launch"])
        self.assertEqual(value["reporting_contract"]["official_primary_denominator"], 220)
        self.assertTrue(
            value["estimator_contract"][
                "same_host_or_family_alone_never_forms_hard_cluster"
            ]
        )

    def test_output_residue_breaks_pristine_freeze(self) -> None:
        with mock.patch.object(prereg, "_parent", return_value={}), mock.patch.object(
            prereg, "_ordinary", side_effect=lambda root, relative, digest=None: root / relative
        ), mock.patch.object(prereg, "_partition", return_value={}):
            with mock.patch.object(prereg.Path, "exists", return_value=True):
                with self.assertRaisesRegex(RuntimeError, "not pristine"):
                    prereg.build_protocol(ROOT, created_at_unix=1, require_pristine=True)

    def test_prior_frozen_files_are_not_in_new_control_surface(self) -> None:
        self.assertFalse(
            any("v24218" in relative or "v24219" in relative for relative in prereg.CONTROL_FILES)
        )


if __name__ == "__main__":
    unittest.main()
