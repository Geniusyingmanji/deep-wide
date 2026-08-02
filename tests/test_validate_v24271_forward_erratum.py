from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import run_v24271_keyless_dev64 as frozen  # noqa: E402
from scripts import validate_v24271_forward_erratum as target  # noqa: E402
from scripts import finalize_v24271_keyless_dev64_erratum as finalizer  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


def valid_receipt() -> dict:
    value = {
        "artifact_version": 1,
        "role": "v24271_forward_validator_field_alias_erratum",
        "created_at_unix": 1,
        "status": "valid_exact64_forward_with_single_validator_field_alias",
        "runner_sha256": target.EXPECTED_RUNNER_SHA256,
        "forward_protocol_sha256": target.EXPECTED_FORWARD_PROTOCOL_SHA256,
        "execution_start_sha256": target.EXPECTED_EXECUTION_START_SHA256,
        "prediction_freeze_sha256": target.EXPECTED_PREDICTION_FREEZE_SHA256,
        "forward_result_sha256": target.EXPECTED_FORWARD_RESULT_SHA256,
        "accepted_alias": {
            "frozen_validator": target.FROZEN_VALIDATOR_KEY,
            "emitted": target.EXPECTED_KEY,
        },
        "accepted_alias_value": False,
        "selected": 64,
        "terminal_predictions": 64,
        "model_generated_tables": 63,
        "fallback_tables": 1,
        "shared_model_receipts": {},
        "control_prediction_mapping_gold_or_evaluator_opened_or_hashed": False,
        "evaluator_side_resource_opened_or_hashed": False,
        "network_or_api_called": False,
        "valid": True,
    }
    value["erratum_payload_sha256"] = payload_sha256(value)
    return value


class ValidateV24271ForwardErratumTests(unittest.TestCase):
    def test_alias_is_exactly_one_strict_false_key_replacement(self) -> None:
        expected = set(frozen.EXECUTION_START_KEYS)
        expected.remove(target.FROZEN_VALIDATOR_KEY)
        expected.add(target.EXPECTED_KEY)
        self.assertEqual(len(expected), len(frozen.EXECUTION_START_KEYS))
        self.assertNotIn(target.FROZEN_VALIDATOR_KEY, expected)
        self.assertIn(target.EXPECTED_KEY, expected)

    def test_receipt_rejects_alias_extra_field_and_true_value(self) -> None:
        value = valid_receipt()
        target.validate_erratum(value)
        for mutation in ("alias", "extra", "true"):
            altered = copy.deepcopy(value)
            if mutation == "alias":
                altered["accepted_alias"]["emitted"] = "question_type"
            elif mutation == "extra":
                altered["score"] = 1
            else:
                altered["accepted_alias_value"] = True
            unsigned = dict(altered)
            unsigned.pop("erratum_payload_sha256", None)
            altered["erratum_payload_sha256"] = payload_sha256(unsigned)
            with self.assertRaisesRegex(RuntimeError, "erratum receipt"):
                target.validate_erratum(altered)

    def test_real_barrier_replays_without_evaluator_side_access(self) -> None:
        value = target.build_erratum(ROOT, now=1)
        target.validate_erratum(value)
        self.assertEqual(value["terminal_predictions"], 64)
        self.assertTrue(value["shared_model_receipts"]["all_acquisitions_match_actual_requests"])
        self.assertFalse(value["evaluator_side_resource_opened_or_hashed"])
        self.assertFalse(value["network_or_api_called"])

    def test_erratum_finalizer_restores_frozen_barrier_after_failure(self) -> None:
        original = finalizer.frozen.validate_candidate_barrier
        with mock.patch.object(
            finalizer, "validate_committed_erratum", return_value={}
        ), mock.patch.object(
            finalizer.frozen,
            "finalize",
            side_effect=RuntimeError("synthetic evaluator boundary"),
        ), self.assertRaisesRegex(RuntimeError, "synthetic evaluator boundary"):
            finalizer.finalize(ROOT)
        self.assertIs(finalizer.frozen.validate_candidate_barrier, original)


if __name__ == "__main__":
    unittest.main()
