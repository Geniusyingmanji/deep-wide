from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import finalize_v24290_neutral_low_coverage as target  # noqa: E402


class V24290NeutralFinalizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_decision(ROOT, now=1)

    def test_real_decision_passes_every_frozen_mechanism_gate(self) -> None:
        target.validate_decision(self.value)
        self.assertTrue(self.value["passed"])
        self.assertEqual(self.value["status"], "neutral_mechanism_go")
        self.assertEqual(self.value["failed_checks"], [])
        self.assertTrue(all(self.value["checks"].values()))
        self.assertTrue(self.value["authorization"]["consumed_dev64_design"])
        self.assertFalse(self.value["authorization"]["consumed_dev64_launch"])

    def test_claim_scope_does_not_promote_mechanism_to_quality(self) -> None:
        claim = self.value["claim_scope"]
        self.assertTrue(claim["fault_injected_mechanism_robustness"])
        self.assertFalse(claim["natural_trigger_frequency_measured"])
        self.assertFalse(claim["benchmark_quality_measured"])
        self.assertFalse(claim["causal_quality_improvement_proven"])
        self.assertFalse(claim["sota_supported"])

    def test_resealed_launch_or_quality_claim_tamper_is_rejected(self) -> None:
        for mutation in ("launch", "quality"):
            altered = copy.deepcopy(self.value)
            if mutation == "launch":
                altered["authorization"]["consumed_dev64_launch"] = True
            else:
                altered["claim_scope"]["benchmark_quality_measured"] = True
            altered["decision_payload_sha256"] = target.payload_sha256(
                {key: value for key, value in altered.items() if key != "decision_payload_sha256"}
            )
            with self.assertRaisesRegex(RuntimeError, "decision drifted"):
                target.validate_decision(altered)


if __name__ == "__main__":
    unittest.main()
