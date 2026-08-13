from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25354_pre_effect_query_compatible_grounded_fact_runtime as old  # noqa: E402
from deepwide_agent import v25362_partial_field_grounded_fact_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import TASK, limits  # noqa: E402
import test_v25349_shared_prefix_grounded_fact_paired_runtime as fixture_module  # noqa: E402


class MixedFieldModel(fixture_module.PairedFactModel):
    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        value = super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
        if self.logical_calls == 2:
            parsed = json.loads(value.text)
            parsed["records"][0]["fields"].append(
                {
                    "column": "Type",
                    "source_field": "Unsupported label",
                    "value": "country-code",
                }
            )
            return ModelResult(
                text=json.dumps(parsed), usage={}, response_id=None, attempts=1
            )
        return value


class ConflictFieldModel(fixture_module.PairedFactModel):
    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        value = super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
        if self.logical_calls == 2:
            parsed = json.loads(value.text)
            second = copy.deepcopy(parsed["records"][0])
            second["fields"][0]["value"] = "visible"
            parsed["records"].append(second)
            return ModelResult(
                text=json.dumps(parsed), usage={}, response_id=None, attempts=1
            )
        return value


class V25362PartialFieldGroundedFactRuntimeTests(unittest.TestCase):
    def _run(self, inner=None):
        fixture = fixture_module.V25349SharedPrefixGroundedFactPairedRuntimeTests()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            original_inner, budget, old_model, searches = fixture._wiring(
                root, joint=True
            )
            chosen = inner or MixedFieldModel(joint=True)
            old_model._inner_limiter.inner = chosen
            first_old = searches[target.FIRST_PHASE]
            first = target.FirstWavePageCaptureHardCappedSearch(
                first_old._inner_search, budget
            )
            wired = dict(searches)
            wired[target.FIRST_PHASE] = first
            model = target.PartialFieldPreEffectHardCappedModel(
                old_model._inner_limiter,
                budget,
                question=TASK["question"],
                limits=limits(),
                first_wave_search=first,
            )
            value = target.run_paired_task(
                TASK,
                model=model,
                searches=wired,
                limits=limits(),
                budget=budget,
                arm_order=target.ARMS,
                monotonic=time.monotonic,
            )
        return chosen, budget, target.validate_result(value)

    def _run_old_mixed(self):
        fixture = fixture_module.V25349SharedPrefixGroundedFactPairedRuntimeTests()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            _inner, budget, old_model, searches = fixture._wiring(root, joint=True)
            chosen = MixedFieldModel(joint=True)
            old_model._inner_limiter.inner = chosen
            model = old.PreEffectQueryCompatibleHardCappedModel(
                old_model._inner_limiter,
                budget,
                question=TASK["question"],
                limits=limits(),
            )
            value = old.run_paired_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                arm_order=old.ARMS,
                monotonic=time.monotonic,
            )
        return old.validate_result(value)

    def test_partial_field_changes_old_record_atomic_noop_into_attributable_treatment(self) -> None:
        baseline = self._run_old_mixed()
        inner, budget, value = self._run()
        stage = value["partial_field_sanitizer_receipt"]
        physical = budget.receipt()
        self.assertFalse(baseline["candidate_production_prompt_changed"])
        self.assertFalse(baseline["attributable_prediction_change"])
        self.assertTrue(value["candidate_production_prompt_changed"])
        self.assertTrue(value["attributable_prediction_change"])
        self.assertTrue(stage["sanitizer_attempted"])
        self.assertTrue(stage["record_output_strictly_valid"])
        self.assertTrue(stage["response_changed"])
        self.assertEqual(stage["parsed_field_count"], 2)
        self.assertEqual(stage["field_accepted_count"], 1)
        self.assertEqual(
            stage["field_label_or_value_binding_rejection_count"], 1
        )
        self.assertEqual(stage["parent_verified_record_count"], 1)
        self.assertEqual(stage["parent_verified_field_count"], 1)
        self.assertEqual(stage["positive_signed_credit_count"], 0)
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(physical["query_admitted_count"], 4)
        self.assertLessEqual(physical["fetch_admitted_count"], 14)
        self.assertEqual(physical["model_admitted_count"], 4)
        self.assertEqual(physical["model_rejected_count"], 0)

    def test_all_valid_input_preserves_parent_predictions_and_effect_budget(self) -> None:
        inner, budget, value = self._run(
            fixture_module.PairedFactModel(joint=True)
        )
        stage = value["partial_field_sanitizer_receipt"]
        self.assertTrue(value["candidate_production_prompt_changed"])
        self.assertTrue(value["attributable_prediction_change"])
        self.assertEqual(stage["parsed_field_count"], 1)
        self.assertEqual(stage["field_accepted_count"], 1)
        self.assertEqual(stage["parent_verified_field_count"], 1)
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(budget.receipt()["model_admitted_count"], 4)

    def test_same_coordinate_conflict_remains_fail_closed(self) -> None:
        _inner, _budget, value = self._run(ConflictFieldModel(joint=True))
        stage = value["partial_field_sanitizer_receipt"]
        self.assertEqual(stage["record_conflict_count"], 1)
        self.assertEqual(stage["parent_verified_record_count"], 0)
        self.assertFalse(value["candidate_production_prompt_changed"])
        self.assertFalse(value["attributable_prediction_change"])

    def test_resealed_stage_parent_or_credit_tamper_fails(self) -> None:
        _inner, _budget, value = self._run()
        for kind in ("stage", "parent", "credit"):
            changed = copy.deepcopy(value)
            stage = changed["partial_field_sanitizer_receipt"]
            if kind == "stage":
                stage["parent_verified_field_count"] += 1
            elif kind == "credit":
                stage["positive_signed_credit_count"] = 1
            else:
                changed["prediction_changed"] = not changed["prediction_changed"]
            stage.pop("receipt_payload_sha256")
            stage["receipt_payload_sha256"] = payload_sha256(stage)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_runtime_is_label_blind_and_has_no_direct_external_capability(self) -> None:
        relative = Path(
            "src/deepwide_agent/v25362_partial_field_grounded_fact_runtime.py"
        )
        source = (ROOT / relative).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_fields = {
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
            and node.slice.value in forbidden_fields
        ]
        self.assertEqual(accesses, [])
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
