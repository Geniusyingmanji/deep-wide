from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25188_export_failure_tolerant_same_response_runtime as target,
)
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from test_v25180_quote_aware_production_runtime import (  # noqa: E402
    CANDIDATE_CONTENT,
    NO_GAIN_CONTENT,
    EscapedProductionModel,
    V25180QuoteAwareProductionRuntimeTests,
)


class V25188ExportFailureTolerantSameResponseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = V25180QuoteAwareProductionRuntimeTests()

    def test_active_completed_export_has_same_response_counterfactual(self):
        inner, _searches, value = self.helper._run(
            target,
            content=NO_GAIN_CONTENT,
            inner=EscapedProductionModel(),
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertTrue(receipt["same_raw_counterfactual_active"])
        self.assertTrue(receipt["prediction_changed"])
        self.assertEqual(receipt["parent_public_export_completed_count"], 1)
        self.assertFalse(receipt["parent_public_export_failure_present"])

    def test_parent_safe_export_failure_is_terminal_not_outer_failure(self):
        with mock.patch.object(
            target.effect_parent,
            "export_public_predictions",
            side_effect=RuntimeError("synthetic export failure"),
        ):
            inner, _searches, value = self.helper._run(
                target,
                content=CANDIDATE_CONTENT,
                inner=EscapedProductionModel(),
            )
        receipt = value["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertTrue(receipt["same_raw_counterfactual_active"])
        self.assertTrue(receipt["prediction_changed"])
        self.assertEqual(receipt["parent_public_export_completed_count"], 0)
        self.assertTrue(receipt["parent_public_export_failure_present"])
        self.assertTrue(
            receipt["parent_public_export_fallback_to_safe_production"]
        )
        self.assertEqual(
            value["predictions"][target.CANDIDATE_ARM],
            value["parent_result"]["production_prediction"],
        )

    def test_inactive_repair_remains_byte_identical(self):
        _inner, _searches, value = self.helper._run(
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

    def test_resealed_export_state_credit_or_effect_tamper_fails_closed(self):
        _inner, _searches, value = self.helper._run(
            target,
            content=NO_GAIN_CONTENT,
            inner=EscapedProductionModel(),
        )
        for field in (
            "parent_public_export_failure_present",
            "entropy_or_information_gain_assigns_signed_credit",
            "additional_model_search_fetch_or_network_effect",
        ):
            changed = copy.deepcopy(value)
            receipt = changed["content_free_receipt"]
            receipt[field] = True
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(field=field), self.assertRaises(ValueError):
                target.validate_result(changed)


if __name__ == "__main__":
    unittest.main()
