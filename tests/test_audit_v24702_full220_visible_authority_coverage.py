from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24702_full220_visible_authority_coverage as audit  # noqa: E402


class V24702VisibleAuthorityCoverageTests(unittest.TestCase):
    def test_real_aggregate_is_fixed_and_label_blind(self) -> None:
        value = audit.build_audit(now=0)
        audit.validate_audit(value)
        self.assertEqual(value["coverage"]["fixed_visible_task_denominator"], 220)
        self.assertEqual(value["coverage"]["adapter_route_eligible_task_count"], 21)
        self.assertEqual(
            value["coverage"]["adapter_route_eligible_namespace_counts"],
            {"github": 1, "iso": 1, "who": 18, "world_bank": 1},
        )
        self.assertFalse(
            value["source_policy"][
                "mapping_category_split_gold_prediction_score_reward_or_evaluator_read"
            ]
        )

    def test_coverage_authorizes_implementation_only(self) -> None:
        value = audit.build_audit(now=0)
        self.assertTrue(
            value["authorization"]["visible_only_multi_namespace_adapter_implementation"]
        )
        self.assertFalse(value["authorization"]["fresh_dev64_protocol_or_launch"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_single_worldbank_adapter_is_rejected_as_transfer_strategy(self) -> None:
        interpretation = audit.build_audit(now=0)["interpretation"]
        self.assertEqual(
            interpretation["worldbank_specific_adapter_natural_coverage_task_count"], 1
        )
        self.assertFalse(
            interpretation[
                "single_worldbank_adapter_is_sufficient_for_deepwidebench_transfer"
            ]
        )
        self.assertTrue(interpretation["who_is_dominant_visible_namespace"])

    def test_resealed_launch_tamper_fails_closed(self) -> None:
        value = audit.build_audit(now=0)
        changed = copy.deepcopy(value)
        changed["authorization"]["exact220"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = audit.payload_sha256(changed)
        with self.assertRaises(ValueError):
            audit.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
