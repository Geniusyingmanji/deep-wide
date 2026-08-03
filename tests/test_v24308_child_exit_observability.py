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

from deepwide_agent import v24308_child_exit_observability as target  # noqa: E402


def receipt(**overrides):
    values = {
        "return_code": 0,
        "timed_out": False,
        "elapsed_seconds": 1.0,
        "subprocess_exception": False,
        "child_terminal_receipt_present": True,
        "child_terminal_receipt_valid": True,
        "result_envelope_present": True,
        "result_envelope_valid": True,
        "model_receipt_present": True,
        "model_receipt_valid": True,
        "transport_receipt_present": True,
        "transport_receipt_valid": True,
    }
    values.update(overrides)
    return target.parent_receipt(**values)


class V24308ChildExitObservabilityTests(unittest.TestCase):
    def test_success_and_all_failure_taxonomies_are_distinct(self) -> None:
        cases = {
            "success": {},
            "hard_deadline_timeout": {"return_code": -15, "timed_out": True},
            "child_nonzero_with_terminal_receipt": {"return_code": 1},
            "child_nonzero_without_terminal_receipt": {
                "return_code": 1,
                "child_terminal_receipt_present": False,
                "child_terminal_receipt_valid": False,
            },
            "zero_exit_missing_result_envelope": {
                "result_envelope_present": False,
                "result_envelope_valid": False,
            },
            "result_envelope_invalid": {"result_envelope_valid": False},
            "model_receipt_missing_or_invalid": {
                "model_receipt_present": False,
                "model_receipt_valid": False,
            },
            "transport_receipt_missing_or_invalid": {"transport_receipt_valid": False},
            "parent_subprocess_exception": {
                "return_code": None,
                "subprocess_exception": True,
            },
        }
        observed = {
            name: receipt(**values)["failure_taxonomy"]
            for name, values in cases.items()
        }
        self.assertEqual(observed, {name: name for name in cases})

    def test_validity_cannot_be_true_when_artifact_is_absent(self) -> None:
        for present, valid in (
            ("child_terminal_receipt_present", "child_terminal_receipt_valid"),
            ("result_envelope_present", "result_envelope_valid"),
            ("model_receipt_present", "model_receipt_valid"),
            ("transport_receipt_present", "transport_receipt_valid"),
        ):
            with self.subTest(present=present):
                with self.assertRaises(ValueError):
                    receipt(**{present: False, valid: True})

    def test_parent_execution_state_cannot_be_self_contradictory(self) -> None:
        with self.assertRaises(ValueError):
            receipt(return_code=1, subprocess_exception=True)
        with self.assertRaises(ValueError):
            receipt(return_code=None)

    def test_child_exception_receipt_is_content_free(self) -> None:
        value = target.child_receipt(
            stage="child_exception",
            exception_type="RuntimeError",
            model_receipt_written=False,
            transport_receipt_written=False,
            result_envelope_written=False,
        )
        target.validate_child_receipt(value)
        encoded = json.dumps(value).casefold()
        for name in target.PROHIBITED:
            self.assertNotIn(f'"{name}"', encoded)

    def test_receipt_builders_have_no_effect_authority(self) -> None:
        value = receipt(return_code=1)
        self.assertFalse(
            value["network_model_search_fetch_or_evaluator_called_by_receipt_builder"]
        )
        self.assertFalse(
            value["mapping_gold_category_question_type_split_evaluator_score_read"]
        )

    def test_resealed_taxonomy_tamper_is_recomputed_and_rejected(self) -> None:
        value = receipt(return_code=1)
        altered = copy.deepcopy(value)
        altered["failure_taxonomy"] = "success"
        altered.pop("receipt_payload_sha256")
        altered["receipt_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaisesRegex(ValueError, "taxonomy drifted"):
            target.validate_parent_receipt(altered)

    def test_resealed_extra_fields_fail_closed(self) -> None:
        parent = receipt()
        parent["extra"] = "content"
        parent.pop("receipt_payload_sha256")
        parent["receipt_payload_sha256"] = target.payload_sha256(parent)
        with self.assertRaisesRegex(ValueError, "parent receipt drifted"):
            target.validate_parent_receipt(parent)

        child = target.child_receipt(
            stage="child_exception",
            exception_type="RuntimeError",
            model_receipt_written=False,
            transport_receipt_written=False,
            result_envelope_written=False,
        )
        child["extra"] = "content"
        child.pop("receipt_payload_sha256")
        child["receipt_payload_sha256"] = target.payload_sha256(child)
        with self.assertRaisesRegex(ValueError, "child receipt drifted"):
            target.validate_child_receipt(child)

    def test_invalid_numeric_and_exception_fields_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            receipt(return_code=True)
        with self.assertRaises(ValueError):
            receipt(elapsed_seconds=float("nan"))
        with self.assertRaises(ValueError):
            target.child_receipt(
                stage="child_exception",
                exception_type="task_0123456789abcdef01234567",
                model_receipt_written=False,
                transport_receipt_written=False,
                result_envelope_written=False,
            )

    def test_exception_coarsening_never_emits_custom_class_name(self) -> None:
        class task_0123456789abcdef01234567(Exception):
            pass

        value = target.coarse_exception_type(
            task_0123456789abcdef01234567("sensitive message")
        )
        self.assertEqual(value, "UnknownError")
        self.assertIn(value, target.COARSE_EXCEPTION_TYPES)


if __name__ == "__main__":
    unittest.main()
