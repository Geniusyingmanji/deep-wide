from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import preregister_v24671_information_gain as prereg  # noqa: E402


class V24671PreregistrationTests(unittest.TestCase):
    def test_build_protocol_is_label_blind_and_inert(self):
        with patch.object(prereg, "_git", side_effect=["", "a" * 40, "a" * 40]):
            value = prereg.build_protocol(
                now=0, require_clean=False, require_pristine=False
            )
        self.assertEqual(
            value["task_contract"]["runtime_input_keys"], ["opaque_id", "question"]
        )
        self.assertEqual(value["task_contract"]["selected_tasks"], 12)
        self.assertFalse(value["authorization"]["preactivation_audit_generation"])
        self.assertFalse(value["authorization"]["activation_or_launch"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_manifest_excludes_evaluator_private_and_gold(self):
        self.assertFalse(
            any(
                marker in path
                for path in prereg.DEPENDENCIES
                for marker in prereg.FORBIDDEN_MARKERS
            )
        )

    def test_mechanism_requires_credit_and_safe_admission_before_outer_utility(self):
        value = prereg.build_protocol(
            now=0, require_clean=False, require_pristine=False
        )
        mechanism = value["mechanism"]
        self.assertTrue(
            mechanism[
                "postfreeze_outer_utility_design_requires_positive_epistemic_credit_and_safe_admission"
            ]
        )
        self.assertTrue(mechanism["query_text_cannot_self_prove_surface_alignment"])
        self.assertTrue(mechanism["fetched_page_text_is_only_active_support"])
        self.assertFalse(mechanism["support_threshold_relaxed"])
        self.assertFalse(
            mechanism[
                "positive_decision_credit_before_safe_change_and_postfreeze_outer_utility"
            ]
        )

    def test_resealed_launch_tamper_differs_from_protocol(self):
        value = prereg.build_protocol(
            now=0, require_clean=False, require_pristine=False
        )
        seal = value.pop("protocol_sha256")
        value["authorization"]["activation_or_launch"] = True
        self.assertNotEqual(prereg.payload_sha256(value), seal)

    def test_fixed_concurrency_and_effect_caps(self):
        value = prereg.build_protocol(
            now=0, require_clean=False, require_pristine=False
        )
        self.assertEqual(value["execution"]["executor_concurrency"], 12)
        self.assertEqual(value["execution"]["model_slot_cap"], 8)
        self.assertEqual(
            [
                value["limits"][key]
                for key in ("model_calls", "search_queries", "fetch_targets")
            ],
            [3, 4, 10],
        )
        self.assertEqual(value["treatment"]["unknown_target_cell_cap"], 1)
        self.assertEqual(value["treatment"]["targeted_fetch_cap"], 4)


if __name__ == "__main__":
    unittest.main()
