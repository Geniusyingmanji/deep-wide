from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25352_fresh_pep_population_selection as target  # noqa: E402


class V25352FreshPepPopulationSelectionTests(unittest.TestCase):
    def test_parent_tree_and_ancestor_history_are_zero_match(self) -> None:
        value = target.build_audit(now=1)
        self.assertEqual(target.validate_audit(value), value)
        self.assertEqual(
            value["canonical_identity_and_slug_tree_match_count"], 0
        )
        self.assertEqual(
            value["canonical_identity_and_slug_history_introduction_count"], 0
        )

    def test_audit_contains_only_aggregate_population_evidence(self) -> None:
        value = target.build_audit(now=1)
        encoded = __import__("json").dumps(value, ensure_ascii=False)
        for forbidden in (
            "https://",
            "Title | Status",
            "ground_truth",
            "api_key",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            value["network_model_search_fetch_evaluator_benchmark_or_api_called"]
        )

    def test_resealed_match_credit_or_launch_tamper_fails(self) -> None:
        value = target.build_audit(now=1)
        for kind in ("match", "credit", "launch"):
            changed = copy.deepcopy(value)
            if kind == "match":
                changed["canonical_identity_and_slug_tree_match_count"] = 1
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
