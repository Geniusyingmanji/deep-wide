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
from deepwide_agent import v25232_header_totality_shadow_runtime as parent  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as target  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    CompatibleModel,
    GroundedFrontierSearch,
    QUESTION,
    TASK,
    limits,
)


class V25253OuterPhysicalCapObservedRuntimeTests(unittest.TestCase):
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

    def test_model_fifth_call_is_rejected_before_slot_and_provider_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner = CompatibleModel()
            limiter = self._model(inner, root)
            budget = target.PhysicalEffectBudget()
            model = target.HardCappedModelLimiter(limiter, budget)
            calls = (
                (target.effect_parent.score.PLAN_SYSTEM, "plan"),
                (
                    target.effect_parent.parent.parent.sparse_parent.target_plan.SYSTEM_PROMPT,
                    "ground",
                ),
                (target.effect_parent.score.SYNTHESIS_SYSTEM, "production"),
                (target.effect_parent.score.SYNTHESIS_SYSTEM, "revision"),
                (target.effect_parent.score.SYNTHESIS_SYSTEM, "unexpected-fifth"),
            )
            for index, (system, user) in enumerate(calls):
                if index < 4:
                    model.complete(system, user, max_output_tokens=10)
                else:
                    with self.assertRaises(target.PhysicalEffectBudgetExceeded):
                        model.complete(system, user, max_output_tokens=10)
            receipt = budget.receipt()
            self.assertEqual(inner.logical_calls, 4)
            self.assertEqual(limiter.acquisitions, 4)
            self.assertEqual(receipt["model_admitted_count"], 4)
            self.assertEqual(receipt["model_rejected_count"], 1)
            self.assertEqual(receipt["rejection_stage_counts"]["model_revision"], 1)

    def test_fetch_overflow_batch_is_atomically_rejected_before_underlying_effect(self) -> None:
        budget = target.PhysicalEffectBudget()
        first_inner = GroundedFrontierSearch(QUESTION, parent.FIRST_PHASE)
        second_inner = GroundedFrontierSearch(QUESTION, parent.SECOND_PHASE)
        first = target.HardCappedSearchClient(first_inner, budget, phase=parent.FIRST_PHASE)
        second = target.HardCappedSearchClient(second_inner, budget, phase=parent.SECOND_PHASE)
        first.search_many(["a", "b"], max_results=3)
        second.search_many(["c", "d"], max_results=3)
        first.fetch_urls([{"url": f"https://example.test/{index}"} for index in range(6)])
        second.fetch_urls([{"url": f"https://example.test/x/{index}"} for index in range(8)])
        with self.assertRaises(target.PhysicalEffectBudgetExceeded):
            second.fetch_urls([{"url": "https://example.test/overflow"}])
        receipt = budget.receipt()
        self.assertEqual(first_inner.fetch_calls, 6)
        self.assertEqual(second_inner.fetch_calls, 8)
        self.assertEqual(receipt["query_admitted_count"], 4)
        self.assertEqual(receipt["fetch_admitted_count"], 14)
        self.assertEqual(receipt["fetch_rejected_count"], 1)
        self.assertEqual(
            receipt["rejection_stage_counts"]["shared_second_wave_union_fetch"], 1
        )

    def _run_observed(self, *, field_page: bool):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner = CompatibleModel()
            budget = target.PhysicalEffectBudget()
            model = target.HardCappedModelLimiter(self._model(inner, root), budget)
            searches = {
                phase: target.HardCappedSearchClient(
                    GroundedFrontierSearch(QUESTION, phase, field_page=field_page),
                    budget,
                    phase=phase,
                )
                for phase in parent.PHASES
            }
            result, receipt = target.run_observed_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                monotonic=time.monotonic,
            )
        return inner, parent.validate_result(result), target.validate_stage_receipt(receipt)

    def test_end_to_end_cap_is_terminal_and_never_exceeds_4_14(self) -> None:
        inner, result, receipt = self._run_observed(field_page=True)
        budget = receipt["outer_physical_budget_receipt"]
        self.assertLessEqual(inner.logical_calls, 4)
        self.assertLessEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertLessEqual(budget["model_admitted_count"], 4)
        self.assertEqual(result["status"], "terminal")
        sparse_result = result
        for _ in range(5):
            sparse_result = sparse_result["parent_result"]
        sparse_receipt = sparse.validate_result(sparse_result)["content_free_receipt"]
        self.assertEqual(sparse_receipt["provider_forward_count"], 4)
        self.assertEqual(result["predictions"][parent.CONTROL_ARM], result["predictions"][parent.CANDIDATE_ARM])

    def test_no_gain_success_matches_parent_result_and_observer_is_side_only(self) -> None:
        inner, result, receipt = self._run_observed(field_page=False)
        self.assertEqual(inner.logical_calls, 3)
        self.assertFalse(receipt["failure_present"])
        self.assertTrue(all(value == 1 for value in receipt["stage_completed_counts"].values()))
        self.assertEqual(result["predictions"], result["parent_result"]["predictions"])
        self.assertEqual(result["prediction_sha256"], result["parent_result"]["prediction_sha256"])

    def test_effect_rebuild_value_error_is_localized_without_content(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner = CompatibleModel()
            budget = target.PhysicalEffectBudget()
            model = target.HardCappedModelLimiter(self._model(inner, root), budget)
            searches = {
                phase: target.HardCappedSearchClient(
                    GroundedFrontierSearch(QUESTION, phase, field_page=False),
                    budget,
                    phase=phase,
                )
                for phase in parent.PHASES
            }
            with mock.patch.object(parent, "_effect_result", side_effect=ValueError("secret detail")):
                with self.assertRaises(target.ObservedRuntimeStageError) as caught:
                    target.run_observed_task(
                        TASK,
                        model=model,
                        searches=searches,
                        limits=limits(),
                        budget=budget,
                        monotonic=time.monotonic,
                    )
        receipt = caught.exception.stage_receipt
        self.assertTrue(receipt["failure_present"])
        self.assertEqual(receipt["failure_stage"], "effect_rebuild")
        self.assertEqual(receipt["failure_type"], "ValueError")
        self.assertNotIn("secret detail", str(receipt))

    def test_receipt_resealed_cap_credit_or_hidden_tamper_fails(self) -> None:
        budget = target.PhysicalEffectBudget()
        value = budget.receipt()
        for kind in ("cap", "credit", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "cap":
                changed["fetch_cap"] = 13
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["hidden_task_label"] = "package-stratum"
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_budget_receipt(changed)

    def test_source_is_label_blind_and_has_no_effect_or_evaluator_capability(self) -> None:
        source = (ROOT / "src/deepwide_agent/v25253_outer_physical_cap_observed_runtime.py").read_text(encoding="utf-8")
        self.assertNotIn("official_eval", source)
        self.assertNotIn("evaluate_", source)
        self.assertNotIn("ground_truth", source)
        self.assertNotIn("api_key", source)


if __name__ == "__main__":
    unittest.main()
