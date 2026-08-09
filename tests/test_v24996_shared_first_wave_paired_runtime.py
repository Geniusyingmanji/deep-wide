from __future__ import annotations

import ast
import copy
import hashlib
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

from deepwide_agent import v24996_shared_first_wave_paired_runtime as target  # noqa: E402
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


class OverlapSyntheticSearch(SyntheticRobustSearch):
    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.calls += 1
        sources = [
            {
                "url": f"https://shared-overlap.example/{index}",
                "fetch_url": f"https://shared-overlap.example/{index}",
                "title": f"Shared {index}",
            }
            for index in range(3)
        ]
        return [
            {
                "query": query,
                "answer": "",
                "results": copy.deepcopy(sources),
                "error": None,
                "provider": "synthetic",
            }
            for query in values
        ]


class SharedFirstWaveRuntimeTests(unittest.TestCase):
    def _run(
        self,
        *,
        search_types=(
            SyntheticRobustSearch,
            SyntheticRobustSearch,
            SyntheticRobustSearch,
        ),
        values=("555", "111", "999"),
    ):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            inner = InnerModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: cls(QUESTION, value)
                for phase, cls, value in zip(
                    target.PHASES, search_types, values, strict=True
                )
            }
            result = target.run_paired_task(
                {
                    "opaque_id": "task_0123456789abcdef01234567",
                    "question": QUESTION,
                },
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=[target.CONTROL_ARM, target.CANDIDATE_ARM],
            )
        return inner, searches, target.validate_result(result)

    def test_one_shared_wave_two_delta_waves_and_two_syntheses(self) -> None:
        inner, searches, result = self._run()
        receipt = result["content_free_receipt"]
        self.assertTrue(receipt["second_wave_strategy_applied"])
        self.assertTrue(receipt["first_two_completed_queries_preserved"])
        self.assertTrue(receipt["query_vectors_differ_only_in_second_wave"])
        self.assertTrue(receipt["shared_first_wave_completed"])
        self.assertTrue(receipt["shared_prefix_byte_equal_between_arms"])
        self.assertEqual(receipt["physical_query_count"], 6)
        self.assertEqual(receipt["physical_fetch_count"], 14)
        self.assertEqual(receipt["model_logical_call_count"], 3)
        self.assertEqual(inner.requests, 3)
        self.assertEqual(searches[target.SHARED_PHASE].calls, 1)
        self.assertEqual(searches[target.SHARED_PHASE].fetch_calls, 6)
        for arm in target.ARMS:
            self.assertEqual(searches[arm].calls, 1)
            self.assertEqual(searches[arm].fetch_calls, 4)
            metric = receipt["arm_metrics"][arm]
            self.assertEqual(metric["executed_queries"], 4)
            self.assertEqual(metric["fetch_attempts"], 10)
            self.assertTrue(metric["model_success"])
        self.assertEqual(len(set(result["evidence_characters"].values())), 1)
        self.assertTrue(result["prediction_changed"])
        self.assertIn("111", result["predictions"][target.CONTROL_ARM])
        self.assertIn("999", result["predictions"][target.CANDIDATE_ARM])

    def test_shared_urls_are_excluded_before_each_delta_cap(self) -> None:
        _inner, searches, result = self._run(
            search_types=(
                OverlapSyntheticSearch,
                OverlapSyntheticSearch,
                OverlapSyntheticSearch,
            )
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["physical_query_count"], 6)
        self.assertEqual(receipt["physical_fetch_count"], 3)
        self.assertEqual(searches[target.SHARED_PHASE].fetch_calls, 3)
        for arm in target.ARMS:
            phase = result["physical_wave_receipts"][arm]
            self.assertEqual(phase["union_sources"], 3)
            self.assertEqual(phase["excluded_shared_sources"], 3)
            self.assertEqual(phase["fetch_attempts"], 0)
            self.assertEqual(searches[arm].fetch_calls, 0)
            self.assertEqual(receipt["arm_metrics"][arm]["fetch_attempts"], 3)
        self.assertFalse(result["prediction_changed"])

    def test_delta_failure_retains_attempted_effect_accounting(self) -> None:
        _inner, _searches, result = self._run(
            search_types=(
                SyntheticRobustSearch,
                FailingSyntheticRobustSearch,
                SyntheticRobustSearch,
            )
        )
        receipt = result["content_free_receipt"]
        self.assertIsNotNone(
            result["failure_types"]["retrieval"][target.CONTROL_ARM]
        )
        self.assertEqual(receipt["physical_query_count"], 6)
        self.assertEqual(receipt["physical_fetch_count"], 10)
        control = receipt["arm_metrics"][target.CONTROL_ARM]
        candidate = receipt["arm_metrics"][target.CANDIDATE_ARM]
        self.assertEqual(control["executed_queries"], 4)
        self.assertEqual(control["fetch_attempts"], 6)
        self.assertEqual(candidate["executed_queries"], 4)
        self.assertEqual(candidate["fetch_attempts"], 10)
        self.assertTrue(control["synthesis_attempted"])
        self.assertTrue(candidate["synthesis_attempted"])

    def test_shared_failure_prevents_delta_and_synthesis(self) -> None:
        _inner, searches, result = self._run(
            search_types=(
                FailingSyntheticRobustSearch,
                SyntheticRobustSearch,
                SyntheticRobustSearch,
            )
        )
        receipt = result["content_free_receipt"]
        self.assertFalse(receipt["shared_first_wave_completed"])
        self.assertFalse(receipt["shared_prefix_byte_equal_between_arms"])
        self.assertEqual(receipt["physical_query_count"], 2)
        self.assertEqual(receipt["physical_fetch_count"], 0)
        self.assertEqual(receipt["model_logical_call_count"], 1)
        for arm in target.ARMS:
            self.assertEqual(searches[arm].calls, 0)
            self.assertIsNotNone(result["failure_types"]["retrieval"][arm])
            metric = receipt["arm_metrics"][arm]
            self.assertEqual(metric["executed_queries"], 2)
            self.assertFalse(metric["synthesis_attempted"])

    def test_resealed_effect_tamper_fails_closed(self) -> None:
        _inner, _searches, result = self._run()
        tampered = copy.deepcopy(result)
        tampered["physical_effects"][target.CANDIDATE_ARM][
            "logical_queries"
        ] = 3
        tampered.pop("result_payload_sha256")
        tampered["result_payload_sha256"] = payload_sha256(tampered)
        with self.assertRaises(ValueError):
            target.validate_result(tampered)

        nested = copy.deepcopy(result)
        phase = nested["physical_wave_receipts"][target.CANDIDATE_ARM]
        phase["fetch_attempts"] = 5
        phase.pop("receipt_payload_sha256")
        phase["receipt_payload_sha256"] = payload_sha256(phase)
        nested.pop("result_payload_sha256")
        nested["result_payload_sha256"] = payload_sha256(nested)
        with self.assertRaises(ValueError):
            target.validate_result(nested)

    def test_runtime_rejects_extra_task_metadata_and_shared_clients(self) -> None:
        with self.assertRaises(ValueError):
            target.run_paired_task(
                {
                    "opaque_id": "task_0123456789abcdef01234567",
                    "question": QUESTION,
                    "category": "hidden",
                },
                model=object(),
                searches={},
                limits=limits(),
            )

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            model = DeadlineAwareGlobalModelSlotLimiter(
                InnerModel(),
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            shared = SyntheticRobustSearch(QUESTION, "111")
            with self.assertRaisesRegex(ValueError, "three distinct"):
                target.run_paired_task(
                    {
                        "opaque_id": "task_0123456789abcdef01234567",
                        "question": QUESTION,
                    },
                    model=model,
                    searches={phase: shared for phase in target.PHASES},
                    limits=limits(),
                )

    def test_module_has_no_effect_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v24996_shared_first_wave_paired_runtime.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "deepwidebench",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )


if __name__ == "__main__":
    unittest.main()
