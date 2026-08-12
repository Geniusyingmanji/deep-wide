from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25186_same_response_quote_quality_runtime as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from test_v25180_quote_aware_production_runtime import (  # noqa: E402
    CANDIDATE_CONTENT,
    NO_GAIN_CONTENT,
    EscapedProductionModel,
    V25180QuoteAwareProductionRuntimeTests,
)


class V25186SameResponseQuoteQualityTests(
    V25180QuoteAwareProductionRuntimeTests
):
    def test_same_raw_repair_exposes_fallback_control_without_extra_effect(self):
        inner, _searches, value = self._run(
            target,
            content=NO_GAIN_CONTENT,
            inner=EscapedProductionModel(),
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertTrue(receipt["same_raw_counterfactual_active"])
        self.assertTrue(receipt["prediction_changed"])
        self.assertIn(
            "Unknown",
            value["predictions"][target.CONTROL_ARM],
        )
        self.assertIn(
            '"country | code"',
            value["predictions"][target.CANDIDATE_ARM],
        )
        self.assertEqual(value["cost"], value["parent_result"]["cost"])

    def test_same_raw_candidate_excludes_later_revision(self):
        inner, _searches, value = self._run(
            target,
            content=CANDIDATE_CONTENT,
            inner=EscapedProductionModel(),
        )
        self.assertEqual(inner.logical_calls, 4)
        candidate = value["predictions"][target.CANDIDATE_ARM]
        self.assertEqual(candidate, value["parent_result"]["production_prediction"])
        self.assertNotEqual(candidate, value["parent_result"]["prediction"])
        self.assertNotIn("999", candidate)

    def test_inactive_repair_has_identical_arms(self):
        _inner, _searches, value = self._run(
            target,
            content=NO_GAIN_CONTENT,
        )
        receipt = value["content_free_receipt"]
        self.assertFalse(receipt["same_raw_counterfactual_active"])
        self.assertFalse(receipt["prediction_changed"])
        self.assertEqual(
            value["predictions"][target.CONTROL_ARM],
            value["predictions"][target.CANDIDATE_ARM],
        )

    def test_resealed_prediction_credit_or_effect_tamper_fails_closed(self):
        _inner, _searches, value = self._run(
            target,
            content=NO_GAIN_CONTENT,
            inner=EscapedProductionModel(),
        )
        for mode in ("prediction", "credit", "effect"):
            changed = copy.deepcopy(value)
            if mode == "prediction":
                changed["predictions"][target.CONTROL_ARM] = changed["predictions"][
                    target.CANDIDATE_ARM
                ]
            elif mode == "credit":
                changed["content_free_receipt"][
                    "entropy_or_information_gain_assigns_signed_credit"
                ] = True
            else:
                changed["content_free_receipt"][
                    "additional_model_search_fetch_or_network_effect"
                ] = True
            receipt = changed["content_free_receipt"]
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            for arm in target.ARMS:
                import hashlib

                changed["prediction_sha256"][arm] = hashlib.sha256(
                    changed["predictions"][arm].encode()
                ).hexdigest()
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                target.validate_result(changed)


if __name__ == "__main__":
    unittest.main()
