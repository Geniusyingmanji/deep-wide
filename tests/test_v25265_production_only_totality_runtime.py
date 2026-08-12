from __future__ import annotations

import copy
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25135_sparse_production_runtime as sparse  # noqa: E402
from deepwide_agent import v25232_header_totality_shadow_runtime as fixture_parent  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25265_production_only_totality_runtime as target  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    CompatibleModel,
    GroundedFrontierSearch,
    QUESTION,
    TASK,
    limits,
)


class V25265ProductionOnlyTotalityRuntimeTests(unittest.TestCase):
    @staticmethod
    def _model(inner, root: Path):
        slots = root / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
        return DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=slots,
            output_root=root,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )

    def _run(self, *, field_page: bool):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner = CompatibleModel()
            budget = cap.PhysicalEffectBudget()
            model = cap.HardCappedModelLimiter(self._model(inner, root), budget)
            searches = {
                phase: cap.HardCappedSearchClient(
                    GroundedFrontierSearch(QUESTION, phase, field_page=field_page),
                    budget,
                    phase=phase,
                )
                for phase in fixture_parent.PHASES
            }
            result, stage = target.run_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                monotonic=time.monotonic,
            )
        return inner, target.validate_result(result), target.validate_stage_receipt(stage)

    def test_verified_gain_never_reaches_revision_provider(self) -> None:
        inner, result, stage = self._run(field_page=True)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(receipt["provider_forward_count"], 3)
        self.assertEqual(receipt["suppressed_revision_entry_count"], 1)
        self.assertEqual(receipt["revision_provider_forward_count"], 0)
        self.assertEqual(receipt["physical_model_forward_count"], 3)
        self.assertTrue(receipt["first_validated_production_is_only_prediction"])
        self.assertFalse(receipt["header_quote_vertical_candidate_or_revision_prediction_used"])
        self.assertFalse(stage["failure_present"])

    def test_no_gain_is_same_three_call_production_path(self) -> None:
        inner, result, stage = self._run(field_page=False)
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(result["prediction_kind"], "model_generated")
        self.assertEqual(result["content_free_receipt"]["physical_query_count"], 4)
        self.assertLessEqual(result["content_free_receipt"]["physical_fetch_count"], 14)
        self.assertFalse(stage["failure_present"])

    def test_parent_failure_preserves_first_production_prediction(self) -> None:
        with mock.patch.object(sparse.parent, "validate_result", side_effect=ValueError("hidden")):
            inner, result, stage = self._run(field_page=False)
        self.assertEqual(inner.logical_calls, 3)
        self.assertIsNone(result["parent_result"])
        self.assertEqual(result["failure_types"]["post_effect"], "ValueError")
        self.assertTrue(result["content_free_receipt"]["prediction_preserved_after_parent_failure"])
        self.assertNotIn("hidden", str(result))
        self.assertFalse(stage["failure_present"])

    def test_stage_failure_is_content_free_and_budget_bound(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner = CompatibleModel()
            budget = cap.PhysicalEffectBudget()
            model = cap.HardCappedModelLimiter(self._model(inner, root), budget)
            searches = {
                phase: cap.HardCappedSearchClient(
                    GroundedFrontierSearch(QUESTION, phase), budget, phase=phase
                )
                for phase in fixture_parent.PHASES
            }
            with mock.patch.object(target, "_run_core", side_effect=RuntimeError("secret")):
                with self.assertRaises(target.ProductionOnlyStageError) as caught:
                    target.run_task(
                        TASK,
                        model=model,
                        searches=searches,
                        limits=limits(),
                        budget=budget,
                        monotonic=time.monotonic,
                    )
        receipt = caught.exception.stage_receipt
        self.assertTrue(receipt["failure_present"])
        self.assertEqual(receipt["failure_stage"], "sparse_production")
        self.assertEqual(receipt["failure_type"], "RuntimeError")
        self.assertNotIn("secret", str(receipt))
        self.assertEqual(receipt["outer_physical_budget_receipt"]["query_cap"], 4)
        self.assertEqual(receipt["outer_physical_budget_receipt"]["fetch_cap"], 14)
        self.assertEqual(receipt["outer_physical_budget_receipt"]["model_cap"], 4)

    def test_resealed_credit_revision_or_hidden_tamper_fails(self) -> None:
        _inner, result, _stage = self._run(field_page=True)
        receipt = result["content_free_receipt"]
        for kind in ("credit", "revision", "hidden"):
            changed = copy.deepcopy(receipt)
            if kind == "credit":
                changed["positive_signed_credit_count"] = 1
            elif kind == "revision":
                changed["revision_provider_forward_count"] = 1
            else:
                changed["task_category"] = "forbidden"
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_source_is_label_blind_and_has_no_effect_or_evaluator_capability(self) -> None:
        source = (ROOT / "src/deepwide_agent/v25265_production_only_totality_runtime.py").read_text(encoding="utf-8")
        for forbidden in (
            "official_eval", "evaluate_", "ground_truth", "answer_key", "api_key",
            "os.environ", "subprocess", "requests.", "urlopen",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
