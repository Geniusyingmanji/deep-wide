from __future__ import annotations

import ast
import copy
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"
for path in (SRC, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24993_hybrid_query_paired_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v24990_query_vector_paired_runtime import (  # noqa: E402
    FailingSyntheticRobustSearch,
    InnerModel,
    SyntheticRobustSearch,
)


QUESTION = (
    "Use web search and the official Example Public Registry public page to "
    "return one table for <ENTITY>Alpha</ENTITY>. Column names: Entity, Value. "
    "The Value must come from the same official Example table record."
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


class HybridQueryPairedRuntimeTests(unittest.TestCase):
    def _run(
        self,
        *,
        question: str = QUESTION,
        values=("111", "999"),
        inner=None,
        search_types=(SyntheticRobustSearch, SyntheticRobustSearch),
    ):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            inner = inner or InnerModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                target.CONTROL_ARM: search_types[0](question, values[0]),
                target.CANDIDATE_ARM: search_types[1](question, values[1]),
            }
            result = target.run_paired_task(
                {
                    "opaque_id": "task_0123456789abcdef01234567",
                    "question": question,
                },
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=[target.CONTROL_ARM, target.CANDIDATE_ARM],
            )
        return inner, searches, target.validate_result(result)

    def test_runtime_rejects_privileged_or_extra_task_metadata(self) -> None:
        for extra in (
            {"question_type": "hidden"},
            {"category": "hidden"},
            {"ground_truth": "hidden"},
            {"unrecognized": "hidden"},
        ):
            with self.subTest(extra=next(iter(extra))):
                with self.assertRaises(ValueError):
                    target.run_paired_task(
                        {
                            "opaque_id": "task_0123456789abcdef01234567",
                            "question": QUESTION,
                            **extra,
                        },
                        model=object(),
                        searches={},
                        limits=limits(),
                    )

    def test_hybrid_runs_one_plan_two_equal_retrieval_arms(self) -> None:
        inner, searches, result = self._run()
        receipt = result["content_free_receipt"]
        hybrid = result["hybrid_query_receipt"]
        self.assertTrue(receipt["hybrid_query_strategy_applied"])
        self.assertTrue(receipt["provider_anchor_preserved_in_first_slot"])
        self.assertTrue(receipt["first_explicit_authority_phrase_selected"])
        self.assertTrue(receipt["query_vectors_differ"])
        self.assertEqual(receipt["model_logical_call_count"], 3)
        self.assertEqual(inner.requests, 3)
        self.assertEqual(hybrid["provider_unique_query_count"], 1)
        for arm in target.ARMS:
            metric = receipt["arm_metrics"][arm]
            self.assertEqual(metric["planned_queries"], 4)
            self.assertEqual(metric["executed_queries"], 4)
            self.assertEqual(metric["fetch_attempts"], 10)
            self.assertEqual(metric["usable_pages"], 10)
            self.assertTrue(metric["model_success"])
            self.assertEqual(searches[arm].calls, 2)
            self.assertEqual(searches[arm].fetch_calls, 10)
        self.assertEqual(len(set(result["evidence_characters"].values())), 1)
        self.assertTrue(result["prediction_changed"])

    def test_missing_facets_uses_identical_query_vectors(self) -> None:
        question = "Return one table. Column names: Entity, Value."
        _inner, _searches, result = self._run(
            question=question, values=("111", "111")
        )
        receipt = result["content_free_receipt"]
        self.assertFalse(receipt["hybrid_query_strategy_applied"])
        self.assertFalse(receipt["first_explicit_authority_phrase_selected"])
        self.assertFalse(receipt["query_vectors_differ"])
        self.assertFalse(result["prediction_changed"])

    def test_invalid_planning_falls_back_without_hybrid_activation(self) -> None:
        class InvalidPlanningModel(InnerModel):
            def complete(self, system, user, *, max_output_tokens, json_mode=False):
                if json_mode:
                    del system, user, max_output_tokens
                    self.requests += 1
                    self.attempts += 1
                    self.input_tokens += 1
                    self.output_tokens += 1
                    self.total_tokens += 2
                    return ModelResult(
                        text="not-json",
                        usage={},
                        response_id=None,
                        attempts=1,
                    )
                return super().complete(
                    system,
                    user,
                    max_output_tokens=max_output_tokens,
                    json_mode=json_mode,
                )

        _inner, _searches, result = self._run(inner=InvalidPlanningModel())
        receipt = result["content_free_receipt"]
        self.assertIsNotNone(result["failure_types"]["plan"])
        self.assertEqual(receipt["provider_unique_query_count"], 0)
        self.assertFalse(receipt["hybrid_query_strategy_applied"])
        self.assertFalse(receipt["provider_anchor_preserved_in_first_slot"])
        self.assertFalse(receipt["first_explicit_authority_phrase_selected"])
        self.assertFalse(receipt["query_vectors_differ"])

    def test_partial_retrieval_failure_preserves_effect_accounting(self) -> None:
        _inner, _searches, result = self._run(
            search_types=(FailingSyntheticRobustSearch, SyntheticRobustSearch)
        )
        receipt = result["content_free_receipt"]
        failed = receipt["arm_metrics"][target.CONTROL_ARM]
        candidate = receipt["arm_metrics"][target.CANDIDATE_ARM]
        self.assertIsNotNone(result["failure_types"]["retrieval"][target.CONTROL_ARM])
        self.assertEqual(failed["executed_queries"], 2)
        self.assertEqual(failed["fetch_attempts"], 0)
        self.assertFalse(failed["synthesis_attempted"])
        self.assertTrue(candidate["synthesis_attempted"])
        self.assertEqual(
            receipt["actual_first_synthesis_arm"], target.CANDIDATE_ARM
        )
        self.assertEqual(receipt["model_logical_call_count"], 2)

    def test_resealed_resource_tamper_fails_closed(self) -> None:
        _inner, _searches, result = self._run()
        tampered = copy.deepcopy(result)
        tampered["content_free_receipt"]["arm_metrics"][target.CANDIDATE_ARM][
            "fetch_attempts"
        ] = 11
        tampered["content_free_receipt"].pop("receipt_payload_sha256")
        tampered["content_free_receipt"]["receipt_payload_sha256"] = payload_sha256(
            tampered["content_free_receipt"]
        )
        tampered.pop("result_payload_sha256")
        tampered["result_payload_sha256"] = payload_sha256(tampered)
        with self.assertRaises(ValueError):
            target.validate_result(tampered)

        negative_cost = copy.deepcopy(result)
        negative_cost["cost"]["model"]["total_tokens"] = -1
        negative_cost.pop("result_payload_sha256")
        negative_cost["result_payload_sha256"] = payload_sha256(negative_cost)
        with self.assertRaises(ValueError):
            target.validate_result(negative_cost)

    def test_module_has_no_effect_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v24993_hybrid_query_paired_runtime.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os", "pathlib", "subprocess", "requests", "deepwidebench"
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )


if __name__ == "__main__":
    unittest.main()
