from __future__ import annotations

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

from deepwide_agent import v24989_short_query_paired_runtime as target  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v24986_robust_paired_runtime import (  # noqa: E402
    InnerModel,
    SyntheticSearch,
)


QUESTION = (
    "Use web search and the official Example Public Registry public page to "
    "return one table for <ENTITY>Alpha</ENTITY>. "
    "Column names: Entity, Value. Preserve exact spelling."
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


class ShortQueryPairedRuntimeTests(unittest.TestCase):
    def test_proxy_changes_only_planning_json(self) -> None:
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
            result = target.run_paired_task(
                {
                    "opaque_id": "task_0123456789abcdef01234567",
                    "question": QUESTION,
                },
                model=model,
                search=SyntheticSearch(QUESTION),
                limits=limits(),
                arm_order=[
                    "raw_parent_prefix",
                    "identity_target_bound_projection",
                ],
            )
        checked = target.validate_result(result)
        short = checked["short_query_receipt"]
        robust = checked["robust_runtime_receipt"]
        self.assertTrue(short["strategy_applied"])
        self.assertEqual(short["provider_unique_query_count"], 1)
        self.assertEqual(short["output_query_count"], 4)
        self.assertEqual(robust["provider_unique_query_count"], 1)
        self.assertEqual(robust["deterministically_added_query_count"], 3)
        self.assertEqual(checked["content_free_receipt"]["executed_query_count"], 4)
        self.assertEqual(checked["content_free_receipt"]["model_logical_call_count"], 3)
        self.assertEqual(inner.requests, 3)

    def test_missing_facets_preserves_parent_query_behavior(self) -> None:
        # Pure-proxy behavior is covered without running retrieval: missing
        # facets leave the provider response byte-for-byte unchanged.
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            inner = InnerModel()
            bounded = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            proxy = target.ShortQueryPlanningModel(
                bounded,
                question="Return a table. Column names: Entity, Value.",
            )
            response = proxy.complete(
                "plan", "plan", max_output_tokens=100, json_mode=True
            )
        self.assertEqual(response.text, '{"language": "English", "columns": ["wrong"], "queries": ["visible planned query"]}')
        self.assertFalse(proxy.receipts[0]["strategy_applied"])

    def test_missing_facets_runs_parent_completion_unchanged(self) -> None:
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
            question = "Return one table. Column names: Entity, Value."
            result = target.run_paired_task(
                {
                    "opaque_id": "task_abcdef0123456789abcdef01",
                    "question": question,
                },
                model=model,
                search=SyntheticSearch(question),
                limits=limits(),
                arm_order=[
                    "raw_parent_prefix",
                    "identity_target_bound_projection",
                ],
            )
        checked = target.validate_result(result)
        short = checked["short_query_receipt"]
        robust = checked["robust_runtime_receipt"]
        self.assertFalse(short["strategy_applied"])
        self.assertEqual(short["output_query_count"], 1)
        self.assertEqual(robust["provider_unique_query_count"], 1)
        self.assertEqual(robust["completed_query_count"], 4)
        self.assertEqual(robust["deterministically_added_query_count"], 3)

    def test_invalid_planning_json_passes_through_unchanged(self) -> None:
        class InvalidPlanningModel:
            requests = attempts = 0
            input_tokens = output_tokens = total_tokens = 0

            def complete(self, system, user, *, max_output_tokens, json_mode=False):
                del system, user, max_output_tokens
                self.requests += 1
                self.attempts += 1
                return ModelResult(
                    text="not-json" if json_mode else "unused",
                    usage={},
                    response_id=None,
                    attempts=1,
                )

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            bounded = DeadlineAwareGlobalModelSlotLimiter(
                InvalidPlanningModel(),
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            proxy = target.ShortQueryPlanningModel(bounded, question=QUESTION)
            response = proxy.complete(
                "plan", "plan", max_output_tokens=100, json_mode=True
            )
        self.assertEqual(response.text, "not-json")
        self.assertFalse(proxy.receipts[0]["provider_query_vector_valid"])
        self.assertFalse(proxy.receipts[0]["strategy_applied"])

    def test_planning_exception_preserves_parent_fallback(self) -> None:
        class FailedPlanningModel(InnerModel):
            def complete(self, system, user, *, max_output_tokens, json_mode=False):
                if json_mode:
                    self.requests += 1
                    self.attempts += 1
                    raise RuntimeError("synthetic planning failure")
                return super().complete(
                    system,
                    user,
                    max_output_tokens=max_output_tokens,
                    json_mode=json_mode,
                )

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            inner = FailedPlanningModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            result = target.run_paired_task(
                {
                    "opaque_id": "task_00112233445566778899aabb",
                    "question": QUESTION,
                },
                model=model,
                search=SyntheticSearch(QUESTION),
                limits=limits(),
                arm_order=[
                    "raw_parent_prefix",
                    "identity_target_bound_projection",
                ],
            )
        checked = target.validate_result(result)
        self.assertFalse(
            checked["short_query_receipt"]["provider_query_vector_valid"]
        )
        self.assertFalse(checked["short_query_receipt"]["strategy_applied"])
        self.assertEqual(
            checked["robust_runtime_receipt"]["provider_unique_query_count"], 0
        )
        self.assertEqual(
            checked["robust_runtime_receipt"]["completed_query_count"], 4
        )


if __name__ == "__main__":
    unittest.main()
