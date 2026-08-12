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

from deepwide_agent import v25165_observed_vertical_key_value_runtime as target  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import TASK  # noqa: E402
from test_v25147_deterministic_quote_candidate_runtime import CandidateModel  # noqa: E402
from test_v25151_generic_record_quote_candidate_runtime import (  # noqa: E402
    GenericRecordSearch,
)


VERTICAL = "Domain | .in\nType | country-code\nTLD Manager | 999"


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


class V25165ObservedVerticalRuntimeTests(unittest.TestCase):
    def _run(self, content: str, *, observer_failure: bool = False):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            inner = CandidateModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GenericRecordSearch(TASK["question"], phase, content=content)
                for phase in target.PHASES
            }
            patcher = (
                mock.patch.object(
                    target.observer,
                    "observe_vertical_admission",
                    side_effect=RuntimeError("synthetic observer failure"),
                )
                if observer_failure
                else mock.patch.object(
                    target.observer,
                    "observe_vertical_admission",
                    wraps=target.observer.observe_vertical_admission,
                )
            )
            with patcher:
                value = target.run_task(
                    TASK, model=model, searches=searches, limits=limits()
                )
        return inner, target.validate_result(value)

    def test_vertical_candidate_observation_preserves_parent_behavior(self) -> None:
        inner, result = self._run(VERTICAL)
        receipt = result["content_free_receipt"]
        observation = receipt["disposition_observation"]
        parent = result["parent_result"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(receipt["disposition_observer_entry_count"], 1)
        self.assertEqual(receipt["disposition_observer_completed_count"], 1)
        self.assertEqual(receipt["verified_delta_computation_count"], 1)
        self.assertEqual(receipt["verified_delta_cache_reuse_count"], 1)
        self.assertFalse(receipt["disposition_observer_failure_present"])
        self.assertEqual(
            observation["disposition_counts"]["identity_bound_candidate_ready"],
            1,
        )
        self.assertEqual(observation["vertical_block_count"], 1)
        self.assertEqual(
            observation["frozen_vertical_candidate_observation_count"], 1
        )
        self.assertEqual(result["prediction"], parent["prediction"])
        self.assertEqual(result["cost"], parent["cost"])
        self.assertNotEqual(
            result["prediction"], result["production_prediction"]
        )

    def test_pre_identity_reject_is_observed_without_candidate_change(self) -> None:
        _inner, result = self._run(
            "Type | country-code\nTLD Manager | 999"
        )
        receipt = result["content_free_receipt"]
        observation = receipt["disposition_observation"]
        self.assertEqual(
            observation["disposition_counts"]["missing_primary_key_row_reject"],
            1,
        )
        self.assertEqual(
            result["parent_result"]["content_free_receipt"][
                "available_candidate_count"
            ],
            0,
        )
        self.assertEqual(result["prediction"], result["production_prediction"])

    def test_no_gain_has_no_observer_entry_and_preserves_three_forwards(self) -> None:
        inner, result = self._run("Public background without requested fields.")
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(receipt["parent_candidate_revision_entry_count"], 0)
        self.assertEqual(receipt["disposition_observer_entry_count"], 0)
        self.assertEqual(receipt["disposition_observer_completed_count"], 0)
        self.assertEqual(receipt["verified_delta_computation_count"], 0)
        self.assertEqual(receipt["verified_delta_cache_reuse_count"], 0)
        self.assertIsNone(receipt["disposition_observation"])
        self.assertFalse(receipt["disposition_observer_failure_present"])
        self.assertEqual(result["prediction"], result["production_prediction"])

    def test_observer_failure_is_isolated_and_parent_candidate_still_applies(self) -> None:
        inner, result = self._run(VERTICAL, observer_failure=True)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertTrue(receipt["disposition_observer_failure_present"])
        self.assertEqual(receipt["verified_delta_computation_count"], 1)
        self.assertEqual(receipt["verified_delta_cache_reuse_count"], 1)
        self.assertEqual(
            receipt["disposition_observer_failure_type"], "RuntimeError"
        )
        self.assertIsNone(receipt["disposition_observation"])
        self.assertEqual(
            result["parent_result"]["content_free_receipt"]["applied_edit_count"],
            1,
        )
        self.assertNotEqual(
            result["prediction"], result["production_prediction"]
        )

    def test_receipt_is_content_free_and_tamper_fails_closed(self) -> None:
        _inner, result = self._run(VERTICAL)
        receipt = result["content_free_receipt"]
        encoded = json.dumps(receipt, ensure_ascii=False)
        for forbidden in (".in", "999", "Domain", TASK["opaque_id"], "https://"):
            self.assertNotIn(forbidden, encoded)
        for kind in ("count", "parent", "behavior", "credit"):
            changed = copy.deepcopy(result)
            observed = changed["content_free_receipt"]
            if kind == "count":
                observed["disposition_observer_completed_count"] = 0
            elif kind == "parent":
                changed["prediction"] = changed["production_prediction"]
            elif kind == "behavior":
                observed[
                    "observer_reason_buckets_change_admission_routing_prediction_or_budget"
                ] = True
            else:
                observed["entropy_or_information_gain_assigns_signed_credit"] = True
            observed.pop("receipt_payload_sha256")
            observed["receipt_payload_sha256"] = payload_sha256(observed)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_module_is_label_blind_and_observer_does_not_add_effect_surface(self) -> None:
        path = ROOT / "src/deepwide_agent/v25165_observed_vertical_key_value_runtime.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        privileged = {
            str(node.slice.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value
            in {
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
        }
        self.assertEqual(privileged, set())
        self.assertFalse(result := target.__dict__.get("benchmark_launch"))
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
