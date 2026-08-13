from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24630_exact220_task_integration as legacy  # noqa: E402
from deepwide_agent import v25286_legacy_outcome_checkpoint as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24630_exact220_task_integration import (  # noqa: E402
    IntegratedExact220TaskOutcome,
)
import test_v24860_coverage_revision_integration as core_test  # noqa: E402
from test_v24861_coverage_revision_exact_task import (  # noqa: E402
    backfill_receipt,
    single_receipt,
)


class V25286LegacyOutcomeCheckpointTests(unittest.TestCase):
    def build(self):
        helper = core_test.V24860CoverageRevisionIntegrationTests()
        temporary, _clock, inner, _model, parent = helper.build_parent(
            [core_test.PLAN, core_test.BASELINE, core_test.SUPPORTED]
        )
        outcome = IntegratedExact220TaskOutcome(
            copy.deepcopy(parent.result),
            copy.deepcopy(parent.model_slot_receipt),
            copy.deepcopy(parent.transport_health),
            copy.deepcopy(single_receipt()),
            copy.deepcopy(backfill_receipt()),
        )
        return temporary, inner, outcome

    def test_clean_path_is_byte_identical_to_legacy_envelope(self) -> None:
        temporary, inner, outcome = self.build()
        self.addCleanup(temporary.cleanup)
        expected = legacy.build_envelope(outcome, arm="baseline")
        calls_before = inner.requests
        envelope, receipt = target.run_from_validated_outcome(outcome)
        self.assertEqual(envelope, expected)
        self.assertEqual(inner.requests, calls_before)
        self.assertTrue(receipt["legacy_envelope_clean"])
        self.assertFalse(receipt["recovery_envelope_created"])
        self.assertIsNone(receipt["failure_stage"])
        for field in (
            "additional_query_count",
            "additional_fetch_count",
            "additional_model_forward_count",
            "additional_system_total_tokens",
            "positive_signed_credit_count",
        ):
            self.assertEqual(receipt[field], 0)

    def test_envelope_build_failure_recovers_same_prediction_cost_and_outcome(self) -> None:
        temporary, inner, outcome = self.build()
        self.addCleanup(temporary.cleanup)
        calls_before = inner.requests
        with mock.patch.object(
            target.parent,
            "build_envelope",
            side_effect=ValueError("hidden build detail"),
        ):
            recovered, receipt = target.run_from_validated_outcome(outcome)
        checked = target.validate_recovery_envelope(recovered)
        self.assertEqual(inner.requests, calls_before)
        self.assertEqual(checked["prediction"], outcome.result["prediction"])
        self.assertEqual(checked["cost"], outcome.result["cost"])
        self.assertEqual(
            checked["outcome_checkpoint"]["validated_outcome"]["result"],
            outcome.result,
        )
        self.assertEqual(receipt["failure_stage"], "legacy_envelope_build")
        self.assertEqual(receipt["failure_type"], "ValueError")
        self.assertNotIn("hidden build detail", str(recovered))

    def test_envelope_validation_failure_recovers_independently(self) -> None:
        temporary, _inner, outcome = self.build()
        self.addCleanup(temporary.cleanup)
        original = target.parent.validate_envelope
        calls = 0

        def fail_second(value):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original(value)
            raise RuntimeError("hidden validation detail")

        with mock.patch.object(
            target.parent,
            "validate_envelope",
            side_effect=fail_second,
        ):
            recovered, receipt = target.run_from_validated_outcome(outcome)
        self.assertEqual(calls, 2)
        self.assertEqual(
            target.validate_recovery_envelope(recovered), recovered
        )
        self.assertEqual(receipt["failure_stage"], "legacy_envelope_validate")
        self.assertEqual(receipt["failure_type"], "RuntimeError")
        self.assertNotIn("hidden validation detail", str(recovered))

    def test_untrusted_precheckpoint_outcome_fails_closed(self) -> None:
        temporary, _inner, outcome = self.build()
        self.addCleanup(temporary.cleanup)
        altered = IntegratedExact220TaskOutcome(
            copy.deepcopy(outcome.result),
            copy.deepcopy(outcome.model_slot_receipt),
            copy.deepcopy(outcome.transport_health),
            copy.deepcopy(outcome.search_single_shot_receipt),
            copy.deepcopy(outcome.citation_title_backfill_receipt),
        )
        altered.result["prediction"] += "x"
        with self.assertRaises(ValueError):
            target.run_from_validated_outcome(altered)

    def test_resealed_checkpoint_receipt_or_recovery_tamper_fails(self) -> None:
        temporary, _inner, outcome = self.build()
        self.addCleanup(temporary.cleanup)
        with mock.patch.object(
            target.parent, "build_envelope", side_effect=ValueError("x")
        ):
            recovered, receipt = target.run_from_validated_outcome(outcome)
        for kind in (
            "checkpoint",
            "receipt",
            "nested_stage",
            "nested_type",
            "recovery",
            "credit",
            "hidden",
        ):
            changed = copy.deepcopy(recovered)
            if kind == "checkpoint":
                checkpoint = changed["outcome_checkpoint"]
                checkpoint["prediction"] += "x"
                checkpoint.pop("checkpoint_payload_sha256")
                checkpoint["checkpoint_payload_sha256"] = payload_sha256(
                    checkpoint
                )
                changed["outcome_checkpoint_payload_sha256"] = checkpoint[
                    "checkpoint_payload_sha256"
                ]
            elif kind == "receipt":
                nested = changed["content_free_checkpoint_receipt"]
                nested["additional_model_forward_count"] = 1
                nested.pop("receipt_payload_sha256")
                nested["receipt_payload_sha256"] = payload_sha256(nested)
            elif kind in {"nested_stage", "nested_type"}:
                nested = changed["content_free_checkpoint_receipt"]
                if kind == "nested_stage":
                    nested["failure_stage"] = "legacy_envelope_validate"
                else:
                    nested["failure_type"] = "RuntimeError"
                nested.pop("receipt_payload_sha256")
                nested["receipt_payload_sha256"] = payload_sha256(nested)
            elif kind == "recovery":
                changed["recovered_failure_stage"] = "outcome_checkpoint"
            elif kind == "credit":
                changed[
                    "entropy_or_information_gain_assigns_signed_credit"
                ] = True
            else:
                changed["hidden"] = True
            changed.pop("recovery_payload_sha256")
            changed["recovery_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_recovery_envelope(changed)
        altered_receipt = copy.deepcopy(receipt)
        altered_receipt["failure_type"] = "Other"
        altered_receipt.pop("receipt_payload_sha256")
        altered_receipt["receipt_payload_sha256"] = payload_sha256(
            altered_receipt
        )
        self.assertEqual(
            target.validate_receipt(altered_receipt), altered_receipt
        )
        self.assertNotEqual(altered_receipt, receipt)

    def test_source_has_no_effect_evaluator_or_label_routing_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25286_legacy_outcome_checkpoint.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ):
                if node.slice.value in {
                    "category",
                    "question_type",
                    "task_category",
                    "split",
                    "ground_truth",
                    "gold",
                    "answer_key",
                    "score",
                    "reward",
                }:
                    privileged.append(str(node.slice.value))
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "socket",
            "urllib",
            "openai",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        self.assertEqual(privileged, [])
        for forbidden in (
            "official_eval",
            "run_official",
            "api_key",
            "os.environ",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
