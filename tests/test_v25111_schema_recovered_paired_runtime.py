from __future__ import annotations

import ast
import copy
import json
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

from deepwide_agent import v25111_schema_recovered_paired_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelRequestError, ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v24990_query_vector_paired_runtime import SyntheticRobustSearch  # noqa: E402


QUESTION = (
    "Use public sources to return one table about <ENTITY>Alpha</ENTITY>. "
    "Columns exactly: Entity | Value | Date | Detail. Preserve exact spelling."
)


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=240,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


class StageFailureModel:
    def __init__(self, *, fail_plan: bool = False, fail_proposal: bool = False) -> None:
        self.fail_plan = fail_plan
        self.fail_proposal = fail_proposal
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens, json_mode
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if self.logical_calls == 1:
            if self.fail_plan:
                raise ModelRequestError("synthetic plan transport failure")
            text = json.dumps(
                {
                    "columns": ["wrong"],
                    "queries": ["one", "two", "three", "four"],
                }
            )
        elif self.logical_calls == 2:
            if self.fail_proposal:
                raise ModelRequestError("synthetic proposal transport failure")
            text = json.dumps({"records": []})
        else:
            text = (
                "| Entity | Value | Date | Detail |\n"
                "|---|---|---|---|\n"
                "| Alpha | 111 | 2026-01-01 | stable |"
            )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class SchemaRecoveredRuntimeTests(unittest.TestCase):
    def _run(self, *, fail_plan: bool = False, fail_proposal: bool = False):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            slots = root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            inner = StageFailureModel(fail_plan=fail_plan, fail_proposal=fail_proposal)
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: SyntheticRobustSearch(QUESTION, "111") for phase in target.PHASES
            }
            wrapped = target.ExactVisibleSchemaStageModel(model, QUESTION)
            with mock.patch.object(
                model, "remaining_effect_seconds", return_value=123.0
            ), mock.patch.object(model, "receipt", return_value={"delegated": True}):
                self.assertEqual(wrapped.remaining_effect_seconds(), 123.0)
                self.assertEqual(wrapped.receipt(), {"delegated": True})
            result = target.run_paired_task(
                {"opaque_id": "task_0123456789abcdef01234567", "question": QUESTION},
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=target.ARMS,
            )
        return inner, target.validate_result(result)

    def test_provider_plan_columns_are_replaced_by_visible_exact_schema(self) -> None:
        inner, result = self._run()
        stage = result["stage_failure_accounting"]
        parent_receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(stage["visible_schema_column_count"], 4)
        self.assertFalse(stage["plan_model_effect_failed"])
        self.assertFalse(stage["proposal_model_effect_failed"])
        self.assertFalse(stage["representation_validation_failed"])
        self.assertEqual(parent_receipt["physical_model_logical_call_count"], 4)
        self.assertTrue(all(result["model_success"].values()))
        self.assertIn(
            "| Entity | Value | Date | Detail |",
            result["predictions"][target.CONTROL_ARM],
        )

    def test_plan_and_proposal_transport_failures_do_not_become_representation_failure(self) -> None:
        inner, result = self._run(fail_plan=True, fail_proposal=True)
        stage = result["stage_failure_accounting"]
        parent_receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertTrue(stage["plan_model_effect_failed"])
        self.assertTrue(stage["plan_transport_failed"])
        self.assertEqual(stage["plan_model_effect_failure_type"], "ModelRequestError")
        self.assertTrue(stage["proposal_model_effect_failed"])
        self.assertTrue(stage["proposal_transport_failed"])
        self.assertEqual(stage["proposal_model_effect_failure_type"], "ModelRequestError")
        self.assertEqual(stage["visible_schema_column_count"], 4)
        self.assertFalse(stage["representation_validation_failed"])
        self.assertFalse(parent_receipt["representation_validation_failed"])
        self.assertIsNotNone(parent_receipt["record_binding_receipt"])
        self.assertEqual(parent_receipt["physical_model_logical_call_count"], 4)
        self.assertEqual(
            parent_receipt["arm_metrics"][target.CONTROL_ARM][
                "effective_model_logical_call_count"
            ],
            3,
        )
        self.assertTrue(all(result["model_success"].values()))
        self.assertFalse(result["prediction_changed"])

    def test_true_representation_exception_remains_separate_and_safe(self) -> None:
        with mock.patch.object(
            target.parent.binding,
            "build_representation",
            side_effect=ValueError("synthetic representation failure"),
        ):
            inner, result = self._run()
        stage = result["stage_failure_accounting"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertFalse(stage["plan_model_effect_failed"])
        self.assertFalse(stage["proposal_model_effect_failed"])
        self.assertTrue(stage["representation_validation_failed"])
        self.assertEqual(stage["representation_failure_type"], "ValueError")
        self.assertTrue(result["content_free_receipt"]["prediction_identity_handoff_applied"])
        self.assertFalse(result["prediction_changed"])

    def test_ambiguous_visible_schema_fails_before_effect(self) -> None:
        inner = StageFailureModel()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            slots = root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: SyntheticRobustSearch("No explicit schema.", "111")
                for phase in target.PHASES
            }
            with self.assertRaisesRegex(ValueError, "schema"):
                target.run_paired_task(
                    {
                        "opaque_id": "task_0123456789abcdef01234567",
                        "question": "No explicit schema.",
                    },
                    model=model,
                    searches=searches,
                    limits=limits(),
                )
        self.assertEqual(inner.logical_calls, 0)

    def test_resealed_stage_transport_representation_or_launch_tamper_fails(self) -> None:
        _inner, result = self._run(fail_plan=True)
        for kind in ("transport", "representation", "launch"):
            changed = copy.deepcopy(result)
            stage = changed["stage_failure_accounting"]
            if kind == "transport":
                stage["plan_transport_failed"] = False
            elif kind == "representation":
                stage["representation_validation_failed"] = True
                stage["representation_failure_type"] = "ValueError"
            else:
                stage["benchmark_launch_or_evaluator_authorized"] = True
            stage.pop("receipt_payload_sha256")
            stage["receipt_payload_sha256"] = target.payload_sha256(stage)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_runtime_ast_is_label_blind_and_has_no_direct_effect_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25111_schema_recovered_paired_runtime.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: list[str] = []
        privileged: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if node.slice.value in {
                    "category",
                    "question_type",
                    "split",
                    "ground_truth",
                    "answer_key",
                    "score",
                    "reward",
                }:
                    privileged.append(str(node.slice.value))
        for forbidden in ("os", "pathlib", "subprocess", "requests", "socket"):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        self.assertEqual(privileged, [])


if __name__ == "__main__":
    unittest.main()
