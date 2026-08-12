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

from deepwide_agent import v25135_sparse_production_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelRequestError, ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    CompatibleModel,
    GroundedFrontierSearch,
    QUESTION,
    TASK,
)
from test_v25134_schema_total_causal_salience_runtime import (  # noqa: E402
    NO_EXACT_SCHEMA,
    NO_SCHEMA,
    TotalityModel,
)


def limits(**changes: int) -> ScoreFirstLimits:
    values = {
        "wall_seconds": 240,
        "model_calls": 3,
        "search_queries": 4,
        "fetch_targets": 10,
        "search_results_per_query": 3,
        "evidence_chars": 60_000,
        "page_chars": 5_000,
    }
    values.update(changes)
    return ScoreFirstLimits(**values)


class FailingRevisionModel(CompatibleModel):
    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        if self.logical_calls == 3:
            self.logical_calls += 1
            self.requests += 1
            self.attempts += 1
            self.input_tokens += 10
            self.output_tokens += 5
            self.total_tokens += 15
            raise ModelRequestError("synthetic revision transport failure")
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


class FailingProductionModel(CompatibleModel):
    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        if self.logical_calls == 2:
            self.logical_calls += 1
            self.requests += 1
            self.attempts += 1
            self.input_tokens += 10
            self.output_tokens += 5
            self.total_tokens += 15
            raise ModelRequestError("synthetic production transport failure")
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


class SparseProductionRuntimeTests(unittest.TestCase):
    def _run(
        self,
        *,
        question: str = QUESTION,
        inner=None,
        field_page: bool = False,
        post_effect_failure: bool = False,
    ):
        task = {"opaque_id": TASK["opaque_id"], "question": question}
        inner = inner or CompatibleModel()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GroundedFrontierSearch(
                    question, phase, field_page=field_page
                )
                for phase in target.PHASES
            }
            original = target.parent.validate_result
            if post_effect_failure:
                def fail_after_effect(value):
                    checked = original(value)
                    if checked["content_free_receipt"]["physical_model_logical_call_count"]:
                        raise RuntimeError("synthetic post-effect projection failure")
                    return checked

                target.parent.validate_result = fail_after_effect
            try:
                result = target.run_task(
                    task,
                    model=model,
                    searches=searches,
                    limits=limits(),
                )
            finally:
                target.parent.validate_result = original
        return inner, searches, target.validate_result(result)

    def test_no_verified_gain_runs_one_production_synthesis_only(self) -> None:
        inner, _searches, result = self._run(field_page=False)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertFalse(receipt["verified_source_identity_field_gain"])
        self.assertEqual(receipt["production_synthesis_entry_count"], 1)
        self.assertEqual(receipt["revision_synthesis_entry_count"], 1)
        self.assertEqual(receipt["production_synthesis_provider_forward_count"], 1)
        self.assertEqual(receipt["revision_synthesis_provider_forward_count"], 0)
        self.assertEqual(receipt["provider_forward_count"], 3)
        self.assertTrue(receipt["identity_replay_used"])
        self.assertEqual(result["prediction"], result["production_prediction"])
        parent = result["parent_result"]
        self.assertTrue(
            parent["content_free_receipt"]["arm_metrics"][target.CANDIDATE_ARM][
                "synthesis_attempted"
            ]
        )
        self.assertEqual(parent["cost"]["model"]["requests"], 3)

    def test_verified_gain_admits_one_revision_and_can_change_prediction(self) -> None:
        inner, _searches, result = self._run(field_page=True)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertTrue(receipt["selection_changed"])
        self.assertGreater(receipt["target_field_page_gain"], 0)
        self.assertTrue(receipt["verified_source_identity_field_gain"])
        self.assertTrue(receipt["revision_eligible"])
        self.assertEqual(receipt["revision_synthesis_provider_forward_count"], 1)
        self.assertTrue(receipt["revision_provider_output_valid"])
        self.assertFalse(receipt["identity_replay_used"])
        self.assertTrue(receipt["final_prediction_changed_from_production"])
        self.assertIn("111", result["production_prediction"])
        self.assertIn("999", result["prediction"])

    def test_revision_failure_preserves_completed_production_prediction(self) -> None:
        inner, _searches, result = self._run(
            inner=FailingRevisionModel(), field_page=True
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertTrue(receipt["verified_source_identity_field_gain"])
        self.assertTrue(receipt["revision_failure_present"])
        self.assertFalse(receipt["revision_provider_output_valid"])
        self.assertTrue(receipt["identity_replay_used"])
        self.assertTrue(receipt["production_prediction_preserved"])
        self.assertEqual(result["prediction"], result["production_prediction"])
        self.assertIn("111", result["prediction"])

    def test_post_effect_projection_failure_is_terminal_and_preserves_production(self) -> None:
        inner, _searches, result = self._run(
            field_page=True, post_effect_failure=True
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertIsNone(result["parent_result"])
        self.assertTrue(receipt["post_effect_failure_present"])
        self.assertTrue(receipt["production_prediction_preserved"])
        self.assertEqual(result["prediction"], result["production_prediction"])
        self.assertIn("111", result["prediction"])

    def test_production_failure_is_schema_valid_terminal_fallback(self) -> None:
        inner, _searches, result = self._run(
            inner=FailingProductionModel(), field_page=True
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertFalse(receipt["production_provider_output_valid"])
        self.assertTrue(receipt["production_fallback_used"])
        self.assertFalse(receipt["revision_eligible"])
        self.assertEqual(receipt["revision_synthesis_provider_forward_count"], 0)
        self.assertEqual(result["prediction_kind"], "fallback")
        self.assertEqual(result["prediction"], result["production_prediction"])
        self.assertIn("| Domain | Type | TLD Manager |", result["prediction"])

    def test_schema_total_provider_and_generic_paths_remain_terminal(self) -> None:
        cases = (
            (NO_EXACT_SCHEMA, TotalityModel(), "provider_plan", 3),
            (NO_SCHEMA, TotalityModel(invalid_plan=True), "generic_result", 1),
        )
        for question, inner, source, count in cases:
            with self.subTest(source=source):
                _inner, _searches, result = self._run(
                    question=question, inner=inner, field_page=False
                )
                receipt = result["content_free_receipt"]
                self.assertEqual(receipt["schema_source"], source)
                self.assertEqual(receipt["effective_column_count"], count)
                self.assertEqual(receipt["revision_synthesis_provider_forward_count"], 0)
                self.assertEqual(result["status"], "terminal")

    def test_privileged_or_budget_input_fails_before_model_and_search_effect(self) -> None:
        for kind in ("privileged", "budget"):
            inner = CompatibleModel()
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
                output_root = Path(raw)
                slots = output_root / "slots"
                slots.mkdir()
                for index in range(1, 5):
                    (slots / f"slot_{index:02d}.lock").write_text("{}\n")
                model = DeadlineAwareGlobalModelSlotLimiter(
                    inner,
                    slot_directory=slots,
                    output_root=output_root,
                    slot_cap=4,
                    absolute_deadline=time.monotonic() + 240,
                )
                searches = {
                    phase: GroundedFrontierSearch(QUESTION, phase)
                    for phase in target.PHASES
                }
                task = (
                    {**TASK, "question_type": "forbidden"}
                    if kind == "privileged"
                    else TASK
                )
                chosen_limits = limits(model_calls=2) if kind == "budget" else limits()
                with self.assertRaises(ValueError):
                    target.run_task(
                        task,
                        model=model,
                        searches=searches,
                        limits=chosen_limits,
                    )
            self.assertEqual(inner.logical_calls, 0)
            self.assertTrue(all(search.calls == 0 for search in searches.values()))

    def test_content_free_receipt_and_resealed_tamper_fail_closed(self) -> None:
        _inner, _searches, result = self._run(field_page=True)
        encoded = json.dumps(result["content_free_receipt"], ensure_ascii=False)
        for forbidden in (
            "New Delhi",
            "India",
            "IANA",
            "https://",
            "111",
            "999",
            TASK["opaque_id"],
        ):
            self.assertNotIn(forbidden, encoded)
        for kind in ("gain", "forward", "launch", "prediction"):
            changed = copy.deepcopy(result)
            receipt = changed["content_free_receipt"]
            if kind == "gain":
                receipt["verified_source_identity_field_gain"] = False
            elif kind == "forward":
                receipt["revision_synthesis_provider_forward_count"] = 0
            elif kind == "launch":
                receipt["benchmark_launch_or_evaluator_authorized"] = True
            else:
                changed["prediction"] = changed["production_prediction"]
                changed["prediction_sha256"] = changed[
                    "production_prediction_sha256"
                ]
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_module_is_label_blind_build_only_and_has_no_effect_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25135_sparse_production_runtime.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
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
            "httpx",
            "socket",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        self.assertEqual(privileged, [])
        encoded = path.read_text(encoding="utf-8")
        self.assertNotIn("run_official_eval_local", encoded)
        self.assertNotIn("target/main", encoded)


if __name__ == "__main__":
    unittest.main()
