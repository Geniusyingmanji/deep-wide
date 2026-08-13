from __future__ import annotations

import ast
import copy
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25110_exact_visible_schema as schema  # noqa: E402
from deepwide_agent import v25117_grounded_target_record_plan as target_plan  # noqa: E402
from deepwide_agent import v25353_fresh_pep_grounded_fact_external_contract as contract  # noqa: E402
from deepwide_agent import v25354_pre_effect_query_compatible_grounded_fact_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelRequestError  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import limits  # noqa: E402
import test_v25349_shared_prefix_grounded_fact_paired_runtime as fixture_module  # noqa: E402


class InvalidOrFailingPlanModel(fixture_module.PairedFactModel):
    def __init__(self, *, fail: bool) -> None:
        super().__init__(joint=True)
        self.fail = fail

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        if self.logical_calls == 0 and self.fail:
            self.logical_calls += 1
            self.attempts += 1
            raise ModelRequestError("synthetic plan transport failure")
        value = super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
        if self.logical_calls == 1:
            value.text = "not-json"
        return value


class V25354PreEffectQueryCompatibleGroundedFactRuntimeTests(unittest.TestCase):
    def _run(self, *, fail: bool):
        fixture = fixture_module.V25349SharedPrefixGroundedFactPairedRuntimeTests()
        task = contract.task_vector()[0]
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            _old_inner, budget, old_model, searches = fixture._wiring(
                output_root, joint=True
            )
            inner = InvalidOrFailingPlanModel(fail=fail)
            old_model._inner_limiter.inner = inner
            model = target.PreEffectQueryCompatibleHardCappedModel(
                old_model._inner_limiter,
                budget,
                question=task["question"],
                limits=limits(),
            )
            value = target.run_paired_task(
                task,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                arm_order=contract.arm_order_vector()[0],
                monotonic=time.monotonic,
            )
        return inner, budget, target.validate_result(value)

    def test_all_fresh_fallback_vectors_rejected_before_and_accepted_after_projection(self) -> None:
        for index, task in enumerate(contract.task_vector()):
            raw = schema.validated_exact_plan({}, task["question"], limits())
            with self.subTest(index=index, phase="before"), self.assertRaises(
                ValueError
            ):
                target_plan.prepare_plan(
                    task["question"], raw["columns"], raw["queries"], []
                )
            projected, observation = target.projected_plan(
                {}, task["question"], limits()
            )
            prepared = target_plan.prepare_plan(
                task["question"],
                projected["columns"],
                projected["queries"],
                [],
            )
            self.assertEqual(len(prepared["legacy_queries"]), 4)
            self.assertTrue(observation["visible_fallback_query_seed_used"])
            self.assertTrue(
                all(
                    target_plan._safe_query(query) == query
                    for query in projected["queries"]
                )
            )

    def test_invalid_plan_is_projected_before_full_physical_effect_sequence(self) -> None:
        _inner, budget, value = self._run(fail=False)
        stage = value["pre_effect_query_contract_receipt"]
        effects = budget.receipt()
        self.assertTrue(stage["plan_output_validation_failed"])
        self.assertTrue(stage["visible_fallback_query_seed_used"])
        self.assertFalse(stage["plan_model_effect_failed"])
        self.assertEqual(effects["query_admitted_count"], 4)
        self.assertEqual(effects["model_admitted_count"], 4)
        self.assertLessEqual(effects["fetch_admitted_count"], 14)
        self.assertTrue(value["content_free_receipt"]["first_wave_completed"])

    def test_transport_failed_plan_is_projected_without_extra_model_effect(self) -> None:
        inner, budget, value = self._run(fail=True)
        stage = value["pre_effect_query_contract_receipt"]
        self.assertTrue(stage["plan_model_effect_failed"])
        self.assertTrue(stage["plan_transport_failed"])
        self.assertTrue(stage["visible_fallback_query_seed_used"])
        self.assertEqual(budget.receipt()["model_admitted_count"], 4)
        self.assertEqual(stage["logical_model_call_count"], 4)
        self.assertEqual(inner.logical_calls, 4)

    def test_valid_plan_preserves_parent_treatment_and_attribution(self) -> None:
        fixture = fixture_module.V25349SharedPrefixGroundedFactPairedRuntimeTests()
        task = fixture_module.TASK
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            inner, budget, old_model, searches = fixture._wiring(
                output_root, joint=True
            )
            model = target.PreEffectQueryCompatibleHardCappedModel(
                old_model._inner_limiter,
                budget,
                question=task["question"],
                limits=limits(),
            )
            value = target.run_paired_task(
                task,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                arm_order=target.ARMS,
                monotonic=time.monotonic,
            )
        checked = target.validate_result(value)
        self.assertEqual(inner.logical_calls, 4)
        self.assertTrue(checked["candidate_production_prompt_changed"])
        self.assertTrue(checked["attributable_prediction_change"])

    def test_resealed_stage_or_parent_binding_tamper_fails(self) -> None:
        _inner, _budget, value = self._run(fail=False)
        for kind in ("stage", "parent"):
            changed = copy.deepcopy(value)
            if kind == "stage":
                changed["pre_effect_query_contract_receipt"][
                    "completed_four_query_vector_valid_under_downstream_grammar"
                ] = False
                receipt = changed["pre_effect_query_contract_receipt"]
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = target.payload_sha256(receipt)
            else:
                changed["prediction_changed"] = not changed["prediction_changed"]
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_successor_source_is_label_blind_and_has_no_external_capability(self) -> None:
        relative = Path(
            "src/deepwide_agent/v25354_pre_effect_query_compatible_grounded_fact_runtime.py"
        )
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        forbidden = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        accesses = [
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in forbidden
        ]
        self.assertEqual(accesses, [])
        source = (ROOT / relative).read_text(encoding="utf-8")
        for forbidden_call in (
            "open(",
            "getenv(",
            "subprocess.",
            "requests.",
            "run_official_eval_local(",
        ):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
