from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25365_third_fresh_pep_population_selection as target  # noqa: E402


class V25365ThirdFreshPepPopulationSelectionTests(unittest.TestCase):
    def test_whole_group_parent_tree_and_ancestor_history_are_zero_match(self) -> None:
        value = target.build_audit(now=1)
        self.assertEqual(target.validate_audit(value), value)
        self.assertEqual(value["canonical_identity_and_slug_tree_match_count"], 0)
        self.assertEqual(
            value["canonical_identity_and_slug_history_introduction_count"], 0
        )
        self.assertTrue(
            value["whole_consecutive_group_tree_and_history_counts_all_zero"]
        )

    def test_audit_is_aggregate_only_and_authorizes_no_effect(self) -> None:
        value = target.build_audit(now=1)
        encoded = json.dumps(value, ensure_ascii=False)
        for forbidden in (
            "PEP 750",
            "pep-0750",
            "https://",
            "Title | Status",
            "ground_truth",
            "api_key",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            value["network_model_search_fetch_evaluator_benchmark_or_api_called"]
        )
        self.assertFalse(
            value["authorization"]
            ["network_model_search_fetch_external_forward_or_evaluator"]
        )

    def test_resealed_match_selection_credit_or_launch_tamper_fails(self) -> None:
        value = target.build_audit(now=1)
        for kind in ("match", "selection", "credit", "launch"):
            changed = copy.deepcopy(value)
            if kind == "match":
                changed["canonical_identity_and_slug_tree_match_count"] = 1
            elif kind == "selection":
                changed[
                    "individual_identity_retained_replaced_or_selected_using_scan_outcome"
                ] = True
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["authorization"][
                    "network_model_search_fetch_external_forward_or_evaluator"
                ] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.population.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
