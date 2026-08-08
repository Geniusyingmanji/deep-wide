from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24273_two_wave_task_runtime as frozen  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent import v24873_keyless_fixed_coverage_runtime as runtime  # noqa: E402
import test_v24860_coverage_revision_integration as core_test  # noqa: E402
from test_v24862_same_task_coverage_runtime import SyntheticThinSearch  # noqa: E402


class LowSourceThinSearch(SyntheticThinSearch):
    def search_many(self, queries, **_kwargs):
        self.search_invocations += 1
        values = list(queries)
        self._increment("calls")
        self._increment("tool_calls")
        return [
            {
                "query": "task-union low-source",
                "answer": "",
                "results": [
                    {
                        "url": f"https://source-{self.search_invocations}.example/record",
                        "title": "synthetic",
                        "content": "discarded discovery snippet",
                    }
                ],
                "error": None,
                "provider": "synthetic",
            }
        ] if values else []


class FullSourceThinSearch(SyntheticThinSearch):
    def search_many(self, queries, **_kwargs):
        self.search_invocations += 1
        values = list(queries)
        self._increment("calls")
        self._increment("tool_calls")
        return [
            {
                "query": query,
                "answer": "",
                "results": [
                    {
                        "url": (
                            f"https://source-{self.search_invocations}-"
                            f"{query_index}-{result_index}.example/record"
                        ),
                        "title": "synthetic",
                        "content": "discarded discovery snippet",
                    }
                    for result_index in range(1, 4)
                ],
                "error": None,
                "provider": "synthetic",
            }
            for query_index, query in enumerate(values, start=1)
        ]


class V24873KeylessFixedCoverageRuntimeTests(unittest.TestCase):
    def clients(self, output: Path, search_cls=SyntheticThinSearch):
        clock = core_test.Clock(100.0)
        inner = core_test.SyntheticModel(
            [core_test.PLAN, core_test.BASELINE, core_test.SUPPORTED]
        )
        model = build_deadline_model(
            url="http://unused.invalid/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=180,
            max_retries=2,
            slot_directory=core_test.make_slots(output),
            output_root=output,
            slot_cap=2,
            pool_id=POOL_ID,
            absolute_deadline=220.0,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
            inner=inner,
        )
        search = search_cls(clock, deadline=220.0)
        return clock, inner, model, search

    def test_full_fixed_budget_chain_captures_ten_pages(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock, _inner, model, search = self.clients(output, FullSourceThinSearch)
            outcome = runtime.run_v24873_task(
                core_test.task(), arm="baseline", model=model, search=search,
                limits=core_test.limits(), monotonic=clock,
            )
            parent = outcome.result["parent_result"]
            total = parent["two_wave_retrieval"]["receipt"]["total"]
            controller = parent["two_wave_retrieval"]["receipt"]["controller"]
            self.assertEqual(total["queries_executed"], 4)
            self.assertEqual(total["fetches_attempted"], 10)
            self.assertEqual(controller["decision"], "expand")
            self.assertEqual(controller["entropy_value"], 0.0)
            self.assertEqual(search.fetch_calls, 10)
            self.assertEqual(len(getattr(search, runtime.PAGE_ATTRIBUTE)), 10)
            self.assertEqual(
                outcome.coverage_revision_receipt["disposition"],
                "admitted_supported_revision",
            )

    def test_low_source_count_is_actual_fetch_not_cap_failure(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock, _inner, model, search = self.clients(output, LowSourceThinSearch)
            outcome = runtime.run_v24873_task(
                core_test.task(), arm="baseline", model=model, search=search,
                limits=core_test.limits(), monotonic=clock,
            )
            parent = outcome.result["parent_result"]
            total = parent["two_wave_retrieval"]["receipt"]["total"]
            self.assertEqual(total["queries_executed"], 4)
            self.assertEqual(total["fetches_attempted"], 2)
            self.assertEqual(parent["cost"]["search"]["fetch_calls"], 2)
            self.assertEqual(search.fetch_calls, 2)
            self.assertEqual(len(getattr(search, runtime.PAGE_ATTRIBUTE)), 2)
            self.assertNotEqual(
                outcome.coverage_revision_receipt["disposition"],
                "identity_incomplete_page_prefix",
            )

    def test_privileged_input_fails_before_model_or_search_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock, inner, model, search = self.clients(output)
            with self.assertRaises(ValueError):
                runtime.run_v24873_task(
                    {**core_test.task(), "question_type": "forbidden"},
                    arm="baseline", model=model, search=search,
                    limits=core_test.limits(), monotonic=clock,
                )
            self.assertEqual(inner.requests, 0)
            self.assertEqual(search.calls, 0)

    def test_isolation_does_not_patch_frozen_search_or_parent(self) -> None:
        runtime.validate_isolation()
        self.assertIsNot(
            frozen.TwoWaveCachingSearchClient.search_many,
            runtime._FIXED_SEARCH_MANY,
        )

    def test_source_has_no_evaluator_credential_or_global_task_store(self) -> None:
        path = ROOT / "src/deepwide_agent/v24873_keyless_fixed_coverage_runtime.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
        self.assertNotIn("os.environ", source)
        self.assertNotIn("contextvars", source)
        self.assertNotIn("threading.local", source)


if __name__ == "__main__":
    unittest.main()
